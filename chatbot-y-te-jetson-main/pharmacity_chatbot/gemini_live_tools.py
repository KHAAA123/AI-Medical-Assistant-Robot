from __future__ import annotations


def pharmacity_search_function_declaration() -> dict:
    return {
        "name": "pharmacity_search",
        "description": (
            "Tra cứu thuốc hoặc sản phẩm thuốc trên Pharmacity. Gọi tool này khi người dùng hỏi "
            "về tên thuốc, cách dùng, công dụng, thành phần, lưu ý, chống chỉ định, tác dụng phụ hoặc giá thuốc."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Câu hỏi tiếng Việt nguyên văn của người dùng, ví dụ: Panadol uống thế nào?",
                }
            },
            "required": ["query"],
        },
    }


def build_pharmacity_instruction() -> str:
    return (
        "Khi người dùng hỏi về thuốc hoặc sản phẩm thuốc, hãy gọi tool pharmacity_search trước. "
        "Sau khi tool trả danh sách sản phẩm, chờ người dùng chọn đúng sản phẩm trên giao diện. "
        "Không tự chẩn đoán, không kê đơn, không tự thay đổi liều. "
        "Câu trả lời cuối phải ngắn, dựa trên dữ liệu Pharmacity đã crawl, và nhắc hỏi bác sĩ hoặc dược sĩ "
        "khi là thuốc kê đơn hoặc có cảnh báo."
    )
