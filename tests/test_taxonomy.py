"""
tests/test_taxonomy.py — Kiểm tra tính toàn vẹn của danh mục chuẩn.
"""
import pytest
from src.taxonomy import (
    VALID_LINH_VUCS,
    VALID_AGE_BANDS,
    VALID_DOC_TYPES,
    VALID_SUB_DOMAIN_IDS,
    VALID_LEVEL_IDS,
    VALID_SOURCE_TIERS,
    DOC_TYPE_TO_GROUP,
    DOC_GROUP_TO_ZONE,
    DOMAIN_TIER_MAP,
    DOMAIN_DOCTYPE_MAP,
)


class TestTaxonomyCompleteness:
    """Kiểm tra số lượng và nội dung các danh mục chuẩn."""

    def test_linh_vucs_co_dung_5_gia_tri(self):
        assert len(VALID_LINH_VUCS) == 5
        assert VALID_LINH_VUCS == {"nhan_thuc", "ngon_ngu", "tham_my", "the_chat", "tinh_cam_xh"}

    def test_age_bands_co_dung_5_gia_tri(self):
        assert len(VALID_AGE_BANDS) == 5
        assert VALID_AGE_BANDS == {"34", "45", "56", "g1_hk1", "g1_hk2"}

    def test_doc_types_co_it_nhat_25_loai(self):
        # 25 loại + 'khac' fallback
        assert len(VALID_DOC_TYPES) >= 25

    def test_doc_types_chua_khac_fallback(self):
        assert "khac" in VALID_DOC_TYPES

    def test_sub_domain_ids_co_dung_12_gia_tri(self):
        assert len(VALID_SUB_DOMAIN_IDS) == 12

    def test_level_ids_co_dung_3_gia_tri(self):
        assert VALID_LEVEL_IDS == {"lv01", "lv02", "lv03"}

    def test_source_tiers_co_dung_3_gia_tri(self):
        assert VALID_SOURCE_TIERS == {1, 2, 3}


class TestDocTypeToGroup:
    """Kiểm tra mapping doc_type → doc_group."""

    def test_pl_types_map_to_PL(self):
        for dt in ["pl.chuong_trinh", "pl.chuan_5t", "pl.thong_tu", "pl.cong_van"]:
            assert DOC_TYPE_TO_GROUP[dt] == "PL", f"{dt} phải map về PL"

    def test_sgk_types_map_to_SGK(self):
        for dt in ["sgk.sgk", "sgk.sbt", "sgk.sgv", "sgk.tap_to"]:
            assert DOC_TYPE_TO_GROUP[dt] == "SGK", f"{dt} phải map về SGK"

    def test_gt_types_map_to_GT(self):
        for dt in ["gt.truong", "gt.quoc_te", "gt.giao_an"]:
            assert DOC_TYPE_TO_GROUP[dt] == "GT", f"{dt} phải map về GT"

    def test_kn_types_map_to_KN(self):
        for dt in ["kn.kinh_nghiem", "kn.skkn", "kn.meo_day", "kn.du_gio"]:
            assert DOC_TYPE_TO_GROUP[dt] == "KN", f"{dt} phải map về KN"

    def test_moi_doc_type_hop_le_deu_co_group(self):
        """Mỗi doc_type trong VALID_DOC_TYPES phải có mapping trong DOC_TYPE_TO_GROUP."""
        for dt in VALID_DOC_TYPES:
            assert dt in DOC_TYPE_TO_GROUP, f"Thiếu mapping cho doc_type: {dt}"

    def test_zone_map_cover_all_groups(self):
        """Mọi doc_group đều phải có zone R2 tương ứng."""
        groups = set(DOC_TYPE_TO_GROUP.values())
        for grp in groups:
            assert grp in DOC_GROUP_TO_ZONE, f"Thiếu zone cho doc_group: {grp}"

    def test_zone_names_bat_dau_bang_so_thu_tu(self):
        zones = [z for z in DOC_GROUP_TO_ZONE.values() if z != "00_Khac"]
        for z in zones:
            assert z[:2].isdigit() or z.startswith("0"), f"Zone sai định dạng: {z}"
