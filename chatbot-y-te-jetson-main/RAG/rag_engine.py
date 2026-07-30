from __future__ import annotations

import argparse
import json
import math
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


HOTLINE = "1900 6765"
MIN_RRF_SCORE = 0.10
MIN_SCORE_TOKEN_COVERAGE = 0.25
MIN_STRONG_TOKEN_COVERAGE = 0.60
OUT_OF_SCOPE_ANSWER = (
    "Mình chỉ hỗ trợ thông tin Bệnh viện Hạnh Phúc và tra cứu sản phẩm thuốc. "
    "Bạn có thể hỏi về khoa, bác sĩ, lịch khám, dịch vụ bệnh viện hoặc một sản phẩm thuốc cụ thể."
)
INSUFFICIENT_CONTEXT_ANSWER = (
    "Mình chưa tìm thấy thông tin đủ tin cậy trong dữ liệu bệnh viện hiện có. "
    f"Vui lòng liên hệ hotline {HOTLINE} để được xác nhận."
)
UNKNOWN_MARKERS = (
    "chưa xác minh",
    "chưa công bố",
    "chưa có dữ liệu",
    "requires_hospital_confirmation",
    "partially_verified",
)

SUPPORTED_DOMAIN_TERMS = (
    "benh vien",
    "hanh phuc",
    "bac si",
    "bs ",
    "phong kham",
    "dat lich",
    "lich kham",
    "gio kham",
    "goi kham",
    "dia chi",
    "hotline",
    "cap cuu",
    "noi tru",
    "ngoai tru",
    "bao hiem",
    "bai do xe",
    "phong vip",
    "nha thuoc",
    "lay thuoc",
    "khay thuoc",
    "arduino",
    "robot",
)

AMBIGUOUS_DOMAIN_TERMS = (
    "khoa",
    "goi dich vu",
    "dich vu",
    "chi phi",
    "gia",
    "tien ich",
)

QUERY_STOPWORDS = {
    "ai",
    "bao",
    "bang",
    "benh",
    "bi",
    "cac",
    "cho",
    "chi",
    "co",
    "cua",
    "duoc",
    "dich",
    "gi",
    "hanh",
    "hay",
    "hoc",
    "khong",
    "khoa",
    "la",
    "lam",
    "may",
    "mot",
    "nao",
    "nhung",
    "o",
    "tai",
    "the",
    "thi",
    "tinh",
    "toi",
    "thong",
    "trong",
    "tu",
    "va",
    "ve",
    "vu",
    "vien",
    "voi",
    "phuc",
}

ENTITY_TYPE_LABELS = {
    "doctor": "Bác sĩ",
    "doctor_schedule": "Lịch khám",
    "package": "Gói dịch vụ",
    "department": "Khoa/đơn vị",
    "faq": "Hỏi đáp",
    "policy": "Chính sách",
    "facility": "Tiện ích/cơ sở",
    "hospital_info": "Thông tin bệnh viện",
}


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFD", text)
    no_marks = "".join(ch for ch in normalized if unicodedata.category(ch) != "Mn")
    return no_marks.replace("đ", "d").replace("Đ", "D")


def normalize_text(text: Any) -> str:
    if text is None:
        return ""
    text = strip_accents(str(text)).lower()
    return re.sub(r"\s+", " ", text).strip()


def tokenize(text: Any) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize_text(text))


def meaningful_tokens(text: Any) -> set[str]:
    return {token for token in tokenize(text) if len(token) > 1 and token not in QUERY_STOPWORDS}


def normalized_phrase_in_text(phrase: str, text: str) -> bool:
    return f" {normalize_text(phrase)} " in f" {normalize_text(text)} "


def unique_sentences(*parts: Any) -> str:
    output: list[str] = []
    seen: list[str] = []
    for part in parts:
        if not part:
            continue
        for sentence in re.split(r"(?<=[.!?])\s+|\n+", str(part).strip()):
            sentence = sentence.strip()
            normalized = re.sub(r"[^a-z0-9]+", " ", normalize_text(sentence)).strip()
            if not normalized:
                continue
            if normalized in seen:
                continue
            if any(
                (normalized in previous or previous in normalized)
                and min(len(normalized), len(previous)) / max(len(normalized), len(previous)) >= 0.85
                for previous in seen
            ):
                continue
            output.append(sentence)
            seen.append(normalized)
    return " ".join(output).strip()


def flatten_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(flatten_value(v) for v in value.values())
    if isinstance(value, list):
        return " ".join(flatten_value(item) for item in value)
    return str(value)


def format_vnd(value: Any) -> str | None:
    if value is None or value == "":
        return None
    try:
        amount = int(value)
    except (TypeError, ValueError):
        return None
    return f"{amount:,}".replace(",", ".") + " VND"


def has_uncertain_data(entity: "RagEntity") -> bool:
    haystack = normalize_text(
        " ".join(
            [
                entity.verification_status,
                entity.answer_context,
                flatten_value(entity.raw.get("generated_fields")),
            ]
        )
    )
    return any(normalize_text(marker) in haystack for marker in UNKNOWN_MARKERS)


@dataclass(frozen=True)
class RagEntity:
    entity_id: str
    entity_type: str
    canonical_name: str
    aliases: tuple[str, ...]
    retrieval_text: str
    answer_context: str
    metadata: dict[str, Any]
    raw: dict[str, Any]
    verification_status: str = ""
    source_url: str = ""


@dataclass
class SearchResult:
    entity: RagEntity
    score: float
    rank: int
    reasons: list[str] = field(default_factory=list)
    expanded_from: str | None = None

    @property
    def needs_confirmation(self) -> bool:
        return has_uncertain_data(self.entity)


class BM25Index:
    def __init__(self, entities: list[RagEntity], *, k1: float = 1.5, b: float = 0.75):
        self.entities = entities
        self.k1 = k1
        self.b = b
        self.doc_tokens = [tokenize(entity.retrieval_text) for entity in entities]
        self.doc_lens = [len(tokens) for tokens in self.doc_tokens]
        self.avgdl = sum(self.doc_lens) / max(len(self.doc_lens), 1)
        self.term_freqs = [Counter(tokens) for tokens in self.doc_tokens]
        self.doc_freqs: Counter[str] = Counter()
        for tokens in self.doc_tokens:
            self.doc_freqs.update(set(tokens))

    def score(self, query: str) -> list[tuple[int, float]]:
        query_terms = tokenize(query)
        if not query_terms:
            return []

        scores: list[tuple[int, float]] = []
        n_docs = max(len(self.entities), 1)
        for idx, freqs in enumerate(self.term_freqs):
            score = 0.0
            doc_len = self.doc_lens[idx] or 1
            for term in query_terms:
                tf = freqs.get(term, 0)
                if not tf:
                    continue
                df = self.doc_freqs.get(term, 0)
                idf = math.log(1 + (n_docs - df + 0.5) / (df + 0.5))
                denom = tf + self.k1 * (1 - self.b + self.b * doc_len / max(self.avgdl, 1))
                score += idf * (tf * (self.k1 + 1)) / denom
            if score > 0:
                scores.append((idx, score))
        return sorted(scores, key=lambda item: item[1], reverse=True)


class RagEngine:
    def __init__(self, jsonl_path: str | Path, *, enable_dense: bool = True):
        self.jsonl_path = Path(jsonl_path)
        self.entities = load_entities(self.jsonl_path)
        self.by_id = {entity.entity_id: entity for entity in self.entities}
        self.bm25 = BM25Index(self.entities)
        self.alias_index = self._build_alias_index()
        self.domain_alias_tokens = meaningful_tokens(" ".join(self.alias_index))
        self.dense = self._load_dense() if enable_dense else None

    def _load_dense(self):
        """Nạp tầng dense tùy chọn; None nếu thiếu lib/artifact (fallback lexical)."""
        try:
            from RAG.dense_retrieval import load_dense_retriever
        except Exception:
            try:
                from dense_retrieval import load_dense_retriever  # chạy trực tiếp trong RAG/
            except Exception:
                return None
        try:
            return load_dense_retriever(self.jsonl_path)
        except Exception:
            return None

    @property
    def dense_enabled(self) -> bool:
        return self.dense is not None

    def _build_alias_index(self) -> dict[str, set[str]]:
        aliases: dict[str, set[str]] = defaultdict(set)
        for entity in self.entities:
            values = [entity.canonical_name, *entity.aliases]
            for value in values:
                norm = normalize_text(value)
                if norm:
                    aliases[norm].add(entity.entity_id)
        return aliases

    def classify_intent(self, query: str) -> str:
        q = normalize_text(query)
        if any(
            term in q
            for term in (
                "sua xe",
                "ve may bay",
                "lich chieu phim",
                "lop hoc piano",
                "khach san du lich",
                "mua dien thoai",
            )
        ):
            return "out_of_scope"
        if any(
            term in q
            for term in (
                "lay thuoc",
                "cap thuoc",
                "nhan thuoc",
                "arduino",
                "khay thuoc",
                "mo khay",
                "robot",
            )
        ):
            return "hardware_confirmation"
        if any(
            term in q
            for term in (
                "chan doan",
                "ke don",
                "uong thuoc gi",
                "toi bi",
                "trieu chung",
                "khang sinh",
                "lieu dung",
                "tu dieu tri",
                "thuoc huyet ap",
            )
        ):
            return "medical_boundary"
        if any(term in q for term in ("lich", "dat lich", "kham luc nao", "gio kham")):
            return "schedule"
        if any(term in q for term in ("gia", "phi", "bao nhieu tien", "chi phi")):
            return "price"
        if any(term in q for term in ("bac si", "bs", "doctor")):
            return "doctor"
        if any(term in q for term in ("phong vip", "phong noi tru", "bai do xe", "nha thuoc", "tien ich")):
            return "facility"
        if any(term in q for term in ("khoa", "phong", "trung tam")):
            return "department"
        if any(term in q for term in ("dia chi", "hotline", "gio lam viec", "cap cuu")):
            return "hospital_info"
        return "hospital_lookup"

    def is_query_in_scope(self, query: str, *, intent: str | None = None) -> bool:
        resolved_intent = intent or self.classify_intent(query)
        if resolved_intent == "out_of_scope":
            return False
        if resolved_intent in {"hardware_confirmation", "medical_boundary"}:
            return True
        normalized_query = normalize_text(query)
        if not normalized_query:
            return False
        if any(normalized_phrase_in_text(term, normalized_query) for term in SUPPORTED_DOMAIN_TERMS):
            return True
        if self._exact_rank(query):
            return True
        if any(normalized_phrase_in_text(term, normalized_query) for term in AMBIGUOUS_DOMAIN_TERMS):
            ambiguous_tokens = meaningful_tokens(" ".join(AMBIGUOUS_DOMAIN_TERMS))
            distinctive_tokens = meaningful_tokens(query) - ambiguous_tokens
            return len(distinctive_tokens.intersection(self.domain_alias_tokens)) >= 1
        return False

    def result_confidence(self, query: str, result: SearchResult) -> tuple[bool, float]:
        query_terms = meaningful_tokens(query)
        entity_terms = meaningful_tokens(result.entity.retrieval_text)
        coverage = len(query_terms.intersection(entity_terms)) / max(len(query_terms), 1)
        has_alias_evidence = any(reason.startswith("alias:") for reason in result.reasons)
        accepted = (
            has_alias_evidence
            or (result.score >= MIN_RRF_SCORE and coverage >= MIN_SCORE_TOKEN_COVERAGE)
            or (len(query_terms) >= 2 and coverage >= MIN_STRONG_TOKEN_COVERAGE)
        )
        return accepted, coverage

    def search(
        self,
        query: str,
        *,
        intent: str | None = None,
        filters: dict[str, str] | None = None,
        top_k: int = 8,
        expand: bool = True,
        use_dense: bool = True,
    ) -> list[SearchResult]:
        intent = intent or self.classify_intent(query)
        filters = filters or {}

        rankings = {
            "exact": self._exact_rank(query),
            "bm25": self._bm25_rank(query),
            "field": self._field_rank(query, intent),
        }
        if use_dense:
            dense_ranking = self._dense_rank(query)
            if dense_ranking:
                rankings["dense"] = dense_ranking
        fused = self._rrf(rankings)
        boosted = self._apply_intent_boosts(fused, intent)
        filtered = self._apply_filters(boosted, filters)

        results = [
            SearchResult(entity=self.by_id[entity_id], score=score, rank=rank + 1, reasons=reasons)
            for rank, (entity_id, score, reasons) in enumerate(filtered[: max(top_k * 2, top_k)])
        ]

        if expand:
            results = self._expand_results(results, limit=max(top_k * 2, top_k))

        results = sorted(results, key=lambda item: (-item.score, item.entity.entity_id))
        for idx, result in enumerate(results[:top_k], start=1):
            result.rank = idx
        return results[:top_k]

    def answer(self, query: str, *, voice: bool = False, top_k: int = 5) -> dict[str, Any]:
        intent = self.classify_intent(query)
        if intent == "hardware_confirmation":
            return {
                "intent": intent,
                "status": "hardware_confirmation",
                "grounded": False,
                "answer": (
                    "Mình đã hiểu yêu cầu lấy thuốc. Để an toàn, vui lòng xác nhận trên màn hình "
                    "trước khi hệ thống gửi lệnh đến thiết bị."
                ),
                "requires_hardware_confirmation": True,
                "contexts": [],
            }

        if intent == "medical_boundary":
            boundary = (
                "Mình chỉ hỗ trợ tra cứu và hướng dẫn thông tin bệnh viện, không chẩn đoán "
                "hoặc kê đơn. Nếu bạn có triệu chứng cần đánh giá, hãy liên hệ bác sĩ hoặc "
                f"gọi hotline {HOTLINE} để được hướng dẫn đặt lịch."
            )
            return {
                "intent": intent,
                "status": "medical_boundary",
                "grounded": False,
                "answer": boundary,
                "requires_hardware_confirmation": False,
                "contexts": [],
            }

        if not self.is_query_in_scope(query, intent=intent):
            return {
                "intent": "out_of_scope",
                "status": "out_of_scope",
                "grounded": False,
                "answer": OUT_OF_SCOPE_ANSWER,
                "requires_hardware_confirmation": False,
                "contexts": [],
            }

        results = self.search(query, intent=intent, top_k=top_k)
        confident = False
        if results:
            confident, _coverage = self.result_confidence(query, results[0])
        if not results or not confident:
            return {
                "intent": intent,
                "status": "insufficient_context",
                "grounded": False,
                "answer": INSUFFICIENT_CONTEXT_ANSWER,
                "requires_hardware_confirmation": False,
                "contexts": [],
            }

        answer = build_grounded_answer(query, results, voice=voice)
        return {
            "intent": intent,
            "status": "grounded",
            "grounded": True,
            "answer": answer,
            "requires_hardware_confirmation": False,
            "contexts": [result_to_dict(result) for result in results],
        }

    def _exact_rank(self, query: str) -> list[tuple[str, float, list[str]]]:
        q = normalize_text(query)
        matches: dict[str, tuple[float, list[str]]] = {}
        for alias, entity_ids in self.alias_index.items():
            if not alias:
                continue
            if alias == q:
                boost = 12.0
            elif len(alias) >= 5 and alias in q:
                boost = 8.0
            elif len(q) >= 5 and q in alias:
                boost = 5.0
            else:
                continue
            for entity_id in sorted(entity_ids):
                old_score, old_reasons = matches.get(entity_id, (0.0, []))
                matches[entity_id] = (max(old_score, boost), old_reasons + [f"alias:{alias}"])
        return sorted(
            ((entity_id, score, reasons) for entity_id, (score, reasons) in matches.items()),
            key=lambda item: (-item[1], item[0]),
        )

    def _bm25_rank(self, query: str) -> list[tuple[str, float, list[str]]]:
        return [
            (self.entities[idx].entity_id, score, ["bm25"])
            for idx, score in self.bm25.score(query)[:50]
        ]

    def _dense_rank(self, query: str) -> list[tuple[str, float, list[str]]]:
        """Xếp hạng theo embeddings; rỗng nếu tầng dense không khả dụng."""
        if not self.dense:
            return []
        try:
            ranked = self.dense.rank(query, top_k=50)
        except Exception:
            return []
        return [(entity_id, score, reasons) for entity_id, score, reasons in ranked if entity_id in self.by_id]

    def _field_rank(self, query: str, intent: str) -> list[tuple[str, float, list[str]]]:
        query_terms = set(tokenize(query))
        if not query_terms:
            return []

        scored: list[tuple[str, float, list[str]]] = []
        for entity in self.entities:
            score = 0.0
            reasons: list[str] = []
            fields = {
                "canonical_name": entity.raw.get("canonical_name"),
                "department": entity.raw.get("department"),
                "category": entity.raw.get("category"),
                "conditions": entity.raw.get("conditions_treated"),
                "recommended_for": entity.raw.get("recommended_for"),
                "services": entity.raw.get("services") or entity.raw.get("service_lines"),
            }
            weights = {
                "canonical_name": 3.0,
                "department": 2.0,
                "category": 1.7,
                "conditions": 1.5,
                "recommended_for": 1.5,
                "services": 1.4,
            }
            for name, value in fields.items():
                overlap = query_terms.intersection(tokenize(flatten_value(value)))
                if overlap:
                    score += len(overlap) * weights[name]
                    reasons.append(f"field:{name}")

            if intent == "schedule" and entity.entity_type == "doctor_schedule":
                score += 2.5
                reasons.append("intent:schedule")
            elif intent == "price" and entity.raw.get("price_vnd"):
                score += 2.0
                reasons.append("intent:price")
            elif intent == "doctor" and entity.entity_type == "doctor":
                score += 1.8
                reasons.append("intent:doctor")
            elif intent == "department" and entity.entity_type == "department":
                score += 1.8
                reasons.append("intent:department")
            elif intent == "hospital_info" and entity.entity_type in {"hospital_info", "faq"}:
                score += 1.5
                reasons.append("intent:hospital_info")

            if score:
                scored.append((entity.entity_id, score, reasons))
        return sorted(scored, key=lambda item: (-item[1], item[0]))

    def _rrf(
        self,
        rankings: dict[str, list[tuple[str, float, list[str]]]],
        *,
        k: int = 60,
    ) -> list[tuple[str, float, list[str]]]:
        scores: dict[str, float] = defaultdict(float)
        reasons: dict[str, list[str]] = defaultdict(list)
        for name, ranking in rankings.items():
            for rank, (entity_id, raw_score, raw_reasons) in enumerate(ranking, start=1):
                scores[entity_id] += 1 / (k + rank)
                if name == "exact":
                    scores[entity_id] += min(raw_score / 100, 0.2)
                elif name == "dense":
                    # Cosine [0,1]: cộng bonus tỉ lệ độ tương đồng để dense có thể
                    # phá thế hòa rank của các case ngữ nghĩa gần nhau (case 1/2/4).
                    scores[entity_id] += min(max(raw_score, 0.0) * 0.15, 0.15)
                reasons[entity_id].extend(raw_reasons)
        return sorted(
            ((entity_id, score, sorted(set(reasons[entity_id]))) for entity_id, score in scores.items()),
            key=lambda item: (-item[1], item[0]),
        )

    def _apply_intent_boosts(
        self,
        fused: list[tuple[str, float, list[str]]],
        intent: str,
    ) -> list[tuple[str, float, list[str]]]:
        preferred_weights = {
            "schedule": {"doctor_schedule": 0.14, "doctor": 0.02},
            "price": {"package": 0.10, "facility": 0.03, "faq": 0.03},
            "package": {"package": 0.10},
            "doctor": {"doctor": 0.10, "doctor_schedule": 0.04},
            "department": {"department": 0.10, "doctor": 0.02},
            "facility": {"facility": 0.10, "faq": 0.04, "policy": 0.03},
            "policy": {"policy": 0.10, "faq": 0.04, "facility": 0.02},
            "faq": {"faq": 0.10, "policy": 0.03, "facility": 0.03},
            "hospital_info": {"hospital_info": 0.10, "faq": 0.04, "policy": 0.03, "facility": 0.02},
        }.get(intent, {})

        boosted = []
        for entity_id, score, reasons in fused:
            entity = self.by_id[entity_id]
            boost = preferred_weights.get(entity.entity_type, 0.0)
            if boost:
                score += boost
                reasons = [*reasons, f"boost:{intent}"]
            boosted.append((entity_id, score, reasons))
        return sorted(boosted, key=lambda item: (-item[1], item[0]))

    def _apply_filters(
        self,
        scored: list[tuple[str, float, list[str]]],
        filters: dict[str, str],
    ) -> list[tuple[str, float, list[str]]]:
        if not filters:
            return scored
        output = []
        for entity_id, score, reasons in scored:
            entity = self.by_id[entity_id]
            keep = True
            for key, expected in filters.items():
                actual = normalize_text(entity.metadata.get(key) or entity.raw.get(key))
                if normalize_text(expected) not in actual:
                    keep = False
                    break
            if keep:
                output.append((entity_id, score, reasons))
        return output

    def _expand_results(self, results: list[SearchResult], *, limit: int) -> list[SearchResult]:
        by_id: dict[str, SearchResult] = {result.entity.entity_id: result for result in results}
        for result in list(results):
            for related_id in related_entity_ids(result.entity):
                related = self.by_id.get(related_id)
                if not related:
                    continue
                expanded_score = result.score * 0.72
                existing = by_id.get(related_id)
                if existing and existing.score >= expanded_score:
                    continue
                by_id[related_id] = SearchResult(
                    entity=related,
                    score=expanded_score,
                    rank=0,
                    reasons=[*result.reasons, "entity_expansion"],
                    expanded_from=result.entity.entity_id,
                )
        return sorted(by_id.values(), key=lambda item: (-item.score, item.entity.entity_id))[:limit]


def load_entities(path: str | Path) -> list[RagEntity]:
    entities = []
    seen_ids: set[str] = set()
    with Path(path).open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            raw = json.loads(line)
            entity_id = raw.get("entity_id")
            if not entity_id:
                raise ValueError(f"Missing entity_id at line {line_no}")
            if entity_id in seen_ids:
                raise ValueError(f"Duplicate entity_id {entity_id!r} at line {line_no}")
            seen_ids.add(entity_id)
            entities.append(build_entity(raw))
    return entities


def build_entity(raw: dict[str, Any]) -> RagEntity:
    aliases = tuple(str(item) for item in raw.get("aliases") or [])
    metadata = {
        "entity_type": raw.get("entity_type"),
        "department": raw.get("department"),
        "category": raw.get("category"),
        "verification_status": raw.get("verification_status"),
        "source_url": raw.get("source_url"),
    }
    retrieval_parts = [
        raw.get("canonical_name"),
        aliases,
        raw.get("search_text"),
        raw.get("summary_text"),
        raw.get("department"),
        raw.get("category"),
        raw.get("conditions_treated"),
        raw.get("procedures_performed"),
        raw.get("service_lines"),
        raw.get("services"),
        raw.get("recommended_for"),
        raw.get("question"),
        raw.get("answer"),
    ]
    return RagEntity(
        entity_id=raw["entity_id"],
        entity_type=raw.get("entity_type", "unknown"),
        canonical_name=raw.get("canonical_name", raw["entity_id"]),
        aliases=aliases,
        retrieval_text=" ".join(flatten_value(part) for part in retrieval_parts if part),
        answer_context=build_answer_context(raw),
        metadata=metadata,
        raw=raw,
        verification_status=raw.get("verification_status", ""),
        source_url=raw.get("source_url", ""),
    )


def build_answer_context(raw: dict[str, Any]) -> str:
    entity_type = raw.get("entity_type")
    name = raw.get("canonical_name", "")
    summary = raw.get("summary_text", "")

    if entity_type == "doctor":
        years = raw.get("years_experience")
        years_text = f", kinh nghiệm khoảng {years} năm" if years else ""
        return unique_sentences(
            f"{name} thuộc khoa {raw.get('department', 'chưa rõ')}{years_text}. "
            f"Thế mạnh/định hướng: {', '.join(raw.get('recommended_for') or raw.get('clinical_focus') or [])}. "
            f"{summary}"
        )

    if entity_type == "doctor_schedule":
        return unique_sentences(
            f"{name}: {raw.get('schedule')} "
            f"Đặt lịch qua hotline {raw.get('booking_hotline') or HOTLINE}. "
            f"{raw.get('fee_note') or ''}"
        )

    if entity_type == "package":
        price = format_vnd(raw.get("price_vnd"))
        includes = ", ".join((raw.get("includes") or [])[:8])
        return unique_sentences(
            f"{name} thuộc nhóm {raw.get('category', 'dịch vụ')}. "
            f"Giá: {price or 'chưa có dữ liệu xác minh'}. "
            f"Bao gồm: {includes}.",
            summary,
        )

    if entity_type == "department":
        return unique_sentences(
            f"{name}. Dịch vụ chính: {', '.join(raw.get('services') or [])}. "
            f"Vị trí/tầng: {raw.get('floor')}.",
            summary,
        )

    if entity_type == "hospital_info":
        working_hours = raw.get("working_hours") if isinstance(raw.get("working_hours"), dict) else {}
        outpatient_hours = working_hours.get("outpatient") or ""
        emergency_hours = working_hours.get("emergency") or raw.get("emergency") or ""
        return unique_sentences(
            f"{name}.",
            f"Địa chỉ: {raw.get('address')}.",
            f"Hotline/đặt lịch: {raw.get('booking_hotline') or raw.get('hotline') or HOTLINE}.",
            f"Giờ khám ngoại trú: {outpatient_hours}." if outpatient_hours else "",
            f"Cấp cứu: {emergency_hours}." if emergency_hours else "",
        )

    if entity_type == "faq":
        return unique_sentences(raw.get("question"), raw.get("answer"))

    if entity_type == "policy":
        return f"{name}: {raw.get('content') or summary}".strip()

    if entity_type == "facility":
        return f"{name}: {raw.get('description') or summary}".strip()

    return summary or flatten_value(raw)


def related_entity_ids(entity: RagEntity) -> list[str]:
    raw = entity.raw
    related: list[str] = []
    for key in ("related_packages", "related_doctors"):
        value = raw.get(key) or []
        for item in value:
            if isinstance(item, dict) and item.get("entity_id"):
                related.append(item["entity_id"])
            elif isinstance(item, str):
                related.append(item)

    if raw.get("doctor_entity_id"):
        related.append(raw["doctor_entity_id"])
    return list(dict.fromkeys(related))


def build_grounded_answer(query: str, results: list[SearchResult], *, voice: bool = False) -> str:
    top = results[0]
    entity = top.entity
    parts = [entity.answer_context]

    related_bits = []
    for result in results[1:4]:
        if result.expanded_from == entity.entity_id:
            label = ENTITY_TYPE_LABELS.get(result.entity.entity_type, result.entity.entity_type)
            related_bits.append(f"{label}: {result.entity.canonical_name}")
    if related_bits and not voice:
        parts.append("Thông tin liên quan: " + "; ".join(related_bits) + ".")

    if top.needs_confirmation:
        current_text = " ".join(parts)
        if HOTLINE in current_text:
            parts.append("Một phần thông tin cần được xác nhận lại trực tiếp với bệnh viện.")
        else:
            parts.append(f"Một phần thông tin cần xác nhận lại với bệnh viện qua hotline {HOTLINE}.")

    if voice:
        compact = unique_sentences(*parts)
        sentences = re.split(r"(?<=[.!?])\s+", compact)
        return " ".join(sentences[:3]).strip()
    return unique_sentences(*parts)


def result_to_dict(result: SearchResult) -> dict[str, Any]:
    entity = result.entity
    return {
        "rank": result.rank,
        "score": round(result.score, 4),
        "entity_id": entity.entity_id,
        "entity_type": entity.entity_type,
        "canonical_name": entity.canonical_name,
        "verification_status": entity.verification_status,
        "source_url": entity.source_url,
        "needs_confirmation": result.needs_confirmation,
        "expanded_from": result.expanded_from,
        "reasons": sorted(set(result.reasons)),
        "answer_context": entity.answer_context,
    }


_ENGINE_CACHE: dict[Path, RagEngine] = {}


def get_engine(jsonl_path: str | Path | None = None) -> RagEngine:
    path = Path(jsonl_path) if jsonl_path else default_jsonl_path()
    path = path.resolve()
    if path not in _ENGINE_CACHE:
        _ENGINE_CACHE[path] = RagEngine(path)
    return _ENGINE_CACHE[path]


def rag_search(
    query: str,
    *,
    intent: str | None = None,
    filters: dict[str, str] | None = None,
    top_k: int = 5,
    jsonl_path: str | Path | None = None,
) -> dict[str, Any]:
    """Backend tool contract for realtime voice agents.

    The realtime agent should call this before answering hospital-data questions.
    It returns short, grounded contexts and metadata; it does not trigger hardware.
    """
    engine = get_engine(jsonl_path)
    resolved_intent = intent or engine.classify_intent(query)
    results = engine.search(query, intent=resolved_intent, filters=filters, top_k=top_k)
    return {
        "query": query,
        "intent": resolved_intent,
        "results": [result_to_dict(result) for result in results],
    }


def rag_answer(
    query: str,
    *,
    voice: bool = False,
    top_k: int = 5,
    jsonl_path: str | Path | None = None,
) -> dict[str, Any]:
    """Return a safe, grounded answer for text or compact voice output."""
    return get_engine(jsonl_path).answer(query, voice=voice, top_k=top_k)


def default_jsonl_path() -> Path:
    return Path(__file__).resolve().parent / "hanhphuc.jsonl"


def main(argv: Iterable[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="Search the Hanh Phuc hospital RAG dataset.")
    parser.add_argument("query", nargs="*", help="Vietnamese user query.")
    parser.add_argument("--jsonl", default=str(default_jsonl_path()), help="Path to hanhphuc.jsonl.")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--voice", action="store_true", help="Return compact voice-oriented answer.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    query = " ".join(args.query).strip()
    if not query:
        parser.error("Please provide a query.")

    engine = RagEngine(args.jsonl)
    payload = engine.answer(query, voice=args.voice, top_k=args.top_k)
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(payload["answer"])
        if payload["contexts"]:
            print("\nNguồn phù hợp:")
            for context in payload["contexts"]:
                print(
                    f"- #{context['rank']} {context['canonical_name']} "
                    f"({context['entity_type']}, score={context['score']})"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
