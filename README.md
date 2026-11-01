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

## 🚀 CÀI ĐẶT 1-CLICK TRÊN JAVISOS / LINUX

### Cách 1: Chạy lệnh cài đặt tự động (Khuyên dùng)
```bash
git clone https://github.com/trunghieuvtth/javis-second-brain.git ~/javis-second-brain
cd ~/javis-second-brain
bash install.sh
```

Hệ thống sẽ tự khởi tạo môi trường, cài đặt thư viện và đăng ký dịch vụ `systemd user service` chạy ngầm 24/7.
- Truy cập giao diện: `http://localhost:8090` (hoặc cấu hình tên miền `brain.centos.vn`).

### Cách 2: Chạy bằng Docker Compose
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
