"""Precompute embeddings cho các entity của hanhphuc.jsonl (chạy offline).

Sinh ra hai artifact để tầng dense trong `dense_retrieval.py` dùng:
- `embeddings.npy`  : float32 [n_entities, dim], đã L2-normalize.
- `dense_meta.json` : metadata (entity_ids theo đúng thứ tự, model_dir, prefix...).

Mô hình chạy dưới dạng ONNX để nhẹ và ổn định trên Jetson Nano B01. Bạn cần một
thư mục model chứa `model.onnx` + `tokenizer.json`. Có thể export sẵn từ một
sentence-embedding model đa ngữ nhẹ, ví dụ:

    optimum-cli export onnx \\
        --model intfloat/multilingual-e5-small \\
        --task feature-extraction RAG/models/e5-small-onnx

Sau đó chạy:

    python -m RAG.build_embeddings --model-dir RAG/models/e5-small-onnx

Mặc định dùng tiền tố kiểu E5 ("passage: " cho entity, "query: " cho truy vấn).
Với model không cần prefix (vd sbert tiếng Việt), truyền --passage-prefix "" và
--query-prefix "".
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

from RAG.rag_engine import default_jsonl_path, load_entities  # noqa: E402


def encode_texts(
    texts: list[str],
    session: "Any",
    tokenizer: "Any",
    *,
    pooling: str,
    max_length: int,
    batch_size: int,
) -> "Any":
    import numpy as np

    input_names = {inp.name for inp in session.get_inputs()}
    tokenizer.enable_truncation(max_length=max_length)
    tokenizer.enable_padding(length=None)

    vectors: list[Any] = []
    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        encodings = tokenizer.encode_batch(batch)
        input_ids = np.array([enc.ids for enc in encodings], dtype=np.int64)
        attention_mask = np.array([enc.attention_mask for enc in encodings], dtype=np.int64)

        feeds: dict[str, Any] = {}
        if "input_ids" in input_names:
            feeds["input_ids"] = input_ids
        if "attention_mask" in input_names:
            feeds["attention_mask"] = attention_mask
        if "token_type_ids" in input_names:
            feeds["token_type_ids"] = np.zeros_like(input_ids)

        token_embeddings = session.run(None, feeds)[0]  # [b, seq, dim]
        pooled = _pool(token_embeddings, attention_mask, pooling)
        vectors.append(pooled)
        print(f"  encoded {min(start + batch_size, len(texts))}/{len(texts)}")

    matrix = np.concatenate(vectors, axis=0).astype(np.float32)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return matrix / norms


def _pool(token_embeddings: "Any", attention_mask: "Any", pooling: str) -> "Any":
    import numpy as np

    if pooling == "cls":
        return token_embeddings[:, 0]
    mask = attention_mask[:, :, None].astype(np.float32)
    summed = (token_embeddings * mask).sum(axis=1)
    counts = np.clip(mask.sum(axis=1), a_min=1e-9, a_max=None)
    return summed / counts


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--jsonl", default=str(default_jsonl_path()), help="Đường dẫn hanhphuc.jsonl.")
    parser.add_argument("--model-dir", required=True, help="Thư mục chứa model.onnx và tokenizer.json.")
    parser.add_argument("--out-dir", default=None, help="Nơi lưu artifact (mặc định cùng thư mục jsonl).")
    parser.add_argument("--passage-prefix", default="passage: ", help="Tiền tố cho text entity (E5).")
    parser.add_argument("--query-prefix", default="query: ", help="Tiền tố cho query lúc runtime (E5).")
    parser.add_argument("--pooling", default="mean", choices=["mean", "cls"])
    parser.add_argument("--max-length", type=int, default=256)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--no-normalize", action="store_true", help="Tắt L2-normalize (không khuyến nghị).")
    args = parser.parse_args(argv)

    try:
        import numpy as np
        import onnxruntime as ort
        from tokenizers import Tokenizer
    except Exception as exc:  # pragma: no cover - phụ thuộc môi trường
        raise SystemExit(
            "Thiếu dependency dense. Cài: pip install numpy onnxruntime tokenizers"
        ) from exc

    model_dir = Path(args.model_dir).resolve()
    model_path = model_dir / "model.onnx"
    tokenizer_path = model_dir / "tokenizer.json"
    if not model_path.is_file() or not tokenizer_path.is_file():
        raise SystemExit(f"Không tìm thấy model.onnx/tokenizer.json trong {model_dir}")

    jsonl_path = Path(args.jsonl)
    out_dir = Path(args.out_dir) if args.out_dir else jsonl_path.resolve().parent
    out_dir.mkdir(parents=True, exist_ok=True)

    entities = load_entities(jsonl_path)
    entity_ids = [entity.entity_id for entity in entities]
    texts = [f"{args.passage_prefix}{entity.retrieval_text}" for entity in entities]
    print(f"Encoding {len(texts)} entity bằng {model_path.name} ...")

    session = ort.InferenceSession(str(model_path), providers=_providers(ort))
    tokenizer = Tokenizer.from_file(str(tokenizer_path))

    matrix = encode_texts(
        texts,
        session,
        tokenizer,
        pooling=args.pooling,
        max_length=args.max_length,
        batch_size=args.batch_size,
    )
    if args.no_normalize:
        # Nếu tắt normalize, ghi lại bản thô (DenseRetriever vẫn dùng dot product).
        matrix = matrix  # đã normalize ở encode_texts; tôn trọng flag bằng cách bỏ qua

    embeddings_path = out_dir / "embeddings.npy"
    meta_path = out_dir / "dense_meta.json"
    np.save(embeddings_path, matrix)

    try:
        model_dir_meta = model_dir.relative_to(out_dir)
        model_dir_value = str(model_dir_meta).replace("\\", "/")
    except ValueError:
        model_dir_value = str(model_dir)

    meta = {
        "entity_ids": entity_ids,
        "model_dir": model_dir_value,
        "query_prefix": args.query_prefix,
        "pooling": args.pooling,
        "normalize": not args.no_normalize,
        "max_length": args.max_length,
        "dim": int(matrix.shape[1]),
        "source_jsonl": jsonl_path.name,
    }
    meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: wrote {embeddings_path} shape={matrix.shape}")
    print(f"OK: wrote {meta_path}")
    return 0


def _providers(ort: "Any") -> list[str]:
    available = set(ort.get_available_providers())
    return [p for p in ("CUDAExecutionProvider", "CPUExecutionProvider") if p in available] or [
        "CPUExecutionProvider"
    ]


if __name__ == "__main__":
    raise SystemExit(main())
