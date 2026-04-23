# GEMINI.md - Chỉ dẫn dự án Model_AITRAFFIC (Cập nhật 06/04/2026)

File này chứa các quy tắc, kiến trúc và thông tin ngữ cảnh quan trọng để vận hành và phát triển hệ thống phân tích giao thông thông minh Full-stack v5.0 (Standard & Advanced Hybrid).

## 1. Tổng quan dự án (Project Overview)
- **Mục tiêu:** Hệ thống phân tích giao thông đa tầng tích hợp Web Dashboard & Live Heatmap chuyên nghiệp.
- **Nền tảng:** 
    - **AI Core:** YOLOv11 + Multi-Tracker (ByteTrack, StrongSORT, OC-SORT, Mask R-CNN).
    - **Core Hybrid:** YOLO + DeepSort cho truy vết bền bỉ.
    - **Web Hub:** Django Backend + REST API + Real-time Dashboard (Light Theme).
    - **Video Standard:** WebM (VP80) - Tương thích 100% trình duyệt.

## 2. Kiến trúc Hệ thống (System Architecture)
- **`traffic_platform.py`**: Nền tảng AI tổng hợp, hỗ trợ chuyển đổi 4 chế độ.
- **Django Server**: Quản lý Database, API và Dashboard.
- **AI Crawler**: Tự động cập nhật dữ liệu 24/7 từ camera công cộng.

## 3. Chỉ dẫn kỹ thuật bắt buộc
- **AI Precision:** Bắt buộc sử dụng ngưỡng `confidence = 0.2` cho mọi lần gọi AI.
- **Mật độ chuẩn:** Sử dụng công thức PCE chuẩn hóa ($D = \frac{\sum (w_i \times 1200)}{A_{road}} \times 100\%$).
- **Lưu lượng:** Giá trị hiển thị là **Trung bình (Mean)** của chu kỳ phân tích gần nhất.
- **Tối ưu:** Duy trì `gc.collect()` và giới hạn biểu đồ ở mức **60 điểm dữ liệu**.

## 4. Quy ước phát triển (Conventions)
- **Giao diện:** Light Theme, Soft Shadows, màu Neon Blue chủ đạo.
- **Tài liệu:** Toàn bộ báo cáo, công thức và nhật ký nằm trong thư mục `Documents/`.

## 5. Lộ trình phát triển (Roadmap)
- [x] Giai đoạn 1-5: Hoàn thiện toàn bộ Core AI, Web Dashboard, Maps và Logic chuẩn hóa.
- [ ] Giai đoạn 6: Tích hợp Local GPU Inference và Hệ thống cảnh báo tự động.

## 6. Lệnh quan trọng (Key Commands)
- **Khởi động Web:** `./env/bin/python3 manage.py runserver`
- **Khởi động AI Crawler:** `./env/bin/python3 manage.py update_traffic`
- **Đồng bộ Git:** `git add . && git commit -m "..." && git push origin main`

---
*Mọi chi tiết về công thức toán học và nhật ký lỗi xem tại thư mục Documents/*
