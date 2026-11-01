# Javis Second Brain AI (Kho Tri Thức Số & Soạn Thảo Báo Cáo NĐ 30)

Nền tảng Quản trị Tri Thức Đa Nguồn và Soạn Thảo Văn Bản Hành Chính chuẩn Nghị định 30/2020/NĐ-CP & Hướng dẫn 05-HD/VPTW độc lập dành cho **JavisOS**, cơ quan hành chính nhà nước và doanh nghiệp.

![Javis Second Brain](https://img.shields.io/badge/JavisOS-Ready-teal?style=for-the-badge)
![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![License](https://img.shields.io/badge/License-MIT-blue?style=for-the-badge)

---

## 🌟 ĐẶC ĐIỂM NỔI BẬT

1. **Nạp tri thức 4 trong 1:**
   - Link chia sẻ Google Drive / Google Docs.
   - Quét chọn nguyên thư mục máy tính (Browse Folder).
   - Tải lên tệp đính kèm đa định dạng (PDF, DOCX, XLSX, TXT, MD, Ảnh OCR).
   - Cào dữ liệu bài báo, văn bản pháp luật từ liên kết Web.
2. **Tự động phân loại RAG chuyên môn:**
   - Tự động bóc tách và phân loại vào 5 nhóm chuẩn: *Chỉ đạo điều hành, Báo cáo chuyên đề, Quy định & Chính sách, Tài liệu cơ quan, Nghiên cứu tham khảo*.
3. **Trợ lý AI Soạn Thảo Báo Cáo chuẩn thể thức NĐ 30 & HD 05:**
   - Tự động sinh trích yếu, trích lọc số liệu từ tài liệu nguồn và xuất trực tiếp tệp Word (`.docx`) chuẩn OpenXML có sẵn Quốc hiệu, Tiêu ngữ, Kính gửi, Thẩm quyền ký duyệt.
   - Hỗ trợ đầy đủ **21 loại văn bản hành chính**.
4. **Phân quyền ma trận 3 tầng tri thức:**
   - **Tầng 1 (Cá nhân):** Riêng tư tuyệt đối cho từng cán bộ.
   - **Tầng 2 (Phòng ban):** Dùng chung cho chuyên viên trong cùng bộ phận.
   - **Tầng 3 (Dùng chung toàn xã/đơn vị):** Kế thừa và chia sẻ tri thức công vụ.
5. **Định danh công vụ bằng CCCD 12 số:**
   - Ràng buộc chức danh theo phòng ban, kiểm tra nhập thiếu báo thiếu, nhập sai báo sai.
   - Tự động gợi ý Vị trí việc làm theo Hướng dẫn 05 bằng AI.

---

## 🚀 CÀI ĐẶT & KÍCH HOẠT 1-CLICK (WINDOWS, JAVISOS, LINUX)

### 💻 Dành cho Windows:
1. Tải repository về máy (Tải ZIP giải nén hoặc `git clone`).
2. Nhấp đúp chuột vào tệp: **`install_windows.bat`**.
   * Hệ thống sẽ tự động tạo môi trường ảo Python `venv`.
   * Cài đặt toàn bộ thư viện cần thiết.
   * Thiết lập **chạy ngầm 24/7 (ẩn cửa sổ đen console)** và tự động khởi động cùng máy tính Windows (`Startup`).
   * **Tự động bật trình duyệt web** mở ngay trang Kho Tri Thức tại `http://localhost:8090`.
*(Khi cần tắt dịch vụ trên Windows: Chỉ cần nhấp đúp file `stop_service.bat`)*.

---

### 🐧 Dành cho JavisOS & Linux:
Mở terminal và chạy 1 dòng lệnh:
```bash
git clone https://github.com/trunghieuvtth/javis-second-brain.git ~/javis-second-brain
cd ~/javis-second-brain && bash install.sh
```
Script sẽ tự động:
* Khởi tạo `venv` và cài đặt thư viện.
* Tạo và kích hoạt dịch vụ chạy ngầm `systemd user service` (`javis-second-brain.service`).
* Bật `Linger` chạy ngầm 24/7 kể cả khi tắt máy ảo/logout.
* **Tự động mở trình duyệt web** vào ngay `http://localhost:8090`.

---

### 🐳 Dành cho Docker Compose:
```bash
docker-compose up -d
```

### Cách 3: Cài đặt từ JavisOS Store
1. Mở JavisOS Store.
2. Tìm kiếm **"Kho Tri Thức Số"** hoặc **"Javis Second Brain"**.
3. Bấm **[Bật Ứng Dụng]** để kích hoạt biểu tượng trên màn hình JavisOS.

---

## 📋 THÔNG TIN BẢN QUYỀN & CHUYỂN GIAO
- **Đơn vị phát triển:** Sở Khoa học và Công nghệ tỉnh Tây Ninh.
- **Giấy phép:** MIT License (Mã nguồn mở, miễn phí trọn đời).
