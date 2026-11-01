#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Tạo Dự Thảo Văn Bản Trả Lời Tự Động (Chuẩn NĐ 30/2020/NĐ-CP & HD 05-HD/VPTW)
Tự động liên kết Văn bản đến thành Văn bản đi cho Sở KH&CN Tây Ninh
"""

import os
import sys
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List

try:                                   # python-docx là bắt buộc (gói hệ thống python3-docx)
    import docx
except ModuleNotFoundError:            # dự phòng: mượn site-packages của môi trường khác
    for p in ("/usr/lib/python3/dist-packages",
              "/home/ubuntu/rag-ocr-env/lib/python3.12/site-packages"):
        if p not in sys.path:
            sys.path.append(p)
    import docx
from docx.shared import Inches, Cm, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

BASE_DIR = Path(__file__).resolve().parent
DRAFTS_DIR = BASE_DIR / "data" / "drafts"
DRAFTS_DIR.mkdir(parents=True, exist_ok=True)

def is_party_organization(co_quan: str, trich_yeu: str) -> bool:
    """Xác định văn bản gửi Khối Đảng (áp dụng HD 05-HD/VPTW) hay Chính quyền (áp dụng NĐ 30/2020/NĐ-CP)"""
    text = (co_quan + " " + trich_yeu).lower()
    party_keywords = ["tỉnh ủy", "tỉnh uỷ", "huyện ủy", "huyện uỷ", "thành ủy", "thành uỷ", "ban thường vụ", "thường trực tỉnh ủy", "văn phòng tỉnh ủy", "ban tuyên giáo", "ban tổ chức", "ban dân vận", "ban nội chính", "ủy ban kiểm tra", "đảng bộ"]
    return any(k in text for k in party_keywords)

def set_cell_border(cell, **kwargs):
    """Xóa viền bảng cho các ô tiêu đề hành chính (tuân thủ nghiêm ngặt chuẩn OpenXML w:tcBorders)"""
    tcPr = cell._tc.get_or_add_tcPr()
    tcBorders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        edge_data = kwargs.get(edge)
        if edge_data:
            tag = 'w:{}'.format(edge)
            element = OxmlElement(tag)
            element.set(qn('w:val'), edge_data.get('val', 'none'))
            tcBorders.append(element)
        else:
            tag = 'w:{}'.format(edge)
            element = OxmlElement(tag)
            element.set(qn('w:val'), 'none')
            tcBorders.append(element)
    tcPr.append(tcBorders)

TEMPLATES_DIR = BASE_DIR / "templates"

TIEU_DE_THEO_LOAI = {
    "ke_hoach": "KẾ HOẠCH",
    "quyet_dinh": "QUYẾT ĐỊNH",
    "to_trinh": "TỜ TRÌNH",
    "bao_cao": "BÁO CÁO",
    "cong_van": "CÔNG VĂN",
    "thong_bao": "THÔNG BÁO",
    "bien_ban": "BIÊN BẢN",
    "de_an": "ĐỀ ÁN",
    "phuong_an": "PHƯƠNG ÁN",
    "chuong_trinh": "CHƯƠNG TRÌNH",
    "huong_dan": "HƯỚNG DẪN",
    "quy_che": "QUY CHẾ",
    "nghi_quyet_dang": "NGHỊ QUYẾT",
    "quyet_dinh_dang": "QUYẾT ĐỊNH",
    "chi_thi_dang": "CHỈ THỊ",
    "ket_luan_dang": "KẾT LUẬN",
    "ke_hoach_dang": "KẾ HOẠCH",
    "bao_cao_dang": "BÁO CÁO",
    "thong_tri_dang": "THÔNG TRI",
    "to_trinh_dang": "TỜ TRÌNH",
    "cong_van_dang": "CÔNG VĂN",
}


def _dat_tieu_de_theo_loai(doc, loai_van_ban: str, ty_text: str) -> None:
    """Đổi dòng trích yếu 'V/v …' thành tiêu đề loại văn bản (KẾ HOẠCH/QUYẾT ĐỊNH/TỜ TRÌNH/BÁO CÁO)."""
    tieu_de = TIEU_DE_THEO_LOAI.get((loai_van_ban or "").strip().lower())
    if not tieu_de:
        return
    paras = list(doc.paragraphs)
    for t in doc.tables:
        for row in t.rows:
            for cell in row.cells:
                paras.extend(cell.paragraphs)
    for p in paras:
        if p.text.strip().lower().startswith("v/v"):
            for r in list(p.runs):
                r.text = ""
            r1 = p.add_run(tieu_de)
            r1.bold = True
            r1.font.name = "Times New Roman"
            r1.font.size = Pt(14 if loai_van_ban == "bao_cao" else 13)
            p.add_run("\n")
            # Trích yếu báo cáo: Về...
            ty_clean = re.sub(r'^(?:v/v|về việc|về)\s*', '', ty_text, flags=re.IGNORECASE).strip()
            r2 = p.add_run(f"Về việc {ty_clean}" if loai_van_ban == "bao_cao" else ty_text)
            r2.italic = (loai_van_ban != "bao_cao")
            r2.bold = (loai_van_ban == "bao_cao")
            r2.font.name = "Times New Roman"
            r2.font.size = Pt(13 if loai_van_ban == "bao_cao" else 12)
            return


def _dat_kho_a4(doc) -> None:
    """Ép khổ A4 (21 × 29,7 cm) cho MỌI trang.

    Template gốc lưu khổ Letter (21,6 × 27,9 cm) nên tệp AI mở ra khác hẳn văn bản
    tải từ máy tính / từ cổng VBĐH (A4). Luôn đặt lại sau khi mở template.
    """
    for section in doc.sections:
        section.page_width = Cm(21)
        section.page_height = Cm(29.7)


def _ghi_dau_trang(cell, dau_trang: Dict[str, Any]) -> None:
    """Ghi lại khối bên trái đầu trang: cơ quan ban hành, số/ký hiệu, tên loại + trích yếu.

    Dùng khi dự thảo KHÔNG phải công văn của Sở: ví dụ Kế hoạch/Quyết định do UBND tỉnh
    ban hành (đầu trang là UBND tỉnh, số /KH-UBND, tiêu đề KẾ HOẠCH).
    """
    dong = []
    if dau_trang.get("co_quan_1"):
        dong.append((dau_trang["co_quan_1"], 12, False, False))
    if dau_trang.get("co_quan_2"):
        dong.append((dau_trang["co_quan_2"], 12, True, False))
    dong.append(("___________", 10, True, False))
    if dau_trang.get("so_ky_hieu"):
        dong.append((dau_trang["so_ky_hieu"], 12, False, False))
    if dau_trang.get("tieu_de"):
        dong.append((dau_trang["tieu_de"], 14, True, False))
    if dau_trang.get("trich_yeu"):
        dong.append((dau_trang["trich_yeu"], 12, False, True))

    # Xoá các đoạn cũ, giữ lại đoạn đầu làm gốc
    for p in list(cell.paragraphs)[1:]:
        p._p.getparent().remove(p._p)
    goc = cell.paragraphs[0]
    goc.text = ""
    for i, (text, size, bold, italic) in enumerate(dong):
        para = goc if i == 0 else cell.add_paragraph()
        para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        para.paragraph_format.space_after = Pt(0)
        para.paragraph_format.line_spacing = 1.0
        r = para.add_run(text)
        r.font.name = "Times New Roman"
        r.font.size = Pt(size)
        r.bold = bold
        r.italic = italic


def create_docx_reply_draft(doc_info: Dict[str, Any], draft_body_text: str, signer_name: str = "Nguyễn Trung Hiếu",
                            signer_title: str = "PHÓ GIÁM ĐỐC", loai_van_ban: str = "cong_van",
                            dau_trang: Optional[Dict[str, Any]] = None,
                            chu_ky: Optional[List[str]] = None,
                            kinh_gui: Optional[str] = None,
                            ten_tep: Optional[str] = None,
                            bo_kinh_gui: bool = False) -> str:
    """Tạo file docx dự thảo văn bản trả lời chuẩn Nghị định 30/2020/NĐ-CP hoặc Hướng dẫn 05-HD/VPTW"""
    if not isinstance(signer_name, str) or isinstance(signer_name, bool):
        signer_name = "Nguyễn Trung Hiếu"
    if not isinstance(signer_title, str) or isinstance(signer_title, bool):
        signer_title = "PHÓ GIÁM ĐỐC"

    co_quan_gui = doc_info.get("co_quan") or "Cơ quan ban hành"
    so_hieu_den = doc_info.get("so_hieu") or "Dự thảo"
    ngay_den = doc_info.get("ngay_ban_hanh") or datetime.now().strftime("%d/%m/%Y")
    trich_yeu_den = doc_info.get("trich_yeu") or ""
    is_party = is_party_organization(co_quan_gui, trich_yeu_den)

    # 1. ƯU TIÊN SỬ DỤNG MẪU CHUẨN TỪ THƯ MỤC TEMPLATES (HD 05 CHO ĐẢNG, NĐ 30 CHO CHÍNH QUYỀN)
    if is_party:
        tpl_path = TEMPLATES_DIR / "mau_cong_van_dang_hd05.docx"
        if not tpl_path.exists():
            tpl_path = TEMPLATES_DIR / "mau_cong_van_nd30.docx"
    else:
        tpl_path = TEMPLATES_DIR / "mau_cong_van_nd30.docx"

    if tpl_path.exists():
        try:
            doc = docx.Document(str(tpl_path))
            t_h = doc.tables[0]
            cell_l = t_h.cell(0, 0)
            cell_r = t_h.cell(0, 1)
            if dau_trang:
                _ghi_dau_trang(cell_l, dau_trang)
                # đã ghi cả trích yếu trong khối đầu trang -> bỏ qua bước ghi mặc định bên dưới

            # Cột trái: Ô 1/2, Ô 2/3, Ô 5b
            if loai_van_ban == "bao_cao":
                for p_so in cell_l.paragraphs:
                    if "/SKHCN-VP" in p_so.text or "Số:" in p_so.text:
                        p_so.text = "Số:       /BC-SKHCN" if not is_party else "Số:       -BC/ĐBU"
                        for r in p_so.runs:
                            r.font.name = "Times New Roman"
                            r.font.size = Pt(12)
            ty_clean = re.sub(r'^(?:v/v|về việc|về)\s*', '', trich_yeu_den, flags=re.IGNORECASE).strip()
            ty_text = f"V/v {ty_clean}" if ty_clean else f"V/v phúc đáp CV số {so_hieu_den}"
            
            # Cập nhật trích yếu ở dòng cuối của cột trái (bỏ qua nếu đầu trang đã ghi đủ)
            if not dau_trang:
                p_ty_idx = len(cell_l.paragraphs) - 1
                cell_l.paragraphs[p_ty_idx].text = ""
                r_ty = cell_l.paragraphs[p_ty_idx].add_run(ty_text)
                r_ty.font.name = "Times New Roman"
                r_ty.font.size = Pt(12)
                r_ty.italic = True

            # Cột phải: Ngày tháng ở dòng cuối của cột phải
            now = datetime.now()
            date_str = f"Tây Ninh, ngày {now.day:02d} tháng {now.month:02d} năm {now.year}"
            p_date_idx = len(cell_r.paragraphs) - 1
            cell_r.paragraphs[p_date_idx].text = ""
            r_d = cell_r.paragraphs[p_date_idx].add_run(date_str)
            r_d.font.name = "Times New Roman"
            r_d.font.size = Pt(14)
            r_d.italic = True

            p_kg_orig = doc.paragraphs[0]
            p_body_orig = doc.paragraphs[1]

            # Tên loại văn bản & Trích yếu nội dung (Kế hoạch, Báo cáo, Quyết định, Tờ trình...)
            # Theo Nghị định 30/2020/NĐ-CP & Hướng dẫn 05-HD/VPTW:
            # Văn bản có tên loại (Kế hoạch, Báo cáo, Quyết định, Tờ trình...) thì Tên loại và Trích yếu
            # được đặt BÊN DƯỚI phần Tiêu ngữ/Ngày tháng và PHẢI CĂN GIỮA trang văn bản!
            is_titled_doc = loai_van_ban in ["ke_hoach", "bao_cao", "quyet_dinh", "to_trinh", "thong_bao", 
                                             "bien_ban", "de_an", "phuong_an", "chuong_trinh", "huong_dan", "quy_che",
                                             "nghi_quyet_dang", "quyet_dinh_dang", "chi_thi_dang", "ket_luan_dang",
                                             "ke_hoach_dang", "bao_cao_dang", "thong_tri_dang", "to_trinh_dang"]
            if is_titled_doc and not dau_trang:
                # Xóa dòng trích yếu ở cột trái bảng tiêu đề
                p_ty_idx = len(cell_l.paragraphs) - 1
                cell_l.paragraphs[p_ty_idx].text = ""

                # Thêm đoạn TÊN LOẠI VĂN BẢN (CĂN GIỮA, CHỮ IN HOA, ĐẬM, CỠ 14-15PT)
                p_title = doc.add_paragraph()
                p_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_title.paragraph_format.space_before = Pt(14)
                p_title.paragraph_format.space_after = Pt(4)
                tieu_de_ten = TIEU_DE_THEO_LOAI.get(loai_van_ban, loai_van_ban.upper())
                r_title = p_title.add_run(tieu_de_ten)
                r_title.bold = True
                r_title.font.name = "Times New Roman"
                r_title.font.size = Pt(14)
                p_kg_orig._p.addprevious(p_title._p)

                # Thêm đoạn TRÍCH YẾU NỘI DUNG (CĂN GIỮA, ĐẬM HOẶC NGHIÊNG, CỠ 13-14PT)
                p_sub = doc.add_paragraph()
                p_sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p_sub.paragraph_format.space_before = Pt(0)
                p_sub.paragraph_format.space_after = Pt(12)
                ty_clean = re.sub(r'^(?:v/v|về việc|về)\s*', '', trich_yeu_den, flags=re.IGNORECASE).strip()
                r_sub = p_sub.add_run(f"Về việc {ty_clean}" if ty_clean else f"Về {tieu_de_ten.lower()}")
                r_sub.bold = True
                r_sub.font.name = "Times New Roman"
                r_sub.font.size = Pt(13)
                p_kg_orig._p.addprevious(p_sub._p)

            # Kính gửi (văn bản như Kế hoạch/Quyết định của UBND thì không có dòng này)
            font_size_body = Pt(14)
            p_kg_orig.text = ""
            if bo_kinh_gui:
                p_kg_orig.paragraph_format.space_after = Pt(0)
                r_kg1 = p_kg_orig.add_run("")
            else:
                # Kính gửi theo NĐ 30 / HD 05: lùi đầu dòng (tab vào 1 - 1.27cm) hoặc căn giữa
                p_kg_orig.paragraph_format.first_line_indent = Inches(0.4)
                p_kg_orig.paragraph_format.space_before = Pt(8)
                p_kg_orig.paragraph_format.space_after = Pt(8)
                r_kg1 = p_kg_orig.add_run("Kính gửi: ")
            r_kg1.font.name = "Times New Roman"
            r_kg1.font.size = font_size_body
            if not bo_kinh_gui:
                if is_party:
                    r_kg1.italic = True # Hướng dẫn 05: từ 'Kính gửi' in nghiêng
                else:
                    r_kg1.bold = True   # Nghị định 30: từ 'Kính gửi' in đậm
                r_kg2 = p_kg_orig.add_run(f"{kinh_gui or co_quan_gui}.")
                r_kg2.font.name = "Times New Roman"
                r_kg2.font.size = font_size_body

            # Thân bài
            p_body_orig.text = ""
            clean_body = re.sub(r'\*\*(.*?)\*\*', r'\1', draft_body_text)
            clean_body = re.sub(r'\.\/\.', '', clean_body).strip()
            raw_paras = [p.strip() for p in clean_body.split('\n') if p.strip()]
            paras = []
            for p_raw in raw_paras:
                p_clean = re.sub(r'^[#\-–—\*\•\s]+', '', p_raw).strip()
                if not p_clean or p_clean in ['---', '***', '___', '---/---']:
                    continue
                if p_clean.upper() in ["BÁO CÁO", "BÁO CÁO:"]:
                    continue
                if p_clean.startswith("Kính gửi:"):
                    continue
                if loai_van_ban == "bao_cao" and re.match(r'^(?:V/v|Về việc|Về)\s+', p_clean, re.IGNORECASE) and len(p_clean) < 120:
                    continue
                paras.append(p_clean)

            if paras:
                p0 = p_body_orig
                p0.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                p0.paragraph_format.line_spacing = 1.15
                p0.paragraph_format.first_line_indent = Inches(0.4)
                p0.paragraph_format.space_after = Pt(6)
                r0 = p0.add_run(paras[0])
                r0.font.name = "Times New Roman"
                r0.font.size = font_size_body

                t_f = doc.tables[1]
                for p_idx in range(1, len(paras)):
                    p_text = paras[p_idx]
                    if p_idx == len(paras) - 1:
                        p_text = p_text + "./."
                    new_p = doc.add_paragraph()
                    new_p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    new_p.paragraph_format.line_spacing = 1.15
                    new_p.paragraph_format.first_line_indent = Inches(0.4)
                    new_p.paragraph_format.space_after = Pt(6)
                    rn = new_p.add_run(p_text)
                    rn.font.name = "Times New Roman"
                    rn.font.size = font_size_body
                    t_f._tbl.addprevious(new_p._p)

            # Footer
            t_f = doc.tables[1]
            cell_fr = t_f.cell(0, 1)
            cell_fr.paragraphs[0].text = ""
            _da_ghi_chu_ky = False
            if chu_ky:
                # Khối chữ ký riêng (VD văn bản do UBND tỉnh ký: TM. ỦY BAN NHÂN DÂN TỈNH / CHỦ TỊCH)
                for i_ck, dong_ck in enumerate(chu_ky):
                    r_ck = cell_fr.paragraphs[0].add_run(dong_ck + ("\n" if i_ck == 0 else ""))
                    r_ck.bold = True
                    r_ck.font.name = "Times New Roman"
                    r_ck.font.size = Pt(13)
                _da_ghi_chu_ky = True
            if _da_ghi_chu_ky:
                pass
            elif not is_party:
                if signer_title != "GIÁM ĐỐC":
                    r_s1 = cell_fr.paragraphs[0].add_run("KT. GIÁM ĐỐC\n")
                    r_s1.bold = True
                    r_s1.font.name = "Times New Roman"
                    r_s1.font.size = Pt(13)
                r_s2 = cell_fr.paragraphs[0].add_run(signer_title)
                r_s2.bold = True
                r_s2.font.name = "Times New Roman"
                r_s2.font.size = Pt(13)
            else:
                r_s1 = cell_fr.paragraphs[0].add_run("T/M ĐẢNG ỦY\n")
                r_s1.bold = True
                r_s1.font.name = "Times New Roman"
                r_s1.font.size = Pt(14)
                chuc_vu_dang = "PHÓ BÍ THƯ" if ("PHÓ" in signer_title or "phó" in signer_title.lower()) else "BÍ THƯ"
                r_s2 = cell_fr.paragraphs[0].add_run(chuc_vu_dang)
                r_s2.bold = False # HD 05: chức vụ người ký in hoa đứng không đậm
                r_s2.font.name = "Times New Roman"
                r_s2.font.size = Pt(14)

            p_name_idx = len(cell_fr.paragraphs) - 1
            cell_fr.paragraphs[p_name_idx].text = ""
            r_s3 = cell_fr.paragraphs[p_name_idx].add_run(signer_name)
            r_s3.bold = True
            r_s3.font.name = "Times New Roman"
            r_s3.font.size = Pt(14)

            safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', doc_info.get("hash_id") or f"doc_{now.strftime('%Y%m%d%H%M%S')}")
            _dat_kho_a4(doc)
            # Cùng cỡ chữ với văn bản thật của Sở (14 pt, Times New Roman) để mở ra nhìn GIỐNG NHAU
            try:
                _st = doc.styles["Normal"]
                _st.font.name = "Times New Roman"
                _st.font.size = Pt(14)
            except Exception:
                pass
            out_filename = ten_tep or f"Du_thao_tra_loi_{safe_name}.docx"
            out_path = DRAFTS_DIR / out_filename
            _dat_tieu_de_theo_loai(doc, loai_van_ban, ty_text)
            doc.save(str(out_path))
            return str(out_path)
        except Exception as e:
            print(f"Lỗi khi dùng template: {e}, chuyển sang vẽ code dự phòng.")

    # FALLBACK DỰ PHÒNG NẾU KHÔNG CÓ TEMPLATE
    doc = docx.Document()
    
    # 1. Cài đặt lề trang theo Nghị định 30/2020/NĐ-CP (Top 20mm, Bottom 20mm, Left 30mm, Right 15mm)
    _dat_kho_a4(doc)
    sections = doc.sections
    for section in sections:
        section.top_margin = Inches(0.79)     # 20mm
        section.bottom_margin = Inches(0.79)  # 20mm
        section.left_margin = Inches(1.18)    # 30mm
        section.right_margin = Inches(0.59)   # 15mm
        
    co_quan_gui = doc_info.get("co_quan") or "Cơ quan ban hành"
    so_hieu_den = doc_info.get("so_hieu") or "Dự thảo"
    ngay_den = doc_info.get("ngay_ban_hanh") or datetime.now().strftime("%d/%m/%Y")
    trich_yeu_den = doc_info.get("trich_yeu") or ""
    
    is_party = is_party_organization(co_quan_gui, trich_yeu_den)
    
    # Thiết lập style mặc định
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(13)
    font.color.rgb = RGBColor(0, 0, 0)
    
    # 2. Phần đầu trang (Bảng 2 cột: Cơ quan ban hành & Quốc hiệu/Tiêu ngữ)
    table_header = doc.add_table(rows=1, cols=2)
    table_header.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_header.autofit = False
    
    col_left = table_header.columns[0]
    col_right = table_header.columns[1]
    col_left.width = Inches(3.2)
    col_right.width = Inches(3.6)
    
    cell_left = table_header.cell(0, 0)
    cell_right = table_header.cell(0, 1)
    set_cell_border(cell_left)
    set_cell_border(cell_right)
    
    # Cột trái: Cơ quan chủ quản và Tên cơ quan
    p_cq1 = cell_left.paragraphs[0]
    p_cq1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cq1.paragraph_format.space_after = Pt(1)
    p_cq1.paragraph_format.line_spacing = 1.0
    r_cq1 = p_cq1.add_run("UBND TỈNH TÂY NINH\n" if not is_party else "TỈNH ỦY TÂY NINH\n")
    r_cq1.font.size = Pt(12)
    r_cq1.bold = False
    
    p_cq2 = cell_left.add_paragraph()
    p_cq2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_cq2.paragraph_format.space_after = Pt(2)
    p_cq2.paragraph_format.line_spacing = 1.0
    r_cq2 = p_cq2.add_run("SỞ KHOA HỌC VÀ CÔNG NGHỆ" if not is_party else "ĐẢNG BỘ SỞ KH&CN")
    r_cq2.bold = True
    r_cq2.font.size = Pt(12)
    
    p_so = cell_left.add_paragraph()
    p_so.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_so.paragraph_format.space_after = Pt(1)
    if loai_van_ban == "bao_cao":
        r_so = p_so.add_run("Số:       /BC-SKHCN" if not is_party else "Số:       -BC/ĐBU")
        r_so.italic = False
        r_so.font.size = Pt(12)
    elif loai_van_ban not in TIEU_DE_THEO_LOAI:
        r_so = p_so.add_run("Số:       /SKHCN-VP" if not is_party else "Số:       -CV/ĐBU")
        r_so.italic = False
        r_so.font.size = Pt(12)

        ty_clean = re.sub(r'^(?:v/v|về việc)\s*', '', trich_yeu_den, flags=re.IGNORECASE).strip()
        ty_text = f"V/v {ty_clean}" if ty_clean else f"V/v phúc đáp CV số {so_hieu_den}"
        p_ty = cell_left.add_paragraph()
        p_ty.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_ty.paragraph_format.space_after = Pt(0)
        p_ty.paragraph_format.line_spacing = 1.0
        r_ty = p_ty.add_run(ty_text)
        r_ty.italic = True
        r_ty.font.size = Pt(12)
    
    # Cột phải: Quốc hiệu & Tiêu ngữ (Chính quyền) hoặc Tiêu đề Đảng
    p_qh = cell_right.paragraphs[0]
    p_qh.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_qh.paragraph_format.space_after = Pt(1)
    p_qh.paragraph_format.line_spacing = 1.0
    if not is_party:
        r_qh = p_qh.add_run("CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM\n")
        r_qh.bold = True
        r_qh.font.size = Pt(12)
        
        p_tn = cell_right.add_paragraph()
        p_tn.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_tn.paragraph_format.space_after = Pt(4)
        r_tn = p_tn.add_run("Độc lập - Tự do - Hạnh phúc")
        r_tn.bold = True
        r_tn.font.size = Pt(13)
    else:
        r_qh = p_qh.add_run("ĐẢNG CỘNG SẢN VIỆT NAM\n")
        r_qh.bold = True
        r_qh.font.size = Pt(13)
        
    now = datetime.now()
    p_date = cell_right.add_paragraph()
    p_date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_date.paragraph_format.space_after = Pt(0)
    r_date = p_date.add_run(f"Tây Ninh, ngày {now.day:02d} tháng {now.month:02d} năm {now.year}")
    r_date.italic = True
    r_date.font.size = Pt(13)
    
    if loai_van_ban == "bao_cao":
        p_bc = doc.add_paragraph()
        p_bc.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_bc.paragraph_format.space_before = Pt(14)
        p_bc.paragraph_format.space_after = Pt(2)
        r_bc = p_bc.add_run("BÁO CÁO")
        r_bc.bold = True
        r_bc.font.size = Pt(14)

        p_bcty = doc.add_paragraph()
        p_bcty.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_bcty.paragraph_format.space_after = Pt(12)
        ty_clean = re.sub(r'^(?:v/v|về việc)\s*', '', trich_yeu_den, flags=re.IGNORECASE).strip()
        r_bcty = p_bcty.add_run(f"Về việc {ty_clean}" if ty_clean else "Về tình hình thực hiện nhiệm vụ")
        r_bcty.bold = True
        r_bcty.font.size = Pt(13)

    # Kính gửi
    has_target = bool(co_quan_gui and co_quan_gui.strip() and co_quan_gui.strip().lower() not in ["không", "none", ""])
    if has_target:
        p_kg = doc.add_paragraph()
        p_kg.paragraph_format.space_before = Pt(8 if loai_van_ban == "bao_cao" else 16)
        p_kg.paragraph_format.space_after = Pt(10)
        p_kg.paragraph_format.left_indent = Inches(0.5)
        r_kg1 = p_kg.add_run("Kính gửi: ")
        r_kg1.bold = True
        r_kg2 = p_kg.add_run(f"{co_quan_gui}.")
        r_kg2.font.size = Pt(13)
    
    # Căn cứ và Liên kết Văn bản đến (Canh đều 2 bên - áp dụng cho công văn hoặc văn bản có số hiệu đến)
    if loai_van_ban != "bao_cao" and so_hieu_den and str(so_hieu_den).strip() not in ["", "None", "0"]:
        p_cc = doc.add_paragraph()
        p_cc.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_cc.paragraph_format.space_after = Pt(8)
        p_cc.paragraph_format.line_spacing = 1.2
        p_cc.paragraph_format.first_line_indent = Inches(0.4)
        r_cc = p_cc.add_run(
            f"Phúc đáp Công văn số {so_hieu_den} ngày {ngay_den} của {co_quan_gui} về việc {trich_yeu_den}; "
            f"sau khi rà soát chức năng, nhiệm vụ và các quy định pháp luật liên quan, "
            f"Sở Khoa học và Công nghệ tỉnh Tây Ninh có ý kiến như sau:"
        )
        r_cc.font.size = Pt(13)
    
    # Thân văn bản (Canh đều, loại bỏ sạch các dấu **, không để lặp lại mở đầu, duy nhất 1 lần ./. ở cuối cùng)
    raw_paragraphs = [p.strip() for p in draft_body_text.split("\n") if p.strip()]
    cleaned_paras = []
    has_custom_end = False

    for p_text in raw_paragraphs:
        clean = re.sub(r'^(?:#+|\-|\•)\s*', '', p_text).strip()
        if not clean:
            continue
        # Bỏ dòng "Kính gửi: ..." nếu AI tự chèn lặp lại
        if re.match(r'^Kính gửi\s*:', clean, re.IGNORECASE):
            continue
        # Bỏ dòng "Phúc đáp Công văn..." nếu AI tự chèn lặp lại
        if re.match(r'^Phúc đáp Công văn\s+', clean, re.IGNORECASE):
            continue
        # Nếu AI đã viết câu kết "Trên đây là ý kiến..."
        if re.match(r'^Trên đây là ý kiến\b', clean, re.IGNORECASE):
            clean = re.sub(r'[\s./]+$', '', clean) + "./."
            has_custom_end = True
            cleaned_paras.append(clean)
            continue
            
        # Các đoạn thân văn bản: chuẩn hóa bỏ ./. nếu có ở cuối
        clean = re.sub(r'\s*\./\.\s*$', '.', clean)
        cleaned_paras.append(clean)

    for clean_text in cleaned_paras:
        p_body = doc.add_paragraph()
        p_body.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_body.paragraph_format.space_after = Pt(6)
        p_body.paragraph_format.line_spacing = 1.2
        p_body.paragraph_format.first_line_indent = Inches(0.4)
        
        # Tách và parse các cụm **bold**
        parts = re.split(r'(\*\*.*?\*\*)', clean_text)
        for part in parts:
            if not part:
                continue
            if part.startswith('**') and part.endswith('**') and len(part) >= 4:
                bold_content = part[2:-2].strip()
                if bold_content:
                    r_b = p_body.add_run(bold_content)
                    r_b.bold = True
            else:
                norm_content = part.replace('**', '').replace('*', '')
                if norm_content:
                    p_body.add_run(norm_content)
            
    # Nếu chưa có câu kết công vụ thì thêm duy nhất 1 câu kết thúc bằng ./.
    if not has_custom_end:
        p_end = doc.add_paragraph()
        p_end.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        p_end.paragraph_format.space_before = Pt(6)
        p_end.paragraph_format.space_after = Pt(14)
        p_end.paragraph_format.first_line_indent = Inches(0.4)
        if loai_van_ban == "bao_cao":
            target = co_quan_gui if has_target else "Ủy ban nhân dân tỉnh"
            p_end.add_run(f"Sở Khoa học và Công nghệ tỉnh Tây Ninh kính báo cáo {target} xem xét, chỉ đạo./.")
        else:
            p_end.add_run(f"Trên đây là ý kiến của Sở Khoa học và Công nghệ tỉnh Tây Ninh kính gửi {co_quan_gui} tổng hợp, theo dõi./.")
    
    # 7. Nơi nhận & Chữ ký (Bảng 2 cột dưới cùng)
    table_footer = doc.add_table(rows=1, cols=2)
    table_footer.alignment = WD_TABLE_ALIGNMENT.CENTER
    table_footer.autofit = False
    
    col_nn = table_footer.columns[0]
    col_sig = table_footer.columns[1]
    col_nn.width = Inches(3.2)
    col_sig.width = Inches(3.6)
    
    cell_nn = table_footer.cell(0, 0)
    cell_sig = table_footer.cell(0, 1)
    set_cell_border(cell_nn)
    set_cell_border(cell_sig)
    
    # Nơi nhận
    p_nn1 = cell_nn.paragraphs[0]
    p_nn1.paragraph_format.space_after = Pt(2)
    r_nn_title = p_nn1.add_run("Nơi nhận:\n")
    r_nn_title.bold = True
    r_nn_title.italic = True
    r_nn_title.font.size = Pt(11)
    
    p_nn2 = cell_nn.add_paragraph()
    p_nn2.paragraph_format.space_after = Pt(0)
    p_nn2.paragraph_format.line_spacing = 1.0
    r_nn_items = p_nn2.add_run(
        f"- Như kính gửi;\n"
        f"- UBND tỉnh (báo cáo);\n"
        f"- Giám đốc, các PGĐ Sở;\n"
        f"- Lưu: VT, VP, P chuyên môn.\n"
    )
    r_nn_items.font.size = Pt(10)
    r_nn_items.italic = True
    
    # Chức danh và chữ ký
    p_sig1 = cell_sig.paragraphs[0]
    p_sig1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sig1.paragraph_format.space_after = Pt(2)
    r_sig1 = p_sig1.add_run("KT. GIÁM ĐỐC\n" if signer_title != "GIÁM ĐỐC" else "")
    r_sig1.bold = True
    r_sig1.font.size = Pt(12)
    
    p_sig2 = cell_sig.add_paragraph()
    p_sig2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sig2.paragraph_format.space_after = Pt(45) # Chừa khoảng trống cho chữ ký số
    r_sig2 = p_sig2.add_run(signer_title)
    r_sig2.bold = True
    r_sig2.font.size = Pt(13)
    
    p_sig3 = cell_sig.add_paragraph()
    p_sig3.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p_sig3.paragraph_format.space_after = Pt(0)
    r_sig3 = p_sig3.add_run(signer_name)
    r_sig3.bold = True
    r_sig3.font.size = Pt(13)
    
    # Lưu file
    safe_name = re.sub(r'[^a-zA-Z0-9_\-]', '_', doc_info.get("hash_id") or f"doc_{now.strftime('%Y%m%d%H%M%S')}")
    out_filename = f"Du_thao_tra_loi_{safe_name}.docx"
    out_path = DRAFTS_DIR / out_filename
    _dat_tieu_de_theo_loai(doc, loai_van_ban, ty_text)
    doc.save(str(out_path))
    return str(out_path)

if __name__ == "__main__":
    test_doc = {
        "hash_id": "test_123",
        "so_hieu": "11003/BC-SNV",
        "co_quan": "Sở Nội vụ tỉnh Tây Ninh",
        "ngay_ban_hanh": "12/10/2026",
        "trich_yeu": "Báo cáo kết quả rà soát, hoàn thiện và xác nhận dữ liệu Điều tra cơ sở hành chính, sự nghiệp năm 2026"
    }
    sample_body = (
        "1. Về số liệu điều tra cơ sở hành chính, sự nghiệp của Sở KH&CN:\n"
        "Sở Khoa học và Công nghệ đã hoàn thành việc rà soát và đối chiếu 100% dữ liệu của các phòng ban chuyên môn và 02 đơn vị sự nghiệp trực thuộc.\n\n"
        "2. Về kiến nghị và đề xuất:\n"
        "Thống nhất với dự thảo báo cáo tổng hợp của Sở Nội vụ; đề nghị Sở Nội vụ tiếp tục hỗ trợ hoàn thiện tài khoản kết xuất báo cáo điện tử."
    )
    p = create_docx_reply_draft(test_doc, sample_body)
    print("Generated test docx:", p)
