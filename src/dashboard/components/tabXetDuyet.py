import re
import hashlib
import textwrap
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from src.dashboard.utils import (
    MANIFEST_PATH, MAP_AGE_BAND, MAP_DOC_TYPE, MAP_LINH_VUC, tai_du_lieu
)

RAW_DIR = MANIFEST_PATH.parent.parent / "raw"

# ─────────────────────────────────────────────────────────────────
# Helpers: lưu phê duyệt
# ─────────────────────────────────────────────────────────────────

def luu_phe_duyet(idx_goc, url):
    chon_lv = st.session_state.get("duyet_lv")
    chon_ab = st.session_state.get("duyet_ab")
    chon_dt = st.session_state.get("duyet_dt")

    df_raw = pd.DataFrame()
    if MANIFEST_PATH.exists() and MANIFEST_PATH.stat().st_size > 0:
        df_raw = pd.read_csv(MANIFEST_PATH)

    if not df_raw.empty:
        df_raw.at[idx_goc, "linh_vuc"] = chon_lv
        df_raw.at[idx_goc, "age_band"] = chon_ab
        df_raw.at[idx_goc, "doc_type"] = chon_dt
    df_raw.at[idx_goc, "need_manual"] = False
    df_raw.at[idx_goc, "status"] = "exported"

    short_hash = hashlib.md5(str(url).encode()).hexdigest()[:4].upper()
    lv_m = {"nhan_thuc": "NT", "ngon_ngu": "NN", "tham_my": "TM", "the_chat": "TC", "tinh_cam_xh": "TX"}.get(chon_lv, "XX")
    dt_m = chon_dt.split(".")[-1].upper()[:3] if "." in chon_dt else chon_dt[:3].upper()
    df_raw.at[idx_goc, "doc_code"] = f"DOC-{lv_m}-{chon_ab}-{dt_m}-{short_hash}"

    df_raw.to_csv(MANIFEST_PATH, index=False, encoding="utf-8")
    tai_du_lieu.clear()
    st.session_state.duyet_thanh_cong = True


# ─────────────────────────────────────────────────────────────────
# Helpers: tìm file raw
# ─────────────────────────────────────────────────────────────────

def _tim_raw_file(hash_name: str) -> Path | None:
    """Tìm file raw tương ứng với hash trong data/raw/."""
    if not hash_name or isinstance(hash_name, float) or len(str(hash_name)) < 32:
        return None
    for ext in (".pdf", ".docx", ".doc", ".html", ".htm"):
        p = RAW_DIR / f"{hash_name}{ext}"
        if p.exists():
            return p
    return None


def _phan_loai_url(url: str) -> str:
    parsed = urlparse(url.lower())
    host, path = parsed.netloc, parsed.path
    if "youtube.com" in host or "youtu.be" in host:
        return "youtube"
    if path.endswith(".pdf"):
        return "pdf"
    if path.endswith((".docx", ".doc")):
        return "docx"
    return "web"


def _youtube_embed_url(url: str) -> str | None:
    match = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    return f"https://www.youtube.com/embed/{match.group(1)}" if match else None


# ─────────────────────────────────────────────────────────────────
# Renderer: PDF → ảnh (PyMuPDF)
# ─────────────────────────────────────────────────────────────────

def _render_pdf(pdf_path: Path, max_trang: int = 20) -> bool:
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

def _render_docx(docx_path: Path) -> bool:
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
    st.iframe(html, height=640)
    return True


# ─────────────────────────────────────────────────────────────────
# Renderer: HTML raw → nhúng nội bộ
# ─────────────────────────────────────────────────────────────────

def _render_html(html_path: Path) -> bool:
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
    # Chặn redirect và script nguy hiểm, giữ layout
    content = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
    content = re.sub(r'<meta[^>]+http-equiv[^>]*>', '', content, flags=re.IGNORECASE)
    kb = len(content.encode()) // 1024
    st.caption(f":material/language: `{html_path.name}` · {kb} KB")
    st.iframe(content, height=640)
    return True


# ─────────────────────────────────────────────────────────────────
# Dispatcher chính
# ─────────────────────────────────────────────────────────────────

def _hien_thi_xem_truoc(url: str, hash_name: str):
    raw_file = _tim_raw_file(hash_name)
    loai_url = _phan_loai_url(url)

    if loai_url == "youtube":
        embed = _youtube_embed_url(url)
        if embed:
            st.iframe(embed, height=440)
        else:
            st.link_button(":material/play_circle: Mở YouTube", url)
        return

    if raw_file is None:
        st.warning(
            "Không tìm thấy file gốc trong kho (`data/raw/`). "
            "File có thể đã bị xoá hoặc chưa tải về.",
            icon=":material/folder_off:"
        )
        st.link_button(":material/open_in_new: Mở tài liệu gốc trong tab mới", url)
        return

    ext = raw_file.suffix.lower()
    st.caption(f"Loại file: `{ext.upper()}` · Kích thước: `{raw_file.stat().st_size // 1024:,} KB`")

    if ext == ".pdf":
        ok = _render_pdf(raw_file)
        if not ok:
            st.link_button(":material/open_in_new: Mở PDF trong tab mới", url)

    elif ext in (".docx", ".doc"):
        ok = _render_docx(raw_file)
        if not ok:
            st.link_button(":material/open_in_new: Mở DOCX trong tab mới", url)

    elif ext in (".html", ".htm"):
        ok = _render_html(raw_file)
        if not ok:
            st.link_button(":material/open_in_new: Mở trang web trong tab mới", url)

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


# ─────────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────────

def render_tab_xet_duyet():
    if st.session_state.pop("duyet_thanh_cong", False):
        st.toast("Đã phê duyệt tài liệu thành công!", icon="✅")

    df_raw_csv = pd.DataFrame()
    if MANIFEST_PATH.exists():
        try:
            df_raw_csv = pd.read_csv(MANIFEST_PATH)
        except pd.errors.EmptyDataError:
            pass

    if df_raw_csv.empty or "need_manual" not in df_raw_csv.columns:
        st.info("Chưa có dữ liệu.", icon=":material/info:")
        return

    df_can_duyet_raw = df_raw_csv[df_raw_csv["need_manual"] == True]
    if df_can_duyet_raw.empty:
        st.success("Tuyệt vời! Không có tài liệu nào cần duyệt tay.", icon=":material/celebration:")
        return

    # Header
    col_h, col_badge = st.columns([4, 1])
    with col_h:
        st.subheader(":material/fact_check: Xét duyệt tài liệu", anchor=False)
    with col_badge:
        st.badge(f"{len(df_can_duyet_raw)} chờ duyệt", color="orange", icon=":material/pending:")

    df_hien_thi = tai_du_lieu()
    df_can_duyet_ht = df_hien_thi[df_hien_thi["Cần duyệt"] == True]
    if df_can_duyet_ht.empty:
        return

    chon = st.selectbox(
        "Chọn tài liệu cần xét duyệt",
        options=df_can_duyet_ht["Tên tài liệu"].tolist(),
        key="chon_tai_lieu_duyet",
        label_visibility="collapsed",
        placeholder="🔍 Chọn tài liệu để xem và phân loại...",
    )

    hang_ht = df_can_duyet_ht[df_can_duyet_ht["Tên tài liệu"] == chon].iloc[0]
    url = hang_ht.get("Đường dẫn gốc", "")

    hang_goc_rows = df_raw_csv[df_raw_csv["source_url"] == url]
    if hang_goc_rows.empty:
        return
    hang_goc = hang_goc_rows.iloc[0]
    hash_name = str(hang_goc.get("name", ""))
    loai = _phan_loai_url(url)

    ICON_LOAI = {"youtube": ":material/smart_display:", "pdf": ":material/picture_as_pdf:", "docx": ":material/description:", "web": ":material/language:"}
    NHAN_LOAI = {"youtube": "YouTube", "pdf": "PDF", "docx": "Word/DOCX", "web": "Trang web"}

    col_panel, col_viewer = st.columns([1, 3], gap="medium")

    # ── Cột trái: thông tin + form phân loại ──
    with col_panel:
        with st.container(border=True):
            st.markdown(f"**{chon[:55]}{'...' if len(chon) > 55 else ''}**")
            st.caption(f"{ICON_LOAI.get(loai)} {NHAN_LOAI.get(loai)}")
            st.link_button(":material/open_in_new: Mở nguồn gốc", url, use_container_width=True)
            st.markdown("---")
            tier = hang_goc.get("source_tier", "?")
            uploaded_at = str(hang_goc.get("uploaded_at", ""))[:10]
            st.markdown(f":material/grade: **Độ uy tín:** `{tier}`")
            st.markdown(f":material/calendar_today: **Tải về:** `{uploaded_at}`")

        st.space("small")

        with st.form("form_xet_duyet", border=True):
            st.markdown("##### :material/tune: Phân loại tài liệu")

            options_lv = list(MAP_LINH_VUC.keys())
            idx_lv = options_lv.index(hang_goc["linh_vuc"]) if hang_goc["linh_vuc"] in options_lv else 0
            st.selectbox("Lĩnh vực phát triển", options=options_lv, index=idx_lv,
                         format_func=lambda x: MAP_LINH_VUC.get(x, x), key="duyet_lv")

            options_ab = list(MAP_AGE_BAND.keys())
            idx_ab = options_ab.index(hang_goc["age_band"]) if hang_goc["age_band"] in options_ab else 0
            st.selectbox("Độ tuổi áp dụng", options=options_ab, index=idx_ab,
                         format_func=lambda x: MAP_AGE_BAND.get(x, x), key="duyet_ab")

            options_dt = list(MAP_DOC_TYPE.keys())
            idx_dt = options_dt.index(hang_goc["doc_type"]) if hang_goc["doc_type"] in options_dt else 0
            st.selectbox("Loại tài liệu", options=options_dt, index=idx_dt,
                         format_func=lambda x: MAP_DOC_TYPE.get(x, x), key="duyet_dt")

            st.space("small")
            idx_goc = hang_goc.name
            submitted = st.form_submit_button(
                "Phê duyệt & lưu", type="primary",
                icon=":material/done_all:", use_container_width=True,
            )
            if submitted:
                luu_phe_duyet(idx_goc, url)
                st.rerun()

    # ── Cột phải: xem tài liệu gốc ──
    with col_viewer:
        st.markdown("##### :material/preview: Tài liệu gốc")
        _hien_thi_xem_truoc(url, hash_name)
