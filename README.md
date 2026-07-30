# 📚 DocsCrawler — Hệ thống Thu thập Tài liệu Giáo dục

DocsCrawler là một công cụ cá nhân giúp tự động thu thập, xử lý và chuẩn hóa tài liệu giáo dục từ Internet. Hệ thống tải dữ liệu thô (PDF, DOCX, HTML, YouTube), bóc tách nội dung, tự động phân loại metadata thông qua Heuristic và Local LLM, sau đó xuất ra định dạng Markdown có cấu trúc để sẵn sàng cho các hệ thống RAG (Retrieval-Augmented Generation).

---

## ✨ Tính năng

- **Thu thập đa nguồn** — Hỗ trợ tải file PDF, DOCX, trích xuất HTML từ web qua API tìm kiếm (Tavily/Exa).
- **YouTube Crawler** — Lấy transcript video, hỗ trợ dịch tự động sang Tiếng Việt.
- **RAG-ready Conversion** — Chuyển đổi PDF/DOCX/HTML sang file Markdown có đánh dấu phân trang chuẩn xác.
- **Heuristic & Local LLM Enrichment** — Tự động suy luận metadata bằng tập luật (heuristics) kết hợp mô hình ngôn ngữ (Ollama/Llama3) chạy hoàn toàn trên máy cá nhân, không tốn chi phí API.
- **Dashboard quản lý** — Giao diện web Streamlit thân thiện để quản lý việc tìm kiếm, thu thập và thống kê tài liệu.

---

## 🚀 Cài đặt & Sử dụng

### Yêu cầu hệ thống
- Python **3.11+**
- [**Ollama**](https://ollama.com) cài đặt và chạy ngầm với model `llama3` hoặc `llama3.1`
- API key của **Tavily** hoặc **Exa** cho việc tìm kiếm web

### Các bước cài đặt
```bash
# 1. Tạo môi trường ảo
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 2. Cài thư viện
pip install -e .

# 3. Cấu hình biến môi trường
cp .env.example .env            # Điền API keys vào file .env
```

### Cấu hình biến môi trường (`.env`)
Đổi tên hoặc copy file `.env.example` thành `.env` và điền các API key của bạn vào. 
**Lưu ý:** File `.env` chứa thông tin nhạy cảm (API keys) nên đã được cấu hình trong `.gitignore` để không bị đẩy lên Git.

```bash
TAVILY_API_KEY=tvly-xxx         # Hoặc EXA_API_KEY=exa-xxx
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3
MAX_REQUESTS_PER_SECOND=1.0
```

---

## 🖥️ Khởi chạy

### Chạy Dashboard Giao diện (Khuyên dùng)
```bash
streamlit run src/dashboard/app.py
```
Mở trình duyệt tại `http://localhost:8501`.

### Chạy qua dòng lệnh (CLI)
```bash
python -m src.main \
  --queries "bài giảng toán 5 tuổi" \
  --provider tavily \
  --limit 5 \
  --semaphore 3
```

---

## 📂 Cấu trúc Thư mục

- `src/`: Mã nguồn chính của dự án (Crawlers, Converters, Enrichers, Validator, Exporters, Dashboard).
- `data/`: Dữ liệu được tải về và xử lý (`raw`, `converted`, `export`).
- `tests/`: Bộ test của hệ thống.
- `logs/`: Nơi lưu trữ log quá trình cào.

---

## 📝 Chạy Test
```bash
pytest tests/ -v
```
