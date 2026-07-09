"""
tests/test_models.py — Unit test cho Pydantic models.

Kiểm tra:
- DocumentMetadata: auto-infer doc_group, is_valid()
- DocumentDTO: to_markdown() sinh đúng frontmatter YAML
"""
import pytest
from src.models import DocumentMetadata, DocumentDTO


class TestDocumentMetadataAutoInference:
    """Auto-infer doc_group từ doc_type qua @model_validator."""

    def test_doc_group_tu_dong_suy_khi_co_doc_type(self):
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            doc_type="sgk.sgk"
        )
        assert meta.doc_group == "SGK"

    def test_doc_group_tu_dong_suy_pl(self):
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            doc_type="pl.thong_tu"
        )
        assert meta.doc_group == "PL"

    def test_doc_group_tu_dong_suy_kn(self):
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            doc_type="kn.skkn"
        )
        assert meta.doc_group == "KN"

    def test_doc_group_tu_dong_suy_bt(self):
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            doc_type="bt.truyen_tho"
        )
        assert meta.doc_group == "BT"

    def test_doc_group_tu_dong_suy_gt(self):
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            doc_type="gt.giao_an"
        )
        assert meta.doc_group == "GT"

    def test_doc_group_khong_ghi_de_khi_da_co(self):
        """doc_group đã được set tay thì không bị ghi đè."""
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            doc_type="sgk.sgk",
            doc_group="CUSTOM",
        )
        assert meta.doc_group == "CUSTOM"

    def test_doc_group_rong_khi_khong_co_doc_type(self):
        meta = DocumentMetadata(name="Test", source_url="https://example.com")
        assert meta.doc_group == ""


class TestDocumentMetadataIsValid:
    """is_valid() — kiểm tra đủ 4 chiều bắt buộc."""

    def test_du_4_chieu_tra_ve_true(self):
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            linh_vucs=["nhan_thuc"],
            age_bands=["56"],
            doc_type="gt.giao_an",
            source_tier=2,
        )
        assert meta.is_valid() is True

    def test_thieu_linh_vuc_tra_ve_false(self):
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            linh_vucs=[],
            age_bands=["56"],
            doc_type="gt.giao_an",
            source_tier=2,
        )
        assert meta.is_valid() is False

    def test_thieu_age_band_tra_ve_false(self):
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            linh_vucs=["nhan_thuc"],
            age_bands=[],
            doc_type="gt.giao_an",
            source_tier=2,
        )
        assert meta.is_valid() is False

    def test_thieu_doc_type_tra_ve_false(self):
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            linh_vucs=["nhan_thuc"],
            age_bands=["56"],
            doc_type="",
            source_tier=2,
        )
        assert meta.is_valid() is False

    def test_source_tier_0_tra_ve_false(self):
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            linh_vucs=["nhan_thuc"],
            age_bands=["56"],
            doc_type="gt.giao_an",
            source_tier=0,
        )
        assert meta.is_valid() is False

    def test_source_tier_4_tra_ve_false(self):
        meta = DocumentMetadata(
            name="Test", source_url="https://example.com",
            linh_vucs=["nhan_thuc"],
            age_bands=["56"],
            doc_type="gt.giao_an",
            source_tier=4,
        )
        assert meta.is_valid() is False


class TestDocumentDTOToMarkdown:
    """to_markdown() phải sinh frontmatter YAML hợp lệ."""

    def _make_dto(self):
        meta = DocumentMetadata(
            name="Giáo án Toán lớp lá",
            source_url="https://example.com/doc",
            linh_vucs=["nhan_thuc"],
            age_bands=["56"],
            doc_type="gt.giao_an",
            source_tier=2,
        )
        return DocumentDTO(
            metadata=meta,
            raw_file_path="/tmp/raw.pdf",
            converted_md_path="/tmp/converted.md",
        )

    def test_frontmatter_bat_dau_va_ket_thuc_bang_dau_gach(self):
        dto = self._make_dto()
        result = dto.to_markdown("Nội dung test.")
        assert result.startswith("---\n")
        assert "---\n\nNội dung test." in result

    def test_frontmatter_chua_name(self):
        dto = self._make_dto()
        result = dto.to_markdown("Content")
        assert "name:" in result
        assert "Giáo án Toán lớp lá" in result

    def test_frontmatter_chua_source_url(self):
        dto = self._make_dto()
        result = dto.to_markdown("Content")
        assert "source_url:" in result
        assert "https://example.com/doc" in result

    def test_frontmatter_chua_linh_vucs_dang_mang(self):
        dto = self._make_dto()
        result = dto.to_markdown("Content")
        assert "linh_vucs:" in result
        assert "nhan_thuc" in result

    def test_frontmatter_chua_doc_type(self):
        dto = self._make_dto()
        result = dto.to_markdown("Content")
        assert "doc_type:" in result
        assert "gt.giao_an" in result

    def test_noi_dung_xuat_hien_sau_frontmatter(self):
        dto = self._make_dto()
        result = dto.to_markdown("# Tiêu đề bài học")
        lines = result.split("\n")
        # Tìm dòng "---" thứ hai (kết thúc frontmatter)
        close_idx = next(i for i, l in enumerate(lines[1:], 1) if l == "---")
        content_part = "\n".join(lines[close_idx + 1:])
        assert "# Tiêu đề bài học" in content_part
