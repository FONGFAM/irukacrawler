"""
Converter module — Chuyển PDF, DOCX, HTML thành Markdown chuẩn.
Quy tắc:
  - Thêm mốc  --- Trang N ---  cho PDF.
  - Giữ nguyên heading dựa trên font-size (PDF) hoặc thẻ h1-h6 (HTML/DOCX).
  - Bỏ ảnh, chỉ giữ placeholder [Ảnh: ...].
"""
import re
from pathlib import Path
from typing import Optional
# pyrefly: ignore [missing-import]
from loguru import logger
# pyrefly: ignore [missing-import]
import fitz  # PyMuPDF
# pyrefly: ignore [missing-import]
import docx
# pyrefly: ignore [missing-import]
from bs4 import BeautifulSoup
# pyrefly: ignore [missing-import]
import html2text


class DocumentConverter:
    def __init__(self, output_dir: str = "data/converted"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def _extract_pdf(self, file_path: str) -> Optional[str]:
        """Trích xuất text từ PDF thành Markdown thô"""
        try:
            doc = fitz.open(file_path)
            md_content = []
            
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                # Đánh dấu số trang
                md_content.append(f"\n--- Trang {page_num + 1} ---\n")
                
                # Trích xuất text (bỏ qua ảnh)
                blocks = page.get_text("dict")["blocks"]
                for b in blocks:
                    if b['type'] == 0:  # Text block
                        for l in b["lines"]:
                            for s in l["spans"]:
                                text = s["text"].strip()
                                if not text:
                                    continue
                                    
                                # Phân tích cơ bản để giữ heading dựa trên font size
                                font_size = s["size"]
                                if font_size > 20:
                                    md_content.append(f"# {text}")
                                elif font_size > 16:
                                    md_content.append(f"## {text}")
                                elif font_size > 14:
                                    md_content.append(f"### {text}")
                                else:
                                    md_content.append(text)
                                    
                                # Thêm newline sau span nếu nó là cuối dòng
                            md_content.append("\n")
                    elif b['type'] == 1: # Image block
                        md_content.append("[Ảnh: (Bị lược bỏ trong quá trình cào)]\n")

            return "".join(md_content)
            
        except Exception as e:
            logger.error(f"Error converting PDF {file_path}: {e}")
            return None

    def _extract_docx(self, file_path: str) -> Optional[str]:
        """Trích xuất DOCX"""
        try:
            doc = docx.Document(file_path)
            md_content = []
            
            part_num = 1
            word_count = 0
            MAX_WORDS_PER_PART = 500
            
            md_content.append(f"\n--- Phần {part_num} ---\n")
            
            for para in doc.paragraphs:
                text = para.text.strip()
                if not text:
                    continue
                # Xử lý heading đơn giản
                if para.style.name.startswith('Heading 1'):
                    md_content.append(f"# {text}\n")
                elif para.style.name.startswith('Heading 2'):
                    md_content.append(f"## {text}\n")
                elif para.style.name.startswith('Heading 3'):
                    md_content.append(f"### {text}\n")
                else:
                    md_content.append(f"{text}\n")
                    
                word_count += len(text.split())
                if word_count >= MAX_WORDS_PER_PART:
                    part_num += 1
                    md_content.append(f"\n--- Phần {part_num} ---\n")
                    word_count = 0
                    
            return "".join(md_content)
        except Exception as e:
            logger.error(f"Error converting DOCX {file_path}: {e}")
            return None

    def _extract_html(self, file_path: str) -> Optional[str]:
        """Trích xuất HTML"""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                html_doc = f.read()
                
            soup = BeautifulSoup(html_doc, 'html.parser')
            # Loại bỏ script, style, nav, footer
            for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
                tag.decompose()
                
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.body_width = 0
            
            return h.handle(str(soup))
        except Exception as e:
            logger.error(f"Error converting HTML {file_path}: {e}")
            return None

    def extract_text(self, file_path: str) -> Optional[str]:
        """Dispatcher theo đuôi file"""
        ext = Path(file_path).suffix.lower()
        if ext == '.pdf':
            return self._extract_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            # doc thì python-docx không parse trực tiếp được (chỉ docx), nhưng cố thử
            return self._extract_docx(file_path)
        elif ext in ['.html', '.htm']:
            return self._extract_html(file_path)
        else:
            # Fallback
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

    def convert(self, file_path: str) -> Optional[str]:
        """Chuyển đổi và lưu file Markdown"""
        text = self.extract_text(file_path)
        if not text:
            return None
            
        # Clean up multiple newlines
        text = re.sub(r'\n{3,}', '\n\n', text)
            
        file_path_obj = Path(file_path)
        output_file = self.output_dir / f"{file_path_obj.stem}.md"
        
        # Kiểm tra xem có phải file ảnh scan không (toàn [Ảnh])
        real_text = re.sub(r'\[Ảnh:.*?\]', '', text).strip()
        real_text = re.sub(r'---\s*Trang\s*\d+\s*---', '', real_text).strip()
        if len(real_text) < 150:
            logger.warning(f"File có thể là ảnh scan (text thực chỉ {len(real_text)} ký tự): {file_path_obj.name}")
            text = f"<!-- IMAGE_ONLY_PDF: Không thể trích xuất text. Cần OCR. -->\n\n{text}"
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(text)
            
        logger.success(f"Converted {file_path} -> {output_file}")
        return str(output_file)

if __name__ == "__main__":
    # Test nhanh
    converter = DocumentConverter()
    # converter.convert("data/raw/test.pdf")
