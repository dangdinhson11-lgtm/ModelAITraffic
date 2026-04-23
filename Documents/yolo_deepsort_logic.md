# 🧠 LOGIC & CÔNG THỨC: MÔ HÌNH KẾT HỢP YOLO + DEEPSORT

Tài liệu này trình bày các cơ sở toán học và quy trình kỹ thuật để triển khai hệ thống nhận diện và theo dõi giao thông bền bỉ.

---

## 1. CÔNG THỨC TÍNH TOÁN LÀN ĐƯỜNG (LANE DETECTION)

Hệ thống sử dụng ma trận biến đổi phối cảnh (**Perspective Transform**) để quy đổi tọa độ từ hình ảnh (2D) sang mặt phẳng thực tế (Ground Plane).

### A. Xác định vùng quan tâm (ROI - Region of Interest)
Vùng làn đường được định nghĩa bởi một đa giác $P$ có $n$ đỉnh:
$$P = \{(x_1, y_1), (x_2, y_2), ..., (x_n, y_n)\}$$

### B. Kiểm tra xe trong làn đường
Một phương tiện tại vị trí $(x_v, y_v)$ được coi là nằm trong làn đường nếu:
$$f(x_v, y_v, P) = \text{true}$$
*(Sử dụng thuật toán Ray Casting để kiểm tra điểm nằm trong đa giác).*

---

## 2. CHIA MẬT ĐỘ GIAO THÔNG (TRAFFIC DENSITY)

Mật độ không chỉ dựa trên số lượng xe mà còn dựa trên **Diện tích chiếm dụng quy đổi (PCE)**.

### A. Hệ số quy đổi PCE (Passenger Car Equivalent)
Mỗi loại phương tiện $i$ được gán một trọng số $w_i$:
- **Xe máy:** $0.5$
- **Ô tô con:** $1.0$
- **Xe tải/Bus:** $2.5 - 3.0$

### B. Công thức tính mật độ (%)
Mật độ $D$ tại thời điểm $t$ được tính bằng:
$$D_t = \frac{\sum (w_i \times \text{Standard\_Area})}{A_{road}} \times 100\%$$

Trong đó:
- $w_i$: Hệ số PCE của phương tiện $i$.
- $\text{Standard\_Area}$: Diện tích trung bình của một xe con tiêu chuẩn (px).
- $A_{road}$: Tổng diện tích lòng đường quan tâm (`road_area_pixels`).

---

## 3. THUẬT TOÁN ĐẾM XE (VEHICLE COUNTING)

Kết hợp sức mạnh nhận diện của **YOLO** và khả năng truy vết của **DeepSort**.

### A. Nguyên lý đếm duy nhất (Unique Counting)
Sử dụng `tracker_id` được cung cấp bởi DeepSort. Một phương tiện chỉ được tính vào tổng lưu lượng khi:
1.  Đã được gán một `ID` duy nhất.
2.  Tâm của Bounding Box di chuyển cắt ngang **Đường ranh giới ảo (Counting Line)** hoặc đi vào vùng **ROI**.

### B. Công thức lưu lượng (Flow Rate)
Lưu lượng $Q$ trong khoảng thời gian $T$:
$$Q = \frac{N_{unique}}{T} (\text{xe/phút})$$

---

## 4. KẾ HOẠCH TRIỂN KHAI (DEPLOYMENT PLAN)

### Bước 1: Tiền xử lý (Preprocessing)
- Resize input về $640 \times 640$ hoặc $1280 \times 1280$ (tùy cấu hình).
- Hiệu chuẩn (Calibration) diện tích lòng đường cho từng Camera.

### Bước 2: Khởi tạo Pipeline
1.  **YOLO Detector:** Nhận diện và trích xuất Bounding Boxes.
2.  **Feature Extractor:** Trích xuất đặc trưng diện mạo (Appearance Embeddings) cho từng Box.
3.  **DeepSort Tracker:** Thực hiện khớp dữ liệu (Matching) bằng thuật toán Hungarian và lọc Kalman.

### Bước 3: Tích hợp Hệ thống
- Đẩy dữ liệu thống kê (`density`, `count`) về Django Backend qua REST API.
- Cập nhật Live Heatmap trên Frontend.

### Bước 4: Tối ưu hóa (Optimization)
- Sử dụng **TensorRT** để tăng tốc Inference.
- Áp dụng **Multi-threading** để xử lý đồng thời nhiều luồng Camera.
- Định kỳ dọn dẹp ID cũ trong bộ nhớ Tracker để tránh rò rỉ RAM.
