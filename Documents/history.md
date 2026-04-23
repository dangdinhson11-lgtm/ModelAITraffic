# 📖 NHẬT KÝ PHÁT TRIỂN DỰ ÁN (PROJECT HISTORY)

## 1. CÁC GIAI ĐOẠN PHÁT TRIỂN

### Giai đoạn 1: Xây dựng Lõi AI (AI Core)
*   **Mục tiêu:** Tích hợp YOLOv11 với các bộ Tracker tiên tiến.
*   **Kết quả:** Triển khai thành công 4 kịch bản theo dõi: ByteTrack (Nhanh), StrongSORT (Ổn định), OC-SORT (Chuyển động phức tạp) và Mask R-CNN (Phân đoạn pixel).

### Giai đoạn 2: Phát triển Backend Django & API
*   **Mục tiêu:** Quản lý dữ liệu tập trung và cung cấp API cho Dashboard.
*   **Kết quả:** Thiết lập hệ thống Model `TrafficCamera` và `TrafficHistory`, xây dựng REST API hoàn chỉnh.

### Giai đoạn 3: Hệ thống Cào dữ liệu Real-time
*   **Mục tiêu:** Duy trì dữ liệu giao thông "sống" từ nguồn công cộng.
*   **Kết quả:** Xây dựng Command `update_traffic` tự động cào ảnh, chạy AI và cập nhật Database sau mỗi 60 giây.

### Giai đoạn 4: Dashboard & Trải nghiệm Người dùng (UX)
*   **Mục tiêu:** Tạo giao diện trực quan và tính năng Demo video.
*   **Kết quả:** Hoàn thiện giao diện Light Theme, tích hợp Live Heatmap (Leaflet), hệ thống Phân trang, Bộ lọc và luồng xử lý video Demo với thanh tiến trình thực tế.

---

## 2. KHÓ KHĂN VÀ THÁCH THỨC

| Khó khăn | Nguyên nhân | Giải pháp khắc phục |
| :--- | :--- | :--- |
| **Lỗi Terminated** | Cạn kiệt RAM do mô hình AI quá nặng trên Codespace. | Sử dụng ByteTrack (không Embedder), nén ảnh (Resize 320p/480p), tăng Stride và dọn RAM thủ công (`gc.collect`). |
| **Video đen/không xem được** | Lỗi Codec không tương thích với trình duyệt web. | Chuyển đổi định dạng sang **WebM (VP80)**. Đây là chuẩn nén video tối ưu nhất cho trình duyệt. |
| **Lỗi 403 Forbidden** | Website nguồn chặn các yêu cầu từ script tự động. | Giả lập đầy đủ bộ Headers và Cookies của trình duyệt thật trong `requests.Session`. |
| **Biểu đồ phình to** | Dữ liệu lịch sử quá lớn gây lỗi render Chart.js. | Sử dụng cơ chế "Sliding Window", chỉ lấy 20 bản ghi mới nhất và cố định chiều cao container. |

---

## 3. ĐÁNH GIÁ TỔNG KẾT

### ✅ Điểm cộng (Pros):
*   **Tính linh hoạt cao:** Hệ thống tích hợp tới 4 mô hình khác nhau, cho phép tùy biến theo tài nguyên phần cứng.
*   **Tối ưu tài nguyên:** Chạy mượt mà trên môi trường RAM thấp (< 4GB) nhờ các kỹ thuật nén và nhảy khung hình.
*   **Dữ liệu thực:** Kết nối trực tiếp với mạng lưới camera giao thông thực tế của TP.HCM.
*   **Giao diện hiện đại:** Đồng bộ phong cách Light Theme sạch sẽ, dễ tiếp cận cho người dùng phổ thông.

### ❌ Điểm trừ (Cons):
*   **Độ trễ:** Việc sử dụng Cloud API khiến tốc độ xử lý video bị phụ thuộc vào đường truyền mạng.
*   **Chất lượng ảnh:** Một số camera nguồn có độ phân giải thấp, ảnh hưởng đến độ chính xác của AI ở khoảng cách xa.

### 🚀 Điểm cần cải thiện (Future Improvements):
*   **Local Inference:** Tích hợp chạy mô hình trực tiếp trên Server có GPU (TensorRT/OpenVINO) để đạt tốc độ 30-60 FPS.
*   **Hệ thống Cảnh báo:** Tích hợp gửi thông báo qua Telegram/Email ngay khi phát hiện mật độ > 80% hoặc có tai nạn.
*   **AI Biển số:** Tích hợp thêm mô hình LPR để nhận diện biển số xe vi phạm.

---
*Người tổng hợp: Gemini CLI Agent*
*Ngày hoàn thiện: 06/04/2026*
