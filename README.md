# 🐬 IruKa Crawler — Hệ thống Thu thập Tài liệu Giáo dục Mầm non

IruKa Crawler là một hệ thống ETL chuyên biệt, tự động thu thập, xử lý và chuẩn hóa tài liệu cho lĩnh vực giáo dục mầm non. Hệ thống đóng vai trò "nhà máy" thu thập dữ liệu thô từ Internet, bóc tách nội dung, gán nhãn siêu dữ liệu (metadata) theo chuẩn Taxonomy của IruKa, và xuất ra định dạng Markdown tối ưu hóa cho RAG (Retrieval-Augmented Generation).

> **Trạng thái hiện tại:** G1 — Demo Local Standalone (5/7 bước pipeline)
> **Mục tiêu G2:** Upload Cloudflare R2 + Bulk-import API → tài liệu vào Xưởng Sản Xuất tự động

---

## ✨ Tính năng

| # | Tính năng | Trạng thái |
|---|---|---|
| 1 | **Thu thập đa nguồn** — PDF, DOCX, HTML từ web giáo dục qua Tavily/Exa | ✅ Hoàn thành |
| 2 | **YouTube Crawler** — Lấy transcript, tự dịch sang Tiếng Việt | ✅ Hoàn thành |
| 3 | **Dedup thông minh** — SHA-256 URL + lọc manifest.csv hiện có | ✅ Hoàn thành |
| 4 | **RAG-ready Conversion** — PDF/DOCX/HTML → Markdown chuẩn có đánh trang | ✅ Hoàn thành |
| 5 | **Heuristic Enrichment** — Bảng quy đổi domain/keyword → 4 chiều metadata | ✅ Hoàn thành |
| 6 | **Local LLM Enrichment** — Ollama/llama3 phân loại khi heuristic chưa đủ | ✅ Hoàn thành |
| 7 | **Strict Validation** — Kiểm tra 4 chiều IruKa Taxonomy + chất lượng file | ✅ Hoàn thành |
| 8 | **Streamlit Dashboard** — 4 tab: Thu thập · Thống kê · Danh sách · Xét duyệt | ✅ Hoàn thành |
| 9 | **Upload Cloudflare R2** — boto3 PUT file theo path chuẩn IruKa | ⏳ G2 |
| 10 | **Bulk-import API** — POST `/bulk-import` vào Xưởng Sản Xuất be-hub | ⏳ G2 |
| 11 | **Discord Reporter** — Báo cáo mẻ crawl qua webhook | ⏳ G2 |
| 12 | **Cron Scheduler** — Tự động chạy định kỳ (arq) | ⏳ G2 |
| 13 | **OCR** — Tesseract/Google Vision cho SGK scan ảnh | ⏳ G3 |

---

## 🏗️ Kiến trúc Pipeline 7 Bước

```
[Queries] → MCPSearcher → DEDUP → Crawler → Converter → Enricher → Validator → Exporter
                                                                               ↓
                                                              [G2] R2Uploader → IruKaIngester
                                                                               ↓
                                                                    Xưởng Sản Xuất (cho_duyet)
```

| Bước | Module | Mô tả |
|---|---|---|
| 1 | `MCPSearcher` + `BaseCrawler` / `YouTubeCrawler` | Tìm kiếm URL → tải file → `data/raw/` |
| 2 | `DocumentConverter` | PDF/DOCX/HTML → Markdown có đánh trang → `data/converted/` |
| 3 | `HeuristicEnricher` → `LocalLLMEnricher` | Suy metadata 2 tầng (rules → Ollama) |
| 4 | `Validator` | Kiểm tra 4 chiều IruKa Taxonomy + chất lượng file |
| 5 | `LocalExporter` | Sinh `doc_code`, ghi YAML Frontmatter, cập nhật `manifest.csv` |
| 6 | `R2Uploader` *(G2)* | Upload file lên Cloudflare R2 |
| 7 | `IruKaIngester` *(G2)* | POST `/bulk-import` → Xưởng Sản Xuất |

> 📖 Chi tiết đầy đủ: [`docs/architecture_and_workflows.md`](docs/architecture_and_workflows.md)

---

## 🚀 Cài đặt & Chạy

### Yêu cầu

- Python **3.11+**
- [**Ollama**](https://ollama.com) đã cài và chạy với model `llama3` hoặc `llama3.1`
- API key: **Tavily** (`TAVILY_API_KEY`) hoặc **Exa** (`EXA_API_KEY`)

### Cài đặt

```bash
# 1. Clone repo
git clone git@github.com:iruka-edu/data-cur.git irukacrawler
cd irukacrawler

# 2. Tạo môi trường ảo
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

# 3. Cài thư viện
pip install -e .

# 4. Cấu hình biến môi trường
cp .env.example .env            # Điền API keys vào .env
```

### Biến môi trường cần thiết (`.env`)

```bash
TAVILY_API_KEY=tvly-xxx         # Hoặc EXA_API_KEY=exa-xxx
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3
MAX_REQUESTS_PER_SECOND=1.0
```

> 📖 Danh sách đầy đủ biến môi trường: [`docs/architecture_and_workflows.md#phụ-lục`](docs/architecture_and_workflows.md)

### Chạy

**Cách 1 — Dashboard (khuyên dùng)**

```bash
streamlit run src/dashboard/app.py
```

Mở trình duyệt tại `http://localhost:8501`. Giao diện có 4 tab: **Tìm & Thu thập · Thống kê · Danh sách · Xét duyệt**.

**Cách 2 — CLI**

```bash
python -m src.main \
  --queries "bài giảng toán mầm non 5 tuổi, giáo án chữ cái lớp lá" \
  --provider tavily \
  --limit 10 \
  --semaphore 5
```

| Tham số | Mặc định | Mô tả |
|---|---|---|
| `--queries` | *(bắt buộc)* | Từ khóa tìm kiếm, cách nhau bằng dấu phẩy |
| `--provider` | `tavily` | `tavily` hoặc `exa` |
| `--limit` | `5` | Số URL trả về mỗi từ khóa |
| `--semaphore` | `5` | Số URL xử lý song song |

**Chạy Tests**

```bash
pytest tests/ -v
# Expected: 110 passed, 2 failed (lỗi taxonomy g1 — xem docs/bao_cao_nghiem_thu.md)
```

---

## 📂 Cấu trúc Thư mục

```text
irukacrawler/
├── src/
│   ├── models.py              # DocumentDTO + DocumentMetadata (Pydantic)
│   ├── taxonomy.py            # 🔑 Single Source of Truth — chuẩn phân loại IruKa
│   ├── main.py                # CLI entry + async pipeline orchestrator
│   ├── crawlers/
│   │   ├── documentCrawlers.py    # BaseCrawler: PDF/DOCX/HTML
│   │   ├── youtubeCrawler.py      # YouTubeCrawler: transcript
│   │   └── siteMetadataMapper.py  # Domain → metadata override
│   ├── converters/
│   │   └── documentConverter.py  # PDF/DOCX/HTML → Markdown
│   ├── enricher/
│   │   ├── heuristicEnricher.py  # Bảng quy đổi §5.6
│   │   ├── localLLMEnricher.py   # Ollama/llama3 enrichment
│   │   └── validator.py          # Kiểm tra 4 chiều IruKa Taxonomy
│   ├── exporter/
│   │   └── LocalExporter.py      # Sinh doc_code, YAML frontmatter, manifest.csv
│   ├── uploader/              # ⏳ G2 — chưa implement
│   │   ├── r2_uploader.py        # (placeholder) boto3 → Cloudflare R2
│   │   └── iruka_ingester.py     # (placeholder) POST /bulk-import
│   ├── searcher/
│   │   └── MCPSearcher.py        # Tavily / Exa search API
│   └── dashboard/
│       ├── app.py                # Streamlit entry (4 pages)
│       ├── utils.py              # Đọc manifest, gọi subprocess pipeline
│       └── components/
│           ├── tabThuThap.py     # Tab: Tìm & Thu thập
│           ├── tabThongKe.py     # Tab: Thống kê (Plotly charts)
│           ├── tabDanhSach.py    # Tab: Danh sách tài liệu
│           └── tabXetDuyet.py    # Tab: Xét duyệt (need_manual)
├── data/
│   ├── raw/                   # File gốc: {sha256}.{pdf|docx|html}
│   ├── converted/             # Markdown tạm: {sha256}.md
│   └── export/                # Markdown hoàn chỉnh + manifest.csv
├── docs/
│   ├── architecture_and_workflows.md   # Kiến trúc & luồng hoạt động chi tiết
│   └── bao_cao_nghiem_thu.md           # Báo cáo nghiệm thu G1
├── tests/                     # 6 file test, 112 test cases
├── logs/                      # crawler_{YYYY-MM-DD}.log (loguru)
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

---

## 📊 Trạng thái Dự án

**G1 — Local Demo** *(hiện tại)*

- ✅ 110/112 tests pass (98.2%)
- ✅ 11/18 modules cốt lõi hoàn thành
- ✅ Pipeline 5/7 bước chạy end-to-end
- ✅ Chi phí LLM: **$0** (Ollama local thay OpenAI)
- ⏳ Bước 6 (R2 Upload) và Bước 7 (Bulk-import API) — dành cho G2

**Lộ trình**

| Giai đoạn | Mục tiêu | Mốc |
|---|---|---|
| **G1** *(hiện tại)* | Demo end-to-end local, pipeline 5/7 bước | Hoàn thành |
| **G2** *(Tháng 8/2026)* | Upload R2 + API, Discord, Cron, ≥ 300 tài liệu/tuần | Tuần 5–8 |
| **G3** *(Tháng 9/2026)* | OCR, Embedding Dedup, ≥ 500 tài liệu/tuần | Tuần 9–12 |

> 📖 Báo cáo chi tiết: [`docs/bao_cao_nghiem_thu.md`](docs/bao_cao_nghiem_thu.md)

---

## 📚 Tài liệu

| File | Nội dung |
|---|---|
| [`docs/architecture_and_workflows.md`](docs/architecture_and_workflows.md) | Kiến trúc hệ thống, sơ đồ pipeline, luồng dữ liệu, chuẩn Taxonomy |
| [`docs/bao_cao_nghiem_thu.md`](docs/bao_cao_nghiem_thu.md) | Báo cáo nghiệm thu G1 — so sánh yêu cầu vs thực tế |
| [`08-07-2026__dev-ops__plan-he-thong-cao-tai-lieu-tham-khao.md`](08-07-2026__dev-ops__plan-he-thong-cao-tai-lieu-tham-khao.md) | Kế hoạch dự án gốc (Mr. Đào) |
