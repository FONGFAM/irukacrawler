import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime
import re

from src.dashboard.components.viewer import render_document_preview

RAW_DIR = Path("data/raw")
CONVERTED_DIR = Path("data/converted")
MANIFEST_PATH = Path("data/export/manifest.csv")

_EXT_ICON  = {".pdf": "📄", ".docx": "📝", ".doc": "📝", ".html": "🌐", ".htm": "🌐"}
_EXT_COLOR = {".pdf": "#e74c3c", ".docx": "#2980b9", ".doc": "#2980b9", ".html": "#27ae60", ".htm": "#27ae60"}

PAGE_SIZE = 5


def _badge(label: str, color: str = "#555") -> str:
    return (
        f'<span style="background:{color};color:white;border-radius:4px;'
        f'padding:2px 8px;font-size:0.75rem;font-weight:600">{label}</span>'
    )

def _fmt_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    return f"{size_bytes / (1024 * 1024):.1f} MB"

def _fmt_time(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%d/%m/%Y %H:%M")


from urllib.parse import urlparse, unquote

def _extract_name_from_url(url: str) -> str:
    try:
        parsed = urlparse(url)
        path = unquote(parsed.path)
        parts = [p for p in path.split("/") if p]
        if not parts:
            return ""
        last_part = parts[-1]
        last_part = re.sub(r"\.[a-zA-Z0-9]+$", "", last_part)
        if last_part.isdigit() and len(parts) > 1:
            last_part = parts[-2] + " " + last_part
        clean_name = last_part.replace("-", " ").replace("_", " ")
        clean_name = " ".join(word.capitalize() for word in clean_name.split())
        return clean_name
    except:
        return ""

def _is_gibberish(text: str) -> bool:
    if not text:
        return True
    weird_count = sum(1 for c in text if c in "#$@%^*_=~`{}[]|\\<>߲߳ԛԧ")
    if weird_count > 3 or len(text.strip()) < 4:
        return True
    return False

def _extract_title_from_md(md_path: str) -> str:
    """Trích xuất dòng tiêu đề đầu tiên có nghĩa từ file Markdown."""
    try:
        text = Path(md_path).read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith("<!--"):
                continue
            # Bỏ dấu --- Trang N ---
            if re.match(r"^---\s*Trang\s*\d+", line):
                continue
            if line.startswith("[Ảnh:"):
                continue
            # Bỏ ký tự markdown thừa
            clean = re.sub(r"^#+\s*", "", line).strip()
            clean = re.sub(r"\*+", "", clean).strip()
            if not _is_gibberish(clean):
                return clean[:80]
    except Exception:
        pass
    return ""


from src.database import SessionLocal, DocumentModel
import hashlib

def _load_db_names() -> dict:
    """Tải tên và metadata từ SQLite DB (do LLM đã generate)."""
    result = {}
    db = SessionLocal()
    try:
        docs = db.query(DocumentModel).all()
        for doc in docs:
            url = str(doc.source_url or "").strip()
            if not url:
                continue
            # Crawler băm SHA-256 của URL để lưu file raw
            stem = hashlib.sha256(url.encode("utf-8")).hexdigest()
            name = str(doc.name or "").strip()
            
            # Nếu tên vẫn là hash (chưa có tên đẹp từ LLM), lấy tiêu đề thay thế
            if name == stem or not name:
                name = ""
                
            result[stem] = {
                "name": name,
                "url": url,
                "status": str(doc.status or ""),
                "doc_type": str(doc.doc_type or ""),
                "age_band": str(doc.age_band or ""),
                "linh_vuc": str(doc.linh_vuc or ""),
            }
    except Exception as e:
        st.error(f"Lỗi đọc DB: {e}")
    finally:
        db.close()
    return result


def _extract_title_from_pdf(pdf_path: str) -> str:
    try:
        import fitz
        doc = fitz.open(pdf_path)
        title = doc.metadata.get("title", "")
        if title and not _is_gibberish(title):
            return title.strip()
    except Exception:
        pass
    return ""

def _load_crawled_urls() -> dict:
    import json
    result = {}
    try:
        with open("data/crawled_urls.json", "r", encoding="utf-8") as f:
            urls = json.load(f)
            for url in urls:
                stem = hashlib.sha256(url.encode("utf-8")).hexdigest()
                result[stem] = url
    except:
        pass
    return result

def _scan_raw_files() -> pd.DataFrame:
    if not RAW_DIR.exists():
        return pd.DataFrame()

    manifest = _load_db_names()
    crawled_urls = _load_crawled_urls()
    rows = []

    for raw_file in sorted(RAW_DIR.iterdir(), key=lambda f: f.stat().st_mtime, reverse=True):
        if raw_file.is_dir():
            continue
        stem = raw_file.stem
        ext  = raw_file.suffix.lower()
        stat = raw_file.stat()

        converted     = CONVERTED_DIR / f"{stem}.md"
        has_converted = converted.exists()
        image_only    = False
        md_title      = ""

        if has_converted:
            try:
                text = converted.read_text(encoding="utf-8", errors="replace")
                image_only = text.startswith("<!-- IMAGE_ONLY_PDF")
                if not image_only:
                    md_title = _extract_title_from_md(str(converted))
            except Exception:
                pass

        meta = manifest.get(stem, {})
        url = meta.get("url", "") or crawled_urls.get(stem, "")
        
        display_name = meta.get("name", "").strip() or md_title
        if not display_name and ext == ".pdf":
            display_name = _extract_title_from_pdf(str(raw_file))
            
        display_name = (
            display_name
            or _extract_name_from_url(url)
            or f"[{ext.lstrip('.').upper()}] {stem[:16]}..."
        )

        rows.append({
            "hash":          stem,
            "display_name":  display_name,
            "url":           meta.get("url", ""),
            "ext":           ext,
            "raw_path":      str(raw_file),
            "size_bytes":    stat.st_size,
            "size_str":      _fmt_size(stat.st_size),
            "modified_ts":   stat.st_mtime,
            "modified":      _fmt_time(stat.st_mtime),
            "has_converted": has_converted,
            "image_only":    image_only,
            "converted_path": str(converted) if has_converted else "",
            "status":        meta.get("status", ""),
            "doc_type":      meta.get("doc_type", ""),
            "age_band":      meta.get("age_band", ""),
            "linh_vuc":      meta.get("linh_vuc", ""),
        })

    return pd.DataFrame(rows)


@st.dialog("📂 Chi tiết tài liệu Raw", width="large")
def popup_raw_detail(row: dict):
    ext   = row.get("ext", "")
    icon  = _EXT_ICON.get(ext, "📁")
    color = _EXT_COLOR.get(ext, "#555")
    name  = row.get("display_name", row["hash"][:24] + "...")

    # Title popup
    st.markdown(f"### {icon} {name}")

    # Metadata bar
    col1, col2, col3, col4 = st.columns(4)
    col1.markdown(f"⚖️ **{row['size_str']}**")
    col2.markdown(f"🕒 **{row['modified']}**")
    col3.markdown(_badge(ext.lstrip(".").upper(), color), unsafe_allow_html=True)
    if row.get("image_only"):
        col4.markdown(_badge("⚠️ Ảnh scan", "#e67e22"), unsafe_allow_html=True)
    elif row.get("has_converted"):
        col4.markdown(_badge("✅ Đã convert", "#27ae60"), unsafe_allow_html=True)
    else:
        col4.markdown(_badge("⏳ Chưa convert", "#7f8c8d"), unsafe_allow_html=True)

    # URL nguồn
    if row.get("url"):
        st.link_button("↗ Xem trang nguồn", url=row["url"], use_container_width=False)

    # Metadata từ manifest
    if row.get("doc_type") or row.get("age_band") or row.get("linh_vuc"):
        info_cols = st.columns(3)
        with info_cols[0]:
            st.caption(f"**Loại:** {row.get('doc_type', '—')}")
        with info_cols[1]:
            st.caption(f"**Độ tuổi:** {row.get('age_band', '—')}")
        with info_cols[2]:
            st.caption(f"**Lĩnh vực:** {row.get('linh_vuc', '—')}")

    st.divider()

    # Preview
    converted_path = row.get("converted_path", "")
    if row.get("image_only"):
        st.warning("File PDF scan ảnh — không trích xuất được chữ. Cần OCR.")
    elif not row.get("has_converted"):
        st.info("File này chưa được convert sang Markdown.")
    else:
        render_document_preview(
            url=row.get("raw_path", ""),
            hash_name=row["hash"],
            local_md_path=converted_path,
        )

    # Kỹ thuật
    with st.expander("🔍 Thông tin kỹ thuật", expanded=False):
        st.code(
            f"Hash:      {row['hash']}\n"
            f"Raw:       {row['raw_path']}\n"
            f"Converted: {row.get('converted_path', 'Chưa có')}",
            language="bash"
        )
        if row.get("has_converted") and not row.get("image_only"):
            try:
                md_text = Path(row["converted_path"]).read_text(encoding="utf-8", errors="replace")
                st.text_area("Nội dung Markdown đầy đủ", value=md_text, height=300)
            except Exception:
                pass


def render_tab_raw_files():
    st.header("📦 Kho Raw — Tài liệu đã tải về")
    st.caption("Danh sách toàn bộ file trong `data/raw/`. Click **Xem chi tiết** để xem nội dung và metadata.")

    df = _scan_raw_files()

    if df.empty:
        st.info("Chưa có file nào trong `data/raw/`. Hãy chạy crawler để thu thập tài liệu.")
        return

    # ── Bộ lọc ──────────────────────────────────────────────────────────────
    col_f1, col_f2, col_f3 = st.columns([1, 1, 2])
    with col_f1:
        loai_file = st.multiselect(
            "Loại file", options=sorted(df["ext"].unique()), default=[], placeholder="Tất cả"
        )
    with col_f2:
        tinh_trang = st.selectbox(
            "Trạng thái convert",
            options=["Tất cả", "Đã convert", "Chưa convert", "Ảnh scan (cần OCR)"],
        )
    with col_f3:
        tim_kiem = st.text_input("🔍 Tìm theo tên hoặc hash", placeholder="Nhập từ khoá...")

    # Áp dụng bộ lọc
    df_hien = df.copy()
    if loai_file:
        df_hien = df_hien[df_hien["ext"].isin(loai_file)]
    if tinh_trang == "Đã convert":
        df_hien = df_hien[df_hien["has_converted"] & ~df_hien["image_only"]]
    elif tinh_trang == "Chưa convert":
        df_hien = df_hien[~df_hien["has_converted"]]
    elif tinh_trang == "Ảnh scan (cần OCR)":
        df_hien = df_hien[df_hien["image_only"]]
    if tim_kiem.strip():
        kw = tim_kiem.strip().lower()
        df_hien = df_hien[
            df_hien["display_name"].str.lower().str.contains(kw, na=False) |
            df_hien["hash"].str.contains(kw, na=False) |
            df_hien["url"].str.lower().str.contains(kw, na=False)
        ]

    # ── Thống kê nhanh ────────────────────────────────────────────────────────
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Tổng file raw", len(df))
    c2.metric("Đã convert", int((df["has_converted"] & ~df["image_only"]).sum()))
    c3.metric("Ảnh scan / cần OCR", int(df["image_only"].sum()))
    tong_mb = df["size_bytes"].sum() / (1024 * 1024)
    c4.metric("Dung lượng", f"{tong_mb:.1f} MB")

    st.divider()

    if df_hien.empty:
        st.warning("Không có file nào khớp với bộ lọc.")
        return

    # ── Phân trang ────────────────────────────────────────────────────────────
    tong_trang = max(1, (len(df_hien) - 1) // PAGE_SIZE + 1)

    col_pg1, col_pg2, col_pg3 = st.columns([3, 1, 1])
    with col_pg1:
        st.caption(f"Tổng **{len(df_hien)}** file")
    with col_pg3:
        if st.button("▶ Sau", use_container_width=True, key="pg_next"):
            st.session_state["raw_page"] = min(tong_trang, st.session_state.get("raw_page", 1) + 1)
    with col_pg2:
        if st.button("◀ Trước", use_container_width=True, key="pg_prev"):
            st.session_state["raw_page"] = max(1, st.session_state.get("raw_page", 1) - 1)

    # Reset về trang 1 khi bộ lọc thay đổi
    if "raw_page_last_filter" not in st.session_state:
        st.session_state["raw_page_last_filter"] = ""
    current_filter = f"{loai_file}{tinh_trang}{tim_kiem}"
    if st.session_state["raw_page_last_filter"] != current_filter:
        st.session_state["raw_page"] = 1
        st.session_state["raw_page_last_filter"] = current_filter

    trang = st.session_state.get("raw_page", 1)
    trang = max(1, min(trang, tong_trang))
    st.session_state["raw_page"] = trang

    # Cập nhật caption với số trang thực
    col_pg1.caption(f"Tổng **{len(df_hien)}** file &nbsp;·&nbsp; Trang **{trang}/{tong_trang}**")

    start    = (trang - 1) * PAGE_SIZE
    df_page  = df_hien.iloc[start : start + PAGE_SIZE].reset_index(drop=True)

    # ── Danh sách ─────────────────────────────────────────────────────────────
    for i, (_, row) in enumerate(df_page.iterrows()):
        ext          = row["ext"]
        icon         = _EXT_ICON.get(ext, "📁")
        color        = _EXT_COLOR.get(ext, "#555")
        is_ok        = row["has_converted"] and not row["image_only"]
        is_scan      = row["image_only"]
        status_icon  = "✅" if is_ok else ("⚠️" if is_scan else "⏳")
        status_label = "Đã convert" if is_ok else ("Ảnh scan" if is_scan else "Chưa convert")
        status_color = "#27ae60" if is_ok else ("#e67e22" if is_scan else "#95a5a6")
        name         = row["display_name"]
        global_idx   = start + i + 1  # số thứ tự toàn cục

        with st.container(border=True):
            c_no, c_info, c_btn = st.columns([0.4, 5, 1])
            with c_no:
                st.markdown(
                    f'<div style="font-size:1.4rem;font-weight:700;color:#bdc3c7;'
                    f'text-align:center;padding-top:4px">{global_idx:02d}</div>',
                    unsafe_allow_html=True
                )
            with c_info:
                badge_html = (
                    f'{_badge(f"{icon} {ext.lstrip(".").upper()}", color)}&nbsp;'
                    f'{_badge(f"{status_icon} {status_label}", status_color)}'
                )
                st.markdown(badge_html, unsafe_allow_html=True)
                # Tên đọc được – in đậm, rõ ràng
                st.markdown(f"**{name}**")
                st.caption(f"`{row['hash'][:20]}...` &nbsp;·&nbsp; {row['size_str']} &nbsp;·&nbsp; 🕒 {row['modified']}")
            with c_btn:
                if st.button("Xem chi tiết", key=f"raw_{row['hash']}", use_container_width=True):
                    popup_raw_detail(row.to_dict())
