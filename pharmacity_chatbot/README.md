# Pharmacity Medicine Chatbot

Standalone chatbot tra cứu thuốc từ Pharmacity, tách riêng khỏi app bệnh viện/Arduino hiện tại.

## Chạy local

```powershell
cd pharmacity_chatbot
pip install -r requirements.txt
python server.py
```

Mở `http://127.0.0.1:8010`.

## API

`POST /api/pharmacity/search`

```json
{ "query": "Panadol uống thế nào?" }
```

Trả về tối đa 4 sản phẩm đầu từ Pharmacity kèm tên, ảnh, `detail_url`, `sku`.

`POST /api/pharmacity/answer`

```json
{
  "original_query": "Panadol uống thế nào?",
  "target_intent": "usage",
  "product": {
    "name": "Panadol Extra Optizorb",
    "detail_url": "https://www.pharmacity.vn/panadol-extra-with-optizorb-hop-12-vi-x-10-vien.html",
    "slug": "panadol-extra-with-optizorb-hop-12-vi-x-10-vien",
    "sku": "P09747"
  }
}
```

Backend lấy dữ liệu chi tiết từ API/trang Pharmacity, trích `thành phần`, `công dụng`, `cách dùng`, `lưu ý`, `chống chỉ định`, sau đó trả lời ngắn. Nếu có `GEMINI_API_KEY`, hệ thống dùng Gemini text để tóm tắt; nếu không có key hoặc AI lỗi, hệ thống dùng fallback từ dữ liệu crawl được.

## Gemini Live

File `gemini_live_tools.py` có sẵn `pharmacity_search_function_declaration()` và instruction ngắn để import khi cần nối module này vào Gemini Live của app chính.

## Kiểm thử

```powershell
cd pharmacity_chatbot
python -m unittest discover -s tests -v
```
