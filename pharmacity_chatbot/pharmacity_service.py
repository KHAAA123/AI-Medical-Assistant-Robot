from __future__ import annotations

import html
import json
import os
import re
from html.parser import HTMLParser
from typing import Any
from urllib.parse import quote, urlparse

import requests


PHARMACITY_HOME_URL = "https://www.pharmacity.vn"
PHARMACITY_API_BASE = "https://api-gateway.pharmacity.vn"
PHARMACITY_SEARCH_API = f"{PHARMACITY_API_BASE}/pmc-ecm-product/api/public/search/suggest"
PHARMACITY_DETAIL_API = f"{PHARMACITY_API_BASE}/pmc-ecm-product/api/public/product/with-slug"
DEFAULT_TIMEOUT_SECONDS = 20
DEFAULT_GEMINI_TEXT_MODEL = "gemini-2.5-flash"

HTTP_HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": PHARMACITY_HOME_URL,
    "Referer": f"{PHARMACITY_HOME_URL}/",
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
}

INTENT_LABELS = {
    "usage": "cách dùng",
    "benefit": "công dụng",
    "ingredients": "thành phần",
    "warning": "lưu ý",
    "side_effects": "tác dụng phụ",
    "contraindication": "chống chỉ định",
    "price": "giá",
    "summary": "thông tin chính",
}

ATTRIBUTE_CODE_MAP = {
    "thanh-phan": "ingredients",
    "cong-dung": "uses",
    "cach-su-dung": "usage",
    "cach-dung": "usage",
    "huong-dan-su-dung": "usage",
    "than-trong": "warnings",
    "luu-y": "warnings",
    "tac-dung-phu": "side_effects",
    "chong-chi-dinh": "contraindication",
    "tuong-tac-thuoc": "interactions",
    "bao-quan": "storage",
    "thong-tin-san-xuat": "manufacturing",
}

ATTRIBUTE_NAME_MAP = {
    "thanh phan": "ingredients",
    "cong dung": "uses",
    "cach su dung": "usage",
    "cach dung": "usage",
    "huong dan su dung": "usage",
    "than trong": "warnings",
    "luu y": "warnings",
    "tac dung phu": "side_effects",
    "chong chi dinh": "contraindication",
    "tuong tac thuoc": "interactions",
    "bao quan": "storage",
    "thong tin san xuat": "manufacturing",
}

LEADING_FIELD_LABELS = [
    "Thành phần",
    "Công dụng",
    "Cách Sử Dụng",
    "Cách sử dụng",
    "Hướng dẫn sử dụng",
    "Cách dùng",
    "Liều dùng",
    "Thận trọng",
    "Lưu ý",
    "Tác dụng phụ",
    "Chống chỉ định",
    "Tương tác thuốc",
    "Thông tin sản xuất",
]

SEARCH_RELEVANCE_STOPWORDS = {
    "thuoc",
    "san",
    "pham",
    "vien",
    "hop",
    "uong",
    "dung",
    "cach",
    "cong",
    "tac",
    "thanh",
    "phan",
    "hoat",
    "chat",
    "luu",
    "than",
    "trong",
    "khong",
    "ton",
    "tai",
    "nhu",
    "the",
    "nao",
    "bao",
    "nhieu",
    "tien",
}


class VisibleTextParser(HTMLParser):
    block_tags = {
        "br",
        "p",
        "div",
        "section",
        "article",
        "li",
        "ul",
        "ol",
        "table",
        "tr",
        "h1",
        "h2",
        "h3",
        "h4",
    }

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() in self.block_tags:
            self._parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in self.block_tags:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if data and data.strip():
            self._parts.append(data.strip())

    def text(self) -> str:
        return normalize_space("\n".join(self._parts), keep_newlines=True)


def normalize_space(value: Any, *, keep_newlines: bool = False) -> str:
    text = html.unescape(str(value or ""))
    if keep_newlines:
        text = re.sub(r"[ \t\r\f\v]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return "\n".join(line.strip() for line in text.splitlines() if line.strip())
    return re.sub(r"\s+", " ", text).strip()


def strip_html(markup: Any) -> str:
    parser = VisibleTextParser()
    parser.feed(str(markup or ""))
    return parser.text()


def clean_attribute_text(value: Any) -> str:
    text = normalize_space(value, keep_newlines=True)
    for label in LEADING_FIELD_LABELS:
        text = re.sub(rf"^(?:{re.escape(label)}\s*[:：-]?\s*)+", "", text, flags=re.I)
    return normalize_space(text, keep_newlines=True)


def slugify_key(value: str) -> str:
    text = normalize_space(value).lower()
    replacements = {
        "đ": "d",
        "á": "a",
        "à": "a",
        "ả": "a",
        "ã": "a",
        "ạ": "a",
        "ă": "a",
        "ắ": "a",
        "ằ": "a",
        "ẳ": "a",
        "ẵ": "a",
        "ặ": "a",
        "â": "a",
        "ấ": "a",
        "ầ": "a",
        "ẩ": "a",
        "ẫ": "a",
        "ậ": "a",
        "é": "e",
        "è": "e",
        "ẻ": "e",
        "ẽ": "e",
        "ẹ": "e",
        "ê": "e",
        "ế": "e",
        "ề": "e",
        "ể": "e",
        "ễ": "e",
        "ệ": "e",
        "í": "i",
        "ì": "i",
        "ỉ": "i",
        "ĩ": "i",
        "ị": "i",
        "ó": "o",
        "ò": "o",
        "ỏ": "o",
        "õ": "o",
        "ọ": "o",
        "ô": "o",
        "ố": "o",
        "ồ": "o",
        "ổ": "o",
        "ỗ": "o",
        "ộ": "o",
        "ơ": "o",
        "ớ": "o",
        "ờ": "o",
        "ở": "o",
        "ỡ": "o",
        "ợ": "o",
        "ú": "u",
        "ù": "u",
        "ủ": "u",
        "ũ": "u",
        "ụ": "u",
        "ư": "u",
        "ứ": "u",
        "ừ": "u",
        "ử": "u",
        "ữ": "u",
        "ự": "u",
        "ý": "y",
        "ỳ": "y",
        "ỷ": "y",
        "ỹ": "y",
        "ỵ": "y",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def extract_target_intent(query: str) -> str:
    text = normalize_space(query).lower()
    if re.search(r"(tac dung phu|tác dụng phụ)", text):
        return "side_effects"
    if re.search(r"(chong chi dinh|chống chỉ định|khong duoc dung|không được dùng)", text):
        return "contraindication"
    if re.search(r"(luu y|lưu ý|than trong|thận trọng|can than|cẩn thận|mang thai|cho con bu)", text):
        return "warning"
    if re.search(r"\b(uong|uống|dung|dùng|lieu|liều|cach|cách|huong dan|hướng dẫn)\b", text):
        return "usage"
    if re.search(r"(cong dung|công dụng|tac dung|tác dụng|tri gi|trị gì|de lam gi|để làm gì)", text):
        return "benefit"
    if re.search(r"(thanh phan|thành phần|hoat chat|hoạt chất)", text):
        return "ingredients"
    if re.search(r"(gia|giá|bao nhieu|bao nhiêu)", text):
        return "price"
    return "summary"


def extract_search_term(query: str) -> str:
    text = normalize_space(query)
    patterns = [
        r"(?i)\b(cho toi hoi|cho tôi hỏi|toi muon biet|tôi muốn biết|hay cho biet|hãy cho biết)\b",
        r"(?i)\b(thuoc|thuốc|san pham|sản phẩm|vien|viên|hop|hộp)\b",
        r"(?i)\b(uong nhu the nao|uống như thế nào|uong the nao|uống thế nào)\b",
        r"(?i)\b(cach su dung|cách sử dụng|cach dung|cách dùng|huong dan su dung|hướng dẫn sử dụng)\b",
        r"(?i)\b(lieu dung|liều dùng|dung may vien|dùng mấy viên)\b",
        r"(?i)\b(co cong dung gi|có công dụng gì|cong dung gi|công dụng gì|co tac dung gi|có tác dụng gì)\b",
        r"(?i)\b(thanh phan gi|thành phần gì|thanh phan|thành phần|hoat chat|hoạt chất)\b",
        r"(?i)\b(tac dung phu|tác dụng phụ|chong chi dinh|chống chỉ định|luu y|lưu ý|than trong|thận trọng)\b",
        r"(?i)\b(gia bao nhieu|giá bao nhiêu|bao nhieu tien|bao nhiêu tiền)\b",
        r"(?i)\b(la gi|là gì|nhu the nao|như thế nào|ra sao|khong|không)\b",
    ]
    for pattern in patterns:
        text = re.sub(pattern, " ", text)
    text = re.sub(r"[?!.:,;\"'“”‘’()\[\]{}]+", " ", text)
    text = normalize_space(text)
    if len(text) >= 2:
        return text
    return normalize_space(query)


def products_from_search_payload(payload: dict[str, Any], *, limit: int = 4) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else {}
    items = data.get("items") if isinstance(data, dict) else []
    products: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items if isinstance(items, list) else []:
        if not isinstance(item, dict):
            continue
        slug = normalize_space(item.get("slug"))
        name = normalize_space(item.get("name"))
        sku = normalize_space(item.get("sku"))
        if not slug or not name:
            continue
        key = slug or sku or name.lower()
        if key in seen:
            continue
        seen.add(key)
        products.append(
            {
                "index": len(products) + 1,
                "name": name,
                "image_url": normalize_space(item.get("image")),
                "detail_url": f"{PHARMACITY_HOME_URL}/{slug}.html",
                "sku": sku,
                "slug": slug,
                "unit": normalize_space(item.get("unit")),
            }
        )
        if len(products) >= limit:
            break
    return products


def relevant_search_tokens(search_term: str) -> set[str]:
    slug = slugify_key(search_term)
    tokens = set()
    for token in slug.split("-"):
        if len(token) < 3 or token.isdigit() or token in SEARCH_RELEVANCE_STOPWORDS:
            continue
        tokens.add(token)
    return tokens


def filter_relevant_products(products: list[dict[str, Any]], search_term: str) -> list[dict[str, Any]]:
    tokens = relevant_search_tokens(search_term)
    if not tokens:
        return products
    relevant: list[dict[str, Any]] = []
    for product in products:
        haystack = slugify_key(
            " ".join(
                [
                    normalize_space(product.get("name")),
                    normalize_space(product.get("slug")),
                    normalize_space(product.get("sku")),
                ]
            )
        )
        if any(token in haystack for token in tokens):
            relevant.append(product)
    return relevant


def search_products(query: str, *, original_query: str | None = None, target_intent: str | None = None) -> dict[str, Any]:
    original = normalize_space(original_query or query)
    intent = target_intent or extract_target_intent(original)
    search_term = extract_search_term(query)
    payload = fetch_search_payload(search_term)
    products = filter_relevant_products(products_from_search_payload(payload), search_term)

    if not products and search_term != normalize_space(query):
        search_term = normalize_space(query)
        payload = fetch_search_payload(search_term)
        products = filter_relevant_products(products_from_search_payload(payload), search_term)

    return {
        "ok": True,
        "original_query": original,
        "search_term": search_term,
        "target_intent": intent,
        "products": products,
        "source": PHARMACITY_SEARCH_API,
    }


def fetch_search_payload(search_term: str) -> dict[str, Any]:
    params = {
        "keyword": search_term,
        "platform": 1,
        "limit": 4,
        "index": 1,
        "refresh": "true",
    }
    response = requests.get(
        PHARMACITY_SEARCH_API,
        params=params,
        headers=HTTP_HEADERS,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def slug_from_product(product: dict[str, Any]) -> str:
    slug = normalize_space(product.get("slug"))
    if slug:
        return slug
    detail_url = normalize_space(product.get("detail_url"))
    parsed = urlparse(detail_url)
    if not parsed.netloc.endswith("pharmacity.vn"):
        raise ValueError("detail_url phải thuộc pharmacity.vn")
    path = parsed.path.strip("/")
    if not path.endswith(".html"):
        raise ValueError("detail_url Pharmacity không hợp lệ")
    return path.removesuffix(".html")


def source_url_from_slug(slug: str) -> str:
    return f"{PHARMACITY_HOME_URL}/{quote(slug)}.html"


def fetch_detail_payload(slug: str) -> dict[str, Any]:
    response = requests.get(
        f"{PHARMACITY_DETAIL_API}/{quote(slug)}",
        params={"limit": 15, "include_related": "false"},
        headers=HTTP_HEADERS,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()


def extract_fields_from_item(item: dict[str, Any]) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "name": normalize_space(item.get("name")),
        "sku": normalize_space(item.get("sku")),
        "brand": normalize_space(item.get("brand_name")),
        "category": normalize_space(item.get("category_name")),
        "product_type": normalize_space(item.get("product_type_name")),
        "is_prescription_drug": bool(item.get("is_prescription_drug")),
        "is_drug": bool(item.get("is_drug")),
        "registration": item.get("registration") or {},
        "updated_at": normalize_space(item.get("updated_at")),
    }
    variants = item.get("variants")
    if isinstance(variants, list) and variants:
        sale_variant = next((variant for variant in variants if variant.get("is_sale_unit")), variants[0])
        price = sale_variant.get("price")
        unit_name = normalize_space(sale_variant.get("unit_name") or sale_variant.get("unit"))
        if price:
            fields["price"] = f"{int(price):,} VND".replace(",", ".") + (f"/{unit_name}" if unit_name else "")

    for group in item.get("attributes") or []:
        for attribute in group.get("items") or []:
            code = slugify_key(attribute.get("code") or "")
            name = normalize_space(attribute.get("name"))
            raw_value = attribute.get("value")
            if isinstance(raw_value, dict):
                raw_value = raw_value.get("value")
            value = clean_attribute_text(strip_html(raw_value))
            if not value:
                continue
            key = ATTRIBUTE_CODE_MAP.get(code) or ATTRIBUTE_NAME_MAP.get(slugify_key(name).replace("-", " "))
            key = key or code or slugify_key(name) or f"field_{len(fields)}"
            if key in fields and isinstance(fields[key], str):
                fields[key] = normalize_space(f"{fields[key]}\n{value}", keep_newlines=True)
            else:
                fields[key] = value

    return {key: value for key, value in fields.items() if value not in ("", None, {})}


def extract_fields_from_html(page_html: str) -> dict[str, Any]:
    text = strip_html(page_html)
    fields: dict[str, Any] = {}
    title_match = re.search(r"<title[^>]*>(.*?)</title>", page_html, flags=re.I | re.S)
    if title_match:
        fields["name"] = normalize_space(strip_html(title_match.group(1)).replace("| Pharmacity", ""))
    headings = [
        ("ingredients", r"Thành phần"),
        ("uses", r"Công dụng"),
        ("usage", r"(?:Cách Sử Dụng|Hướng dẫn sử dụng|Cách dùng)"),
        ("warnings", r"(?:Thận trọng|Lưu ý)"),
        ("side_effects", r"Tác dụng phụ"),
        ("contraindication", r"Chống chỉ định"),
        ("manufacturing", r"Thông tin sản xuất"),
    ]
    for index, (key, pattern) in enumerate(headings):
        next_patterns = [next_pattern for _, next_pattern in headings[index + 1 :]]
        stop_pattern = "|".join(next_patterns) if next_patterns else r"Hỏi & Đáp|Về Pharmacity"
        match = re.search(
            rf"({pattern})\s+(.*?)(?=\n(?:{stop_pattern})\b|$)",
            text,
            flags=re.I | re.S,
        )
        if match:
            fields[key] = clip_text(match.group(2), 1400)
    return fields


def detail_fields_for_product(product: dict[str, Any]) -> tuple[dict[str, Any], str]:
    slug = slug_from_product(product)
    source_url = source_url_from_slug(slug)
    try:
        payload = fetch_detail_payload(slug)
        item = payload.get("data", {}).get("item") or {}
        fields = extract_fields_from_item(item)
        if fields:
            return fields, source_url
    except requests.HTTPError:
        pass

    response = requests.get(source_url, headers=HTTP_HEADERS, timeout=DEFAULT_TIMEOUT_SECONDS)
    response.raise_for_status()
    fields = extract_fields_from_html(response.text)
    fields.setdefault("name", normalize_space(product.get("name")))
    fields.setdefault("sku", normalize_space(product.get("sku")))
    return fields, source_url


def answer_product_question(original_query: str, target_intent: str, product: dict[str, Any]) -> dict[str, Any]:
    fields, source_url = detail_fields_for_product(product)
    product_name = normalize_space(fields.get("name") or product.get("name") or "sản phẩm")
    intent = target_intent or extract_target_intent(original_query)
    answer = summarize_with_gemini(original_query, intent, product_name, fields) or build_fallback_answer(
        intent,
        product_name,
        fields,
    )
    return {
        "ok": True,
        "answer": answer,
        "source_url": source_url,
        "product": {
            "name": product_name,
            "sku": fields.get("sku") or product.get("sku") or "",
            "detail_url": source_url,
        },
        "extracted_fields": fields,
    }


def summarize_with_gemini(
    original_query: str,
    target_intent: str,
    product_name: str,
    fields: dict[str, Any],
) -> str:
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        return ""
    try:
        from google import genai
    except ImportError:
        return ""

    compact_fields = json.dumps(fields, ensure_ascii=False, indent=2)
    prompt = (
        "Bạn là trợ lý tra cứu thuốc. Chỉ dùng dữ liệu Pharmacity dưới đây, không dùng kiến thức ngoài.\n"
        "Trả lời tiếng Việt ngắn gọn tối đa 4 câu, đúng trọng tâm câu hỏi.\n"
        "Không chẩn đoán, không kê đơn, không tự điều chỉnh liều. Nếu thuốc kê đơn hoặc dữ liệu có cảnh báo, "
        "nhắc hỏi bác sĩ hoặc dược sĩ.\n\n"
        f"Câu hỏi gốc: {original_query}\n"
        f"Mục tiêu: {INTENT_LABELS.get(target_intent, target_intent)}\n"
        f"Sản phẩm: {product_name}\n"
        f"Dữ liệu Pharmacity:\n{compact_fields[:9000]}"
    )
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=os.environ.get("GEMINI_MODEL", DEFAULT_GEMINI_TEXT_MODEL),
            contents=prompt,
        )
        return normalize_space(getattr(response, "text", ""))
    except Exception:
        return ""


def build_fallback_answer(target_intent: str, product_name: str, fields: dict[str, Any]) -> str:
    field_plan = {
        "usage": [("Cách dùng", "usage")],
        "benefit": [("Công dụng", "uses")],
        "ingredients": [("Thành phần", "ingredients")],
        "warning": [("Lưu ý", "warnings"), ("Chống chỉ định", "contraindication")],
        "side_effects": [("Tác dụng phụ", "side_effects"), ("Lưu ý", "warnings")],
        "contraindication": [("Chống chỉ định", "contraindication"), ("Lưu ý", "warnings")],
        "price": [("Giá tham khảo", "price")],
        "summary": [("Công dụng", "uses"), ("Thành phần", "ingredients"), ("Cách dùng", "usage")],
    }
    pieces = [f"Theo dữ liệu Pharmacity, {product_name}:"]
    for label, key in field_plan.get(target_intent, field_plan["summary"]):
        value = fields.get(key)
        if value:
            pieces.append(f"{label}: {clip_text(value, 520)}")
    if len(pieces) == 1:
        pieces.append("mình chỉ lấy được thông tin cơ bản, chưa thấy mục chi tiết phù hợp với câu hỏi.")
    if fields.get("is_prescription_drug"):
        pieces.append("Đây là thuốc kê đơn, vui lòng dùng theo chỉ định bác sĩ và hỏi dược sĩ nếu cần.")
    else:
        pieces.append("Thông tin chỉ để tham khảo, không thay thế tư vấn của bác sĩ hoặc dược sĩ.")
    return " ".join(pieces)


def clip_text(value: Any, limit: int) -> str:
    text = normalize_space(value)
    if len(text) <= limit:
        return text
    clipped = text[:limit].rsplit(" ", 1)[0].rstrip(".,;: ")
    return f"{clipped}..."
