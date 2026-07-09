"""
tests/test_validator.py — Unit test cho Validator (§ 2.6 trong Plan).

Kiểm tra:
- validate_file: tồn tại, kích thước, độ dài
- validate_metadata: lọc giá trị lạ, kiểm tra đủ 4 chiều
"""
import os
import tempfile
import pytest
from src.enricher.validator import Validator
from src.models import DocumentMetadata


@pytest.fixture
def v():
    return Validator(max_size_mb=5, min_chars=500)


@pytest.fixture
def valid_meta():
    return DocumentMetadata(
        name="Giáo án Toán trẻ 5-6 tuổi",
        source_url="https://example.com/doc",
        linh_vucs=["nhan_thuc"],
        age_bands=["56"],
        doc_type="gt.giao_an",
        source_tier=2,
        sub_domain_ids=["nt.toan"],
    )


# ─────────────────────────────────────────────────────────────
# validate_file
# ─────────────────────────────────────────────────────────────
class TestValidateFile:
    def test_file_hop_le_tra_ve_true(self, v):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("A" * 600)
            path = f.name
        try:
            assert v.validate_file(path) is True
        finally:
            os.unlink(path)

    def test_file_qua_ngan_tra_ve_false(self, v):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False, encoding="utf-8") as f:
            f.write("Rác")  # < 500 ký tự
            path = f.name
        try:
            assert v.validate_file(path) is False
        finally:
            os.unlink(path)

    def test_file_khong_ton_tai_tra_ve_false(self, v):
        assert v.validate_file("/tmp/khong_co_file_nay_xyz.md") is False

    def test_none_tra_ve_false(self, v):
        assert v.validate_file(None) is False

    def test_file_qua_lon_tra_ve_false(self, v):
        """File vượt 5MB phải bị từ chối."""
        v_small = Validator(max_size_mb=1, min_chars=10)
        with tempfile.NamedTemporaryFile(mode="wb", suffix=".md", delete=False) as f:
            f.write(b"X" * (1 * 1024 * 1024 + 1))  # 1MB + 1 byte
            path = f.name
        try:
            assert v_small.validate_file(path) is False
        finally:
            os.unlink(path)


# ─────────────────────────────────────────────────────────────
# validate_metadata — các trường hợp PASS
# ─────────────────────────────────────────────────────────────
class TestValidateMetadataPass:
    def test_metadata_hop_le_tra_ve_true(self, v, valid_meta):
        assert v.validate_metadata(valid_meta) is True

    def test_metadata_nhieu_linh_vuc_van_pass(self, v):
        meta = DocumentMetadata(
            name="Tích hợp Toán + Tạo hình",
            source_url="https://example.com/doc",
            linh_vucs=["nhan_thuc", "tham_my"],
            age_bands=["45", "56"],
            doc_type="gt.giao_an",
            source_tier=2,
        )
        assert v.validate_metadata(meta) is True

    def test_source_tier_3_pass(self, v):
        meta = DocumentMetadata(
            name="Thông tư Bộ GD",
            source_url="https://moet.gov.vn/doc",
            linh_vucs=["ngon_ngu"],
            age_bands=["56"],
            doc_type="pl.thong_tu",
            source_tier=3,
        )
        assert v.validate_metadata(meta) is True


# ─────────────────────────────────────────────────────────────
# validate_metadata — lọc giá trị lạ
# ─────────────────────────────────────────────────────────────
class TestValidateMetadataFilter:
    def test_linh_vuc_la_bi_loc_bo(self, v):
        meta = DocumentMetadata(
            name="Test doc",
            source_url="https://example.com/doc",
            linh_vucs=["nhan_thuc", "khong_ton_tai"],
            age_bands=["56"],
            doc_type="gt.giao_an",
            source_tier=2,
        )
        v.validate_metadata(meta)
        assert "khong_ton_tai" not in meta.linh_vucs
        assert "nhan_thuc" in meta.linh_vucs

    def test_age_band_la_bi_loc_bo(self, v):
        meta = DocumentMetadata(
            name="Test doc",
            source_url="https://example.com/doc",
            linh_vucs=["nhan_thuc"],
            age_bands=["56", "999"],
            doc_type="gt.giao_an",
            source_tier=2,
        )
        v.validate_metadata(meta)
        assert "999" not in meta.age_bands
        assert "56" in meta.age_bands

    def test_doc_type_la_bi_gan_khac(self, v):
        meta = DocumentMetadata(
            name="Test doc",
            source_url="https://example.com/doc",
            linh_vucs=["nhan_thuc"],
            age_bands=["56"],
            doc_type="loai_tu_che",
            source_tier=2,
        )
        v.validate_metadata(meta)
        assert meta.doc_type == "khac"

    def test_sub_domain_la_bi_loc_bo(self, v):
        meta = DocumentMetadata(
            name="Test doc",
            source_url="https://example.com/doc",
            linh_vucs=["nhan_thuc"],
            age_bands=["56"],
            doc_type="gt.giao_an",
            source_tier=2,
            sub_domain_ids=["nt.toan", "abc.xyz_invalid"],
        )
        v.validate_metadata(meta)
        assert "abc.xyz_invalid" not in meta.sub_domain_ids
        assert "nt.toan" in meta.sub_domain_ids


# ─────────────────────────────────────────────────────────────
# validate_metadata — các trường hợp FAIL (thiếu 4 chiều)
# ─────────────────────────────────────────────────────────────
class TestValidateMetadataFail:
    def test_thieu_linh_vuc_tra_ve_false(self, v):
        meta = DocumentMetadata(
            name="Test doc",
            source_url="https://example.com/doc",
            linh_vucs=[],          # thiếu
            age_bands=["56"],
            doc_type="gt.giao_an",
            source_tier=2,
        )
        assert v.validate_metadata(meta) is False

    def test_thieu_age_band_tra_ve_false(self, v):
        meta = DocumentMetadata(
            name="Test doc",
            source_url="https://example.com/doc",
            linh_vucs=["nhan_thuc"],
            age_bands=[],          # thiếu
            doc_type="gt.giao_an",
            source_tier=2,
        )
        assert v.validate_metadata(meta) is False

    def test_thieu_doc_type_tra_ve_false(self, v):
        meta = DocumentMetadata(
            name="Test doc",
            source_url="https://example.com/doc",
            linh_vucs=["nhan_thuc"],
            age_bands=["56"],
            doc_type="",           # thiếu
            source_tier=2,
        )
        assert v.validate_metadata(meta) is False

    def test_source_tier_sai_tra_ve_false(self, v):
        meta = DocumentMetadata(
            name="Test doc",
            source_url="https://example.com/doc",
            linh_vucs=["nhan_thuc"],
            age_bands=["56"],
            doc_type="gt.giao_an",
            source_tier=0,         # sai (phải là 1, 2, hoặc 3)
        )
        assert v.validate_metadata(meta) is False

    def test_tat_ca_linh_vuc_la_bi_loc_thi_fail(self, v):
        """Nếu tất cả linh_vuc đều lạ → bị lọc sạch → fail."""
        meta = DocumentMetadata(
            name="Test doc",
            source_url="https://example.com/doc",
            linh_vucs=["abc", "xyz"],
            age_bands=["56"],
            doc_type="gt.giao_an",
            source_tier=2,
        )
        assert v.validate_metadata(meta) is False
        assert meta.linh_vucs == []
