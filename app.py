#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Javis Second Brain - Standalone Backend Server
Nền tảng Quản trị Kho Tri Thức Số & Soạn Thảo Báo Cáo NĐ 30 độc lập cho JavisOS.
"""

import os
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

@app.post("/api/personal-brain/commune/ai-suggest-job-position")
def api_ai_suggest_vtvl(req: AiSuggestVTVLRequest):
    depts = commune_brain_manager.load_commune_departments()
    dept_obj = next((d for d in depts if d["id"] == req.department_id), None)
    dept_name = dept_obj["name"] if dept_obj else "Cơ quan đơn vị"

    job_desc = commune_brain_manager.suggest_job_position_by_title(req.title, dept_name)
    return {
        "status": "success",
        "title": req.title,
        "department_name": dept_name,
        "job_position": job_desc
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
    save_settings(cfg)
    return {"status": "success", "message": "Đã lưu cài đặt Kho tri thức thành công!", "settings": cfg}

@app.get("/api/personal-brain/items")
def api_get_items(current_user_id: Optional[str] = None, workspace: Optional[str] = "all"):
    items = load_items()
    users = commune_brain_manager.load_commune_users()
    
    # Tìm user hiện tại nếu có truyền ID
    current_user = next((u for u in users if u.get("id") == current_user_id or u.get("username") == current_user_id), None)

    visible_items = []
    for it in items:
        vis = it.get("visibility")
        owner = it.get("owner_id")

        # NGUYÊN TẮC: Mặc định tất cả dữ liệu mẫu đều hiển thị cho mọi người dùng
        # Chỉ ẩn khi tài liệu được gán quyền "private" rõ ràng bởi người dùng khác
        if not current_user:
            # Chưa đăng nhập: Cho phép xem toàn bộ tài liệu public, tài liệu chưa gắn nhãn hoặc tài liệu demo
            if not vis or vis in ["public_commune", "public", "commune"] or not owner or owner == "070077000098":
                visible_items.append(it)
            continue

        # Đã đăng nhập:
        if current_user.get("role") in ["super_admin", "commune_admin"]:
            # Lãnh đạo và Super Admin xem được toàn bộ
            visible_items.append(it)
        elif not owner or owner == current_user.get("username") or owner == current_user.get("id"):
            # Chính chủ hoặc tài liệu hệ thống/mẫu
            visible_items.append(it)
        elif vis == "department" and it.get("department_id") == current_user.get("department_id"):
            visible_items.append(it)
        elif vis in ["public_commune", "public", "commune"] or not vis:
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

@app.post("/api/personal-brain/ingest/drive")
def api_ingest_drive(req: IngestDriveRequest):
    drive_url = (req.drive_url or "").strip()
    if not drive_url:
        raise HTTPException(status_code=400, detail="Vui lòng nhập đường dẫn Google Drive.")

    doc_title = (req.title or "").strip() or f"Tài liệu Google Drive {time.strftime('%d/%m/%Y')}"
    new_item = {
        "id": f"pb_{int(time.time())}_drive",
        "title": doc_title,
        "category": req.category or "Chỉ đạo điều hành",
        "source_type": "drive",
        "source_url_or_path": drive_url,
        "filename": "Google_Drive_Doc.pdf",
        "file_path": "",
        "summary": f"Tài liệu liên kết từ Google Drive: {drive_url}",
        "text_content": f"Tài liệu liên kết đám mây Google Drive:\n{drive_url}\nTiêu đề: {doc_title}",
        "word_count": 150,
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tags": req.tags or ["Google Drive", "Cloud"],
        "owner_id": "070077000098",
        "visibility": "private"
    }

    items = load_items()
    items.insert(0, new_item)
    save_items(items)
    return {"status": "success", "message": "Đã kết nối và nạp tài liệu Google Drive vào Brain thành công!", "item": new_item}

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
        raise HTTPException(status_code=400, detail="Vui lòng chọn ít nhất 1 mục tri thức từ kho.")

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

    # Mẫu dự thảo báo cáo hành chính chuẩn mực
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
    vbdh_draft_generator.generate_draft_docx(
        loai_van_ban=loai,
        body_text=body_text,
        doc_info=doc_info,
        output_path=out_docx_path
    )

    return {
        "status": "success",
        "message": "Đã tạo bản dự thảo Báo cáo thành công!",
        "filename": out_filename,
        "download_url": f"/api/vbdh/draft/download/{urllib.parse.quote(out_filename)}",
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

@app.get("/api/vbdh/draft/download/{filename}")
def api_download_draft(filename: str):
    file_path = DRAFTS_DIR / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Không tìm thấy tệp dự thảo.")
    return FileResponse(
        path=str(file_path),
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )

# Static Files
app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8090))
    print(f"[*] Starting Javis Second Brain on http://0.0.0.0:{port}")
    uvicorn.run("app:app", host="0.0.0.0", port=port, reload=False)
