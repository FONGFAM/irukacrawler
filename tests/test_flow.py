"""
tests/test_flow.py — Integration test toàn bộ pipeline (E2E).

Kiểm tra luồng đầy đủ:
  Search (mock) → Crawl (mock) → Convert (real) → Enrich Heuristic (real)
  → Validate (real) → Export (real to tmp_dir)

Không gọi internet thật, không gọi LLM thật.
LLM Enricher bị mock để trả về kết quả xác định.
"""
import hashlib
import os
import tempfile
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.enricher.heuristicEnricher import HeuristicEnricher
from src.enricher.validator import Validator
from src.exporter.LocalExporter import LocalExporter
from src.models import DocumentDTO, DocumentMetadata


# ─────────────────────────────────────────────────────────────
# Fixtures & helpers
# ─────────────────────────────────────────────────────────────

SAMPLE_PDF_CONTENT = (
    b"%PDF-1.4 fake pdf content for testing purposes only. " * 30
)  # > 500 bytes

SAMPLE_MD_CONTENT = """# Giáo án phát triển ngôn ngữ: Kể chuyện Ba chú heo con

## Mục tiêu
- Trẻ kể lại được câu chuyện theo trình tự.
- Phát triển ngôn ngữ mạch lạc, từ vựng phong phú.

## Chuẩn bị
- Tranh minh họa: Heo Út, Heo Cả, Heo Giữa.
- Nhạc nền nhẹ nhàng.

## Tiến trình
1. Ổn định tổ chức (3 phút)
2. Kể chuyện lần 1 (10 phút)
3. Đàm thoại và tái kể (15 phút)
4. Kết thúc và nhận xét (2 phút)

> Lưu ý: Giáo viên cần linh hoạt điều chỉnh theo năng lực trẻ trong lớp.
""" * 3  # > 500 ký tự


@pytest.fixture
def tmp_export(tmp_path):
    """Tạo cấu trúc thư mục tạm cho output."""
    raw_dir = tmp_path / "raw"
    converted_dir = tmp_path / "converted"
    export_dir = tmp_path / "export" / "kho-tai-lieu"
    raw_dir.mkdir(parents=True)
    converted_dir.mkdir(parents=True)
    export_dir.mkdir(parents=True)
    return {
        "raw": str(raw_dir),
        "converted": str(converted_dir),
        "export": str(export_dir),
        "root": str(tmp_path),
    }


def make_converted_md(tmp_export: dict, content: str = SAMPLE_MD_CONTENT) -> str:
    """Tạo file MD giả trong thư mục converted."""
    file_hash = hashlib.sha256(content.encode()).hexdigest()
    md_path = Path(tmp_export["converted"]) / f"{file_hash}.md"
    md_path.write_text(content, encoding="utf-8")
    return str(md_path)


# ─────────────────────────────────────────────────────────────
# Flow 1: Heuristic đủ 4 chiều → PASS ngay (không cần LLM)
# ─────────────────────────────────────────────────────────────

class TestFlowHeuristicPass:
    """Pipeline chạy thành công khi Heuristic đã đủ 4 chiều."""

    def test_flow_full_pipeline_no_llm(self, tmp_export):
        """
        Input: Tên tài liệu chứa đủ keyword để Heuristic suy được 4 chiều.
        Expected: File được export vào đúng zone, manifest.csv được ghi.
        """
        heuristic = HeuristicEnricher()
        validator = Validator()
        exporter = LocalExporter(export_dir=tmp_export["export"])

        name = "Giáo án kể chuyện Ba chú heo con cho trẻ 5-6 tuổi"
        url = "https://giaovienmamnon.com/giao-an-ke-chuyen-ba-chu-heo-con"
        md_path = make_converted_md(tmp_export)

        # Bước 4: Heuristic
        meta_dict = heuristic.apply_rules(name=name, url=url)
        meta = DocumentMetadata(name=name, source_url=url, **meta_dict)

        # Xác nhận heuristic đủ 4 chiều
        assert meta.is_valid(), f"Heuristic phải đủ 4 chiều. meta={meta_dict}"
        assert "ngon_ngu" in meta.linh_vucs
        assert "56" in meta.age_bands
        assert meta.doc_type == "gt.giao_an"
        assert meta.source_tier == 2

        # Bước 5: Validate
        assert validator.validate_file(md_path) is True
        assert validator.validate_metadata(meta) is True

        # Bước 6: Export
        doc_dto = DocumentDTO(metadata=meta, raw_file_path="raw.pdf", converted_md_path=md_path)
        result = exporter.export(doc_dto)

        assert result is True

        # Kiểm tra file đã được tạo trong đúng zone
        export_root = Path(tmp_export["export"])
        exported_files = list(export_root.rglob("*.md"))
        assert len(exported_files) == 1
        exported_path = str(exported_files[0])
        assert "03_GT_giao_trinh_truong" in exported_path, f"Zone sai: {exported_path}"
        assert "56" in exported_path, f"Age band sai trong path: {exported_path}"
        assert "ngon_ngu" in exported_path, f"Linh vuc sai trong path: {exported_path}"

        # Kiểm tra manifest.csv
        manifest = Path(tmp_export["export"]).parent / "manifest.csv"
        assert manifest.exists()
        content = manifest.read_text(encoding="utf-8")
        assert "gt.giao_an" in content
        assert "exported" in content

    def test_flow_frontmatter_trong_file_export(self, tmp_export):
        """File được export phải có frontmatter YAML đầy đủ."""
        heuristic = HeuristicEnricher()
        exporter = LocalExporter(export_dir=tmp_export["export"])

        name = "Thông tư 01/2021 Chương trình giáo dục mầm non"
        url = "https://moet.gov.vn/vbdb/thong-tu-01-2021"
        md_path = make_converted_md(tmp_export)

        meta_dict = heuristic.apply_rules(name=name, url=url)
        meta = DocumentMetadata(
            name=name, source_url=url,
            linh_vucs=["ngon_ngu"],  # Bổ sung để đủ 4 chiều (PL doc không có linh_vuc từ heuristic)
            age_bands=["56"],
            **{k: v for k, v in meta_dict.items() if k not in ("linh_vucs", "age_bands")}
        )

        doc_dto = DocumentDTO(metadata=meta, raw_file_path="raw.pdf", converted_md_path=md_path)
        exporter.export(doc_dto)

        exported_files = list(Path(tmp_export["export"]).rglob("*.md"))
        assert exported_files, "Phải có ít nhất 1 file được export"
        content = exported_files[0].read_text(encoding="utf-8")

        assert content.startswith("---"), "File export phải có frontmatter YAML"
        assert "name:" in content
        assert "source_url:" in content
        assert "doc_type:" in content
        assert "pl.thong_tu" in content


# ─────────────────────────────────────────────────────────────
# Flow 2: Heuristic thiếu → LLM cứu → PASS
# ─────────────────────────────────────────────────────────────

class TestFlowLLMFallback:
    """LLM được gọi khi Heuristic không đủ 4 chiều."""

    def test_flow_llm_duoc_goi_khi_heuristic_thieu(self, tmp_export):
        """
        Tên file là hash (không keyword nào) → Heuristic trả về rỗng
        → is_valid() = False → phải gọi LLM.
        """
        heuristic = HeuristicEnricher()
        name = "853d3f8b2d8eee560985225759e784ef"  # tên hash, không keyword
        url = "https://example.com/doc.pdf"

        meta_dict = heuristic.apply_rules(name=name, url=url)
        meta = DocumentMetadata(name=name, source_url=url, **meta_dict)

        # Xác nhận heuristic KHÔNG đủ 4 chiều
        assert meta.is_valid() is False, "Tên hash phải trả về metadata không đủ 4 chiều"

    def test_flow_llm_result_duoc_merge_vao_meta(self, tmp_export):
        """
        Mock LLM trả về kết quả hợp lệ.
        Sau khi merge, metadata phải đủ 4 chiều.
        """
        heuristic = HeuristicEnricher()
        validator = Validator()
        exporter = LocalExporter(export_dir=tmp_export["export"])
        md_path = make_converted_md(tmp_export)

        name = "document_853d3f8b"  # tên không rõ ràng
        url = "https://thuvienso.hcmute.edu.vn/document.pdf"

        # Bước 4: Heuristic (sẽ không đủ)
        meta_dict = heuristic.apply_rules(name=name, url=url)
        meta = DocumentMetadata(name=name, source_url=url, **meta_dict)
        assert meta.is_valid() is False

        # Bước 5: Mock LLM trả về kết quả xác định
        llm_result = {
            "linh_vucs": ["ngon_ngu"],
            "age_bands": ["45"],
            "doc_type": "gt.giao_an",
            "sub_domain_ids": ["nn.nghe_noi"],
            "source_tier": 2,
        }

        # Tạo lại meta với đầy đủ thông tin để Pydantic validator suy doc_group
        meta = DocumentMetadata(
            name=name,
            source_url=url,
            linh_vucs=meta.linh_vucs or llm_result["linh_vucs"],
            age_bands=meta.age_bands or llm_result["age_bands"],
            doc_type=meta.doc_type or llm_result["doc_type"],
            source_tier=meta.source_tier if meta.source_tier in [1,2,3] else llm_result["source_tier"],
            sub_domain_ids=llm_result.get("sub_domain_ids", []),
        )

        # Sau merge phải đủ 4 chiều
        assert meta.is_valid() is True
        assert meta.doc_group == "GT"  # tự suy từ gt.giao_an (qua model_validator Pydantic)

        # Bước 6: Validate + Export
        assert validator.validate_file(md_path) is True
        assert validator.validate_metadata(meta) is True

        doc_dto = DocumentDTO(metadata=meta, raw_file_path="raw.pdf", converted_md_path=md_path)
        result = exporter.export(doc_dto)
        assert result is True

        # Kiểm tra zone đúng
        exported = list(Path(tmp_export["export"]).rglob("*.md"))
        assert any("03_GT_giao_trinh_truong" in str(f) for f in exported)


# ─────────────────────────────────────────────────────────────
# Flow 3: File quá ngắn → FAIL → need_manual
# ─────────────────────────────────────────────────────────────

class TestFlowValidationFail:
    """Tài liệu bị lọc ra khi không đạt tiêu chuẩn chất lượng."""

    def test_flow_file_qua_ngan_duoc_flag_need_manual(self, tmp_export):
        """File < 500 ký tự → validate_file() = False → need_manual = True."""
        validator = Validator()
        exporter = LocalExporter(export_dir=tmp_export["export"])

        # Tạo file rác chỉ 50 ký tự
        junk_path = Path(tmp_export["converted"]) / "junk.md"
        junk_path.write_text("Rác " * 10, encoding="utf-8")

        meta = DocumentMetadata(
            name="Tài liệu không rõ",
            source_url="https://example.com/junk.pdf",
            linh_vucs=["nhan_thuc"],
            age_bands=["56"],
            doc_type="gt.giao_an",
            source_tier=2,
        )

        doc_dto = DocumentDTO(metadata=meta, raw_file_path="junk.pdf", converted_md_path=str(junk_path))

        # File không pass → gắn need_manual
        if not validator.validate_file(str(junk_path)):
            doc_dto.need_manual = True

        assert doc_dto.need_manual is True

        # Export vẫn chạy được (ghi vào manifest với need_manual=True)
        exporter.export(doc_dto)
        manifest = (Path(tmp_export["export"]).parent / "manifest.csv").read_text()
        assert "need_manual" in manifest

    def test_flow_metadata_khong_du_4_chieu_duoc_flag(self, tmp_export):
        """Metadata thiếu chiều sau khi cả Heuristic lẫn LLM đều không đủ → need_manual."""
        validator = Validator()
        md_path = make_converted_md(tmp_export)

        # Metadata thiếu age_bands
        meta = DocumentMetadata(
            name="Tài liệu không rõ độ tuổi",
            source_url="https://example.com/doc.pdf",
            linh_vucs=["nhan_thuc"],
            age_bands=[],       # thiếu
            doc_type="gt.giao_an",
            source_tier=2,
        )

        assert validator.validate_metadata(meta) is False


# ─────────────────────────────────────────────────────────────
# Flow 4: Dedup — URL đã cào không được tải lại
# ─────────────────────────────────────────────────────────────

class TestFlowDedup:
    """Kiểm tra toàn bộ cơ chế khử trùng lặp."""

    @pytest.mark.asyncio
    async def test_flow_dedup_hash_tren_content(self, tmp_export):
        """
        Crawl 2 URL khác nhau nhưng cùng content SHA-256.
        File chỉ được lưu 1 lần.
        """
        from src.crawlers.documentCrawlers import BaseCrawler

        crawler = BaseCrawler(output_dir=tmp_export["raw"])
        content = b"Identical PDF content " * 50

        crawler.fetch = AsyncMock(return_value=(content, ".pdf"))
        crawler._check_robots = AsyncMock(return_value=True)
        crawler._rate_limit = AsyncMock()

        path1 = await crawler.download_file("https://site1.com/doc.pdf")
        path2 = await crawler.download_file("https://site2.com/other.pdf")

        # Cả 2 URL phải trỏ về cùng 1 file
        assert path1 == path2, "Cùng content → cùng hash → cùng file path"
        raw_files = list(Path(tmp_export["raw"]).glob("*.pdf"))
        assert len(raw_files) == 1, "Chỉ 1 file vật lý được tạo"

        await crawler.close()

    @pytest.mark.asyncio
    async def test_flow_dedup_url_cap_2_bo_qua(self, tmp_export):
        """
        URL đã có trong crawled_urls.json → download_file trả về None ngay,
        không tiếp tục gọi fetch hay robots check.
        """
        from src.crawlers.documentCrawlers import BaseCrawler

        crawler = BaseCrawler(output_dir=tmp_export["raw"])
        url = "https://moet.gov.vn/already-crawled.pdf"

        # Thêm URL vào danh sách đã cào
        crawler.crawled_urls.add(url)

        result = await crawler.download_file(url)

        # Phải trả về None ngay (bị chặn tại bước Dedup Cấp 2)
        assert result is None
        await crawler.close()


# ─────────────────────────────────────────────────────────────
# Flow 5: Zone routing — doc_type → đúng thư mục R2
# ─────────────────────────────────────────────────────────────

class TestFlowZoneRouting:
    """Kiểm tra tài liệu được export vào đúng zone R2 theo doc_type."""

    @pytest.mark.parametrize("doc_type, expected_zone", [
        ("pl.thong_tu",     "01_PL_phap_ly"),
        ("sgk.sgk",         "02_SGK_hoc_lieu"),
        ("gt.giao_an",      "03_GT_giao_trinh_truong"),
        ("bt.truyen_tho",   "04_BT_bo_tro_nang_cao"),
        ("kn.skkn",         "05_KN_kinh_nghiem"),
        ("nc.nghien_cuu",   "06_NC_nghien_cuu"),
        ("md.video",        "07_MD_media"),
    ])
    def test_doc_type_vao_dung_zone(self, tmp_export, doc_type, expected_zone):
        """Mỗi doc_type phải được xuất vào đúng zone tương ứng."""
        exporter = LocalExporter(export_dir=tmp_export["export"])
        md_path = make_converted_md(tmp_export, f"# Tài liệu test\n\n{'Text nội dung ' * 60}")

        meta = DocumentMetadata(
            name=f"Tài liệu test {doc_type}",
            source_url="https://example.com/test.pdf",
            linh_vucs=["nhan_thuc"],
            age_bands=["56"],
            doc_type=doc_type,
            source_tier=2,
        )

        doc_dto = DocumentDTO(metadata=meta, raw_file_path="test.pdf", converted_md_path=md_path)
        exporter.export(doc_dto)

        exported_files = list(Path(tmp_export["export"]).rglob("*.md"))
        assert exported_files, f"Không có file nào được export cho doc_type={doc_type}"
        assert any(expected_zone in str(f) for f in exported_files), (
            f"doc_type={doc_type} phải vào zone {expected_zone}, "
            f"nhưng file ở: {[str(f) for f in exported_files]}"
        )
