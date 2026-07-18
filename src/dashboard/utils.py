import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import sys
import re
import hashlib
import textwrap
from urllib.parse import urlparse
from pathlib import Path
import requests

# ─────────────────────────────────────────────────────────────
# Cấu hình hằng số
# ─────────────────────────────────────────────────────────────
MANIFEST_PATH = Path("data/export/manifest.csv")
RAW_DIR = MANIFEST_PATH.parent.parent / "raw"
PYTHON_BIN    = sys.executable

MAP_LINH_VUC = {
    "nhan_thuc": "Nhận thức", "ngon_ngu": "Ngôn ngữ",
    "tham_my": "Thẩm mỹ", "the_chat": "Thể chất",
    "tinh_cam_xh": "Tình cảm - Xã hội", "chung": "Chung"
}

MAP_AGE_BAND = {
    "34": "3–4 tuổi", "45": "4–5 tuổi",
    "56": "5–6 tuổi", "g1_hk1": "Lớp 1 (HK1)", "g1_hk2": "Lớp 1 (HK2)", "chung": "Chung (Mọi độ tuổi)"
}

MAP_DOC_TYPE = {
    "pl.chuong_trinh": "Chương trình (PL)", "pl.chuan_5t": "Chuẩn 5 tuổi (PL)",
    "pl.thong_tu": "Thông tư (PL)", "pl.cong_van": "Công văn (PL)",
    "sgk.sgk": "Sách GK (SGK)", "sgk.sbt": "Sách BT (SGK)",
    "sgk.sgv": "Sách GV (SGK)", "sgk.tap_to": "Tập tô (SGK)",
    "gt.truong": "GT Trường (GT)", "gt.quoc_te": "GT Quốc tế (GT)", "gt.giao_an": "Giáo án (GT)",
    "bt.nang_cao": "Nâng cao (BT)", "bt.bo_tro": "Bổ trợ (BT)",
    "bt.truyen_tho": "Truyện/Thơ (BT)", "bt.ky_nang": "Kỹ năng (BT)",
    "bt.phieu_bai_tap": "Phiếu bài tập (BT)", "bt.tro_choi": "Trò chơi (BT)",
    "kn.kinh_nghiem": "Kinh nghiệm (KN)", "kn.skkn": "Sáng kiến KN (KN)",
    "kn.meo_day": "Mẹo dạy (KN)", "kn.du_gio": "Dự giờ (KN)",
    "nc.nghien_cuu": "Nghiên cứu (NC)", "nc.bai_bao": "Bài báo (NC)",
    "nc.tap_huan": "Tập huấn (NC)", "nc.ct_nuoc_ngoai": "CT Nước ngoài (NC)",
    "md.hinh_anh": "Hình ảnh (MD)", "md.am_thanh": "Âm thanh (MD)", "md.video": "Video (MD)",
    "khac": "Khác"
}

MAP_SUB_DOMAIN = {
    "nt.toan": "Toán học (NT)", "nt.kpkh": "Khám phá khoa học (NT)", "nt.kpxh": "Khám phá xã hội (NT)",
    "nn.doc_viet": "Đọc viết (NN)", "nn.nghe_noi": "Nghe nói (NN)", "nn.van_hoc": "Văn học (NN)",
    "tm.tao_hinh": "Tạo hình (TM)", "tm.am_nhac": "Âm nhạc (TM)",
    "tc.van_dong": "Vận động (TC)", "tc.dinh_duong": "Dinh dưỡng sức khỏe (TC)",
    "tx.tinh_cam": "Tình cảm (TX)", "tx.kn_xh": "Kỹ năng xã hội (TX)"
}

MAP_LEVELS = {
    "lv01": "Mức 1: Nhận biết",
    "lv02": "Mức 2: Vận dụng",
    "lv03": "Mức 3: Nâng cao sáng tạo"
}

# ─────────────────────────────────────────────────────────────
# Hàm tiện ích dùng chung
# ─────────────────────────────────────────────────────────────

from src.database import engine, init_db

@st.cache_data(ttl=30)
def tai_du_lieu() -> pd.DataFrame:
    """Đọc bảng documents từ PostgreSQL và cache 30 giây."""
    try:
        # Nếu chưa tạo bảng thì thử tạo (chỉ có tác dụng nếu kết nối được DB)
        init_db()
        df = pd.read_sql_table("documents", engine)
    except Exception as e:
        # Nếu có lỗi (chẳng hạn không kết nối được PostgreSQL), bỏ qua
        return pd.DataFrame()
        
    if df.empty:
        return df

    try:
        # Chuyển đổi tên thân thiện
        if "linh_vuc" in df.columns:
            df["linh_vuc"] = df["linh_vuc"].map(lambda x: MAP_LINH_VUC.get(str(x), str(x)))
        if "age_band" in df.columns:
            df["age_band"] = df["age_band"].map(lambda x: MAP_AGE_BAND.get(str(x), str(x)))
        if "doc_type" in df.columns:
            df["doc_type"] = df["doc_type"].map(lambda x: MAP_DOC_TYPE.get(str(x), str(x)))
            
        # Parse boolean fields (đã lưu bool trong DB, nhưng ta cứ check an toàn)
        if "need_manual" in df.columns:
            df["need_manual"] = df["need_manual"].astype(bool)
            
        # Rename columns to friendly names globally
        df = df.rename(columns={
            "doc_code": "Mã tài liệu",
            "name": "Tên tài liệu",
            "linh_vuc": "Lĩnh vực",
            "age_band": "Độ tuổi",
            "doc_type": "Loại tài liệu",
            "source_tier": "Độ uy tín",
            "status": "Trạng thái",
            "source_url": "Đường dẫn gốc",
            "need_manual": "Cần duyệt",
            "uploaded_at": "Ngày tải"
        })
        
        if "Trạng thái" in df.columns:
            df["Trạng thái"] = df["Trạng thái"].map({"need_manual": "Cần duyệt", "exported": "Hoàn thành"}).fillna(df["Trạng thái"])
            
        # Xử lý các giá trị kỹ thuật khó hiểu
        if "Mã tài liệu" in df.columns:
            df["Mã tài liệu"] = df["Mã tài liệu"].replace("NEED_MANUAL_MIGRATED", "Chưa cấp mã").replace("NEED_MANUAL", "Chưa cấp mã")
            
        if "Tên tài liệu" in df.columns and "Đường dẫn gốc" in df.columns:
            # Nếu tên tài liệu là chuỗi hash (độ dài 64), lấy tên file từ URL
            def fix_name(row):
                name = str(row.get("Tên tài liệu", ""))
                if len(name) == 64 and name.isalnum(): # Giả định là mã SHA-256
                    url = str(row.get("Đường dẫn gốc", ""))
                    if url and "/" in url:
                        return url.split("/")[-1].split("?")[0] or "Tài liệu không tên"
                return name
            df["Tên tài liệu"] = df.apply(fix_name, axis=1)
            
        return df
    except Exception as e:
        st.error(f"Lỗi khi xử lý dữ liệu từ Database: {e}")
        return pd.DataFrame()


def to_mau_log(dong: str) -> str:
    """Tô màu dòng log theo mức độ (loguru format)."""
    dong = dong.replace("<", "&lt;").replace(">", "&gt;")
    if "| ERROR" in dong or "| CRITICAL" in dong:
        return f'<span style="color:#ff7b72">{dong}</span>'
    if "| SUCCESS" in dong:
        return f'<span style="color:#3fb950">{dong}</span>'
    if "| WARNING" in dong:
        return f'<span style="color:#d29922">{dong}</span>'
    if "| INFO" in dong:
        return f'<span style="color:#79c0ff">{dong}</span>'
    return f'<span style="color:#8b949e">{dong}</span>'


def hien_thi_log(cac_dong: list[str]) -> None:
    """Hiển thị log dạng terminal đen có cuộn."""
    noi_dung = "\n".join(to_mau_log(d) for d in cac_dong[-80:])
    st.markdown(
        f"""<div style="
            background:#0d1117; color:#c9d1d9;
            font-family:'Fira Code',monospace; font-size:0.78rem;
            padding:0.8rem 1rem; border-radius:8px;
            border:1px solid #30363d;
            max-height:380px; overflow-y:auto;
            white-space:pre-wrap; word-break:break-all;
        ">{noi_dung}</div>""",
        unsafe_allow_html=True,
    )


# ─────────────────────────────────────────────────────────────────
# Helpers: tìm file raw
# ─────────────────────────────────────────────────────────────────

def tim_raw_file(hash_name: str) -> Path | None:
    """Tìm file raw tương ứng với tên/hash trong data/raw/."""
    if not hash_name or isinstance(hash_name, float):
        return None
    name_str = str(hash_name).strip()
    if not name_str or name_str.lower() == "nan":
        return None
    for ext in (".pdf", ".docx", ".doc", ".html", ".htm"):
        p = RAW_DIR / f"{name_str}{ext}"
        if p.exists():
            return p
    return None


def phan_loai_url(url: str) -> str:
    parsed = urlparse(url.lower())
    host, path = parsed.netloc, parsed.path
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if path.endswith(".pdf"):
        return "pdf"
    if path.endswith((".docx", ".doc")):
        return "docx"
    if path.endswith((".html", ".htm")):
        return "html"
    return "web"


def youtube_embed_url(url: str) -> str | None:
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    return f"https://www.youtube.com/embed/{match.group(1)}" if match else None


# ─────────────────────────────────────────────────────────────────
# Renderer: PDF → ảnh (PyMuPDF)
# ─────────────────────────────────────────────────────────────────

def render_pdf(pdf_path: Path, max_trang: int = 20) -> bool:
    try:
        import fitz
    except ImportError:
        return False
    try:
        doc = fitz.open(str(pdf_path))
        tong_trang = len(doc)
        hien_thi = min(tong_trang, max_trang)
        st.caption(f":material/picture_as_pdf: `{pdf_path.name}` · {tong_trang} trang — cuộn bên trong khung để xem")
        with st.container(height=640, border=True):
            for i in range(hien_thi):
                page = doc[i]
                pix = page.get_pixmap(matrix=fitz.Matrix(1.8, 1.8), alpha=False)
                st.image(pix.tobytes("png"), caption=f"Trang {i + 1}", use_container_width=True)
            if tong_trang > max_trang:
                st.caption(f"... còn {tong_trang - max_trang} trang. Tải về để xem đầy đủ.")
        doc.close()
        return True
    except Exception as e:
        st.warning(f"Không thể đọc PDF: {e}")
        return False


# ─────────────────────────────────────────────────────────────────
# Renderer: DOCX → HTML có định dạng (python-docx)
# ─────────────────────────────────────────────────────────────────

_DOCX_HTML_WRAP = textwrap.dedent("""\
<!DOCTYPE html><html lang="vi"><head><meta charset="UTF-8">
<style>
  body {{ font-family:'Segoe UI',Arial,sans-serif; font-size:14px;
          line-height:1.8; color:#212121; background:#fff;
          padding:32px 44px; max-width:820px; margin:0 auto; }}
  h1 {{ font-size:1.5em; font-weight:700; color:#1a237e; margin:1em 0 .4em; border-bottom:2px solid #e8eaf6; padding-bottom:.3em; }}
  h2 {{ font-size:1.25em; font-weight:600; color:#283593; margin:1em 0 .3em; }}
  h3 {{ font-size:1.1em; font-weight:600; color:#3949ab; margin:.8em 0 .25em; }}
  p  {{ margin:.5em 0; }}
  b,strong {{ color:#1a237e; }}
  table {{ border-collapse:collapse; width:100%; margin:1em 0; font-size:.93em; }}
  th {{ background:#3f51b5; color:#fff; padding:8px 12px; text-align:left; }}
  td {{ padding:7px 12px; border-bottom:1px solid #e8eaf6; }}
  tr:nth-child(even) td {{ background:#f5f5ff; }}
  ul,ol {{ padding-left:1.6em; margin:.4em 0; }}
  li {{ margin:.2em 0; }}
  .img-wrap {{ text-align:center; margin:1em 0; }}
  .img-wrap img {{ max-width:100%; border-radius:6px; border:1px solid #e0e0e0; }}
</style></head><body>{content}</body></html>
""")

def render_docx(docx_path: Path) -> bool:
    try:
        from docx import Document
        from docx.oxml.ns import qn
        import base64
    except ImportError:
        return False

    try:
        doc = Document(str(docx_path))
    except Exception as e:
        st.warning(f"Không thể mở DOCX: {e}")
        return False

    # Trích xuất ảnh nhúng trong file để dùng inline base64
    rels = {}
    try:
        for rel in doc.part.rels.values():
            if "image" in rel.reltype:
                img_data = rel.target_part.blob
                ext = rel.target_part.content_type.split("/")[-1]
                b64 = base64.b64encode(img_data).decode()
                rels[rel.rId] = f"data:image/{ext};base64,{b64}"
    except Exception:
        pass

    def _run_html(run) -> str:
        text = run.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if not text:
            return ""
        if run.bold:
            text = f"<strong>{text}</strong>"
        if run.italic:
            text = f"<em>{text}</em>"
        if run.underline:
            text = f"<u>{text}</u>"
        return text

    def _para_html(para) -> str:
        style = para.style.name if para.style else "Normal"
        inner = "".join(_run_html(r) for r in para.runs)
        if not inner.strip():
            return "<p>&nbsp;</p>"
        if "Heading 1" in style:
            return f"<h1>{inner}</h1>"
        if "Heading 2" in style:
            return f"<h2>{inner}</h2>"
        if "Heading 3" in style or "Heading 4" in style:
            return f"<h3>{inner}</h3>"
        if "List" in style:
            return f"<li>{inner}</li>"
        return f"<p>{inner}</p>"

    def _table_html(table) -> str:
        rows_html = []
        for i, row in enumerate(table.rows):
            cells = "".join(
                f"<{'th' if i==0 else 'td'}>{c.text.replace('&','&amp;').replace('<','&lt;')}</{'th' if i==0 else 'td'}>"
                for c in row.cells
            )
            rows_html.append(f"<tr>{cells}</tr>")
        return "<table>" + "".join(rows_html) + "</table>"

    parts = []
    # Duyệt body theo thứ tự xuất hiện (đoạn văn + bảng xen kẽ)
    from docx.oxml import OxmlElement
    body = doc.element.body
    for child in body:
        tag = child.tag.split("}")[-1]
        if tag == "p":
            from docx.text.paragraph import Paragraph
            para = Paragraph(child, doc)
            # Kiểm tra ảnh inline
            imgs = child.findall(".//" + qn("a:blip"), namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"})
            if imgs:
                for blip in imgs:
                    embed = blip.get(qn("r:embed"))
                    if embed and embed in rels:
                        parts.append(f'<div class="img-wrap"><img src="{rels[embed]}"></div>')
            else:
                parts.append(_para_html(para))
        elif tag == "tbl":
            from docx.table import Table
            parts.append(_table_html(Table(child, doc)))

    html = _DOCX_HTML_WRAP.format(content="".join(parts))
    st.caption(f":material/description: `{docx_path.name}` · {len(doc.paragraphs)} đoạn văn")
    # Wrap in a div with height
    full_html = f'<div style="height: 640px; overflow-y: auto;">{html}</div>'
    st.markdown(full_html, unsafe_allow_html=True)
    return True


# ─────────────────────────────────────────────────────────────────
# Renderer: HTML raw → nhúng nội bộ
# ─────────────────────────────────────────────────────────────────

def render_html(html_path: Path) -> bool:
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    # Chặn redirect và script nguy hiểm, giữ layout
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<meta[^>]+http-equiv[^>]*>', '', content, flags=re.IGNORECASE)
    kb = len(content.encode()) // 1024
    st.caption(f":material/language: `{html_path.name}` · {kb} KB")
    full_html = f'<div style="height: 640px; overflow-y: auto; background: white;">{content}</div>'
    st.markdown(full_html, unsafe_allow_html=True)
    return True


# ─────────────────────────────────────────────────────────────────
# Dispatcher chính
# ─────────────────────────────────────────────────────────────────

@st.cache_data(ttl=3600)
def can_embed_url(url: str) -> bool:
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        r = requests.head(url, headers=headers, timeout=3, allow_redirects=True)
        
        # Nếu server không hỗ trợ HEAD, thử GET
        if r.status_code == 405 or r.status_code == 403:
            r = requests.get(url, headers=headers, timeout=3, stream=True)
            r.close()

        xfo = r.headers.get('X-Frame-Options', '').upper()
        if 'DENY' in xfo or 'SAMEORIGIN' in xfo:
            return False
            
        csp = r.headers.get('Content-Security-Policy', '').lower()
        if 'frame-ancestors' in csp:
            # Rất khó parse chính xác csp, an toàn nhất là coi như bị chặn nếu có rules
            if 'none' in csp or 'self' in csp:
                return False
                
        return True
    except Exception:
        # Lỗi mạng, timeout -> có thể trang sập hoặc chặn bot -> thử render offline
        return False

def hien_thi_xem_truoc(url: str, hash_name: str):
    raw_file = tim_raw_file(hash_name)
    loai_url = phan_loai_url(url)

    if loai_url == "youtube":
        embed = youtube_embed_url(url)
        if embed:
            components.iframe(embed, height=440)
        else:
            st.link_button(":material/play_circle: Mở YouTube", url)
        return

    if loai_url == "web":
        # Nếu đã có file HTML offline → ưu tiên render offline, tránh hoàn toàn vấn đề X-Frame-Options
        if raw_file is not None and raw_file.suffix.lower() in (".html", ".htm"):
            st.caption(":material/language: Đang xem phiên bản HTML đã tải về")
            ok = render_html(raw_file)
            if ok:
                st.link_button(":material/open_in_new: Mở trang web gốc trong tab mới", url)
                return
        
        # Không có file offline → thử nhúng live URL
        if can_embed_url(url):
            st.caption(f":material/language: Đang xem trực tiếp từ: `{url}`")
            html_code = f"""
            <div style="width: 100%; height: 800px; overflow: hidden; position: relative; border-radius: 8px; border: 1px solid #e0e0e0;">
                <iframe src="{url}" style="position: absolute; top: 0; left: 0; width: 133.33%; height: 133.33%; border: none; transform: scale(0.75); transform-origin: top left; background: white;"></iframe>
            </div>
            """
            st.markdown(html_code, unsafe_allow_html=True)
            st.caption("*(Nếu trang web trắng tinh do chặn iframe, hãy dùng nút mở tab mới bên dưới)*")
            st.link_button(":material/open_in_new: Mở trang web trong tab mới", url)
            return
        else:
            # Bị chặn iframe và không có file offline
            st.warning(
                "Trang web bị chặn nhúng (X-Frame-Options) và không có bản HTML offline trong kho. "
                "Dùng nút bên dưới để mở trực tiếp.",
                icon=":material/block:"
            )
            st.link_button(":material/open_in_new: Mở trang web trong tab mới", url)
            return

    if raw_file is None:
        st.warning(
            "Không tìm thấy file gốc trong kho (`data/raw/`). "
            "File có thể đã bị xoá hoặc chưa tải về.",
            icon=":material/folder_off:"
        )
        st.link_button(":material/open_in_new: Mở tài liệu gốc trong tab mới", url)
        
        # Fallback: nếu là PDF, cố gắng nhúng trực tiếp url gốc
        if loai_url == "pdf":
            st.info("Đang thử nhúng trực tiếp PDF từ web...")
            st.markdown(f'<iframe src="{url}" width="100%" height="800px" style="border: none;"></iframe>', unsafe_allow_html=True)
            
        return

    ext = raw_file.suffix.lower()
    st.caption(f"Loại file: `{ext.upper()}` · Kích thước: `{raw_file.stat().st_size // 1024:,} KB`")

    if ext == ".pdf":
        ok = render_pdf(raw_file)
        if not ok:
            st.link_button(":material/open_in_new: Mở PDF trong tab mới", url)

    elif ext in (".docx", ".doc"):
        ok = render_docx(raw_file)
        if not ok:
            st.link_button(":material/open_in_new: Mở DOCX trong tab mới", url)

    else:
        st.info(f"Định dạng `{ext}` chưa được hỗ trợ xem trước.", icon=":material/help:")
        st.link_button(":material/open_in_new: Mở trong tab mới", url)

    # Nút tải file gốc
    with open(raw_file, "rb") as f:
        st.download_button(
            label=f":material/download: Tải về file gốc ({ext.upper()})",
            data=f,
            file_name=raw_file.name,
            mime={".pdf": "application/pdf", ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}.get(ext, "application/octet-stream"),
        )
