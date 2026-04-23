# 🚦 Smart Traffic Analytics Platform (Model_AITRAFFIC)

[![Python Version](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![AI Engine](https://img.shields.io/badge/AI-YOLOv11-orange.svg)](https://roboflow.com)
[![Status](https://img.shields.io/badge/Status-Completed--v1.0-green.svg)]()

Hệ thống phân tích giao thông thông minh đa nhiệm, tích hợp các công nghệ State-of-the-Art (SOTA) để đo lường mật độ, lưu lượng và theo dõi phương tiện giao thông.

---

## ✨ Tính năng nổi bật

- **Nhận diện đa lớp:** Nhận diện Xe máy, Ô tô, Xe tải, Xe bus... sử dụng YOLOv11.
- **Phân tích mật độ chuẩn PCE:** Áp dụng hệ số quy đổi xe con (Passenger Car Equivalent).
- **Phân đoạn Pixel:** Sử dụng Mask R-CNN để tính diện tích chiếm dụng thực tế chính xác đến từng pixel.
- **Báo cáo tự động:** Xuất dữ liệu ra file `.csv` và vẽ biểu đồ biến thiên mật độ `.png`.
- **Đa chế độ xử lý:** Cho phép tùy chọn mô hình Tracker linh hoạt theo cấu hình máy chủ.

---

## 🏗️ Kiến trúc Mô-đun (Universal Platform)

Dự án tích hợp 4 chế độ phân tích chuyên biệt thông qua file `traffic_platform.py`:

| Chế độ (`--mode`) | Công nghệ | Ưu điểm | Mục tiêu |
| :--- | :--- | :--- | :--- |
| **`fast`** | ByteTrack | Cực nhanh, nhẹ RAM | Giám sát thời gian thực |
| **`stable`** | StrongSORT | ID ổn định, chống khuất | Theo dõi xe vi phạm |
| **`motion`** | OC-SORT | Chính xác khi quay đầu | Ngã tư phức tạp |
| **`mask`** | Mask R-CNN | Chính xác diện tích 99% | Báo cáo khoa học |

---

## 🚀 Hướng dẫn cài đặt

### 1. Chuẩn bị môi trường
```bash
# Clone dự án
git clone https://github.com/Dunglele/Model_AITRAFFIC.git
cd Model_AITRAFFIC

# Tạo môi trường ảo
python3 -m venv env
source env/bin/activate  # Linux/Mac
# env\Scripts\activate  # Windows

# Cài đặt thư viện
pip install -r requirements.txt
```

### 2. Cấu hình API
Tạo file `.env` trong thư mục gốc và thêm API Key của bạn:
```env
ROBOFLOW_API_KEY=your_api_key_here
```

---

## 💻 Cách vận hành

Chỉ cần một câu lệnh duy nhất để bắt đầu phân tích:

```bash
python traffic_platform.py --input video_mau.mp4 --mode fast --output result.avi
```

### Các tham số:
- `--input`: Đường dẫn video đầu vào (hoặc ảnh).
- `--mode`: `fast` | `stable` | `motion` | `mask` (Mặc định: `fast`).
- `--output`: Tên file kết quả (Mặc định: `result.avi`).

---

## 📊 Kết quả phân tích

Sau khi xử lý xong, hệ thống sẽ tự động tạo các tệp báo cáo:
1. **Video kết quả:** Vẽ khung nhận diện, ID và Mật độ % trực tiếp trên khung hình.
2. **`traffic_report.csv`:** Bảng dữ liệu thống kê theo thời gian thực (giây).
3. **`chart_*.png`:** Biểu đồ mật độ giao thông trực quan với dải màu phân loại (Thông thoáng/Trung bình/Tắc nghẽn).

---

## 🗺️ Lộ trình phát triển (Roadmap)

- [x] **Giai đoạn 1:** Hoàn thiện AI Core & 4 mô hình bổ trợ.
- [x] **Giai đoạn 2:** Tích hợp Backend Django và Celery Task Queue.
- [x] **Giai đoạn 3:** Xây dựng Dashboard Web hiển thị dữ liệu thời gian thực.

---

## 🤝 Đóng góp & Hỗ trợ
Nếu bạn gặp bất kỳ vấn đề nào, hãy mở một **Issue** hoặc liên hệ qua:
- **Người thực hiện:** Đặng Đình Sơn
- **Repository:** [Model_AITRAFFIC](https://github.com/Dunglele/Model_AITRAFFIC)

---
*Dự án được tối ưu hóa để chạy ổn định trên môi trường hạn chế tài nguyên (RAM < 4GB).*
