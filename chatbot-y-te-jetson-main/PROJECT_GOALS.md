# Mục tiêu dự án: Webapp Trợ lý Y tế Thông minh

## 1. Tầm nhìn tổng quát

Dự án hướng tới xây dựng một webapp trợ lý y tế thông minh, đóng vai trò là điểm tương tác trung tâm giữa người dùng, dữ liệu bệnh viện, AI hội thoại, giọng nói tiếng Việt và thiết bị ngoại vi Arduino.

Hệ thống không chỉ là một chatbot hỏi đáp đơn lẻ, mà là một trải nghiệm thống nhất giúp bệnh nhân hoặc người nhà:

- Tra cứu thông tin bệnh viện nhanh chóng.
- Hỏi đáp bằng tiếng Việt tự nhiên.
- Tương tác bằng giọng nói theo hướng speak-to-speak realtime.
- Nhận hướng dẫn rõ ràng về khoa, bác sĩ, lịch khám và dịch vụ.
- Điều khiển hoặc kích hoạt cơ chế ngoại vi như demo lấy thuốc thông qua Arduino sau khi đã xác nhận.

Mục tiêu quan trọng nhất của dự án là tạo ra một webapp dễ dùng, trả lời đúng theo dữ liệu bệnh viện, giao diện đáng tin cậy và đủ rõ ràng để người dùng phổ thông có thể thao tác mà không cần được hướng dẫn nhiều.

## 2. Người dùng chính

Người dùng chính của hệ thống là bệnh nhân và người nhà bệnh nhân. Vì vậy, toàn bộ sản phẩm cần ưu tiên sự rõ ràng, dễ đọc, dễ thao tác và ít gây nhầm lẫn.

Khi thiết kế tính năng hoặc giao diện, cần giả định rằng người dùng có thể:

- Không quen với công nghệ phức tạp.
- Cần tra cứu nhanh trong môi trường bệnh viện.
- Muốn nhận câu trả lời ngắn gọn, trực tiếp, bằng tiếng Việt dễ hiểu.
- Có thể tương tác trên màn hình cảm ứng hoặc kiosk gắn với robot y tế.
- Cần được cảnh báo rõ khi hệ thống không đủ dữ liệu hoặc không chắc chắn.

## 3. Phạm vi MVP

Phiên bản đầu tiên của webapp tập trung vào các năng lực cốt lõi sau:

### AI Chatbot

Chatbot là lớp hội thoại chính, cho phép người dùng đặt câu hỏi bằng tiếng Việt về thông tin bệnh viện, quy trình cơ bản và các dịch vụ liên quan.

Chatbot cần trả lời theo hướng hỗ trợ tra cứu và hướng dẫn, không chẩn đoán bệnh, không kê đơn và không thay thế ý kiến của bác sĩ hoặc nhân viên y tế.

### RAG trên dữ liệu bệnh viện nội bộ

RAG là cơ chế giúp chatbot trả lời dựa trên dữ liệu đáng tin cậy thay vì chỉ dựa vào kiến thức tổng quát của mô hình AI.

Dữ liệu ưu tiên trong MVP gồm:

- Khoa và phòng chức năng.
- Thông tin bác sĩ.
- Lịch khám hoặc lịch làm việc.
- Dịch vụ bệnh viện.
- Thông tin hướng dẫn người bệnh liên quan trực tiếp đến các mục trên.

Khi dữ liệu không có trong nguồn RAG hoặc độ chắc chắn thấp, hệ thống phải nói rõ giới hạn thay vì bịa câu trả lời.

### Voice tiếng Việt speak-to-speak realtime

Voice là một phần trọng tâm của trải nghiệm, không chỉ là tính năng phụ.

Mục tiêu là người dùng có thể nói bằng tiếng Việt, hệ thống nhận dạng nội dung, xử lý qua chatbot/RAG và phản hồi lại bằng giọng nói trong một luồng hội thoại gần realtime.

Trải nghiệm voice cần ưu tiên:

- Nhận diện tiếng Việt tự nhiên.
- Phản hồi nhanh và rõ.
- Hiển thị trạng thái đang nghe, đang xử lý, đang nói hoặc gặp lỗi.
- Có transcript để người dùng nhìn lại nội dung đã nói và câu trả lời.
- Có cách dừng, thử lại hoặc chuyển sang nhập văn bản khi voice gặp vấn đề.

### Arduino và cơ chế lấy thuốc

Arduino đóng vai trò điều khiển ngoại vi trong hệ thống, tập trung vào demo cơ chế lấy thuốc.

Trong MVP, Arduino không xử lý logic AI. Webapp và backend mới là nơi quyết định luồng xử lý, xác nhận yêu cầu và gửi lệnh phù hợp đến Arduino.

Mọi lệnh liên quan đến lấy thuốc hoặc điều khiển phần cứng phải có bước xác nhận rõ ràng trên webapp trước khi thực thi. Không để AI tự động kích hoạt phần cứng nếu người dùng chưa xác nhận.

## 4. Màn hình và trải nghiệm chính

Webapp nên có các khu vực chức năng chính sau:

- Chat/Voice: nơi người dùng hỏi đáp bằng văn bản hoặc giọng nói.
- Tra cứu bệnh viện: nơi hiển thị thông tin khoa, bác sĩ, lịch khám và dịch vụ.
- Thiết bị/Arduino: nơi xem trạng thái thiết bị, xác nhận thao tác và kích hoạt demo lấy thuốc.

MVP chưa cần bắt buộc đăng nhập. Người dùng nên có thể truy cập nhanh vào các chức năng chính để phục vụ trải nghiệm demo và sử dụng tức thì.

Nếu sau này cần mở rộng, hệ thống có thể bổ sung tài khoản người dùng, lịch sử hội thoại, phân quyền quản trị và màn hình quản lý dữ liệu RAG.

## 5. Phong cách giao diện web

Phong cách giao diện cần bám theo tinh thần đã mô tả trong `stype_wed.md`: medical kiosk, touch-first, teal soft UI, chữ tiếng Việt lớn dễ đọc, card trắng trong nhẹ, khung robot bo góc lớn và các nút thao tác rõ ràng.

Định hướng giao diện:

- Sạch, sáng, hiện đại và đáng tin cậy.
- Phù hợp môi trường bệnh viện, robot y tế hoặc kiosk cảm ứng.
- Ưu tiên nền trắng/xanh rất nhạt, màu nhấn teal và xanh dương nhẹ.
- Nút bấm lớn, dễ chạm, có icon kèm chữ.
- Văn bản ngắn, trực tiếp, tránh thuật ngữ khó hiểu.
- Trạng thái hệ thống phải rõ: sẵn sàng nghe, đang nghe, đang xử lý, đang nói, lỗi, cần xác nhận.
- Không dùng theme tối, màu quá gắt hoặc trang trí rối mắt.

Voice overlay nên là điểm nhấn của trải nghiệm giọng nói. Bot face/mascot bằng HTML/CSS cần tạo cảm giác thân thiện, đang lắng nghe và phù hợp với robot y tế, nhưng không quá trẻ con hoặc quá hoạt hình.

## 6. Nguyên tắc an toàn và độ tin cậy

Vì dự án thuộc bối cảnh y tế, hệ thống cần có giới hạn rõ ràng:

- Không chẩn đoán bệnh.
- Không kê đơn thuốc.
- Không thay thế bác sĩ, dược sĩ hoặc nhân viên y tế.
- Không bịa thông tin khi dữ liệu RAG không có câu trả lời.
- Luôn nói rõ khi thiếu dữ liệu, không chắc chắn hoặc cần liên hệ bệnh viện.
- Với thao tác phần cứng, luôn yêu cầu xác nhận trước khi gửi lệnh đến Arduino.

Câu trả lời của chatbot nên ưu tiên tính đúng, rõ và hữu ích hơn là trả lời dài hoặc phức tạp.

## 7. Định hướng kỹ thuật

Hệ thống được định hướng theo mô hình Python backend + web UI.

Backend chịu trách nhiệm:

- Xử lý hội thoại AI.
- Truy vấn RAG trên dữ liệu bệnh viện.
- Điều phối voice pipeline.
- Cung cấp API cho frontend.
- Giao tiếp với Arduino hoặc lớp điều khiển thiết bị.
- Kiểm soát xác nhận trước khi thực thi lệnh phần cứng.

Frontend chịu trách nhiệm:

- Hiển thị giao diện chat và voice realtime.
- Cho phép tra cứu thông tin bệnh viện.
- Hiển thị trạng thái xử lý của AI, voice và thiết bị.
- Cho phép người dùng xác nhận hoặc hủy thao tác phần cứng.
- Đảm bảo trải nghiệm cảm ứng rõ ràng, dễ dùng và nhất quán với `stype_wed.md`.

Tài liệu này không khóa chặt framework cụ thể. Khi build, có thể chọn framework phù hợp, miễn là kiến trúc vẫn rõ module, dễ mở rộng và bám sát trải nghiệm sản phẩm đã nêu.

## 8. Tiêu chí thành công

Một phiên bản webapp được xem là đi đúng mục tiêu khi đạt các tiêu chí sau:

- Người dùng có thể mở app và hiểu ngay các chức năng chính.
- Chatbot trả lời đúng dựa trên dữ liệu bệnh viện nội bộ.
- Voice tiếng Việt hoạt động theo luồng speak-to-speak rõ ràng, có trạng thái và transcript.
- Giao diện sáng, sạch, dễ đọc, phù hợp kiosk/robot y tế.
- Arduino có thể demo cơ chế lấy thuốc nhưng chỉ chạy sau khi có xác nhận.
- Khi thiếu dữ liệu, hệ thống nói rõ giới hạn và gợi ý liên hệ bệnh viện hoặc nhân viên y tế.
- Code và kiến trúc sau này có thể mở rộng thêm dữ liệu, màn hình quản trị, lịch sử hội thoại hoặc thiết bị mới.

## 9. Kim chỉ nam khi phát triển

Mọi quyết định khi build webapp nên trả lời được các câu hỏi sau:

- Tính năng này có giúp bệnh nhân hoặc người nhà tra cứu và thao tác dễ hơn không?
- Câu trả lời của AI có dựa trên dữ liệu bệnh viện đáng tin cậy không?
- Người dùng có hiểu hệ thống đang nghe, xử lý, nói hay gặp lỗi không?
- Thao tác liên quan đến phần cứng đã có bước xác nhận đủ rõ chưa?
- Giao diện có bám phong cách medical kiosk trong `stype_wed.md` không?
- Hệ thống có tránh đưa ra thông tin y tế vượt quá phạm vi hỗ trợ không?

Nếu một thay đổi làm app rối hơn, khó hiểu hơn, dễ trả lời sai hơn hoặc tự động hóa phần cứng thiếu kiểm soát, thay đổi đó không phù hợp với mục tiêu của dự án.
