"""
commune_brain_manager.py - Hệ thống Quản trị Người Dùng, Phân Quyền Ma Trận & Kho Tri Thức 3 Tầng
Áp dụng cho UBND cấp xã (Thí điểm: UBND Xã Thạnh Đức, huyện Gò Dầu, tỉnh Tây Ninh)
"""
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data" / "personal_brain"
DATA_DIR.mkdir(parents=True, exist_ok=True)

USERS_FILE = DATA_DIR / "commune_users.json"
DEPARTMENTS_FILE = DATA_DIR / "commune_departments.json"
AUDIT_LOG_FILE = DATA_DIR / "commune_audit_log.json"

DEFAULT_DEPARTMENTS = [
    {
        "id": "lanh_dao",
        "name": "Thường trực UBND Xã",
        "code": "UBND",
        "description": "Chủ tịch và các Phó Chủ tịch UBND xã chỉ đạo, điều hành chung",
        "leader_title": "Chủ tịch UBND xã"
    },
    {
        "id": "van_phong",
        "name": "Văn phòng - Thống kê",
        "code": "VP-TK",
        "description": "Công tác văn thư lưu trữ, tổng hợp, thống kê, kiểm soát TTHC",
        "leader_title": "Công chức Văn phòng - Thống kê"
    },
    {
        "id": "dia_chinh",
        "name": "Địa chính - Nông nghiệp - Xây dựng - Môi trường",
        "code": "ĐC-NN-XD-MT",
        "description": "Quản lý đất đai, quy hoạch, tài nguyên, nông nghiệp, môi trường",
        "leader_title": "Công chức Địa chính - Xây dựng"
    },
    {
        "id": "tu_phap",
        "name": "Tư pháp - Hộ tịch",
        "code": "TP-HT",
        "description": "Công tác hộ tịch, chứng thực, hòa giải cơ sở, phổ biến pháp luật",
        "leader_title": "Công chức Tư pháp - Hộ tịch"
    },
    {
        "id": "tai_chinh",
        "name": "Tài chính - Kế toán",
        "code": "TC-KT",
        "description": "Quản lý ngân sách xã, kế toán, tài sản công",
        "leader_title": "Công chức Tài chính - Kế toán"
    },
    {
        "id": "van_hoa",
        "name": "Văn hóa - Xã hội",
        "code": "VH-XH",
        "description": "Chính sách người có công, bảo trợ xã hội, văn hóa, y tế, giáo dục",
        "leader_title": "Công chức Văn hóa - Xã hội"
    },
    {
        "id": "cong_an",
        "name": "Công an Xã",
        "code": "CAX",
        "description": "Đảm bảo an ninh trật tự, quản lý cư trú, đề án 06",
        "leader_title": "Trưởng Công an xã"
    },
    {
        "id": "to_cds",
        "name": "Tổ Chuyển đổi số cộng đồng",
        "code": "TỔ-CĐS",
        "description": "Hỗ trợ người dân thực hiện dịch vụ công trực tuyến và thanh toán số",
        "leader_title": "Tổ trưởng Tổ CĐS"
    }
]

DEFAULT_USERS = [
    {
        "id": "user_super_admin",
        "username": "070077000098",
        "fullname": "Nguyễn Trung Hiếu",
        "title": "Phó Giám đốc Sở KH&CN (Super Admin)",
        "department_id": "lanh_dao",
        "phone": "0913955333",
        "email": "hieunt@tayninh.gov.vn",
        "role": "super_admin",
        "can_approve_public": True,
        "is_active": True,
        "quota_mb": 51200,
        "created_at": "2026-01-01 08:00:00"
    },
    {
        "id": "user_01_hung",
        "username": "070077000001",
        "fullname": "Nguyễn Văn Hùng",
        "title": "Chủ tịch UBND xã",
        "department_id": "lanh_dao",
        "phone": "0918112233",
        "email": "hungnv@thanhduc.tayninh.gov.vn",
        "role": "commune_admin",
        "can_approve_public": True,
        "is_active": True,
        "quota_mb": 10240,
        "created_at": "2026-01-01 08:00:00"
    },
    {
        "id": "user_02_mai",
        "username": "070077000002",
        "fullname": "Lê Thị Mai",
        "title": "Công chức Văn phòng - Thống kê",
        "department_id": "van_phong",
        "phone": "0918223344",
        "email": "mailt@thanhduc.tayninh.gov.vn",
        "role": "department_lead",
        "can_approve_public": False,
        "is_active": True,
        "quota_mb": 5120,
        "created_at": "2026-01-01 08:00:00"
    },
    {
        "id": "user_03_tam",
        "username": "070077000003",
        "fullname": "Trần Thanh Tâm",
        "title": "Công chức Địa chính - Nông nghiệp - Xây dựng và Môi trường",
        "department_id": "dia_chinh",
        "phone": "0918334455",
        "email": "tamtt@thanhduc.tayninh.gov.vn",
        "role": "department_lead",
        "can_approve_public": False,
        "is_active": True,
        "quota_mb": 5120,
        "created_at": "2026-01-01 08:00:00"
    },
    {
        "id": "user_04_thao",
        "username": "070077000004",
        "fullname": "Phạm Thị Thảo",
        "title": "Công chức Tư pháp - Hộ tịch",
        "department_id": "tu_phap",
        "phone": "0918445566",
        "email": "thaopt@thanhduc.tayninh.gov.vn",
        "role": "department_lead",
        "can_approve_public": False,
        "is_active": True,
        "quota_mb": 5120,
        "created_at": "2026-01-01 08:00:00"
    },
    {
        "id": "user_05_tai",
        "username": "070077000005",
        "fullname": "Huỳnh Tấn Tài",
        "title": "Công chức Tài chính - Kế toán",
        "department_id": "tai_chinh",
        "phone": "0918556677",
        "email": "taiht@thanhduc.tayninh.gov.vn",
        "role": "department_lead",
        "can_approve_public": False,
        "is_active": True,
        "quota_mb": 5120,
        "created_at": "2026-01-01 08:00:00"
    },
    {
        "id": "user_06_yen",
        "username": "070077000006",
        "fullname": "Đặng Thị Kim Yến",
        "title": "Công chức Văn hóa - Xã hội",
        "department_id": "van_hoa",
        "phone": "0918667788",
        "email": "yendtk@thanhduc.tayninh.gov.vn",
        "role": "officer",
        "can_approve_public": False,
        "is_active": True,
        "quota_mb": 5120,
        "created_at": "2026-01-01 08:00:00"
    },
    {
        "id": "user_07_nam",
        "username": "070077000007",
        "fullname": "Võ Hoàng Nam",
        "title": "Trưởng Công an xã",
        "department_id": "cong_an",
        "phone": "0918778899",
        "email": "namvh@thanhduc.tayninh.gov.vn",
        "role": "department_lead",
        "can_approve_public": False,
        "is_active": True,
        "quota_mb": 5120,
        "created_at": "2026-01-01 08:00:00"
    },
    {
        "id": "user_08_trong",
        "username": "070077000008",
        "fullname": "Ngô Văn Trọng",
        "title": "Tổ trưởng Tổ Chuyển đổi số cộng đồng",
        "department_id": "to_cds",
        "phone": "0918889900",
        "email": "trongnv@thanhduc.tayninh.gov.vn",
        "role": "officer",
        "can_approve_public": False,
        "is_active": True,
        "quota_mb": 5120,
        "created_at": "2026-01-01 08:00:00"
    }
]

def get_default_commune_password() -> str:
    """
    Sinh mật khẩu mặc định công vụ theo cú pháp: {TenXa}@2026
    Ví dụ: 'UBND Xã Thạnh Đức' -> 'ThanhDuc@2026'
    """
    settings_file = DATA_DIR / "settings.json"
    unit_name = "Thạnh Đức"
    if settings_file.exists():
        try:
            cfg = json.loads(settings_file.read_text(encoding="utf-8"))
            unit_name = cfg.get("user_unit") or "Thạnh Đức"
        except Exception:
            unit_name = "Thạnh Đức"

    # Chuẩn hóa loại bỏ các tiền tố hành chính: UBND, Xã, Phường, Thị trấn, Sở...
    import unicodedata
    clean_unit = re.sub(r'^(ủy ban nhân dân|ubnd|sở khoa học và công nghệ|sở kh&cn|sở)\s+', '', unit_name, flags=re.IGNORECASE).strip()
    clean_unit = re.sub(r'^(xã|phường|thị trấn)\s+', '', clean_unit, flags=re.IGNORECASE).strip()
    # Loại bỏ cả chữ "xã/phường/thị trấn" nếu còn sót
    clean_unit = re.sub(r'\b(xã|phường|thị trấn)\b', '', clean_unit, flags=re.IGNORECASE).strip()
    # Thay thế ký tự đ/Đ trước khi bỏ dấu
    clean_unit = clean_unit.replace('đ', 'd').replace('Đ', 'D')
    # Loại bỏ dấu tiếng Việt để tạo chuỗi PascalCase an toàn
    nfkd = unicodedata.normalize('NFKD', clean_unit)
    ascii_clean = "".join([c for c in nfkd if not unicodedata.combining(c)])
    # Bỏ ký tự đặc biệt, ghép CamelCase/PascalCase
    words = re.findall(r'[a-zA-Z0-9]+', ascii_clean)
    if not words:
        pascal_name = "ThanhDuc"
    else:
        pascal_name = "".join(w.capitalize() for w in words)
    # Nếu là Thạnh Đức thì luôn chuẩn hóa về ThanhDuc
    if "thanhduc" in pascal_name.lower():
        pascal_name = "ThanhDuc"
    return f"{pascal_name}@2026"

def load_commune_departments() -> List[Dict[str, Any]]:
    if not DEPARTMENTS_FILE.exists():
        DEPARTMENTS_FILE.write_text(json.dumps(DEFAULT_DEPARTMENTS, ensure_ascii=False, indent=2), encoding="utf-8")
        return DEFAULT_DEPARTMENTS
    try:
        return json.loads(DEPARTMENTS_FILE.read_text(encoding="utf-8"))
    except Exception:
        return DEFAULT_DEPARTMENTS

def save_commune_departments(departments: List[Dict[str, Any]]) -> None:
    DEPARTMENTS_FILE.write_text(json.dumps(departments, ensure_ascii=False, indent=2), encoding="utf-8")

def load_commune_users() -> List[Dict[str, Any]]:
    # Luôn đồng bộ danh sách chuẩn CCCD 12 số và Super Admin
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps(DEFAULT_USERS, ensure_ascii=False, indent=2), encoding="utf-8")
        return DEFAULT_USERS
    try:
        users = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        # Đảm bảo tài khoản Super Admin luôn hiện diện
        if not any(u.get("username") == "070077000098" for u in users):
            users.insert(0, DEFAULT_USERS[0])
            save_commune_users(users)
        return users
    except Exception:
        return DEFAULT_USERS

def save_commune_users(users: List[Dict[str, Any]]) -> None:
    USERS_FILE.write_text(json.dumps(users, ensure_ascii=False, indent=2), encoding="utf-8")

def sync_user_job_position_to_brain(user: Dict[str, Any]) -> None:
    """
    Tự động đồng bộ hồ sơ Vị trí việc làm & Nhiệm vụ vào:
    1. Second Brain wiki/notes dạng Markdown để RAG & AI Copilot tra cứu tức thì
    2. Ghi nhớ lâu dài để khi giao nhiệm vụ / phân công VBĐH biết đúng người xử lý chính và phối hợp
    """
    fullname = user.get("fullname", "")
    cccd = user.get("username", "")
    title = user.get("title", "")
    dept_id = user.get("department_id", "")
    dept_name = user.get("department_name") or dept_id
    job_position = user.get("job_position", "")

    if not job_position:
        return

    # Ghi nhận vào file markdown trong Second Brain để RAG tự động học
    brain_wiki_dir = BASE_DIR / "data" / "wiki" / "phan_cong_nhiem_vu"
    brain_wiki_dir.mkdir(parents=True, exist_ok=True)
    
    clean_slug = "".join([c for c in cccd if c.isalnum()]) or f"user_{int(time.time())}"
    doc_path = brain_wiki_dir / f"Vi_tri_viec_lam_{clean_slug}.md"
    
    content = f"""# Bản Mô Tả Vị Trí Việc Làm & Phân Công Nhiệm Vụ

- **Họ và tên cán bộ:** {fullname}
- **Số CCCD (Định danh):** `{cccd}`
- **Chức danh:** {title}
- **Bộ phận / Phòng ban:** {dept_name}
- **Thời điểm cập nhật:** {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}

## 1. Vị trí việc làm & Phạm vi tham mưu (Theo Hướng dẫn 05 & Quyết định phân công)
{job_position}

## 2. Nguyên tắc phân công văn bản & Điều hành công việc
- **Xử lý chính:** Khi có văn bản hoặc vụ việc liên quan trực tiếp đến các mảng công việc nêu trên, hệ thống AI tự động đề xuất **{fullname}** ({title}) là người **Chủ trì / Trực tiếp tham mưu**.
- **Chỉ đạo:** Tham mưu cho Lãnh đạo phụ trách khối duyệt ký theo Quyết định phân công nhiệm vụ của đơn vị.
- **Phối hợp & Nắm biết:** Các cán bộ cùng phòng ban hoặc cán bộ cấp dưới trong bộ phận phối hợp thực hiện.
"""
    doc_path.write_text(content, encoding="utf-8")

def log_audit_action(user_id: str, username: str, action: str, details: str, target_id: Optional[str] = None) -> None:
    logs = []
    if AUDIT_LOG_FILE.exists():
        try:
            logs = json.loads(AUDIT_LOG_FILE.read_text(encoding="utf-8"))
        except Exception:
            logs = []
    log_entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "user_id": user_id,
        "username": username,
        "action": action,
        "details": details,
        "target_id": target_id or ""
    }
    logs.insert(0, log_entry)
    # Giữ tối đa 1000 logs gần nhất
    if len(logs) > 1000:
        logs = logs[:1000]
    AUDIT_LOG_FILE.write_text(json.dumps(logs, ensure_ascii=False, indent=2), encoding="utf-8")

def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    users = load_commune_users()
    for u in users:
        if u.get("id") == user_id or u.get("username") == user_id:
            return u
    return None

def filter_accessible_items(items: List[Dict[str, Any]], current_user: Dict[str, Any], workspace: str = "all") -> List[Dict[str, Any]]:
    """
    Ma trận phân quyền đọc tài liệu:
    - workspace == 'private': chỉ tài liệu của chính current_user (owner_id == user.id)
    - workspace == 'department': tài liệu do phòng ban current_user tạo hoặc được share cho phòng ban
    - workspace == 'commune': tài liệu dùng chung toàn xã (visibility == 'public_commune')
    - workspace == 'all': kết hợp cả 3 không gian mà current_user có quyền
    """
    u_id = current_user.get("id")
    dept_id = current_user.get("department_id")
    is_commune_admin = current_user.get("role") == "commune_admin"

    res = []
    for it in items:
        owner_id = it.get("owner_id") or "user_01_hung" # fallback
        visibility = it.get("visibility") or "public_commune" # fallback tệp cũ coi như dùng chung
        it_dept = it.get("department_id") or "lanh_dao"
        shared_users = it.get("shared_users") or []
        shared_depts = it.get("shared_departments") or []

        # Kiểm tra quyền truy cập cơ bản
        has_access = False
        if is_commune_admin:
            # Lãnh đạo xã / Admin được xem toàn bộ để giám sát
            has_access = True
        elif owner_id == u_id:
            # Chính chủ sở hữu
            has_access = True
        elif visibility == "public_commune":
            # Kho dùng chung toàn xã
            has_access = True
        elif visibility == "department" and (it_dept == dept_id or dept_id in shared_depts):
            # Tài liệu của phòng hoặc được chia sẻ cho phòng mình
            has_access = True
        elif u_id in shared_users:
            # Được chia sẻ trực tiếp cho cá nhân
            has_access = True

        if not has_access:
            continue

        # Lọc theo Workspace đang chọn
        if workspace == "private":
            if owner_id == u_id:
                res.append(it)
        elif workspace == "department":
            if visibility == "department" and (it_dept == dept_id or dept_id in shared_depts):
                res.append(it)
        elif workspace == "commune":
            if visibility == "public_commune":
                res.append(it)
        else:
            # 'all'
            res.append(it)

    return res
