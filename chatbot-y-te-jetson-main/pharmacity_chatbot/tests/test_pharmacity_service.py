import unittest

from pharmacity_chatbot.pharmacity_service import (
    extract_fields_from_item,
    extract_search_term,
    extract_target_intent,
    filter_relevant_products,
    products_from_search_payload,
)


class PharmacityServiceTests(unittest.TestCase):
    def test_extract_search_term_keeps_medicine_name(self):
        self.assertEqual(extract_search_term("Panadol uống thế nào?"), "Panadol")
        self.assertEqual(extract_search_term("Thuốc Ramifix 2,5 Savi có công dụng gì?"), "Ramifix 2 5 Savi")

    def test_extract_target_intent(self):
        self.assertEqual(extract_target_intent("Panadol uống thế nào?"), "usage")
        self.assertEqual(extract_target_intent("Ramifix có thành phần gì?"), "ingredients")
        self.assertEqual(extract_target_intent("Hapacol có tác dụng phụ không?"), "side_effects")

    def test_products_from_search_payload_limits_to_four(self):
        payload = {
            "data": {
                "items": [
                    {"sku": f"P{i}", "name": f"Thuốc {i}", "slug": f"thuoc-{i}", "image": f"https://image/{i}.jpg"}
                    for i in range(1, 7)
                ]
            }
        }
        products = products_from_search_payload(payload)
        self.assertEqual(len(products), 4)
        self.assertEqual(products[0]["detail_url"], "https://www.pharmacity.vn/thuoc-1.html")
        self.assertEqual(products[0]["image_url"], "https://image/1.jpg")

    def test_filter_relevant_products_drops_search_fallback_noise(self):
        products = [
            {"name": "Dung dịch dùng ngoài Sovasol", "slug": "dung-dich-dung-ngoai-sovasol", "sku": "P1"},
            {"name": "Panadol Extra Optizorb", "slug": "panadol-extra-optizorb", "sku": "P2"},
        ]
        self.assertEqual(filter_relevant_products(products, "Panadol"), [products[1]])
        self.assertEqual(filter_relevant_products(products, "zzzxxyy thuốc không tồn tại 987654"), [])

    def test_extract_fields_from_api_item(self):
        item = {
            "name": "Ramifix 2,5 Savi (Hộp 3 vĩ x 10 viên)",
            "sku": "P30155",
            "brand_name": "Savi",
            "category_name": "Thuốc tim mạch, huyết áp",
            "product_type_name": "Thuốc kê đơn",
            "is_drug": True,
            "is_prescription_drug": True,
            "variants": [{"unit_name": "Hộp", "price": 90000, "is_sale_unit": True}],
            "attributes": [
                {
                    "items": [
                        {"code": "thanh-phan", "name": "Thành phần", "value": {"value": "<h2>Thành phần</h2><p>Ramipril 2.5mg</p>"}},
                        {"code": "cong-dung", "name": "Công dụng", "value": {"value": "<p>Tăng huyết áp.</p>"}},
                        {"code": "cach-su-dung", "name": "Cách Sử Dụng", "value": {"value": "<p>Dùng đường uống.</p>"}},
                    ]
                }
            ],
        }
        fields = extract_fields_from_item(item)
        self.assertTrue(fields["is_prescription_drug"])
        self.assertEqual(fields["price"], "90.000 VND/Hộp")
        self.assertIn("Ramipril", fields["ingredients"])
        self.assertIn("Tăng huyết áp", fields["uses"])
        self.assertIn("Dùng đường uống", fields["usage"])


if __name__ == "__main__":
    unittest.main()
