# 🔄 Workflows & Sơ đồ Luồng Hoạt động — Hệ thống Cào tài liệu IruKa

> **Phiên bản:** Demo / Local Standalone
> **Dựa trên:** `08-07-2026__dev-ops__plan-he-thong-cao-tai-lieu-tham-khao.md`
> **Trạng thái đánh giá:** 2026-07-09
>
> ⚠️ **Ghi chú quan trọng:** Đây là bản **demo** nên các dịch vụ bên thứ 3 (Cloudflare R2, OpenAI, Discord webhook, VPS Vultr...) và các tính năng trả phí đều được **scale nhỏ lại** hoặc để ở chế độ "sẽ làm sau". Hệ thống hiện tại chạy **100% local** không phụ thuộc internet (ngoại trừ MCP Search và YouTube Transcript API).

---

## Mục lục

1. [Kiến trúc tổng thể (System Architecture)](#1-kiến-trúc-tổng-thể)
2. [Pipeline 7 bước chi tiết (7-Step Pipeline)](#2-pipeline-7-bước-chi-tiết)
3. [Luồng dữ liệu (Data Flow)](#3-luồng-dữ-liệu)
4. [Vòng đời tài liệu (Document Lifecycle)](#4-vòng-đời-tài-liệu)
5. [Luồng tương tác thành phần (Component Interaction)](#5-luồng-tương-tác-thành-phần)
6. [Luồng xử lý metadata (Metadata Enrichment Flow)](#6-luồng-xử-lý-metadata)
7. [Luồng xét duyệt (Review Flow)](#7-luồng-xét-duyệt)
8. [Luồng triển khai (Deployment Flow)](#8-luồng-triển-khai)
9. [Luồng dashboard (Dashboard UI Flow)](#9-luồng-dashboard)
10. [So sánh trạng thái hiện tại vs yêu cầu](#10-so-sánh-trạng-thái-hiện-tại-vs-yêu-cầu)

---

## 1. Kiến trúc tổng thể

```mermaid
graph TB
    subgraph "🌐 Nguồn dữ liệu (Data Sources)"
        A1["moet.gov.vn<br/>(Bộ GD-ĐT)"]
        A2["mamnon.com<br/>giaovienmamnon.com"]
        A3["YouTube<br/>(Transcript)"]
        A4["Tavily / Exa<br/>(Search API)"]
    end

    subgraph "🕷️ IruKa Crawler (Local Standalone)"
        B1["🔍 MCPSearcher<br/>(Tavily/Exa MCP)"]
        B2["📥 BaseCrawler<br/>(PDF/DOCX/HTML)"]
        B3["🎬 YouTubeCrawler<br/>(Transcript API)"]
        B4["📝 DocumentConverter<br/>(→ Markdown)"]
        B5["🧠 HeuristicEnricher<br/>(Bảng 5.6)"]
        B6["🤖 LocalLLMEnricher<br/>(Ollama)"]
        B7["🛡️ Validator<br/>(Chất lượng)"]
        B8["📁 LocalExporter<br/>(File + Manifest)"]
    end

    subgraph "📂 Đích đến (Local Storage)"
        C1["📂 data/export/kho-tai-lieu<br/>(Cấu trúc R2 local)"]
        C2["📋 manifest.csv<br/>(Bảng kê)"]
        C3["⏭️ Upload R2<br/>(Sẽ làm sau)"]
        C4["⏭️ Bulk-import API<br/>(Sẽ làm sau)"]
        C5["⏭️ Xưởng Sản Xuất<br/>(cur.irukaedu.vn)"]
    end

    subgraph "📊 Dashboard (Streamlit)"
        D1["📥 Tab Thu thập<br/>(Chạy pipeline)"]
        D2["📈 Tab Thống kê<br/>(Biểu đồ Plotly)"]
        D3["📋 Tab Danh sách<br/>(Bảng dữ liệu)"]
        D4["🔍 Tab Xét duyệt<br/>(Sửa metadata tay)"]
    end

    A4 --> B1
    B1 --> B2
    A1 --> B2
    A2 --> B2
    A3 --> B3
    
    B2 --> B4
    B3 --> B4
    B4 --> B5
    B5 --> B6
    B6 --> B7
    B7 --> B8
    
    B8 --> C1
    B8 --> C2
    C1 -.->|"Sẽ làm sau"| C3
    C2 -.->|"Sẽ làm sau"| C3
    C3 -.-> C4
    C4 -.-> C5
    
    D1 -->|"subprocess"| B1
    D2 -->|"Đọc"| C2
    D3 -->|"Đọc"| C2
    D4 -->|"Đọc/Ghi"| C2

    classDef source fill:#e3f2fd,stroke:#1565c0
    classDef crawler fill:#fff3e0,stroke:#e65100
    classDef dest fill:#e8f5e9,stroke:#2e7d32
    classDef dash fill:#f3e5f5,stroke:#6a1b9a
    classDef later fill:#f5f5f5,stroke:#9e9e9e,stroke-dasharray: 5 5

    class A1,A2,A3,A4 source
    class B1,B2,B3,B4,B5,B6,B7,B8 crawler
    class C1,C2 dest
    class C3,C4,C5 later
    class D1,D2,D3,D4 dash
```

---

## 2. Pipeline 7 bước chi tiết

```mermaid
flowchart LR
    subgraph "Bước 1: Tìm kiếm & Cào"
        direction TB
        S1["🔍 MCPSearcher<br/>Tavily / Exa"] --> S2["🕷️ Crawl URL<br/>BaseCrawler"]
        S2 --> S3{"Định dạng?"}
        S3 -->|PDF| S4["📄 PyMuPDF"]
        S3 -->|DOCX| S5["📝 python-docx"]
        S3 -->|HTML| S6["🌐 BeautifulSoup"]
        S3 -->|YouTube| S7["🎬 Transcript API"]
    end

    subgraph "Bước 2: Convert → Markdown"
        direction TB
        C1["📄 File gốc"] --> C2["📝 DocumentConverter"]
        C2 --> C3["➕ Thêm --- Trang N ---"]
        C2 --> C4["🔤 Giữ Heading (H1-H3)"]
        C2 --> C5["🖼️ Bỏ ảnh → [Ảnh: ...]"]
        C2 --> C6["💾 data/converted/*.md"]
    end

    subgraph "Bước 3: Enrich Metadata"
        direction TB
        E1["📄 File MD"] --> E2["🧠 HeuristicEnricher<br/>(Bảng 5.6)"]
        E2 --> E3{"Đủ 4 chiều?"}
        E3 -->|Có| E4["✅ Metadata tạm"]
        E3 -->|Không| E5["🤖 LocalLLMEnricher<br/>(Ollama)"]
        E5 --> E6["📋 JSON metadata"]
        E6 --> E4
    end

    subgraph "Bước 4: Validate"
        direction TB
        V1["📄 File + Metadata"] --> V2["🛡️ Validator"]
        V2 --> V3{"File > 500 ký tự?"}
        V3 -->|Không| V4["❌ need_manual=true"]
        V3 -->|Có| V5{"File < 5MB?"}
        V5 -->|Không| V4
        V5 -->|Có| V6{"Đủ 4 chiều?"}
        V6 -->|Không| V4
        V6 -->|Có| V7{"doc_type hợp lệ?"}
        V7 -->|Không| V8["🔄 Gán 'khac'"]
        V8 --> V4
        V7 -->|Có| V9["✅ Pass"]
    end

    subgraph "Bước 5: Sinh doc_code"
        direction TB
        D1["✅ Pass"] --> D2["🏷️ Sinh mã<br/>DOC-{LV2}-{age}-{NHOM}-{seq4}"]
        D2 --> D3["Ví dụ:<br/>DOC-NN-56-SGK-0001"]
    end

    subgraph "Bước 6: Export Local"
        direction TB
        X1["📄 File MD + Metadata"] --> X2["📁 LocalExporter"]
        X2 --> X3["📂 data/export/kho-tai-lieu/<br/>{zone}/{origin}/{series}/{age}/{linh_vuc}/"]
        X2 --> X4["📋 manifest.csv"]
        X3 --> X5["💾 File .md có frontmatter YAML"]
    end

    subgraph "Bước 7: Upload & Import (⏭️ Sẽ làm sau)"
        direction TB
        U1["📂 File export"] -.-> U2["☁️ Upload R2<br/>(presigned URL)"]
        U2 -.-> U3["🏭 Bulk-import API"]
        U3 -.-> U4["✅ Xưởng Sản Xuất<br/>cho_duyet"]
    end

    S4 --> C1
    S5 --> C1
    S6 --> C1
    S7 --> C1
    C6 --> E1
    E4 --> V1
    V9 --> D1
    D3 --> X1
    X5 -.-> U1

    classDef step1 fill:#e3f2fd,stroke:#1565c0
    classDef step2 fill:#fff3e0,stroke:#e65100
    classDef step3 fill:#e8f5e9,stroke:#2e7d32
    classDef step4 fill:#fce4ec,stroke:#c62828
    classDef step5 fill:#f3e5f5,stroke:#6a1b9a
    classDef step6 fill:#e0f2f1,stroke:#00695c
    classDef step7 fill:#f5f5f5,stroke:#9e9e9e,stroke-dasharray: 5 5

    class S1,S2,S3,S4,S5,S6,S7 step1
    class C1,C2,C3,C4,C5,C6 step2
    class E1,E2,E3,E4,E5,E6 step3
    class V1,V2,V3,V4,V5,V6,V7,V8,V9 step4
    class D1,D2,D3 step5
    class X1,X2,X3,X4,X5 step6
    class U1,U2,U3,U4 step7
```

---

## 3. Luồng dữ liệu

```mermaid
flowchart TD
    subgraph "Input Layer"
        I1["🔗 URL từ MCP Search<br/>(Tavily/Exa)"]
        I2["🔗 URL từ người dùng<br/>(Dashboard)"]
        I3["🎬 URL YouTube"]
    end

    subgraph "Raw Storage"
        R1["📁 data/raw/<br/>{sha256}.pdf"]
        R2["📁 data/raw/<br/>{sha256}.docx"]
        R3["📁 data/raw/<br/>{sha256}.html"]
        R4["📁 data/raw/<br/>{title}.md (YouTube)"]
        R5["📄 data/crawled_urls.json<br/>(Dedup DB)"]
    end

    subgraph "Converted Storage"
        V1["📁 data/converted/<br/>{sha256}.md"]
    end

    subgraph "Export Storage <br/>(⏭️ Đích đến của Demo)"
        E1["📁 data/export/kho-tai-lieu/<br/>{zone}/{origin}/{series}/{age}/{linh_vuc}/<br/>{doc_code}__{slug}.md"]
        E2["📋 data/export/manifest.csv"]
    end

    subgraph "Metadata Flow"
        M1["🧠 HeuristicEnricher<br/>→ linh_vuc, age_band,<br/>doc_type, source_tier"]
        M2["🤖 LocalLLMEnricher<br/>(Ollama)<br/>→ Fallback khi thiếu"]
        M3["🛡️ Validator<br/>→ Lọc, chuẩn hoá"]
    end

    I1 -->|"BaseCrawler.download_file()"| R1
    I1 -->|"BaseCrawler.download_file()"| R2
    I1 -->|"BaseCrawler.download_file()"| R3
    I3 -->|"YouTubeCrawler.download_file()"| R4
    I2 -->|"BaseCrawler.download_file()"| R1

    R1 -->|"DocumentConverter.convert()"| V1
    R2 -->|"DocumentConverter.convert()"| V1
    R3 -->|"DocumentConverter.convert()"| V1
    R4 --> V1

    V1 -->|"Đọc nội dung"| M1
    M1 -->|"Thiếu 4 chiều"| M2
    M2 -->|"Merge metadata"| M1
    M1 -->|"Metadata đầy đủ"| M3
    M3 -->|"Pass"| E1
    M3 -->|"Pass"| E2
    M3 -->|"Fail → need_manual"| E2

    R5 -.->|"Dedup check"| I1

    classDef input fill:#e3f2fd,stroke:#1565c0
    classDef raw fill:#fff3e0,stroke:#e65100
    classDef conv fill:#e8f5e9,stroke:#2e7d32
    classDef export fill:#f5f5f5,stroke:#9e9e9e
    classDef meta fill:#fce4ec,stroke:#c62828

    class I1,I2,I3 input
    class R1,R2,R3,R4,R5 raw
    class V1 conv
    class E1,E2 export
    class M1,M2,M3 meta
```

---

## 4. Vòng đời tài liệu

```mermaid
stateDiagram-v2
    [*] --> RAW: Crawl URL thành công
    
    state RAW {
        [*] --> PDF: Đuôi .pdf
        [*] --> DOCX: Đuôi .docx
        [*] --> HTML: Đuôi .html
        [*] --> YT_MD: YouTube transcript
    end
    
    RAW --> CONVERTED: DocumentConverter
    
    CONVERTED --> ENRICHED: HeuristicEnricher
    
    ENRICHED --> NEED_MANUAL: Validator FAIL
    ENRICHED --> PENDING_REVIEW: Validator PASS
    
    state NEED_MANUAL {
        [*] --> CHO_DUYET_TAY: Ghi manifest.csv
        CHO_DUYET_TAY --> DANG_SUA: Admin chọn
        DANG_SUA --> DA_SUA: Lưu metadata
        DA_SUA --> PENDING_REVIEW: Đủ 4 chiều
    end
    
    state PENDING_REVIEW {
        [*] --> CHO_DUYET: Chờ duyệt
        CHO_DUYET --> DA_DUYET: Admin bấm Duyệt
        CHO_DUYET --> TU_CHOI: Admin từ chối
    end
    
    DA_DUYET --> APPROVED: Băm vector
    TU_CHOI --> [*]
    APPROVED --> [*]

    note right of RAW
        Lưu tại data/raw/{hash}.{ext}
        Dedup bằng SHA-256
    end note

    note right of CONVERTED
        Lưu tại data/converted/{hash}.md
        Có mốc --- Trang N ---
    end note

    note right of ENRICHED
        Frontmatter YAML đầy đủ
        4 chiều: linh_vuc, age_band,
        doc_type, source_tier
    end note

    note right of PENDING_REVIEW
        Đã export ra data/export/
        Có trong manifest.csv
        (Demo dừng ở đây — R2 upload
        + bulk-import sẽ làm sau)
    end note
```

---

## 5. Luồng tương tác thành phần

```mermaid
sequenceDiagram
    autonumber
    
    actor User as 👤 Người dùng / Mr. Đào
    participant UI as 📊 Streamlit Dashboard
    participant CLI as 🖥️ CLI (src/main.py)
    participant Search as 🔍 MCPSearcher
    participant Crawler as 🕷️ BaseCrawler
    participant Web as 🌐 Web Sources
    participant YT as 🎬 YouTubeCrawler
    participant YTAPI as 📺 YouTube API
    participant Conv as 📝 DocumentConverter
    participant Heur as 🧠 HeuristicEnricher
    participant LLM as 🤖 LocalLLMEnricher (Ollama)
    participant Valid as 🛡️ Validator
    participant Export as 📁 LocalExporter

    User->>UI: Nhập từ khoá, chọn nguồn
    UI->>CLI: subprocess: python -m src.main --queries ...
    
    CLI->>Search: search(query, limit)
    Search-->>CLI: Danh sách URL
    
    loop Mỗi URL
        CLI->>Crawler: download_file(url)
        
        alt URL YouTube
            Crawler->>YT: download_file(url)
            YT->>YTAPI: Lấy transcript
            YTAPI-->>YT: Transcript text
            YT-->>Crawler: File .md
        else URL thường
            Crawler->>Web: GET request (rate limited)
            Web-->>Crawler: File PDF/DOCX/HTML
            Crawler-->>CLI: data/raw/{hash}.{ext}
            
            CLI->>Conv: convert(file_path)
            Conv-->>CLI: data/converted/{hash}.md
        end
        
        CLI->>Heur: apply_rules(name, url)
        Heur-->>CLI: metadata_dict
        
        alt Thiếu 4 chiều
            CLI->>LLM: analyze_document(name, url, preview)
            LLM-->>CLI: JSON metadata
            CLI->>CLI: Merge vào metadata
        end
        
        CLI->>Valid: validate_file(md_path)
        CLI->>Valid: validate_metadata(meta)
        Valid-->>CLI: True/False
        
        alt Không pass
            CLI->>Export: export(need_manual=true)
            Export-->>CLI: Ghi manifest.csv
            CLI-->>UI: "⚠️ Cần duyệt tay"
        else Pass
            CLI->>Export: export(doc_dto)
            Export-->>CLI: File + manifest
            CLI-->>UI: "✅ Thành công"
        end
    end
    
    CLI-->>UI: Báo cáo thống kê (===STATS===)
    UI-->>User: Hiển thị kết quả

    Note over UI: ✅ Demo dừng ở đây<br/>Dữ liệu đã có trong data/export/<br/>Upload R2 + Bulk-import sẽ làm sau
```

---

## 6. Luồng xử lý metadata

```mermaid
flowchart TD
    A["📄 Tên file + URL"] --> B["🧠 HeuristicEnricher.apply_rules()"]
    
    subgraph "Tầng 1: Heuristic (Bảng 5.6)"
        B --> B1["🔍 Domain → source_tier<br/>(DOMAIN_TIER_MAP)"]
        B --> B2["🔍 Domain → doc_type<br/>(DOMAIN_DOCTYPE_MAP)"]
        B --> B3["🔍 Tên → linh_vuc + sub_domain<br/>(~40 keyword patterns)"]
        B --> B4["🔍 Tên → doc_type<br/>(~25 patterns)"]
        B --> B5["🔍 Tên → age_band<br/>(3-4, 4-5, 5-6, lớp 1)"]
        B1 --> B6["📋 Metadata tạm"]
        B2 --> B6
        B3 --> B6
        B4 --> B6
        B5 --> B6
    end
    
    B6 --> C{"is_valid()?<br/>Đủ 4 chiều?"}
    
    C -->|"Có ✅"| D["📦 Export ngay"]
    
    C -->|"Không ❌"| E["🤖 LocalLLMEnricher.analyze_document()"]
    
    subgraph "Tầng 2: LLM (Ollama) <br/>⏭️ Dùng Ollama thay OpenAI<br/>(Miễn phí, chạy local)"
        E --> E1["📝 Prompt với taxonomy chuẩn"]
        E1 --> E2["🔄 Gọi Ollama API<br/>(format=json, temp=0)"]
        E2 --> E3{"Parse JSON thành công?"}
        E3 -->|"Có"| E4["🧪 Validate bằng Pydantic"]
        E4 --> E5{"Pass Pydantic?"}
        E5 -->|"Có"| E6["🔀 Merge vào metadata"]
        E5 -->|"Không"| E7["❌ Bỏ qua LLM result"]
        E3 -->|"Không"| E7
    end
    
    E6 --> F{"Đủ 4 chiều sau merge?"}
    F -->|"Có"| D
    F -->|"Không"| G["🏷️ need_manual = true"]
    
    E7 --> F

    subgraph "Tầng 3: Validator"
        D --> V1["🛡️ Validator.validate_metadata()"]
        V1 --> V2["🔍 Lọc giá trị lạ<br/>(linh_vuc, age_band, doc_type, sub_domain)"]
        V2 --> V3{"doc_type lạ?"}
        V3 -->|"Có"| V4["🔄 Gán 'khac'"]
        V3 -->|"Không"| V5{"Còn đủ 4 chiều?"}
        V4 --> V5
        V5 -->|"Có"| V6["✅ Pass → Export"]
        V5 -->|"Không"| V7["🏷️ need_manual = true"]
    end

    G --> V7

    classDef heuristic fill:#fff3e0,stroke:#e65100
    classDef llm fill:#f3e5f5,stroke:#6a1b9a
    classDef valid fill:#e8f5e9,stroke:#2e7d32
    classDef result fill:#e3f2fd,stroke:#1565c0

    class B,B1,B2,B3,B4,B5,B6 heuristic
    class E,E1,E2,E3,E4,E5,E6,E7 llm
    class V1,V2,V3,V4,V5,V6,V7 valid
    class C,D,F,G result
```

---

## 7. Luồng xét duyệt

```mermaid
flowchart TD
    A["📋 manifest.csv"] --> B["🔍 Đọc dòng có need_manual=true"]
    B --> C["📊 Dashboard Tab Xét duyệt"]
    
    C --> D["👤 Admin chọn tài liệu"]
    D --> E["📝 Hiển thị thông tin hiện tại"]
    
    E --> F["✏️ Sửa metadata:"]
    F --> F1["Lĩnh vực (linh_vuc)"]
    F --> F2["Độ tuổi (age_band)"]
    F --> F3["Loại tài liệu (doc_type)"]
    
    F1 --> G["💾 Lưu & Phê duyệt"]
    F2 --> G
    F3 --> G
    
    G --> H["Cập nhật manifest.csv:"]
    H --> H1["need_manual = false"]
    H --> H2["status = 'exported'"]
    H --> H3["Sinh doc_code mới"]
    
    H --> I["🔄 Xoá cache dashboard"]
    I --> J["✅ Toast: Phê duyệt thành công"]

    subgraph "Luồng tự động (không cần duyệt)"
        K["📄 Tài liệu pass validator"] --> L["✅ Export trực tiếp"]
        L --> M["status = 'exported'<br/>need_manual = false"]
    end

    classDef manual fill:#fce4ec,stroke:#c62828
    classDef auto fill:#e8f5e9,stroke:#2e7d32
    classDef action fill:#e3f2fd,stroke:#1565c0

    class A,B,C,D,E,F,F1,F2,F3,G,H,H1,H2,H3,I,J manual
    class K,L,M auto
```

---

## 8. Luồng triển khai (Demo)

```mermaid
flowchart LR
    subgraph "Development"
        Dev1["💻 Code Python"]
        Dev2["🧪 pytest"]
        Dev3["📦 pyproject.toml"]
    end

    subgraph "Chạy local (Demo)"
        L1["🖥️ python -m src.main<br/>--queries ..."]
        L2["📊 streamlit run<br/>src/dashboard/app.py"]
        L3["🤖 ollama serve<br/>(nếu dùng LLM)"]
    end

    subgraph "Docker (Tuỳ chọn)"
        D1["🐳 docker-compose up -d"]
        D2["🕷️ Crawler Service"]
        D3["📊 Dashboard (port 8501)"]
        D4["🤖 Ollama (port 11434)"]
    end

    Dev1 --> Dev2
    Dev2 --> L1
    Dev2 --> L2
    Dev2 --> L3
    
    L1 --> D1
    L2 --> D1
    
    D1 --> D2
    D1 --> D3
    D1 --> D4

    classDef dev fill:#e3f2fd,stroke:#1565c0
    classDef local fill:#e8f5e9,stroke:#2e7d32
    classDef docker fill:#fff3e0,stroke:#e65100

    class Dev1,Dev2,Dev3 dev
    class L1,L2,L3 local
    class D1,D2,D3,D4 docker
```

---

## 9. Luồng dashboard

```mermaid
flowchart TD
    subgraph "Streamlit App (port 8501)"
        A["🏠 app.py<br/>st.navigation()"]
        
        A --> T1["📥 Tab Thu thập<br/>(tabThuThap.py)"]
        A --> T2["📈 Tab Thống kê<br/>(tabThongKe.py)"]
        A --> T3["📋 Tab Danh sách<br/>(tabDanhSach.py)"]
        A --> T4["🔍 Tab Xét duyệt<br/>(tabXetDuyet.py)"]
        
        subgraph "Tab Thu thập"
            T1 --> T1a["📝 Form nhập từ khoá"]
            T1 --> T1b["⚙️ Cấu hình:<br/>nguồn, limit, semaphore"]
            T1 --> T1c["▶️ Bắt đầu thu thập"]
            T1c --> T1d["🔄 subprocess: src.main"]
            T1d --> T1e["📊 Hiển thị log real-time"]
            T1e --> T1f["📈 Báo cáo kết quả"]
        end
        
        subgraph "Tab Thống kê"
            T2 --> T2a["🔍 Bộ lọc:<br/>trạng thái, tier"]
            T2 --> T2b["📊 KPIs:<br/>tổng, tự động, cần duyệt, tier3"]
            T2 --> T2c["📈 Biểu đồ:<br/>- Tier (pie)<br/>- Lĩnh vực (bar)<br/>- Độ tuổi (bar)<br/>- Loại tài liệu (bar)"]
        end
        
        subgraph "Tab Danh sách"
            T3 --> T3a["🔎 Tìm kiếm nhanh"]
            T3 --> T3b["📋 Bảng dữ liệu"]
            T3 --> T3c["📥 Tải xuống CSV"]
            T3 --> T3d["🔍 Xem chi tiết tài liệu"]
        end
        
        subgraph "Tab Xét duyệt"
            T4 --> T4a["📋 Danh sách cần duyệt"]
            T4 --> T4b["✏️ Form sửa metadata:<br/>linh_vuc, age_band, doc_type"]
            T4 --> T4c["💾 Lưu & Phê duyệt"]
            T4c --> T4d["✅ Cập nhật manifest.csv"]
        end
    end

    subgraph "Data Source"
        D1["📋 data/export/manifest.csv"]
        D2["📁 data/export/kho-tai-lieu/"]
    end

    T1d -->|"Ghi"| D1
    T1d -->|"Ghi"| D2
    T2 -->|"Đọc (cache 30s)"| D1
    T3 -->|"Đọc"| D1
    T4 -->|"Đọc/Ghi"| D1

    classDef app fill:#e3f2fd,stroke:#1565c0
    classDef tab fill:#fff3e0,stroke:#e65100
    classDef data fill:#e8f5e9,stroke:#2e7d32

    class A app
    class T1,T1a,T1b,T1c,T1d,T1e,T1f,T2,T2a,T2b,T2c,T3,T3a,T3b,T3c,T3d,T4,T4a,T4b,T4c,T4d tab
    class D1,D2 data
```

---

## 10. So sánh trạng thái hiện tại vs yêu cầu

> **Lưu ý:** Đánh giá dưới đây trong bối cảnh **Demo / Local Standalone**. Các mục đánh dấu ⏭️ là "sẽ làm sau" khi chuyển lên production — không ảnh hưởng đến chức năng demo hiện tại.

### 10.1 · Mức độ hoàn thành theo module

| Module | Spec gốc | Trạng thái Demo | % Demo |
|---|---|---|---|
| **Taxonomy** (§5) | 25 doc_type, 7 nhóm, 5 linh_vuc, 12 sub_domain | ✅ Hoàn chỉnh | **100%** |
| **BaseCrawler** (§7.1) | robots.txt, rate limit, dedup, blacklist | ✅ Đầy đủ | **100%** |
| **YouTubeCrawler** (§4.1) | Transcript API, ưu tiên tiếng Việt | ✅ Hoạt động | **100%** |
| **DocumentConverter** (§7.2) | PDF/DOCX/HTML → MD, giữ heading, bỏ ảnh | ✅ Đầy đủ | **100%** |
| **HeuristicEnricher** (§5.6) | Bảng quy đổi 5.6, ~40 patterns | ✅ Rất chi tiết | **100%** |
| **LocalLLMEnricher** (§7.3) | Ollama (local, miễn phí) thay vì OpenAI | ✅ Phù hợp demo | **100%** |
| **Validator** (§7.4) | File check, metadata check, lọc giá trị lạ | ✅ Đầy đủ | **100%** |
| **LocalExporter** (§8) | Frontmatter YAML, cấu trúc thư mục, manifest | ✅ Hoạt động | **100%** |
| **R2 Uploader** (§7.6) | Upload lên Cloudflare R2 | ⏭️ Sẽ làm sau | **—** |
| **Iruka Ingester** (§7.7) | Gọi API bulk-import | ⏭️ Sẽ làm sau | **—** |
| **MCPSearcher** (§6.2) | Tavily + Exa MCP | ✅ Hoạt động | **100%** |
| **Dashboard** (§10 G3) | Streamlit, 4 tab, biểu đồ, xét duyệt | ✅ Rất tốt | **100%** |
| **SiteMetadataMapper** (§4.1) | Metadata override theo domain (12 site, 3 nhóm) | ✅ Hoạt động — vừa thêm | **100%** |
REPLACE
| **Báo cáo Discord** (§8.3) | Webhook báo cáo mẻ chạy | ⏭️ Sẽ làm sau (xem log trên Dashboard) | **—** |
| **OCR** (§10 G3) | Tesseract/Google Vision cho SGK scan | ⏭️ Sẽ làm sau | **—** |
| **Cron job** (§10 G2) | arq/Celery scheduled task | ⏭️ Sẽ làm sau (chạy tay qua Dashboard) | **—** |
| **DMCA/opt-out** (§9.3) | Blacklist source_url, xoá tài liệu | ⏭️ Sẽ làm sau | **—** |
| **Tests** (§11) | pytest, 6 test files, Postman | ✅ Khá tốt | **80%** |

### 10.2 · Tổng quan demo

| Hạng mục | Giá trị |
|---|---|
| **Tổng số module đã hoạt động** | **10/18** module (còn lại ⏭️ sẽ làm sau) |
| **Tỷ lệ hoàn thành trên module demo** | **10/10 = 100%** (các module trong phạm vi demo đều hoạt động) |
| **Số dòng code ước tính** | ~2,000+ lines Python |
| **Số test** | 6 test files, ~80+ test cases |
| **Dependencies** | Python 3.11+, Playwright, PyMuPDF, Ollama, Streamlit, httpx, pandas, plotly |
| **Cách chạy** | `streamlit run src/dashboard/app.py` hoặc `python -m src.main --queries "từ khoá" --provider tavily` |

### 10.3 · Các file gợi ý phát triển sau (khi lên production)

| File | Mục đích | Ghi chú |
|---|---|---|
| `src/uploader/r2_uploader.py` | Upload lên Cloudflare R2 | Cần credentials R2 + API presign |
| `src/uploader/iruka_ingester.py` | Gọi bulk-import API be-hub | Cần IRUKA_ADMIN_TOKEN |
| `src/reporter/discord_reporter.py` | Gửi báo cáo Discord | Cần Discord webhook URL |
| `src/processors/ocr_processor.py` | OCR cho SGK scan | Cần Tesseract / Google Vision |
REPLACE

---

## Chú thích

| Ký hiệu | Ý nghĩa |
|---|---|
| ✅ **Hoạt động** | Module đã được implement và hoạt động trong bản demo |
| ⏭️ **Sẽ làm sau** | Module nằm ngoài phạm vi demo (cần dịch vụ trả phí / production) |
| Đường nét đứt (`-.-` hoặc `-.->`) | Luồng chưa được kết nối (sẽ làm sau) |
| Màu xám | Thành phần nằm ngoài phạm vi demo hiện tại |

---

> **Tài liệu tham khảo:**
> - `08-07-2026__dev-ops__plan-he-thong-cao-tai-lieu-tham-khao.md` — Kế hoạch gốc
> - `workflow_roles.md` — Flow-Roles phiên bản độc lập
> - `src/taxonomy.py` — Chuẩn phân loại IruKa (Single Source of Truth)
> - `src/main.py` — Entry point pipeline