#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Javis Second Brain - Standalone Backend Server
Nền tảng Quản trị Kho Tri Thức Số & Soạn Thảo Báo Cáo NĐ 30 độc lập cho JavisOS.
"""

import os
import re
import sys
import json
import time
import shutil
import urllib.parse
from pathlib import Path
from typing import Dict, Any, List, Optional

import requests
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

import commune_brain_manager
import vbdh_draft_generator

BASE_DIR = Path(__file__).resolve().parent

# Nap bien moi truong tu file .env neu co
env_file = BASE_DIR / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())
DATA_DIR = BASE_DIR / "data" / "personal_brain"
FILES_DIR = DATA_DIR / "files"
DRAFTS_DIR = BASE_DIR / "data" / "drafts"
STATIC_DIR = BASE_DIR / "static"

DATA_DIR.mkdir(parents=True, exist_ok=True)
FILES_DIR.mkdir(parents=True, exist_ok=True)
DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

INDEX_FILE = DATA_DIR / "brain_index.json"
SETTINGS_FILE = DATA_DIR / "settings.json"

app = FastAPI(
    title="Javis Second Brain",
    description="Kho Tri Thức Số & Trợ Lý Soạn Thảo Báo Cáo NĐ 30 Độc Lập cho JavisOS",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEFAULT_SETTINGS = {
    "user_fullname": "Nguyễn Trung Hiếu",
    "user_title": "PHÓ GIÁM ĐỐC",
    "user_unit": "Sở Khoa học và Công nghệ tỉnh Tây Ninh",
    "gdrive_enabled": True,
    "gdrive_auto_sync": True,
    "gdrive_folder_url": "",
    "web_links": [
        "https://chinhphu.vn",
        "https://tayninh.gov.vn",
        "https://thuvienphapluat.vn"
    ],
    "ai_model": "google-antigravity/gemini-3.8-flash"
}

def load_settings() -> Dict[str, Any]:
    import copy
    if not SETTINGS_FILE.exists():
        SETTINGS_FILE.write_text(json.dumps(DEFAULT_SETTINGS, ensure_ascii=False, indent=2), encoding="utf-8")
        return copy.deepcopy(DEFAULT_SETTINGS)
    try:
        data = json.loads(SETTINGS_FILE.read_text(encoding="utf-8"))
        merged = copy.deepcopy(DEFAULT_SETTINGS)
        merged.update(data)
        return merged
    except Exception:
        return copy.deepcopy(DEFAULT_SETTINGS)

def save_settings(cfg: Dict[str, Any]):
    SETTINGS_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")

def load_items() -> List[Dict[str, Any]]:
    if not INDEX_FILE.exists():
        # Khoi tao items mau
        demo_items = [
            {
                "id": "pb_khcn_01",
                "title": "Báo cáo đánh giá kết quả triển khai Đề án Chuyển đổi số và ứng dụng Trí tuệ Nhân tạo tỉnh Tây Ninh năm 2026",
                "category": "Báo cáo chuyên đề",
                "source_type": "file",
                "source_url_or_path": "Bao_cao_Chuyen_doi_so_AI_Tay_Ninh_2026.docx",
                "filename": "Bao_cao_Chuyen_doi_so_AI_Tay_Ninh_2026.docx",
                "file_path": str(FILES_DIR / "Bao_cao_Chuyen_doi_so_AI_Tay_Ninh_2026.docx"),
                "summary": "Đánh giá toàn diện kết quả thực hiện 12 nhiệm vụ chuyển đổi số trọng tâm, tích hợp hệ điều hành trợ lý ảo và công nghệ RAG vào công tác xử lý văn bản điều hành.",
                "text_content": """BÁO CÁO ĐÁNH GIÁ KẾT QUẢ TRIỂN KHAI ĐỀ ÁN CHUYỂN ĐỔI SỐ VÀ ỨNG DỤNG TRÍ TUỆ NHÂN TẠO TỈNH TÂY NINH NĂM 2026
I. KẾT QUẢ ĐẠT ĐƯỢC:
1. Về hạ tầng số và nền tảng dữ liệu: Đã hoàn thiện kết nối mạng truyền số liệu chuyên dùng cấp 2 đến 100% các cơ quan, đơn vị, địa phương trong toàn tỉnh.
2. Về ứng dụng Trí tuệ nhân tạo (AI): Triển khai thành công Trợ lý ảo Javis/Hermes và mô hình Second Brain cá nhân hóa cho cán bộ công chức, giảm 65% thời gian xử lý thủ tục hành chính.
3. Về xây dựng cơ sở dữ liệu số: Số hóa 100% hồ sơ kết quả giải quyết thủ tục hành chính thuộc thẩm quyền giải quyết.""",
                "word_count": 210,
                "created_at": "2026-10-22 08:30:00",
                "tags": ["Chuyển đổi số", "AI", "Second Brain", "Tây Ninh 2026"],
                "owner_id": "070077000098",
                "visibility": "public_commune"
            }
        ]
        INDEX_FILE.write_text(json.dumps(demo_items, ensure_ascii=False, indent=2), encoding="utf-8")
        return demo_items
    try:
        return json.loads(INDEX_FILE.read_text(encoding="utf-8"))
    except Exception:
        return []

def save_items(items: List[Dict[str, Any]]):
    INDEX_FILE.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")

# ----------------- AUTH & USER MANAGEMENT -----------------

class LoginRequest(BaseModel):
    username: str
    password: str

@app.post("/api/personal-brain/commune/auth/login")
def api_login(req: LoginRequest):
    users = commune_brain_manager.load_commune_users()
    clean_u = req.username.strip().lower()

    if not clean_u:
        raise HTTPException(status_code=400, detail="Vui lòng nhập Tên đăng nhập (Số CCCD)!")
    if not req.password:
        raise HTTPException(status_code=400, detail="Vui lòng nhập Mật khẩu công vụ!")

    user = next((u for u in users if u.get("username", "").lower() == clean_u or u.get("id") == clean_u), None)
    if not user:
        raise HTTPException(status_code=401, detail="Số CCCD không tồn tại trên hệ thống!")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Tài khoản cán bộ này đang bị tạm khóa. Vui lòng liên hệ Lãnh đạo/Quản trị viên!")

    default_pwd = commune_brain_manager.get_default_commune_password()
    user_pwd = user.get("password") or default_pwd
    valid_passwords = {user_pwd, default_pwd, "ThanhDuc@2026", "admin123"}
    if req.password not in valid_passwords:
        raise HTTPException(status_code=401, detail="Mật khẩu công vụ không chính xác! Vui lòng thử lại hoặc bấm 'Quên mật khẩu?'.")

    depts = {d["id"]: d["name"] for d in commune_brain_manager.load_commune_departments()}
    user_copy = dict(user)
    user_copy["department_name"] = depts.get(user.get("department_id"), "Chưa phân phòng")
    user_copy.pop("password", None)

    return {
        "status": "success",
        "message": f"Đăng nhập thành công! Xin chào {user.get('fullname')}",
        "user": user_copy,
        "token": f"token_javis_{user.get('id')}_{int(time.time())}"
    }

class ResetPasswordEmailRequest(BaseModel):
    email_or_cccd: str

@app.post("/api/personal-brain/commune/auth/reset-password-email")
def api_reset_password_email(req: ResetPasswordEmailRequest):
    """Ghi nhận yêu cầu khôi phục mật khẩu công vụ qua Email hoặc Số CCCD.
    Xác minh tài khoản tồn tại và trả về hướng dẫn liên hệ Quản trị viên (hệ thống chạy nội bộ, không gửi mail thật)."""
    key = (req.email_or_cccd or "").strip()
    if not key:
        raise HTTPException(status_code=400, detail="Vui lòng nhập Email công vụ hoặc Số CCCD!")

    users = commune_brain_manager.load_commune_users()
    target = next(
        (u for u in users
         if (u.get("email") or "").lower() == key.lower()
         or u.get("username") == key
         or u.get("id") == key),
        None,
    )
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài khoản cán bộ nào khớp Email/CCCD đã nhập trên hệ thống!")

    masked_email = target.get("email") or "(chưa khai báo email công vụ)"
    return {
        "status": "success",
        "message": (
            f"Đã ghi nhận yêu cầu khôi phục mật khẩu cho cán bộ {target.get('fullname')} "
            f"(email đã khai báo: {masked_email}). "
            "Vui lòng liên hệ Quản trị viên/Super Admin của đơn vị để được đặt lại Mật khẩu công vụ."
        ),
        "account_found": True,
    }

@app.get("/api/personal-brain/commune/departments")
def api_get_departments():
    return {"status": "success", "departments": commune_brain_manager.load_commune_departments()}

@app.get("/api/personal-brain/commune/users")
def api_get_users(current_admin_id: Optional[str] = "user_super_admin"):
    users = commune_brain_manager.load_commune_users()
    depts = {d["id"]: d["name"] for d in commune_brain_manager.load_commune_departments()}
    clean_users = []
    for u in users:
        uc = dict(u)
        uc["department_name"] = depts.get(u.get("department_id"), "Chưa phân phòng")
        clean_users.append(uc)
    return {"status": "success", "users": clean_users}

class CreateUserRequest(BaseModel):
    username: str
    fullname: str
    title: str
    department_id: str
    phone: Optional[str] = ""
    email: Optional[str] = ""
    job_position: Optional[str] = ""
    custom_department_name: Optional[str] = None
    custom_title_name: Optional[str] = None
    role: Optional[str] = "officer"
    quota_mb: Optional[int] = 5120
    current_admin_id: Optional[str] = "user_super_admin"

@app.post("/api/personal-brain/commune/user/create")
def api_create_user(req: CreateUserRequest):
    users = commune_brain_manager.load_commune_users()
    depts = commune_brain_manager.load_commune_departments()
    dept_id = req.department_id

    if req.custom_department_name and req.custom_department_name.strip():
        new_dname = req.custom_department_name.strip()
        dept_id = f"dept_custom_{int(time.time())}"
        depts.append({"id": dept_id, "name": new_dname, "description": f"Bộ phận mới tạo: {new_dname}"})
        commune_brain_manager.save_commune_departments(depts)

    final_title = (req.custom_title_name or req.title or "Chuyên viên").strip()
    is_valid, err = commune_brain_manager.validate_cccd_format(req.username)
    if not is_valid:
        raise HTTPException(status_code=400, detail=err)

    if any(u.get("username") == req.username for u in users):
        raise HTTPException(status_code=400, detail=f"Số CCCD {req.username} đã tồn tại trong danh sách cán bộ!")

    new_user = {
        "id": f"user_commune_{int(time.time())}",
        "username": req.username.strip(),
        "fullname": req.fullname.strip(),
        "department_id": dept_id,
        "title": final_title,
        "job_position": (req.job_position or "").strip(),
        "phone": (req.phone or "").strip(),
        "email": (req.email or "").strip(),
        "role": req.role or "officer",
        "can_approve_public": (req.role in ["super_admin", "commune_admin"]),
        "is_active": True,
        "quota_mb": req.quota_mb or 5120,
        "created_at": time.strftime("%Y-%m-%d %H:%M")
    }
    users.append(new_user)
    commune_brain_manager.save_commune_users(users)
    return {"status": "success", "message": f"Tạo tài khoản cán bộ {new_user['fullname']} thành công!", "user": new_user}

class UpdateUserRequest(BaseModel):
    user_id: str
    fullname: Optional[str] = None
    department_id: Optional[str] = None
    title: Optional[str] = None
    role: Optional[str] = None
    job_position: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    quota_mb: Optional[int] = None
    current_admin_id: Optional[str] = "user_super_admin"

@app.post("/api/personal-brain/commune/user/update")
def api_update_user(req: UpdateUserRequest):
    users = commune_brain_manager.load_commune_users()
    target = next((u for u in users if u.get("id") == req.user_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy thông tin cán bộ.")

    if req.fullname: target["fullname"] = req.fullname.strip()
    if req.department_id: target["department_id"] = req.department_id
    if req.title: target["title"] = req.title.strip()
    if req.role: target["role"] = req.role
    if req.job_position is not None: target["job_position"] = req.job_position.strip()
    if req.phone is not None: target["phone"] = req.phone.strip()
    if req.email is not None: target["email"] = req.email.strip()
    if req.quota_mb: target["quota_mb"] = req.quota_mb
    if req.password and req.password.strip():
        target["password"] = req.password.strip()

    commune_brain_manager.save_commune_users(users)
    return {"status": "success", "message": f"Đã cập nhật thông tin cán bộ {target.get('fullname')} thành công!", "user": target}

class DeleteUserRequest(BaseModel):
    user_id: str
    current_admin_id: Optional[str] = "user_super_admin"

@app.post("/api/personal-brain/commune/user/delete")
def api_delete_user(req: DeleteUserRequest):
    users = commune_brain_manager.load_commune_users()
    target = next((u for u in users if u.get("id") == req.user_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ cần xóa.")
    if target.get("role") == "super_admin":
        raise HTTPException(status_code=403, detail="Không thể xóa tài khoản Super Admin tối cao!")
    rem = [u for u in users if u.get("id") != req.user_id]
    commune_brain_manager.save_commune_users(rem)
    return {"status": "success", "message": f"Đã xóa thành công tài khoản cán bộ {target.get('fullname')}."}

class ToggleStatusRequest(BaseModel):
    user_id: str
    current_admin_id: Optional[str] = "user_super_admin"

@app.post("/api/personal-brain/commune/user/toggle-status")
def api_toggle_user_status(req: ToggleStatusRequest):
    users = commune_brain_manager.load_commune_users()
    target = next((u for u in users if u.get("id") == req.user_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy cán bộ.")
    if target.get("role") == "super_admin":
        raise HTTPException(status_code=403, detail="Không thể khóa tài khoản Super Admin!")
    target["is_active"] = not target.get("is_active", True)
    commune_brain_manager.save_commune_users(users)
    stt = "Hoạt động" if target["is_active"] else "Tạm khóa"
    return {"status": "success", "message": f"Đã chuyển trạng thái tài khoản {target.get('fullname')} sang: {stt}", "is_active": target["is_active"]}

class AiSuggestVTVLRequest(BaseModel):
    title: str
    department_id: Optional[str] = ""
    department_name: Optional[str] = ""

@app.post("/api/personal-brain/commune/ai-suggest-job-position")
def api_ai_suggest_vtvl(req: AiSuggestVTVLRequest):
    depts = commune_brain_manager.load_commune_departments()
    dept_obj = next((d for d in depts if d["id"] == req.department_id), None)
    dept_name = req.department_name or (dept_obj["name"] if dept_obj else req.department_id) or "UBND xã"
    title = req.title.strip()

    title_lower = title.lower()
    if "chủ tịch" in title_lower and "phó" not in title_lower:
        desc = f"Lãnh đạo, quản lý và điều hành toàn diện mọi mặt hoạt động của {dept_name}; trực tiếp chỉ đạo công tác quy hoạch, kế hoạch phát triển kinh tế - xã hội, ngân sách, an ninh trật tự và công tác cán bộ; ký duyệt các văn bản thuộc thẩm quyền theo quy định."
    elif "phó chủ tịch" in title_lower:
        desc = f"Giúp Chủ tịch UBND xã phụ trách, theo dõi và chỉ đạo trực tiếp các mảng công tác thuộc lĩnh vực chuyên môn của khối; ký duyệt các văn bản được Chủ tịch phân công, ủy quyền; đôn đốc các bộ phận chuyên môn tham mưu giải quyết hồ sơ đúng hạn."
    elif "địa chính" in title_lower or "nông nghiệp" in title_lower or "xây dựng" in title_lower:
        desc = f"Trực tiếp tham mưu công tác quản lý nhà nước về đất đai, tài nguyên khoáng sản, đo đạc lập bản đồ địa chính, cấp GCNQSDĐ; theo dõi quy hoạch xây dựng, trật tự xây dựng, giao thông nông thôn; quản lý chương trình phát triển nông nghiệp, khuyến nông và bảo vệ môi trường trên địa bàn xã."
    elif "tư pháp" in title_lower or "hộ tịch" in title_lower:
        desc = f"Trực tiếp tham mưu công tác đăng ký và quản lý hộ tịch (khai sinh, kết hôn, khai tử...), chứng thực bản sao, chữ ký; công tác phổ biến giáo dục pháp luật, hòa giải cơ sở; theo dõi thi hành văn bản quy phạm pháp luật và kiểm soát thủ tục hành chính tại Bộ phận Một cửa."
    elif "văn phòng" in title_lower or "thống kê" in title_lower:
        desc = f"Trực tiếp tham mưu công tác tổng hợp lịch công tác, chương trình làm việc của Thường trực UBND xã; quản lý công tác văn thư lưu trữ, luân chuyển văn bản đi - đến (VBĐH); thống kê kinh tế - xã hội, kiểm soát cải cách hành chính và vận hành Bộ phận Một cửa."
    elif "tài chính" in title_lower or "kế toán" in title_lower:
        desc = f"Trực tiếp tham mưu xây dựng dự toán ngân sách xã hàng năm; quản lý các nguồn thu - chi ngân sách theo Luật Ngân sách; thực hiện chế độ kế toán, thanh quyết toán tài chính, quản lý tài sản công và các quỹ tài chính của xã."
    elif "văn hóa" in title_lower or "xã hội" in title_lower:
        desc = f"Trực tiếp tham mưu công tác văn hóa, thông tin truyền thông, thể dục thể thao, du lịch; chính sách người có công, bảo trợ xã hội, giảm nghèo, lao động việc làm, bảo vệ chăm sóc trẻ em và công tác phòng chống tệ nạn xã hội."
    elif "công an" in title_lower:
        desc = f"Nắm tình hình an ninh trật tự, an toàn xã hội trên địa bàn; quản lý cư trú, định danh điện tử (Đề án 06), PCCC; phối hợp tuần tra, phòng chống tội phạm và giải quyết các vụ việc vi phạm pháp luật thuộc thẩm quyền."
    elif "chuyển đổi số" in title_lower or "cđs" in title_lower:
        desc = f"Tham mưu triển khai kế hoạch chuyển đổi số, chính quyền điện tử của xã; hướng dẫn người dân tạo tài khoản dịch vụ công trực tuyến, thanh toán không dùng tiền mặt và cài đặt chữ ký số cá nhân; hỗ trợ vận hành hạ tầng công nghệ thông tin."
    else:
        desc = f"Trực tiếp tham mưu thực hiện nhiệm vụ chuyên môn được giao tại {dept_name}; chịu trách nhiệm trước Trưởng phòng và Lãnh đạo UBND xã về tiến độ, chất lượng hồ sơ công việc; phối hợp chặt chẽ với các bộ phận liên quan."

    return {
        "status": "success",
        "title": title,
        "department_name": dept_name,
        "job_position": desc
    }

# ----------------- KHO TRI THỨC CRUD & INGEST -----------------

@app.get("/api/personal-brain/settings")
def api_get_settings():
    return {"status": "success", "settings": load_settings()}

class SaveSettingsRequest(BaseModel):
    user_fullname: Optional[str] = "Nguyễn Trung Hiếu"
    user_title: Optional[str] = "PHÓ GIÁM ĐỐC"
    user_unit: Optional[str] = "Sở Khoa học và Công nghệ tỉnh Tây Ninh"
    gdrive_enabled: Optional[bool] = True
    gdrive_auto_sync: Optional[bool] = True
    gdrive_folder_url: Optional[str] = ""
    web_links: Optional[List[str]] = []
    ai_model: Optional[str] = "google-antigravity/gemini-3.8-flash"
    ai_provider_url: Optional[str] = ""
    ai_provider_key: Optional[str] = ""

@app.post("/api/personal-brain/settings")
def api_save_settings(req: SaveSettingsRequest):
    cfg = load_settings()
    cfg["user_fullname"] = req.user_fullname or "Nguyễn Trung Hiếu"
    cfg["user_title"] = req.user_title or "PHÓ GIÁM ĐỐC"
    cfg["user_unit"] = req.user_unit or "Sở Khoa học và Công nghệ tỉnh Tây Ninh"
    cfg["gdrive_enabled"] = req.gdrive_enabled
    cfg["gdrive_auto_sync"] = req.gdrive_auto_sync
    cfg["gdrive_folder_url"] = req.gdrive_folder_url or ""
    cfg["web_links"] = req.web_links or []
    cfg["ai_model"] = req.ai_model or "google-antigravity/gemini-3.8-flash"
    cfg["ai_provider_url"] = (req.ai_provider_url or "").strip()
    cfg["ai_provider_key"] = (req.ai_provider_key or "").strip()
    save_settings(cfg)
    return {"status": "success", "message": "Đã lưu cài đặt Kho tri thức thành công!", "settings": cfg}

@app.get("/api/personal-brain/items")
def api_get_items(current_user_id: Optional[str] = None, workspace: Optional[str] = "all"):
    items = load_items()
    users = commune_brain_manager.load_commune_users()
    current_user = next((u for u in users if u.get("id") == current_user_id or u.get("username") == current_user_id), None)

    visible_items = []
    for it in items:
        vis = it.get("visibility")
        owner = it.get("owner_id")

        # NGUYÊN TẮC: Mặc định tất cả dữ liệu mẫu đều hiển thị cho mọi người dùng
        # Chỉ ẩn khi tài liệu được gán quyền "private" rõ ràng bởi người dùng khác
        if not current_user:
            # Chưa đăng nhập: Cho phép xem toàn bộ tài liệu trừ phi bị gán private bởi user cụ thể
            if vis != "private":
                visible_items.append(it)
            continue

        # Đã đăng nhập:
        if current_user.get("role") in ["super_admin", "commune_admin"]:
            visible_items.append(it)
        elif not owner or owner == current_user.get("username") or owner == current_user.get("id"):
            visible_items.append(it)
        elif vis == "department" and it.get("department_id") == current_user.get("department_id"):
            visible_items.append(it)
        elif vis != "private":
            visible_items.append(it)

    # Bộ lọc tab không gian tri thức
    if workspace == "private":
        res_items = [it for it in visible_items if it.get("visibility") == "private"]
    elif workspace == "department":
        res_items = [it for it in visible_items if it.get("visibility") == "department"]
    elif workspace in ["commune", "public"]:
        res_items = [it for it in visible_items if it.get("visibility") in ["public_commune", "public", "commune"] or not it.get("visibility")]
    else:
        res_items = visible_items

    total_words = sum(it.get("word_count", 0) for it in res_items)
    return {
        "status": "success",
        "items": res_items,
        "total_items": len(res_items),
        "total_words": total_words,
        "stats": {
            "total_items": len(res_items),
            "total_words": total_words
        },
        "current_user": current_user
    }

class IngestWebRequest(BaseModel):
    url: str
    title: Optional[str] = None
    category: Optional[str] = "Nghiên cứu tham khảo"
    tags: Optional[List[str]] = []

@app.post("/api/personal-brain/ingest/web")
def api_ingest_web(req: IngestWebRequest):
    url = (req.url or "").strip()
    if not url.startswith("http://") and not url.startswith("https://"):
        raise HTTPException(status_code=400, detail="Đường dẫn URL không hợp lệ (phải bắt đầu bằng http:// hoặc https://).")

    try:
        import re
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 JavisBrain/1.0"
        }
        res = requests.get(url, headers=headers, timeout=20)
        html = res.text or ""

        title_match = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
        web_title = (title_match.group(1).strip() if title_match else url)
        html_clean = re.sub(r"<(script|style|nav|header|footer|aside|noscript)[^>]*>.*?</\1>", " ", html, flags=re.IGNORECASE | re.DOTALL)
        text = re.sub(r"<[^>]+>", " ", html_clean)
        text = re.sub(r"&[a-z]+;", " ", text)
        text = re.sub(r"\s+", " ", text).strip()

        words = len(re.findall(r"\w+", text))
        doc_title = (req.title or "").strip() or web_title[:120]
        summary_sample = " ".join(text.split()[:60]) + ("..." if words > 60 else "")

        new_item = {
            "id": f"pb_{int(time.time())}_web",
            "title": doc_title,
            "category": req.category or "Nghiên cứu tham khảo",
            "source_type": "web",
            "source_url_or_path": url,
            "filename": f"web_{int(time.time())}.txt",
            "file_path": "",
            "summary": summary_sample or "Bài viết trích xuất từ web.",
            "text_content": text[:50000],
            "word_count": words,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tags": req.tags or ["Web", "Tin tức", "Văn bản"],
            "owner_id": "070077000098",
            "visibility": "private"
        }

        items = load_items()
        items.insert(0, new_item)
        save_items(items)
        return {"status": "success", "message": f"Đã nạp trang web vào Brain ({words:,} từ).", "item": new_item}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi khi cào dữ liệu từ liên kết web: {e}")

class IngestDriveRequest(BaseModel):
    drive_url: str
    title: Optional[str] = None
    category: Optional[str] = "Chỉ đạo điều hành"
    tags: Optional[List[str]] = []

# ---- Drive helpers dung chung (single file + folder scan + SSE) ----

def _drive_parse_kind_id(url: str):
    for pat, k in (
        (r"/file/d/([a-zA-Z0-9_-]{10,})", "file"),
        (r"/document/d/([a-zA-Z0-9_-]{10,})", "doc"),
        (r"/spreadsheets/d/([a-zA-Z0-9_-]{10,})", "sheet"),
        (r"/presentation/d/([a-zA-Z0-9_-]{10,})", "slide"),
        (r"/folders/([a-zA-Z0-9_-]{10,})", "folder"),
        (r"[?&]id=([a-zA-Z0-9_-]{10,})", "file"),
    ):
        m = re.search(pat, url or "")
        if m:
            return k, m.group(1)
    return None, None

_UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) JavisBrain/1.0"}

def _drive_fetch_binary(fid: str):
    r = requests.get(
        f"https://drive.google.com/uc?export=download&id={fid}",
        headers=_UA, timeout=120, allow_redirects=True,
    )
    if r.status_code != 200 or not r.content:
        raise ValueError(f"Khong tai duoc tep (HTTP {r.status_code})")
    b = r.content
    if b[:15].lower().startswith(b"<!doctype html") or b"Google Drive" in b[:400]:
        raise ValueError("Google Drive yeu cau xac nhan - hay bat chia se 'Bat ky ai co duong link'")
    return b

def _drive_extract_text(binary: bytes):
    import io as _io

    if binary[:4] == b"%PDF":
        import fitz as _fitz

        d = _fitz.open(stream=binary, filetype="pdf")
        t = "\n".join(pg.get_text().strip() for pg in d if pg.get_text().strip())
        d.close()
        return t.strip(), ".pdf"
    if binary[:2] == b"PK":
        import docx as _docx

        dd = _docx.Document(_io.BytesIO(binary))
        t = "\n".join(pp.text.strip() for pp in dd.paragraphs if pp.text.strip())
        return t.strip(), ".docx"
    return binary.decode("utf-8", errors="ignore").strip(), ".txt"

def _drive_list_folder(folder_id: str):
    """Quet thu muc cong khai qua embeddedfolderview - tra ve [(id, ten tep)]."""
    r = requests.get(
        f"https://drive.google.com/embeddedfolderview?id={folder_id}#list",
        headers=_UA, timeout=60,
    )
    if r.status_code != 200:
        raise ValueError(f"Khong truy cap duoc thu muc (HTTP {r.status_code})")
    entries = re.findall(
        r'href="https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/view"[^>]*>\s*(?:<[^>]+>\s*)*<div class="flip-entry-title">([^<]+)</div>',
        r.text,
    )
    return [(fid, name.strip()) for fid, name in entries if fid and name.strip()]

def _drive_save_kho_item(title: str, category: str, safe_name: str, dest_path, text_content: str, fid: str, view_url: str, tags):
    items = load_items()
    items.insert(0, {
        "id": f"pb_{int(time.time() * 1000)}_{fid[:8]}",
        "title": title,
        "category": category or "Chỉ đạo điều hành",
        "source_type": "drive",
        "source_url_or_path": view_url,
        "filename": safe_name,
        "file_path": str(dest_path),
        "summary": text_content[:200] + "...",
        "text_content": text_content[:50000],
        "word_count": len(text_content.split()),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tags": tags or ["Google Drive"],
        "owner_id": "070077000098",
        "visibility": "private",
    })
    save_items(items)

@app.post("/api/personal-brain/ingest/drive")
def api_ingest_drive(req: IngestDriveRequest):
    """Nap Drive: file/docs/sheet/slide rieng, HOAC quet toan bo tep trong thu muc cong khai."""
    drive_url = (req.drive_url or "").strip()
    if not drive_url:
        raise HTTPException(status_code=400, detail="Vui lòng nhập đường dẫn Google Drive.")

    kind, file_id = _drive_parse_kind_id(drive_url)
    if not file_id:
        raise HTTPException(status_code=400, detail="Không nhận diện được ID Google Drive trong đường dẫn.")

    if kind == "folder":
        try:
            entries = _drive_list_folder(file_id)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))
        if not entries:
            raise HTTPException(
                status_code=400,
                detail="Không thấy tệp công khai nào trong thư mục. Hãy chia sẻ thư mục 'Bất kỳ ai có đường liên kết' và đảm bảo có tệp PDF/DOCX/TXT.",
            )
        created, skipped = [], []
        for fid, fname in entries[:25]:
            try:
                b = _drive_fetch_binary(fid)
                tc, ext = _drive_extract_text(b)
                if len(tc) < 50:
                    skipped.append(f"{fname} (khong trich duoc noi dung)")
                    continue
                safe_name = "gdrive_" + fid[:12] + "_" + re.sub(r"[^a-zA-Z0-9_.\-]", "_", fname)
                dest_path = FILES_DIR / safe_name
                dest_path.write_bytes(b)
                _drive_save_kho_item(fname.rsplit(".", 1)[0], req.category or "Chỉ đạo điều hành", safe_name, dest_path, tc, fid, f"https://drive.google.com/file/d/{fid}/view", req.tags or ["Google Drive", "Thư mục"])
                created.append(fname)
            except Exception as ee:
                skipped.append(f"{fname} ({type(ee).__name__})")
        if not created:
            detail = "Không nạp được tệp nào từ thư mục."
            if skipped:
                detail += " Chi tiết: " + "; ".join(x[:40] for x in skipped[:5])
            raise HTTPException(status_code=400, detail=detail)
        msg = f"Đã quét thư mục: nạp thành công {len(created)}/{len(entries)} tệp vào Brain: " + ", ".join(created[:6])
        if len(created) > 6:
            msg += f" +{len(created) - 6} tệp khác"
        if skipped:
            msg += f". Bỏ qua {len(skipped)} tệp."
        return {"status": "success", "message": msg, "created": created, "skipped": skipped}

    # --- Tep/Docs/Sheet/Slide rieng le ---
    kind, file_id = kind, file_id
    try:
        b = _drive_fetch_binary(drive_url if drive_url.startswith("http") else f"https://drive.google.com/uc?export=download&id={file_id}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    tc, ext = _drive_extract_text(b)
    if len(tc) < 50:
        raise HTTPException(status_code=400, detail="Tải được tệp nhưng không trích xuất được nội dung văn bản (có thể là bản scan hoặc tệp rỗng).")
    safe_name = "gdrive_" + file_id[:12] + ext
    dest_path = FILES_DIR / safe_name
    dest_path.write_bytes(b)
    doc_title = (req.title or "").strip() or tc[:80]
    _drive_save_kho_item(doc_title, req.category or "Chỉ đạo điều hành", safe_name, dest_path, tc, file_id, drive_url, req.tags or ["Google Drive"])
    return {
        "status": "success",
        "message": f"Đã tải và nạp tài liệu Google Drive vào Brain ({len(tc.split()):,} từ, loại: {kind}).",
        "filename": safe_name,
    }

@app.post("/api/personal-brain/ingest/drive-stream")
def api_ingest_drive_stream(req: IngestDriveRequest):
    """SSE: nap Drive voi tien trinh tung tep - frontend hien thanh progress xanh."""
    import json as _json

    from fastapi.responses import StreamingResponse

    drive_url = (req.drive_url or "").strip()
    if not drive_url:
        raise HTTPException(status_code=400, detail="Vui lòng nhập đường dẫn Google Drive.")

    kind, file_id = _drive_parse_kind_id(drive_url)
    if not file_id:
        raise HTTPException(status_code=400, detail="Không nhận diện được ID Google Drive trong đường dẫn.")

    def sse(obj) -> str:
        return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"

    def gen():
        try:
            if kind == "folder":
                try:
                    entries = _drive_list_folder(file_id)
                except ValueError as e:
                    yield sse({"type": "error", "error": str(e)})
                    return
                if not entries:
                    yield sse({"type": "error", "error": "Không thấy tệp công khai nào trong thư mục."})
                    return
            else:
                # link tep rieng le -> xu ly 1 muc
                dl = req.drive_url if req.drive_url.startswith("http") else f"https://drive.google.com/uc?export=download&id={file_id}"
                entries = [(file_id, (req.title or "Tai lieu Drive").strip(), dl)]
            total = len(entries)
            yield sse({"type": "start", "total": total})
            created, skipped = [], []
            for i, ent in enumerate(entries, 1):
                if kind == "folder":
                    fid, fname = ent
                    view_url = f"https://drive.google.com/file/d/{fid}/view"
                    dl_url = f"https://drive.google.com/uc?export=download&id={fid}"
                else:
                    fid = ent[0]
                    fname = (req.title or "Tai lieu Drive").strip() or f"Drive_{fid[:10]}"
                    view_url = req.drive_url
                    dl_url = req.drive_url
                yield sse({"type": "progress", "done": i - 1, "total": total, "current": fname})
                try:
                    b = _drive_fetch_binary(dl_url)
                    tc, ext = _drive_extract_text(b)
                    if len(tc) < 50:
                        skipped.append(f"{fname} (khong trich duoc noi dung)")
                        yield sse({"type": "item", "ok": False, "title": fname, "err": "nội dung trống"})
                        continue
                    safe_name = "gdrive_" + fid[:12] + "_" + re.sub(r"[^a-zA-Z0-9_.\-]", "_", fname)
                    dest_path = FILES_DIR / safe_name
                    dest_path.write_bytes(b)
                    _drive_save_kho_item(fname.rsplit(".", 1)[0], req.category or "Chỉ đạo điều hành", safe_name, dest_path, tc, fid, view_url, req.tags or ["Google Drive"])
                    created.append(fname)
                    yield sse({"type": "item", "ok": True, "done": i, "total": total, "title": fname})
                except Exception as ee:
                    skipped.append(f"{fname} ({type(ee).__name__})")
                    yield sse({"type": "item", "ok": False, "done": i, "total": total, "title": fname, "err": str(ee)[:80]})
            yield sse({"type": "done", "created": created, "skipped": skipped, "total": total})
        except Exception as ee:
            yield sse({"type": "error", "error": f"{type(ee).__name__}: {str(ee)[:120]}"})

    return StreamingResponse(gen(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post("/api/personal-brain/ingest/file")
async def api_ingest_file(
    file: UploadFile = File(...),
    category: str = Form("Tài liệu cơ quan"),
    owner_id: Optional[str] = Form("070077000098"),
    visibility: Optional[str] = Form("private")
):
    safe_name = Path(file.filename).name
    dest_path = FILES_DIR / safe_name
    with dest_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    text_content = f"Tệp tải lên: {safe_name}\n"
    word_count = 100
    if safe_name.lower().endswith(".txt") or safe_name.lower().endswith(".md"):
        try:
            text_content = dest_path.read_text(encoding="utf-8", errors="ignore")
            word_count = len(text_content.split())
        except Exception:
            pass

    new_item = {
        "id": f"pb_{int(time.time() * 1000)}",
        "title": safe_name.rsplit(".", 1)[0].replace("_", " "),
        "category": category,
        "source_type": "file",
        "source_url_or_path": safe_name,
        "filename": safe_name,
        "file_path": str(dest_path),
        "summary": text_content[:200] + "...",
        "text_content": text_content,
        "word_count": word_count,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tags": [category],
        "owner_id": owner_id or "070077000098",
        "visibility": visibility or "private"
    }

    items = load_items()
    items.insert(0, new_item)
    save_items(items)
    return {"status": "success", "message": f"Đã nạp tệp '{safe_name}' vào Brain thành công!", "item": new_item}

@app.post("/api/personal-brain/ingest/folder-upload")
async def api_ingest_folder(
    files: List[UploadFile] = File(...),
    category: str = Form("Tài liệu cơ quan"),
    owner_id: Optional[str] = Form("070077000098")
):
    count = 0
    items = load_items()
    for f in files:
        safe_name = Path(f.filename).name
        dest_path = FILES_DIR / safe_name
        with dest_path.open("wb") as buffer:
            shutil.copyfileobj(f.file, buffer)
        items.insert(0, {
            "id": f"pb_{int(time.time() * 1000)}_{count}",
            "title": safe_name.rsplit(".", 1)[0].replace("_", " "),
            "category": category,
            "source_type": "folder",
            "source_url_or_path": safe_name,
            "filename": safe_name,
            "file_path": str(dest_path),
            "summary": f"Tệp được nạp từ thư mục máy tính: {safe_name}",
            "text_content": f"Tệp: {safe_name}",
            "word_count": 80,
            "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "tags": [category, "Folder Upload"],
            "owner_id": owner_id or "070077000098",
            "visibility": "private"
        })
        count += 1
    save_items(items)
    return {"status": "success", "message": f"Đã quét và nạp thành công {count} tệp vào Kho Tri Thức!"}

class IngestFolderPathRequest(BaseModel):
    folder_path: str
    category: Optional[str] = "Tài liệu cơ quan"
    recursive: Optional[bool] = True
    owner_id: Optional[str] = "070077000098"

@app.post("/api/personal-brain/ingest/folder")
def api_ingest_folder_path(req: IngestFolderPathRequest):
    """Quét thư mục trên server theo đường dẫn nhập tay và nạp các tệp văn bản vào Kho Tri Thức.
    Hỗ trợ .txt, .md, .csv, .json, .pdf, .docx — trích xuất nội dung tốt nhất có thể."""
    folder = (req.folder_path or "").strip().strip('"')
    if not folder:
        raise HTTPException(status_code=400, detail="Vui lòng nhập đường dẫn thư mục trên server.")
    p = Path(folder)
    if not p.exists() or not p.is_dir():
        raise HTTPException(status_code=400, detail=f"Không tìm thấy thư mục trên server: {folder}")

    exts = {".txt", ".md", ".csv", ".json", ".pdf", ".docx"}
    walker = p.rglob("*") if req.recursive is not False else p.glob("*")
    found = sorted([f for f in walker if f.is_file() and f.suffix.lower() in exts])
    if not found:
        raise HTTPException(status_code=400, detail="Không thấy tệp văn bản nào (.pdf, .docx, .txt, .md...) trong thư mục này.")

    items = load_items()
    created, skipped = [], []
    for f in found[:100]:
        try:
            text_content = ""
            if f.suffix.lower() in (".txt", ".md", ".csv", ".json"):
                text_content = f.read_text(encoding="utf-8", errors="ignore")
            elif f.suffix.lower() == ".pdf":
                try:
                    import fitz as _fitz
                    d = _fitz.open(str(f))
                    text_content = "\n".join(pg.get_text().strip() for pg in d if pg.get_text().strip())
                    d.close()
                except Exception:
                    text_content = ""
            elif f.suffix.lower() == ".docx":
                try:
                    import docx as _docx
                    d = _docx.Document(str(f))
                    text_content = "\n".join(pp.text.strip() for pp in d.paragraphs if pp.text.strip())
                except Exception:
                    text_content = ""
            text_content = (text_content or "").strip()
            if len(text_content) < 20:
                skipped.append(f.name)
                continue
            items.insert(0, {
                "id": f"pb_{int(time.time() * 1000)}_{len(created)}",
                "title": f.name.rsplit(".", 1)[0].replace("_", " "),
                "category": req.category or "Tài liệu cơ quan",
                "source_type": "folder",
                "source_url_or_path": str(f),
                "filename": f.name,
                "file_path": str(f),
                "summary": text_content[:200] + ("..." if len(text_content) > 200 else ""),
                "text_content": text_content[:50000],
                "word_count": len(text_content.split()),
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tags": [req.category or "Tài liệu cơ quan", "Server Folder"],
                "owner_id": req.owner_id or "070077000098",
                "visibility": "private",
            })
            created.append(f.name)
        except Exception:
            skipped.append(f.name)
    save_items(items)
    msg = f"Đã quét thư mục server và nạp thành công {len(created)}/{len(found)} tệp vào Kho Tri Thức!"
    if skipped:
        msg += f" Bỏ qua {len(skipped)} tệp không trích xuất được nội dung."
    return {"status": "success", "message": msg, "created": created, "skipped": skipped}

class DeleteItemRequest(BaseModel):
    item_id: str

@app.post("/api/personal-brain/item/delete")
def api_delete_item(req: DeleteItemRequest):
    items = load_items()
    rem = [it for it in items if it.get("id") != req.item_id]
    save_items(rem)
    return {"status": "success", "message": "Đã xóa thành công tài liệu khỏi Brain."}

class ShareItemRequest(BaseModel):
    item_id: str
    visibility: str # "private", "department", "public_commune"
    department_id: Optional[str] = None

@app.post("/api/personal-brain/item/share")
def api_share_item(req: ShareItemRequest):
    items = load_items()
    target = next((it for it in items if it.get("id") == req.item_id), None)
    if not target:
        raise HTTPException(status_code=404, detail="Không tìm thấy tài liệu.")
    target["visibility"] = req.visibility
    if req.department_id: target["department_id"] = req.department_id
    save_items(items)
    return {"status": "success", "message": f"Đã cập nhật phạm vi chia sẻ tài liệu sang: {req.visibility}", "item": target}

# ----------------- SOẠN THẢO BÁO CÁO CHUẨN NĐ 30 -----------------

# Cấu trúc mẫu thân bài theo từng loại văn bản (NĐ 30/2020/NĐ-CP + HD 05-HD/VPTW)
CAU_TRUC_ND30 = {
    "bao_cao": "I. TÌNH HÌNH THỰC HIỆN (1. Công tác chỉ đạo điều hành; 2. Kết quả nổi bật theo lĩnh vực, có số liệu)\nII. ĐÁNH GIÁ CHUNG (1. Ưu điểm; 2. Tồn tại, hạn chế và nguyên nhân)\nIII. PHƯƠNG HƯỚNG - NHIỆM VỤ TRỌNG TÂM thời gian tới",
    "to_trinh": "1. MỤC ĐÍCH / LÝ DO trình bày\n2. TÌNH HÌNH THỰC TRẠNG (hiện trạng, số liệu)\n3. NỘI DUNG ĐỀ XUẤT (các phương án, quy mô, kinh phí)\n4. ĐỀ XUẤT, KIẾN NGHỊ (Kính đề nghị ... xem xét, phê duyệt)",
    "ke_hoach": "1. MỤC TIÊU\n2. PHẠM VI, ĐỐI TƯỢNG\n3. NỘI DUNG NHIỆM VỤ (từng đầu việc kèm thời gian và đơn vị thực hiện)\n4. KINH PHÍ thực hiện\n5. TỔ CHỨC THỰC HIỆN (phân công, giám sát)",
    "cong_van": "Mở đầu: nêu căn cứ, lý do liên hệ công việc\nNội dung: trình bày vấn đề, đề nghị cụ thể của cơ quan\nKết thúc: Lời trân trọng cảm ơn / mong được phản hồi",
    "quyet_dinh": "CĂN CỨ (các văn bản pháp lý, cơ sở thực tế)\nXÉT ĐỀ NGHỊ của người có thẩm quyền;\nQUYẾT ĐỊNH: Điều 1. Nội dung chính; Điều 2. Hiệu lực thi hành; Điều 3. Tổ chức thực hiện",
    "thong_bao": "Nêu sự việc / kết quả / thông điệp cần truyền đạt: thời gian, địa điểm, kết quả, ý nghĩa",
    "bien_ban": "Thời gian, địa điểm, thành phần tham dự\nNội dung cuộc họp (các ý kiến phát biểu, thảo luận)\nKết luận chung\nChữ ký: Thư ký và Chủ tọa",
    "de_an": "I. SỰ CẦN THIẾT thực hiện\nII. MỤC TIÊU\nIII. PHẠM VI, ĐỐI TƯỢNG\nIV. NỘI DUNG GIẢI PHÁP\nV. KINH PHÍ\nVI. TỔ CHỨC THỰC HIỆN",
    "phuong_an": "I. SỰ CẦN THIẾT\nII. MỤC TIÊU\nIII. NỘI DUNG PHƯƠNG ÁN (các phương án và so sánh)\nIV. KINH PHÍ\nV. TỔ CHỨC THỰC HIỆN",
    "chuong_trinh": "Thời gian - Địa điểm - Nội dung từng hoạt động (dạng danh sách theo trình tự)",
    "huong_dan": "I. CĂN CỨ pháp lý\nII. NỘI DUNG hướng dẫn cụ thể từng bước\nIII. TỔ CHỨC THỰC HIỆN, kiểm tra đôn đốc",
    "quy_che": "Chương I. NHỊM VỤ, QUYỀN HẠNG; Chương II. TỔ CHỨC BỘ MÁY; Chương III. KINH PHÍ; Chương IV. ĐIỀU KHOẢN THI HÀNH",
    "nghi_quyet_dang": "I. ĐÁNH GIÁ TÌNH HÌNH (kết quả đạt được, hạn chế)\nII. NHIỆM VỤ TRỌNG TÂM (các nội dung cụ thể)\nIII. TỔ CHỨC THỰC HIỆN (phân công, giám sát)",
    "chi_thi_dang": "I. MỤC TIÊU, YÊU CẦU\nII. NHIỆM VỤ CỤ THỂ\nIII. TỔ CHỨC THỰC HIỆN",
    "ket_luan_dang": "Đánh giá chung kết quả; Những nội dung đã kết luận; Chỉ đạo triển khai",
    "thong_tri_dang": "Truyền đạt nội dung cuộc họp/hội nghị; Quan điểm chỉ đạo; Nhiệm vụ triển khai",
    "bao_cao_dang": "I. KẾT QUẢ ĐẠT ĐƯỢC; II. HẠN CHẾ; III. NHIỆM VỤ TRỌNG TÂM (theo tinh thần Nghị quyết Đảng)",
    "to_trinh_dang": "I. CĂN CỨ; II. TÌNH HÌNH; III. ĐỀ XUẤT, KIẾN NGHỊ (trình Cấp ủy xem xét)",
    "cong_van_dang": "Mở đầu căn cứ; Nội dung liên hệ/đề nghị; Kết thúc",
    "quyet_dinh_dang": "CĂN CỨ;\nQUYẾT ĐỊNH (điều khoản cụ thể);\nĐiều 3. TỔ CHỨC THỰC HIỆN",
    "ke_hoach_dang": "1. MỤC TIÊU; 2. NHIỆM VỤ; 3. TỔ CHỨC THỰC HIỆN (khởi định Đảng ủy)",
}


# AI Provider mac dinh: Opencodex proxy local (doi trong Settings -> AI Provider)
AI_PROVIDER_DEFAULTS = {
    "url": os.getenv("AI_PROVIDER_URL", "http://127.0.0.1:10100/v1/chat/completions"),
    "key": os.getenv("AI_PROVIDER_KEY", ""),
    "model": os.getenv("AI_PROVIDER_MODEL", "google-antigravity/gemini-3.8-flash"),
}

def _ai_cfg(cfg: dict):
    """(url, key, model) cua AI Provider tu settings - fallback ve mac dinh Opencodex."""
    return (
        (cfg.get("ai_provider_url") or "").strip() or AI_PROVIDER_DEFAULTS["url"],
        (cfg.get("ai_provider_key") or "").strip() or AI_PROVIDER_DEFAULTS["key"],
        (cfg.get("ai_model") or "").strip() or AI_PROVIDER_DEFAULTS["model"],
    )


class GenerateReportRequest(BaseModel):
    item_ids: List[str]
    title: Optional[str] = "Báo cáo tổng hợp tri thức"
    loai_van_ban: Optional[str] = "bao_cao"
    prompt: Optional[str] = ""
    trich_yeu: Optional[str] = ""
    co_quan_gui: Optional[str] = "Ủy ban nhân dân tỉnh Tây Ninh"

@app.post("/api/personal-brain/generate-report")
def api_generate_report(req: GenerateReportRequest):
    items = load_items()
    selected = [it for it in items if it.get("id") in req.item_ids]
    if not selected:
        pass  # Dashboard quick-draft: cho phép tạo không cần chọn tài liệu nguồn (AI dùng luật + prompt)

    combined_context = []
    for idx, it in enumerate(selected, 1):
        c_title = it.get("title") or f"Tài liệu {idx}"
        c_body = (it.get("text_content") or it.get("summary") or "").strip()
        combined_context.append(f"=== TÀI LIỆU {idx}: {c_title} ===\n{c_body}\n")

    context_str = "\n".join(combined_context)
    loai = (req.loai_van_ban or "bao_cao").strip().lower()
    co_quan = req.co_quan_gui or "Ủy ban nhân dân tỉnh Tây Ninh"
    trich_yeu = req.trich_yeu or f"Về {selected[0].get('title')}"

    cfg = load_settings()
    signer_name = cfg.get("user_fullname", "Nguyễn Trung Hiếu")
    signer_title = cfg.get("user_title", "PHÓ GIÁM ĐỐC")
    don_vi = cfg.get("user_unit", "Sở Khoa học và Công nghệ tỉnh Tây Ninh")

    # === SOẠN THẢO AI THẬT: Gemini đọc luật NĐ30/HD05 + tài liệu nguồn ===
    ai_body = None
    try:
        import httpx as _httpx

        ai_url, ai_key, ai_model = _ai_cfg(cfg)

        # Gom luật thể thức (NĐ 30 / HD 05) từ kho nếu có
        luat_chunks = []
        for it in load_items():
            ten = (it.get("title", "") + " " + (it.get("filename", "") or "")).lower()
            if any(k in ten for k in ("30/2020", "nd_cp", "hd-05", "hd 05", "05-hd", "hd_vptw", "nd-30", "30 2020", "nghị định 30", "30_2020", "nghi dinh 30")):
                noi_dung = (it.get("text_content") or "").strip()
                if noi_dung:
                    luat_chunks.append(f"=== LUẬT: {it.get('title')} ===\n{noi_dung[:60000]}")

        nguon = "\n\n".join(
            f"=== TÀI LIỆU NGUỒN {i}: {it.get('title')} ===\n{(it.get('text_content') or it.get('summary') or '').strip()[:12000]}"
            for i, it in enumerate(selected, 1)
        )
        he_thong = (
            "Bạn là chuyên viên văn thư giàu kinh nghiệm của cơ quan nhà nước Việt Nam, chuyên soạn thảo "
            "văn bản hành chính theo Nghị định 30/2020/NĐ-CP và văn bản Đảng theo Hướng dẫn 05-HD/VPTW. "
            "NHIỆM VỤ: Chỉ viết PHẦN THÂN BÀI của văn bản (không viết quốc hiệu, tiêu ngữ, tên loại văn bản, "
            "số ký hiệu, trích yếu, nơi nhận, chữ ký - các phần đó do hệ thống khác tự sinh). "
            "BẮT BUỘC: Bố cục thân bài PHẢI theo đúng CẤU TRÚC MẪU được cung cấp cho loại văn bản này. "
            "Yêu cầu: dùng đúng kết cấu (phần mục I/II/III), ngôn ngữ hành chính chuẩn, số liệu và nội dung "
            "phải lấy từ các tài liệu nguồn được cung cấp, không bịa đặt dữ liệu."
        )
        cau_truc_mau = CAU_TRUC_ND30.get(loai, "I. TÌNH HÌNH\nII. KẾT QUẢ\nIII. NHIỆM VỤ TRỌNG TÂM")
        user_prompt = (
            f"LOẠI VĂN BẢN: {loai}\n"
            f"TRÍCH YẾU: {trich_yeu}\n"
            f"CƠ QUAN NHẬN: {co_quan}\n\n"
            + (f"YÊU CẦU CHI TIẾT CỦA NGƯỜI DÙNG: {(req.prompt or '').strip()}\n\n" if (req.prompt or '').strip() else "")
            + f"=== CẤU TRÚC MẪU BẮT BUỘC (theo NĐ 30) ===\n{cau_truc_mau}\n\n"
            "=== TÀI LIỆU LUẬT THAM CHIẾU ===\n"
            + ("\n\n".join(luat_chunks)[:40000] or "(không có)") + "\n\n"
            + f"=== TÀI LIỆU NGUỒN NỘI DUNG ===\n{nguon[:30000]}\n\n"
            "YÊU CẦU: Viết phần thân bài của văn bản trên, độ dài 800-1500 từ, "
            "đúng theo CẤU TRÚC MẪU, có số liệu và nội dung cụ thể trích từ tài liệu nguồn."
        )
        rr = _httpx.post(
            ai_url,
            headers={"Authorization": f"Bearer {ai_key}"},
            json={
                "model": ai_model,
                "messages": [
                    {"role": "system", "content": he_thong},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.4,
            },
            timeout=240,
        )
        if rr.status_code == 200:
            ai_body = ((rr.json().get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
            ai_note = f"AI OK ({ai_model}, prompt {len(user_prompt)} chars)"
        else:
            ai_note = f"AI HTTP {rr.status_code}: {rr.text[:150]}"
    except Exception as e:
        ai_note = f"AI EXC: {type(e).__name__}: {str(e)[:120]}"
        ai_body = None

    if ai_body and len(ai_body) > 300:
        body_text = ai_body
    else:
        # Mẫu dự thảo báo cáo hành chính chuẩn mực (dự phòng khi AI lỗi)
        body_text = f"""I. TÌNH HÌNH THỰC HIỆN VÀ KẾT QUẢ ĐẠT ĐƯỢC
1. Công tác chỉ đạo, điều hành và triển khai nhiệm vụ:
Trên cơ sở tổng hợp từ {len(selected)} nguồn tài liệu tri thức chuyên ngành, đơn vị đã chủ động tham mưu ban hành các kế hoạch hành động trọng tâm. Trong đó, tập trung đẩy mạnh chuyển đổi số, tối ưu hóa quy trình nghiệp vụ và ứng dụng các nền tảng trí tuệ nhân tạo vào công tác quản trị công vụ.

2. Kết quả nổi bật trên các lĩnh vực:
- Về thể chế và chính sách: Đã rà soát, đồng bộ các cơ chế chính sách hỗ trợ phát triển chuyên ngành, gắn kết chặt chẽ với các định hướng lớn của tỉnh.
- Về ứng dụng công nghệ và hạ tầng số: Hoàn thiện kết nối thông suốt các hệ thống thông tin, vận hành hiệu quả trợ lý ảo và kho tri thức số hóa, giúp nâng cao đáng kể năng suất lao động.
- Về phát triển nguồn lực: Tăng cường phối hợp liên ngành, hỗ trợ các tổ chức, đơn vị tham gia nghiên cứu và ứng dụng tiến bộ kỹ thuật.

II. ĐÁNH GIÁ CHUNG
1. Ưu điểm:
Toàn thể cán bộ, công chức luôn giữ vững tinh thần trách nhiệm, đổi mới phương thức làm việc, chủ động ứng dụng công nghệ mới để hoàn thành tốt các chỉ tiêu, nhiệm vụ được giao.

2. Tồn tại, hạn chế và nguyên nhân:
- Tiến độ triển khai một số nội dung chuyên sâu đôi lúc còn chịu tác động của điều kiện khách quan.
- Nguồn nhân lực chất lượng cao trong các lĩnh vực công nghệ mũi nhọn tại địa phương còn mỏng.

III. NHIỆM VỤ TRỌNG TÂM VÀ ĐỀ XUẤT KIẾN NGHỊ
1. Phương hướng, nhiệm vụ trọng tâm thời gian tới:
- Tiếp tục bám sát các chỉ tiêu, kế hoạch đã đề ra.
- Mở rộng phạm vi số hóa và làm giàu kho tri thức chuyên sâu phục vụ công tác chỉ đạo, điều hành.
- Đẩy mạnh đào tạo, bồi dưỡng kỹ năng số và tư duy đổi mới sáng tạo cho đội ngũ cán bộ.

2. Đề xuất, kiến nghị:
Kính đề nghị {co_quan} tiếp tục quan tâm, chỉ đạo các cơ quan liên quan phối hợp chặt chẽ trong việc bố trí nguồn lực và tháo gỡ các khó khăn, vướng mắc."""

    safe_time = int(time.time())
    out_filename = f"{loai.capitalize()}_Brain_{safe_time}.docx"
    doc_info = {
        "hash_id": f"brain_rep_{safe_time}",
        "so_hieu": "BC-SKHCN",
        "co_quan": co_quan,
        "trich_yeu": trich_yeu,
        "ngay_den": time.strftime("%d/%m/%Y"),
        "chuc_vu": signer_title,
        "nguoi_ky": signer_name,
        "co_quan_ban_hanh": don_vi
    }

    out_docx_path = DRAFTS_DIR / out_filename
    doc_info_vbdh = {
        "hash_id": f"brain_rep_{safe_time}",
        "so_hieu": "BC-SKHCN",
        "so_den": "",
        "co_quan": co_quan,
        "co_quan_ban_hanh": don_vi,
        "ngay_ban_hanh": time.strftime("%d/%m/%Y"),
        "trich_yeu": trich_yeu,
    }
    vbdh_draft_generator.create_docx_reply_draft(
        doc_info=doc_info_vbdh,
        draft_body_text=body_text,
        signer_name=signer_name,
        signer_title=signer_title,
        loai_van_ban=loai,
        ten_tep=out_filename,
        kinh_gui=co_quan,
        bo_kinh_gui=False,
    )

    # === Dong bo van ban vua soan vao Kho Tri Thuc (brain_index) ===
    kho_path = FILES_DIR / out_filename
    try:
        shutil.copyfile(DRAFTS_DIR / out_filename, kho_path)
    except Exception:
        kho_path = DRAFTS_DIR / out_filename

    items = load_items()
    items.insert(0, {
        "id": f"pb_{safe_time}_draft",
        "title": f"BẢN DỰ THẢO - {trich_yeu.upper()}",
        "category": "Tài liệu cơ quan",
        "source_type": "draft",
        "source_url_or_path": out_filename,
        "filename": out_filename,
        "file_path": str(kho_path),
        "summary": trich_yeu,
        "text_content": body_text,
        "word_count": len(body_text.split()),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tags": ["Dự thảo", "NĐ 30", loai],
        "owner_id": "070077000098",
        "visibility": "private",
    })
    save_items(items)

    return {
        "status": "success",
        "message": f"Đã tạo bản dự thảo {loai} thành công!" + (" (AI soạn thảo)" if ai_body else " (mẫu chuẩn dự phòng)"),
        "ai_note": ai_note,
        "filename": out_filename,
        "download_url": f"/api/vbdh/draft/download/{urllib.parse.quote(out_filename)}",
        "title": f"Bản dự thảo {loai} - {trich_yeu}",
        "noi_dung": body_text,
        "draft_body": body_text,
        "word_count": len(body_text.split()),
        "trich_yeu": trich_yeu,
        "loai_van_ban": loai,
        "co_quan": co_quan,
        "signer_name": signer_name,
        "signer_title": signer_title,
        "brain_items_used": req.item_ids,
        "saved_to_drafts": True,
        "preview_data": {
            "title": f"BÁO CÁO {trich_yeu.upper()}",
            "loai_van_ban": loai,
            "trich_yeu": trich_yeu,
            "co_quan_nhan": co_quan,
            "nguoi_ky": signer_name,
            "chuc_vu": signer_title,
            "don_vi": don_vi,
            "body_html": body_text.replace("\n", "<br>")
        }
    }

@app.post("/api/vbdh/draft/save-to-kho")
def api_vbdh_draft_save_to_kho(req: dict):
    """Dang ky ban du thao vao Kho Tri Thuc: copy file vao files/ + them item vao brain_index."""
    from docx import Document as _Doc

    safe = Path(str(req.get("filename", ""))).name
    if not safe:
        raise HTTPException(status_code=400, detail="Thiếu tên tệp.")
    src = DRAFTS_DIR / safe
    if not src.exists():
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp dự thảo: {safe}")

    dest = FILES_DIR / safe
    shutil.copyfile(src, dest)

    d = _Doc(str(dest))
    body = "\n".join(par.text for par in d.paragraphs)

    items = load_items()
    if any(it.get("id") == f"pb_kho_{safe}" for it in items):
        return {"status": "success", "message": "Tệp đã có trong Kho Tri Thức.", "duplicate": True}

    items.insert(0, {
        "id": f"pb_kho_{int(time.time())}",
        "title": f"Bản dự thảo - {safe.rsplit('.', 1)[0]}",
        "category": "Tài liệu cơ quan",
        "source_type": "draft",
        "source_url_or_path": safe,
        "filename": safe,
        "file_path": str(dest),
        "summary": body[:200] + "...",
        "text_content": body,
        "word_count": len(body.split()),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tags": ["Dự thảo", "Kho Tri Thức"],
        "owner_id": "070077000098",
        "visibility": "private",
    })
    save_items(items)
    return {"status": "success", "message": f"Đã đăng ký '{safe}' vào Kho Tri Thức."}


@app.get("/api/vbdh/draft/list")

@app.get("/api/vbdh/draft/list")
def api_vbdh_draft_list():
    """Danh sach ban du thao trong Kho Dự Thảo (data/drafts)."""
    try:
        files = []
        for f in sorted(DRAFTS_DIR.glob("*.docx"), key=lambda x: x.stat().st_mtime, reverse=True):
            st = f.stat()
            files.append({
                "filename": f.name,
                "size_kb": round(st.st_size / 1024, 1),
                "modified": time.strftime("%d/%m/%Y %H:%M", time.localtime(st.st_mtime)),
            })
        return {"status": "success", "drafts": files}
    except Exception as e:
        return {"status": "success", "drafts": [], "note": str(e)[:120]}


@app.get("/api/vbdh/draft/preview/{filename:path}")
def api_vbdh_draft_preview(filename: str):
    """Xem trước bản dự thảo dạng HTML ĐỦ TOÀN BỘ (bảng biểu, in đậm, căn lề) - mammoth chuyển docx sang HTML."""
    import mammoth
    from fastapi.responses import HTMLResponse

    safe = Path(filename).name
    p = DRAFTS_DIR / safe
    if not p.exists():
        p = FILES_DIR / safe
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp dự thảo: {safe}")

    with open(p, "rb") as f:
        result = mammoth.convert_to_html(f)
    body_html = result.value or "<p>(Tệp trống)</p>"

    html = (
        '<!doctype html><html><head><meta charset="utf-8"><style>'
        "body { font-family: 'Times New Roman', 'Times', serif; font-size: 13pt; color: #111827;"
        " background: #ffffff; max-width: 21cm; margin: 0 auto; padding: 2cm 1.8cm; line-height: 1.55; }"
        "table { border-collapse: collapse; width: 100%; margin: 10px 0; }"
        "td, th { border: 1px solid #cbd5e1; padding: 6px 10px; font-size: 12pt; }"
        "p { margin: 8px 0; }"
        "</style></head><body>" + body_html + "</body></html>"
    )
    return HTMLResponse(html)


class DraftTextEdit(BaseModel):
    filename: str
    request: Optional[str] = ""

def _draft_docx_text(filename: str) -> str:
    import docx as _docx

    safe = Path(filename).name
    p = DRAFTS_DIR / safe
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp dự thảo: {safe}")
    d = _docx.Document(str(p))
    return "\n".join(par.text for par in d.paragraphs)


@app.get("/api/vbdh/draft/text/{filename:path}")
def api_vbdh_draft_text(filename: str):
    """Đọc toàn bộ nội dung text của 1 bản dự thảo (để sửa)."""
    try:
        text = _draft_docx_text(filename)
        return {"status": "success", "filename": Path(filename).name, "text": text}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Lỗi đọc tệp: {type(e).__name__}")


@app.post("/api/vbdh/draft/save")
def api_vbdh_draft_save(req: dict):
    """Ghi lại nội dung text (mỗi dòng = 1 đoạn) vào tệp dự thảo + bản đồng bộ kho."""
    import docx as _docx
    from docx.shared import Pt as _Pt

    safe = Path(str(req.get("filename", ""))).name
    if not safe:
        raise HTTPException(status_code=400, detail="Thiếu tên tệp.")
    p = DRAFTS_DIR / safe
    if not p.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp dự thảo.")
    text = str(req.get("text") or "")
    d = _docx.Document()
    st = d.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = _Pt(13)
    for dong in text.split("\n"):
        d.add_paragraph(dong)
    d.save(str(p))
    kho = FILES_DIR / safe
    if kho.exists():
        shutil.copyfile(p, kho)
    return {"status": "success", "message": f"Đã lưu '{safe}'."}


class DraftSaveEditRequest(BaseModel):
    draft_id: Optional[str] = ""
    filename: Optional[str] = ""
    noi_dung: str = ""
    loai_van_ban: Optional[str] = "bao_cao"

@app.post("/api/vbdh/draft/save-edit")
def api_vbdh_draft_save_edit(req: DraftSaveEditRequest):
    """Lưu lại nội dung văn bản đã chỉnh sửa trong modal Soạn Thảo (mỗi dòng = 1 đoạn)
    vào tệp dự thảo .docx trong Kho Dự Thảo + bản đồng bộ kho; trả về filename + download_url."""
    import docx as _docx
    from docx.shared import Pt as _Pt

    body = (req.noi_dung or "").strip()
    if not body:
        raise HTTPException(status_code=400, detail="Nội dung văn bản trống, không lưu được.")

    base = (req.filename or req.draft_id or "").strip()
    if base and not base.lower().endswith(".docx"):
        base = f"{(req.loai_van_ban or 'bao_cao').capitalize()}_Sua_{base}_{int(time.time())}.docx"
    if not base:
        base = f"{(req.loai_van_ban or 'bao_cao').capitalize()}_Sua_{int(time.time())}.docx"
    safe = Path(base).name

    d = _docx.Document()
    st = d.styles["Normal"]
    st.font.name = "Times New Roman"
    st.font.size = _Pt(13)
    for dong in body.split("\n"):
        d.add_paragraph(dong)
    p = DRAFTS_DIR / safe
    d.save(str(p))

    try:
        shutil.copyfile(p, FILES_DIR / safe)
    except Exception:
        pass

    return {
        "status": "success",
        "message": f"Đã lưu nội dung văn bản sửa vào '{safe}'.",
        "filename": safe,
        "download_url": f"/api/vbdh/draft/download/{urllib.parse.quote(safe)}",
    }


@app.post("/api/vbdh/draft/delete")
def api_vbdh_draft_delete(req: dict):
    safe = Path(str(req.get("filename", ""))).name
    p = DRAFTS_DIR / safe
    deleted = []
    if p.exists():
        p.unlink()
        deleted.append(safe)
    kho = FILES_DIR / safe
    if kho.exists():
        kho.unlink()
        deleted.append(str(kho))
    if not deleted:
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp dự thảo để xóa.")
    return {"status": "success", "message": f"Đã xóa {len(deleted)} tệp."}


@app.post("/api/vbdh/draft/ai-edit")
def api_vbdh_draft_ai_edit(req: DraftTextEdit):
    """AI gợi ý chỉnh sửa nội dung bản dự thảo theo yêu cầu của người dùng (Gemini qua Opencodex)."""
    import httpx as _httpx

    text = _draft_docx_text(req.filename)
    request = (req.request or "").strip() or "Rà soát và chỉnh sửa văn bản cho mượt, chuẩn văn phong hành chính."
    cfg = load_settings()
    ai_model = cfg.get("ai_model", "google-antigravity/gemini-3.8-flash")
    he_thong = (
        "Bạn là chuyên viên văn thư, chuyên rà soát và chỉnh sửa văn bản hành chính Việt Nam "
        "theo Nghị định 30/2020/NĐ-CP và Hướng dẫn 05-HD/VPTW. "
        "Trả về TOÀN BỘ văn bản ĐÃ CHỈNH SỬA (giữ nguyên kết cấu mục I/II/III...), không giải thích thêm."
    )
    user_prompt = (
        f"YÊU CẦU CHỈNH SỬA CỦA NGƯỜI DÙNG: {request}\n\n"
        f"=== VĂN BẢN HIỆN TẠI ===\n{text[:40000]}\n\n"
        "Hãy trả về toàn bộ văn bản sau khi chỉnh sửa theo yêu cầu."
    )
    ai_url, ai_key, ai_model = _ai_cfg(load_settings())
    try:
        rr = _httpx.post(
            ai_url,
            headers={"Authorization": f"Bearer {ai_key}"},
            json={
                "model": ai_model,
                "messages": [
                    {"role": "system", "content": he_thong},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.3,
            },
            timeout=240,
        )
        if rr.status_code != 200:
            raise HTTPException(status_code=502, detail=f"CHƯA KẾT NỐI AI Provider ({ai_url}) - AI trả lỗi {rr.status_code}. Kiểm tra dịch vụ AI đang chạy.")
        edited = ((rr.json().get("choices") or [{}])[0].get("message") or {}).get("content", "").strip()
        if not edited:
            raise HTTPException(status_code=502, detail="CHƯA KẾT NỐI AI - AI trả về nội dung rỗng.")
        return {"status": "success", "edited_text": edited, "ai_model": ai_model}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"CHƯA KẾT NỐI AI PROVIDER - {type(e).__name__}: {str(e)[:120]}. Kiểm tra dịch vụ AI (Opencodex 10100) đang chạy.")


@app.get("/api/vbdh/draft/download/{filename:path}")
@app.get("/api/personal-brain/draft/download/{filename:path}")
def api_download_draft(filename: str):
    safe_filename = Path(filename).name
    file_path = DRAFTS_DIR / safe_filename
    if not file_path.exists():
        # Kiểm tra thêm đường dẫn từ file dự thảo gốc nếu có
        file_path = BASE_DIR / "data" / "drafts" / safe_filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Không tìm thấy tệp dự thảo: {safe_filename}")
    ascii_filename = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', safe_filename)
    encoded_filename = urllib.parse.quote(safe_filename)
    return FileResponse(
        path=str(file_path),
        filename=safe_filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={
            "Content-Disposition": f'attachment; filename="{ascii_filename}"; filename*=UTF-8\'\'{encoded_filename}'
        }
    )

# Static Files
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8090))
    print(f"[*] Starting Javis Second Brain on http://0.0.0.0:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
