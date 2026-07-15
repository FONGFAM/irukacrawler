import streamlit as st
from pathlib import Path
import re
import base64

def tim_raw_file(hash_name: str) -> Path | None:
    """Tìm file raw tương ứng với hash trong data/raw/."""
    raw_dir = Path("data/raw")
    if not raw_dir.exists():
        return None
    for ext in (".pdf", ".docx", ".doc", ".html", ".htm"):
        p = raw_dir / f"{hash_name}{ext}"
        if p.exists():
            return p
    return None

def render_pdf(pdf_path: Path) -> bool:
    try:
        import fitz
    except ImportError:
        st.error("Cần cài đặt PyMuPDF (fitz) để xem PDF.")
        return False
    try:
        doc = fitz.open(str(pdf_path))
        tong_trang = len(doc)
        hien_thi = min(tong_trang, 20)
        with st.container(height=700):
            for i in range(hien_thi):
                page = doc[i]
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                st.image(pix.tobytes("png"), caption=f"Trang {i + 1}", use_container_width=True)
            if tong_trang > 20:
                st.caption(f"... còn {tong_trang - 20} trang. Tải về để xem đầy đủ.")
        doc.close()
        return True
    except Exception as e:
        st.warning(f"Không thể đọc PDF: {e}")
        return False

def render_docx(docx_path: Path) -> bool:
    try:
        from docx import Document
        from docx.oxml.ns import qn
    except ImportError:
        st.error("Cần cài python-docx để xem DOCX.")
        return False

    try:
        doc = Document(str(docx_path))
    except Exception as e:
        st.warning(f"Không thể mở DOCX: {e}")
        return False

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

    def _run_html(run):
        text = run.text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if not text: return ""
        if run.bold: text = f"<strong>{text}</strong>"
        if run.italic: text = f"<em>{text}</em>"
        return text

    def _para_html(para):
        style = para.style.name if para.style else "Normal"
        inner = "".join(_run_html(r) for r in para.runs)
        if not inner.strip(): return "<p>&nbsp;</p>"
        if "Heading 1" in style: return f"<h1>{inner}</h1>"
        if "Heading 2" in style: return f"<h2>{inner}</h2>"
        return f"<p>{inner}</p>"

    parts = []
    body = doc.element.body
    for child in body:
        tag = child.tag.split("}")[-1]
        if tag == "p":
            from docx.text.paragraph import Paragraph
            para = Paragraph(child, doc)
            imgs = child.findall(".//" + qn("a:blip"), namespaces={"a": "http://schemas.openxmlformats.org/drawingml/2006/main"})
            if imgs:
                for blip in imgs:
                    embed = blip.get(qn("r:embed"))
                    if embed and embed in rels:
                        parts.append(f'<div style="text-align:center"><img src="{rels[embed]}" style="max-width:100%"></div>')
            else:
                parts.append(_para_html(para))
        elif tag == "tbl":
            # Gọn nhẹ table view
            parts.append('<table border="1" style="border-collapse:collapse;width:100%"><tr><td>Table...</td></tr></table>')

    content = "".join(parts)
    html = f"<div style='font-family:sans-serif;line-height:1.6;color:#333;padding:15px'>{content}</div>"
    st.markdown(f'<div style="height:700px;overflow-y:auto;background:white;border-radius:8px;padding:20px;box-shadow:0 1px 3px rgba(0,0,0,0.1)">{html}</div>', unsafe_allow_html=True)
    return True

def render_html(html_path: Path, url: str = "") -> bool:
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return False
        
    if url:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        base_url = f"{parsed.scheme}://{parsed.netloc}/"
        # Dùng CSS zoom để mở rộng viewport ảo, giúp trang không bị móp/vỡ layout khi nhét vào iframe hẹp
        base_tag = f'<base href="{base_url}">\n<style>body {{ zoom: 0.65; min-width: 1000px !important; }}</style>'
        if "<head>" in content.lower():
            content = re.sub(r'(<head[^>]*>)', r'\1\n' + base_tag, content, count=1, flags=re.IGNORECASE)
        else:
            content = f"<head>{base_tag}</head>\n" + content
            
    # Xóa meta http-equiv để tránh auto-refresh hoặc frame-breaking bằng thẻ meta
    content = re.sub(r'<meta[^>]+http-equiv[^>]*>', '', content, flags=re.IGNORECASE)
    
    st.components.v1.html(content, height=700, scrolling=True)
    return True

@st.cache_data(ttl=300)
def get_content_hash_from_md(local_md_path: str) -> str:
    if not local_md_path or not Path(local_md_path).exists():
        return ""
    try:
        content = Path(local_md_path).read_text(encoding="utf-8")
        if content.startswith("---"):
            parts = content.split("---", 2)
            body = parts[2].strip() if len(parts) >= 3 else content.strip()
        else:
            body = content.strip()
            
        conv_dir = Path("data/converted")
        if conv_dir.exists():
            for p in conv_dir.glob("*.md"):
                if p.read_text(encoding="utf-8").strip() == body:
                    return p.stem
    except Exception:
        pass
    return ""

def render_document_preview(url: str, hash_name: str, local_md_path: str = ""):
    """Hiển thị bản xem trước tốt nhất có thể."""
    
    # 1. Tìm file raw
    content_hash = get_content_hash_from_md(local_md_path)
    if not content_hash:
        content_hash = hash_name # Fallback to URL hash
        
    raw_file = tim_raw_file(content_hash)
    
    # Nếu có PDF, DOCX hoặc HTML nội bộ, ưu tiên hiển thị vì nó là tài liệu chuẩn
    if raw_file:
        ext = raw_file.suffix.lower()
        if ext == ".pdf":
            st.info(f"Đang hiển thị PDF gốc: {raw_file.name}")
            render_pdf(raw_file)
            return
        elif ext in (".docx", ".doc"):
            st.info(f"Đang hiển thị DOCX gốc: {raw_file.name}")
            render_docx(raw_file)
            return
        elif ext in (".html", ".htm"):
            tab_web, tab_md = st.tabs(["🌐 Trang web gốc", "📝 Văn bản trích xuất"])
            with tab_web:
                st.caption("Hiển thị giao diện trang web gốc (đã lưu cache nội bộ).")
                render_html(raw_file, url)
            with tab_md:
                st.caption("Hiển thị nội dung chữ đã được hệ thống bóc tách tự động.")
                if local_md_path and Path(local_md_path).exists():
                    md_content = Path(local_md_path).read_text(encoding="utf-8")
                    with st.container(height=650, border=True):
                        st.markdown(md_content)
                else:
                    st.warning("Chưa có bản trích xuất nội dung cho trang này.")
            return

    # 2. Xử lý các link Web thông thường nếu KHÔNG có raw file
    if str(url).startswith("http"):
        if "youtube.com" in url or "youtu.be" in url:
            st.video(url)
            return
            
        tab_web, tab_md = st.tabs(["🌐 Trang web gốc", "📝 Văn bản trích xuất"])
        
        with tab_web:
            st.caption("Hiển thị giao diện trang web gốc như trên mạng.")
            st.components.v1.iframe(url, height=700, scrolling=True)
            
        with tab_md:
            st.caption("Hiển thị nội dung chữ đã được hệ thống bóc tách tự động.")
            if local_md_path and Path(local_md_path).exists():
                md_content = Path(local_md_path).read_text(encoding="utf-8")
                with st.container(height=650, border=True):
                    st.markdown(md_content)
            else:
                st.warning("Chưa có bản trích xuất nội dung cho trang này.")
    else:
        st.error(f"Đường dẫn không hợp lệ: {url}")
