"""Tầng dense retrieval nhẹ, tùy chọn cho RAG engine.

Thiết kế cho edge (Jetson Nano B01):
- Embeddings của các entity được precompute offline bằng `build_embeddings.py`
  và lưu ra `embeddings.npy` + `dense_meta.json`.
- Runtime chỉ nhúng MỘT câu query ngắn qua mô hình ONNX (1 forward pass), rồi
  tính cosine similarity với ma trận entity đã chuẩn hóa.
- Mọi dependency (numpy, onnxruntime, tokenizers) đều import lazy. Nếu thiếu bất
  kỳ thứ gì (lib hoặc file artifact), `load_dense_retriever()` trả về None và RAG
  engine tự rơi về hybrid lexical — giống pattern optional-dependency của
  openpyxl/pyserial trong server.py.

File artifact (mặc định nằm cùng thư mục với dataset):
- `embeddings.npy`     : ma trận float32 [n_entities, dim], đã L2-normalize.
- `dense_meta.json`    : {"entity_ids": [...], "model_dir": "...", "query_prefix":
                          "query: ", "pooling": "mean", "normalize": true,
                          "max_length": 256, "dim": 384}
- `<model_dir>/model.onnx` và `<model_dir>/tokenizer.json`.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


DEFAULT_EMBEDDINGS_NAME = "embeddings.npy"
DEFAULT_META_NAME = "dense_meta.json"


class DenseRetriever:
    """Mã hóa query qua ONNX và xếp hạng entity theo cosine similarity."""

    def __init__(
        self,
        embeddings: "Any",
        entity_ids: list[str],
        session: "Any",
        tokenizer: "Any",
        *,
        query_prefix: str = "",
        pooling: str = "mean",
        normalize: bool = True,
        max_length: int = 256,
    ) -> None:
        self._embeddings = embeddings  # np.ndarray [n, dim], đã normalize
        self.entity_ids = entity_ids
        self._session = session
        self._tokenizer = tokenizer
        self.query_prefix = query_prefix
        self.pooling = pooling
        self.normalize = normalize
        self.max_length = max_length
        self._input_names = {inp.name for inp in session.get_inputs()}

    def encode_query(self, query: str) -> "Any":
        import numpy as np

        text = f"{self.query_prefix}{query}" if self.query_prefix else query
        encoding = self._tokenizer.encode(text)
        ids = encoding.ids[: self.max_length]
        mask = encoding.attention_mask[: self.max_length]

        input_ids = np.array([ids], dtype=np.int64)
        attention_mask = np.array([mask], dtype=np.int64)
        feeds: dict[str, Any] = {}
        if "input_ids" in self._input_names:
            feeds["input_ids"] = input_ids
        if "attention_mask" in self._input_names:
            feeds["attention_mask"] = attention_mask
        if "token_type_ids" in self._input_names:
            feeds["token_type_ids"] = np.zeros_like(input_ids)

        outputs = self._session.run(None, feeds)
        token_embeddings = outputs[0]  # [1, seq, dim]
        vector = self._pool(token_embeddings, attention_mask)
        if self.normalize:
            norm = np.linalg.norm(vector) or 1.0
            vector = vector / norm
        return vector.astype(np.float32)

    def _pool(self, token_embeddings: "Any", attention_mask: "Any") -> "Any":
        import numpy as np

        if self.pooling == "cls":
            return token_embeddings[0, 0]
        # mean pooling có tính attention mask (mặc định cho e5 / sbert).
        mask = attention_mask[0][:, None].astype(np.float32)
        summed = (token_embeddings[0] * mask).sum(axis=0)
        counts = mask.sum(axis=0)
        counts = np.clip(counts, a_min=1e-9, a_max=None)
        return summed / counts

    def rank(self, query: str, *, top_k: int = 50) -> list[tuple[str, float, list[str]]]:
        """Trả về [(entity_id, cosine_score, ["dense"])] đã sắp giảm dần."""
        import numpy as np

        vector = self.encode_query(query)
        scores = self._embeddings @ vector  # cosine vì cả hai đã normalize
        order = np.argsort(-scores)[: max(top_k, 1)]
        ranked: list[tuple[str, float, list[str]]] = []
        for idx in order:
            score = float(scores[idx])
            if score <= 0:
                continue
            ranked.append((self.entity_ids[int(idx)], score, ["dense"]))
        return ranked


def load_dense_retriever(
    jsonl_path: str | Path | None = None,
    *,
    artifacts_dir: str | Path | None = None,
) -> DenseRetriever | None:
    """Nạp DenseRetriever nếu đủ điều kiện, ngược lại trả None (fallback an toàn).

    artifacts_dir mặc định là thư mục chứa dataset jsonl (tức RAG/).
    """
    base = Path(artifacts_dir) if artifacts_dir else _default_dir(jsonl_path)
    embeddings_path = base / DEFAULT_EMBEDDINGS_NAME
    meta_path = base / DEFAULT_META_NAME
    if not embeddings_path.is_file() or not meta_path.is_file():
        return None

    try:
        import numpy as np  # noqa: F401
        import onnxruntime as ort
        from tokenizers import Tokenizer
    except Exception:
        return None

    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        entity_ids = list(meta.get("entity_ids") or [])
        if not entity_ids:
            return None

        model_dir = Path(meta.get("model_dir") or base)
        if not model_dir.is_absolute():
            model_dir = (base / model_dir).resolve()
        model_path = model_dir / "model.onnx"
        tokenizer_path = model_dir / "tokenizer.json"
        if not model_path.is_file() or not tokenizer_path.is_file():
            return None

        embeddings = np.load(embeddings_path)
        if embeddings.shape[0] != len(entity_ids):
            return None

        providers = _select_providers(ort)
        session = ort.InferenceSession(str(model_path), providers=providers)
        tokenizer = Tokenizer.from_file(str(tokenizer_path))

        return DenseRetriever(
            embeddings=embeddings,
            entity_ids=entity_ids,
            session=session,
            tokenizer=tokenizer,
            query_prefix=str(meta.get("query_prefix") or ""),
            pooling=str(meta.get("pooling") or "mean"),
            normalize=bool(meta.get("normalize", True)),
            max_length=int(meta.get("max_length") or 256),
        )
    except Exception:
        # Bất kỳ lỗi nạp nào cũng coi như không có dense → fallback lexical.
        return None


def _select_providers(ort: "Any") -> list[str]:
    available = set(ort.get_available_providers())
    preferred = ["CUDAExecutionProvider", "CPUExecutionProvider"]
    return [provider for provider in preferred if provider in available] or ["CPUExecutionProvider"]


def _default_dir(jsonl_path: str | Path | None) -> Path:
    if jsonl_path:
        return Path(jsonl_path).resolve().parent
    return Path(__file__).resolve().parent
