# 🐬 IruKa Crawler — Hệ thống Thu thập Tài liệu Giáo dục Mầm non

IruKa Crawler là một hệ thống thu thập, xử lý và chuẩn hóa tài liệu tự động được thiết kế riêng cho lĩnh vực giáo dục mầm non. Hệ thống đóng vai trò như một "nhà máy" thu thập dữ liệu thô từ Internet, bóc tách nội dung, gán nhãn siêu dữ liệu (metadata) theo chuẩn Taxonomy của IruKa, và xuất ra định dạng Markdown tối ưu hóa cho các hệ thống RAG (Retrieval-Augmented Generation) và AI.

> **Trạng thái hiện tại:** Phiên bản Demo (Local Standalone)
> **Mục tiêu:** Tự động hóa quá trình thu thập tài liệu từ web, YouTube, chuyển đổi sang Markdown và gán nhãn thông minh bằng LLM cục bộ.

---

## ✨ Tính năng Nổi bật

1. **Thu thập Đa nguồn (Multi-source Crawling)**
   - Tìm kiếm URL động thông qua **MCP Searcher** (tích hợp API Tavily/Exa).
   - Tải và xử lý các tệp PDF, DOCX, HTML từ các trang web giáo dục.
   - Hỗ trợ thu thập phụ đề **YouTube** (`youtube-transcript-api`), tự động dịch sang Tiếng Việt nếu video dùng ngôn ngữ khác.
   - Khả năng **Dedup (lọc trùng lặp)** tự động dựa trên SHA-256 hash của URL và nội dung.

2. **Xử lý Nội dung Tối ưu cho AI (RAG-ready Conversion)**
   - Chuyển đổi PDF, DOCX, HTML sang định dạng Markdown chuẩn.
   - **Tự động đánh dấu trang**: Chèn thẻ `--- Trang N ---` cho PDF (thông qua PyMuPDF) và chèn `--- Phần N ---` sau mỗi 500 từ cho DOCX. Điều này giúp các hệ thống Vector DB và LLM phía sau dễ dàng cắt nhỏ (chunking) nội dung mà không mất ngữ cảnh.

3. **Gán nhãn Siêu dữ liệu Thông minh (Two-tier Metadata Enrichment)**
   - **Tầng 1 - Heuristic Enrichment**: Áp dụng hệ thống luật (regex/rules) cực nhanh dựa trên tên miền và tiêu đề để tự động gán phân loại (Ví dụ: `moet.gov.vn` → `pl.thong_tu`, `tier 3`).
   - **Tầng 2 - Local LLM (Ollama)**: Sử dụng mô hình Llama3 chạy cục bộ hoàn toàn miễn phí để đọc hiểu nội dung tài liệu và gán nhãn tự động cho những trường còn thiếu (Lĩnh vực, Độ tuổi, Loại tài liệu).

4. **Kiểm duyệt Chất lượng Chặt chẽ (Strict Validation)**
   - Kiểm tra định dạng Markdown: Độ dài tệp, tỷ lệ nội dung chữ/số (lọc file rác).
   - Xác thực metadata bám sát 100% chuẩn **IruKa Taxonomy** (4 chiều).
   - Các tài liệu không đạt chuẩn sẽ tự động được gán cờ `need_manual=True` để chuyển sang quy trình xét duyệt tay.

5. **Bảng điều khiển Trực quan (Streamlit Dashboard)**
   - Theo dõi tiến độ thu thập dữ liệu qua log thời gian thực.
   - Báo cáo thống kê trực quan với biểu đồ (Lĩnh vực, Tier, Độ tuổi).
   - Giao diện xét duyệt tài liệu dễ sử dụng dành cho Admin.

---

## 🏗️ Kiến trúc Hệ thống (Pipeline 7 Bước)

Pipeline hoạt động của hệ thống được chia làm 7 bước chính:

1. **Tìm kiếm & Cào (Crawler)**: `MCPSearcher` tìm kiếm URL -> `BaseCrawler` / `YouTubeCrawler` tải nội dung.
2. **Chuyển đổi (Converter)**: `DocumentConverter` chuyển tệp gốc sang Markdown (`data/converted/`).
3. **Làm giàu Dữ liệu (Enricher)**: `HeuristicEnricher` & `LocalLLMEnricher` phân tích tài liệu và xuất ra metadata.
4. **Kiểm duyệt (Validator)**: Đảm bảo tài liệu đáp ứng Taxonomy và chất lượng nội dung.
5. **Sinh mã (Doc Coder)**: Tạo mã tài liệu chuẩn `DOC-{LV2}-{age}-{NHOM}-{seq4}`.
6. **Xuất file (Exporter)**: `LocalExporter` lưu file Markdown kèm YAML Frontmatter vào `data/export/` và cập nhật `manifest.csv`.
7. **Đẩy lên Cloud & Import (Sẽ làm sau)**: Tích hợp Cloudflare R2 và Bulk-import API.

*Để xem chi tiết hơn về luồng kiến trúc, vui lòng tham khảo file `workflows_and_diagrams.md`.*

---

## 🚀 Hướng dẫn Cài đặt & Chạy thử nghiệm

### 1. Yêu cầu Hệ thống
- **Python 3.11+**
- **Ollama** (đã tải model `llama3` hoặc `llama3.1`)
- Môi trường ảo (Virtual Environment)

### 2. Cài đặt

```bash
# Clone source code và truy cập thư mục
git clone <repo_url> irukacrawler
cd irukacrawler

# Khởi tạo môi trường ảo và cài đặt thư viện
python -m venv venv
source venv/bin/activate  # Trên Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Vận hành

**Cách 1: Khởi động Giao diện Dashboard (Khuyên dùng)**
Sử dụng giao diện Streamlit để thao tác và theo dõi thống kê trực quan.
```bash
streamlit run src/dashboard/app.py
```

**Cách 2: Chạy trực tiếp qua CLI**
Bạn có thể chạy luồng thu thập tài liệu thông qua Command Line.
```bash
python -m src.main --queries "bài giảng điện tử mầm non lớp 5 tuổi" --provider tavily --limit 10
```

---

## 📂 Cấu trúc Thư mục Chính

```text
irukacrawler/
├── src/
│   ├── crawlers/          # Các module thu thập (Base, YouTube, MetadataMapper)
│   ├── converters/        # Module chuyển đổi PDF/DOCX sang Markdown
│   ├── enricher/          # Module xử lý LLM, Heuristic, Validator
│   ├── searcher/          # Tích hợp MCP Tavily/Exa để tìm kiếm
│   ├── exporter/          # Module đóng gói, xuất file và ghi manifest
│   ├── dashboard/         # Mã nguồn UI Streamlit
│   ├── models.py          # Khai báo các Dataclass (DocumentDTO, DocumentMetadata)
│   ├── taxonomy.py        # Định nghĩa chuẩn phân loại IruKa (Single Source of Truth)
│   └── main.py            # Entry point kết nối toàn bộ Pipeline
├── data/
│   ├── raw/               # Tệp thô vừa tải về
│   ├── converted/         # Tệp Markdown tạm trước khi gán nhãn
│   └── export/            # Tệp Markdown hoàn chỉnh kèm manifest.csv
├── tests/                 # Thư mục unit test
└── logs/                  # Chứa file log chi tiết theo ngày
```

---

## 🛠️ Trạng thái Dự án (Nghiệm thu Local Demo)

Hệ thống đã hoàn thành xuất sắc các chỉ tiêu trong giai đoạn Demo:
- **Tích hợp thành công 11/18 modules cốt lõi** (các module rớt lại là các tính năng Cloud Production).
- **Pass 110/112 tests pipeline**.
- **Chuyển đổi văn bản thông minh**: Hỗ trợ RAG Chunking qua kỹ thuật đánh dấu trang cho PDF và Word.
- **Tiết kiệm chi phí**: Thành công bypass API trả phí của OpenAI bằng mô hình Local LLM.

### Lộ trình Phát triển Tiếp theo (Production Phase)
- Bổ sung module **Uploader** đẩy file lên Cloudflare R2 (Yêu cầu API Keys).
- Viết script **IruKa Ingester** để gọi API Bulk-import.
- Tích hợp **Discord Reporter** gửi thông báo về Webhook sau mỗi mẻ crawl.
- Áp dụng **OCR** (Tesseract / Google Vision) để bóc tách tài liệu sách giáo khoa bị scan ảnh.
- Khởi tạo **Scheduled Tasks** (Cronjob) tự động chạy định kỳ.
