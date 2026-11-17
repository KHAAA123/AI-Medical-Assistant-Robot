# Hanh Phuc RAG Engine

Module này triển khai nền RAG local nhẹ cho `hanhphuc.jsonl`, bám theo `docs/PROJECT_GOALS.md`: trả lời dựa trên dữ liệu bệnh viện, ưu tiên đúng và rõ, không chẩn đoán/kê đơn, và không tự kích hoạt Arduino.

## Thành phần đã có

- Loader JSONL theo từng entity, không chunk mù.
- `retrieval_text` cho tìm kiếm và `answer_context` ngắn cho câu trả lời.
- Metadata chuẩn: `entity_type`, `department`, `category`, `verification_status`, `source_url`.
- Exact/alias matching cho tên bác sĩ, khoa, gói khám, hotline và tiện ích.
- BM25 local không cần dependency ngoài.
- Reciprocal Rank Fusion giữa exact, BM25 và field matching.
- Entity expansion: bác sĩ, lịch khám, gói dịch vụ và liên kết liên quan.
- Safety gates cho câu hỏi y tế vượt phạm vi và lệnh lấy thuốc/Arduino.

## Cách chạy nhanh

```powershell
python -m RAG.rag_engine "Bệnh viện Hạnh Phúc ở đâu?"
python -m RAG.rag_engine "lịch khám bác sĩ Nhật Nam" --voice
python -m RAG.rag_engine "Gói IVF Advanced giá bao nhiêu?" --json
python -m unittest RAG.test_rag_engine -v
```

## Contract cho backend voice

Realtime voice agent nên gọi `rag_search()` trước khi trả lời câu hỏi về bệnh viện.

```python
from RAG.rag_engine import rag_search, rag_answer

search_payload = rag_search("lịch khám bác sĩ Nhật Nam", top_k=5)
answer_payload = rag_answer("lịch khám bác sĩ Nhật Nam", voice=True)
```

`rag_search()` trả về context đã xếp hạng:

- `entity_id`
- `entity_type`
- `canonical_name`
- `verification_status`
- `source_url`
- `needs_confirmation`
- `answer_context`

`rag_answer()` trả về:

- `intent`
- `answer`
- `requires_hardware_confirmation`
- `contexts`

Nếu `requires_hardware_confirmation = true`, UI chỉ được mở màn hình xác nhận. Không gửi lệnh Arduino tự động từ voice.

## Luồng voice đề xuất

1. Browser mở cloud realtime speech-to-speech qua WebRTC.
2. UI giữ trạng thái theo `docs/STYLE_GUIDE.md`: `idle`, `listening`, `processing`, `speaking`, `error`.
3. Khi người dùng hỏi về bệnh viện, realtime agent gọi backend tool `rag_search(query, intent, filters)`.
4. Agent chỉ trả lời dựa trên `answer_context` đã trả về.
5. Nếu context có `needs_confirmation`, câu trả lời phải nhắc xác nhận qua hotline `1900 6765`.
6. Nếu voice yêu cầu lấy thuốc, backend trả `requires_hardware_confirmation = true`; frontend mở màn hình xác nhận trước khi gửi lệnh thiết bị.

## Nâng cấp tiếp theo

MVP hiện chạy được bằng Python chuẩn. Khi cần chất lượng cao hơn, có thể cắm thêm:

- Dense embeddings: BGE-M3 hoặc multilingual-E5.
- Vector store local: FAISS hoặc Chroma.
- Reranker: BGE reranker multilingual cho top 20 kết quả.
- Evaluation: Recall@5, MRR/nDCG và groundedness/faithfulness.

