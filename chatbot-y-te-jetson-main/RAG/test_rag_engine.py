import unittest
from collections import Counter

from RAG.rag_engine import RagEngine, default_jsonl_path, rag_answer, rag_search


class RagEngineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = RagEngine(default_jsonl_path())

    def test_dataset_shape(self):
        self.assertEqual(len(self.engine.entities), 223)
        counts = Counter(entity.entity_type for entity in self.engine.entities)
        self.assertEqual(counts["doctor"], 59)
        self.assertEqual(counts["doctor_schedule"], 59)
        self.assertEqual(counts["package"], 43)
        self.assertEqual(counts["department"], 23)
        self.assertEqual(counts["faq"], 20)
        self.assertEqual(counts["policy"], 9)
        self.assertEqual(counts["facility"], 8)
        self.assertEqual(counts["hospital_info"], 2)

    def test_address_retrieval(self):
        result = self.engine.search("Bệnh viện Hạnh Phúc ở đâu?", top_k=1)[0]
        self.assertEqual(result.entity.entity_id, "hospital_hanh-phuc-main")

    def test_schedule_requires_confirmation(self):
        result = self.engine.search("lịch khám bác sĩ Nhật Nam", top_k=1)[0]
        self.assertEqual(result.entity.entity_id, "schedule_ts-bs-nguyen-nhat-nam")
        self.assertTrue(result.needs_confirmation)

    def test_package_price_retrieval(self):
        result = self.engine.search("Gói IVF Advanced giá bao nhiêu?", top_k=1)[0]
        self.assertEqual(result.entity.entity_id, "package_goi-ivf-advanced")
        answer = self.engine.answer("Gói IVF Advanced giá bao nhiêu?")
        self.assertIn("129.000.000 VND", answer["answer"])

    def test_medical_boundary(self):
        answer = self.engine.answer("tôi bị đau bụng nên uống thuốc gì")
        self.assertEqual(answer["intent"], "medical_boundary")
        self.assertIn("không chẩn đoán hoặc kê đơn", answer["answer"])
        self.assertEqual(answer["contexts"], [])

    def test_hardware_requires_confirmation(self):
        answer = self.engine.answer("tôi muốn lấy thuốc")
        self.assertTrue(answer["requires_hardware_confirmation"])
        self.assertEqual(answer["contexts"], [])

    def test_tool_contracts(self):
        search_payload = rag_search("Khoa Nhi tiếp nhận vấn đề gì?", top_k=2)
        self.assertIn("results", search_payload)
        self.assertGreaterEqual(len(search_payload["results"]), 1)

        voice_payload = rag_answer("phòng VIP có gì?", voice=True)
        self.assertIn("Phòng VIP", voice_payload["answer"])
        self.assertNotIn("Một phần thông tin cần xác nhận", voice_payload["answer"])

    def test_intent_classification(self):
        cases = {
            "lịch khám bác sĩ Nam": "schedule",
            "gói IVF giá bao nhiêu": "price",
            "thông tin bác sĩ Tài": "doctor",
            "khoa nhi ở đâu": "department",
            "địa chỉ bệnh viện": "hospital_info",
            "tôi muốn lấy thuốc": "hardware_confirmation",
            "tôi bị sốt nên uống thuốc gì": "medical_boundary",
            "bệnh viện có sửa xe không": "out_of_scope",
        }
        for query, expected in cases.items():
            self.assertEqual(self.engine.classify_intent(query), expected, query)

    def test_alias_matching(self):
        # Tên viết tắt/alias vẫn truy ra đúng bác sĩ.
        result = self.engine.search("BS Hoàng Ngọc Hải thuộc khoa nào?", top_k=1)[0]
        self.assertEqual(result.entity.entity_id, "doctor_bs-cki-hoang-ngoc-hai")

    def test_accent_invariance(self):
        # Engine chuẩn hóa bỏ dấu => câu có dấu và không dấu cho cùng top-1.
        with_accent = self.engine.search("Bệnh viện Hạnh Phúc ở đâu?", top_k=1)[0]
        no_accent = self.engine.search("Benh vien Hanh Phuc o dau?", top_k=1)[0]
        self.assertEqual(with_accent.entity.entity_id, no_accent.entity.entity_id)

    def test_out_of_scope_gate(self):
        answer = self.engine.answer("bệnh viện có bán vé máy bay không?")
        self.assertEqual(answer["intent"], "out_of_scope")
        self.assertEqual(answer["status"], "out_of_scope")
        self.assertFalse(answer["grounded"])
        self.assertEqual(answer["contexts"], [])
        self.assertNotIn("1900 6765", answer["answer"])

    def test_general_knowledge_queries_are_rejected(self):
        cases = (
            "Thủ đô nước Pháp là gì?",
            "Ai là tổng thống Mỹ?",
            "Hôm nay thời tiết thế nào?",
            "2 cộng 2 bằng mấy?",
            "Dịch vụ cloud nào tốt?",
            "Khoa học máy tính là gì?",
        )
        for query in cases:
            with self.subTest(query=query):
                answer = self.engine.answer(query)
                self.assertEqual(answer["status"], "out_of_scope")
                self.assertFalse(answer["grounded"])
                self.assertEqual(answer["contexts"], [])
                self.assertNotIn("1900 6765", answer["answer"])
                self.assertNotIn("tầm soát", answer["answer"].lower())

    def test_in_scope_low_confidence_query_does_not_return_unrelated_entity(self):
        answer = self.engine.answer("Bệnh viện có wifi không?")
        self.assertEqual(answer["status"], "insufficient_context")
        self.assertFalse(answer["grounded"])
        self.assertEqual(answer["contexts"], [])
        self.assertNotIn("bãi đỗ xe", answer["answer"].lower())

    def test_grounded_payload_and_contact_details_are_not_repeated(self):
        answer = self.engine.answer("Bệnh viện Hạnh Phúc ở đâu?")
        self.assertEqual(answer["status"], "grounded")
        self.assertTrue(answer["grounded"])
        self.assertEqual(answer["answer"].count("1900 6765"), 1)
        self.assertEqual(answer["answer"].count("18 Đại lộ Bình Dương"), 1)

    def test_empty_query_is_safe(self):
        # Không được crash với query rỗng/toàn khoảng trắng.
        self.assertEqual(self.engine.search("   ", top_k=3), [])
        answer = self.engine.answer("")
        self.assertEqual(answer["contexts"], [])

    def test_use_dense_flag_lexical_path(self):
        # use_dense=False luôn chạy (đường lexical), không phụ thuộc artifact dense.
        result = self.engine.search("Gói IVF Advanced giá bao nhiêu?", top_k=1, use_dense=False)[0]
        self.assertEqual(result.entity.entity_id, "package_goi-ivf-advanced")

    def test_dense_attribute_present(self):
        # Thuộc tính dense luôn tồn tại; None khi thiếu lib/artifact (fallback an toàn).
        self.assertTrue(hasattr(self.engine, "dense"))
        self.assertEqual(self.engine.dense_enabled, self.engine.dense is not None)


if __name__ == "__main__":
    unittest.main()
