---
name: javis-second-brain
description: "Sử dụng khi cần tra cứu tài liệu trong Kho Tri Thức Số hoặc tự động soạn thảo Báo cáo/Tờ trình chuẩn thể thức Nghị định 30/2020/NĐ-CP và Hướng dẫn 05-HD/VPTW."
---

# Javis Second Brain AI Skill

Skill này giúp các AI Agent trên JavisOS, Hermes Agent và OpenCode tương tác trực tiếp với **Kho Tri Thức Số** và **Engine Soạn Thảo Văn Bản Hành Chính**.

## Các chức năng hỗ trợ:

1. **Tra cứu tri thức chuyên ngành:**
   - Tìm kiếm nội dung văn bản, chỉ đạo, đề án theo ngữ nghĩa (Semantic Search).
   - Lọc theo phạm vi phân quyền: Cá nhân, Phòng ban chuyên môn, hoặc Dùng chung toàn cơ quan/xã.

2. **Soạn thảo báo cáo chuẩn thể thức NĐ 30:**
   - Hỗ trợ 21 loại văn bản hành chính theo Nghị định số 30/2020/NĐ-CP và văn bản Đảng theo Hướng dẫn số 05-HD/VPTW.
   - Tự động sinh file Word (.docx) chuẩn OpenXML, có sẵn Quốc hiệu, Tiêu ngữ, Kính gửi, Thẩm quyền ký duyệt.

## Cú pháp API gọi từ Agent:

- **Lấy danh mục tri thức:**
  ```bash
  curl -s "http://127.0.0.1:8090/api/personal-brain/items?workspace=all"
  ```

- **Tạo báo cáo tự động từ danh sách tài liệu:**
  ```bash
  curl -X POST "http://127.0.0.1:8090/api/personal-brain/generate-report" \
    -H "Content-Type: application/json" \
    -d '{
      "item_ids": ["pb_khcn_01"],
      "loai_van_ban": "bao_cao",
      "trich_yeu": "Về tình hình chuyển đổi số và ứng dụng trí tuệ nhân tạo năm 2026",
      "co_quan_gui": "Ủy ban nhân dân tỉnh Tây Ninh"
    }'
  ```
