"""
tests/test_heuristic_enricher.py — Unit test cho HeuristicEnricher (Bảng 5.6).

Mỗi test case kiểm tra 1 rule trong bảng quy đổi để đảm bảo
heuristic suy đúng metadata từ tên tài liệu + URL domain.
"""
import pytest
from src.enricher.heuristicEnricher import HeuristicEnricher


@pytest.fixture
def h():
    return HeuristicEnricher()


# ─────────────────────────────────────────────────────────────
# Nhận thức
# ─────────────────────────────────────────────────────────────
class TestNhanThuc:
    def test_toan_suy_nhan_thuc(self, h):
        r = h.apply_rules("Làm quen với Toán cho trẻ 4-5 tuổi", "https://example.com/doc")
        assert "nhan_thuc" in r.get("linh_vucs", [])
        assert "nt.toan" in r.get("sub_domain_ids", [])

    def test_so_luong_suy_nhan_thuc(self, h):
        r = h.apply_rules("Nhận biết số lượng và chữ số", "https://example.com/doc")
        assert "nhan_thuc" in r.get("linh_vucs", [])

    def test_kpkh_suy_nhan_thuc(self, h):
        r = h.apply_rules("Khám phá khoa học tự nhiên mầm non", "https://example.com/doc")
        assert "nhan_thuc" in r.get("linh_vucs", [])
        assert "nt.kpkh" in r.get("sub_domain_ids", [])

    def test_kpxh_suy_nhan_thuc(self, h):
        r = h.apply_rules("Khám phá xã hội nghề nghiệp cho trẻ 5-6 tuổi", "https://example.com/doc")
        assert "nhan_thuc" in r.get("linh_vucs", [])
        assert "nt.kpxh" in r.get("sub_domain_ids", [])


# ─────────────────────────────────────────────────────────────
# Ngôn ngữ
# ─────────────────────────────────────────────────────────────
class TestNgonNgu:
    def test_chu_cai_suy_ngon_ngu_doc_viet(self, h):
        r = h.apply_rules("Làm quen chữ cái A B C trẻ 5 tuổi", "https://example.com/doc")
        assert "ngon_ngu" in r.get("linh_vucs", [])
        assert "nn.doc_viet" in r.get("sub_domain_ids", [])

    def test_ke_chuyen_suy_ngon_ngu_van_hoc(self, h):
        r = h.apply_rules("Kể chuyện Thỏ và Rùa cho trẻ mầm non", "https://example.com/doc")
        assert "ngon_ngu" in r.get("linh_vucs", [])
        assert "nn.van_hoc" in r.get("sub_domain_ids", [])

    def test_ke_chuyen_default_doctype_truyen_tho(self, h):
        r = h.apply_rules("Truyện cổ tích Cô bé quàng khăn đỏ", "https://example.com/doc")
        assert r.get("doc_type") == "bt.truyen_tho"

    def test_phat_trien_ngon_ngu_suy_nghe_noi(self, h):
        r = h.apply_rules("Phát triển ngôn ngữ nghe nói trẻ 4 tuổi", "https://example.com/doc")
        assert "ngon_ngu" in r.get("linh_vucs", [])
        assert "nn.nghe_noi" in r.get("sub_domain_ids", [])


# ─────────────────────────────────────────────────────────────
# Thẩm mỹ
# ─────────────────────────────────────────────────────────────
class TestThamMy:
    def test_tao_hinh_suy_tham_my(self, h):
        r = h.apply_rules("Tạo hình con vật từ đất nặn", "https://example.com/doc")
        assert "tham_my" in r.get("linh_vucs", [])
        assert "tm.tao_hinh" in r.get("sub_domain_ids", [])

    def test_ve_suy_tham_my(self, h):
        r = h.apply_rules("Vẽ tranh phong cảnh cho trẻ 5 tuổi", "https://example.com/doc")
        assert "tham_my" in r.get("linh_vucs", [])

    def test_nan_cat_dan_suy_tao_hinh(self, h):
        r = h.apply_rules("Bài học nặn, cắt, dán con bướm từ giấy", "https://example.com/doc")
        assert "tham_my" in r.get("linh_vucs", [])
        assert "tm.tao_hinh" in r.get("sub_domain_ids", [])

    def test_am_nhac_suy_tham_my(self, h):
        r = h.apply_rules("Âm nhạc và hát dân ca cho trẻ mầm non", "https://example.com/doc")
        assert "tham_my" in r.get("linh_vucs", [])
        assert "tm.am_nhac" in r.get("sub_domain_ids", [])


# ─────────────────────────────────────────────────────────────
# Thể chất
# ─────────────────────────────────────────────────────────────
class TestTheChat:
    def test_the_duc_suy_the_chat_van_dong(self, h):
        r = h.apply_rules("Thể dục sáng cho trẻ mẫu giáo", "https://example.com/doc")
        assert "the_chat" in r.get("linh_vucs", [])
        assert "tc.van_dong" in r.get("sub_domain_ids", [])

    def test_dinh_duong_suy_the_chat(self, h):
        r = h.apply_rules("Giáo dục dinh dưỡng và vệ sinh cá nhân", "https://example.com/doc")
        assert "the_chat" in r.get("linh_vucs", [])
        assert "tc.dinh_duong" in r.get("sub_domain_ids", [])


# ─────────────────────────────────────────────────────────────
# Tình cảm - Xã hội
# ─────────────────────────────────────────────────────────────
class TestTinhCamXH:
    def test_ky_nang_song_suy_tinh_cam_xh(self, h):
        r = h.apply_rules("Kỹ năng sống tự phục vụ cho trẻ 3-4 tuổi", "https://example.com/doc")
        assert "tinh_cam_xh" in r.get("linh_vucs", [])
        assert "tx.kn_xh" in r.get("sub_domain_ids", [])

    def test_tinh_cam_suy_tinh_cam_xh(self, h):
        r = h.apply_rules("Phát triển tình cảm và cảm xúc trẻ mầm non", "https://example.com/doc")
        assert "tinh_cam_xh" in r.get("linh_vucs", [])


# ─────────────────────────────────────────────────────────────
# Doc type rules
# ─────────────────────────────────────────────────────────────
class TestDocTypeRules:
    def test_skkn_suy_kn_skkn(self, h):
        r = h.apply_rules("SKKN Nâng cao chất lượng giảng dạy mầm non", "https://example.com/doc")
        assert r.get("doc_type") == "kn.skkn"

    def test_sang_kien_kinh_nghiem_suy_skkn(self, h):
        r = h.apply_rules("Sáng kiến kinh nghiệm tổ chức hoạt động ngoại khóa", "https://example.com/doc")
        assert r.get("doc_type") == "kn.skkn"

    def test_kinh_nghiem_suy_kn_kinh_nghiem(self, h):
        r = h.apply_rules("Kinh nghiệm dạy trẻ tự lập", "https://example.com/doc")
        assert r.get("doc_type") == "kn.kinh_nghiem"

    def test_giao_an_suy_gt_giao_an(self, h):
        r = h.apply_rules("Giáo án phát triển thể chất lớp nhà trẻ", "https://example.com/doc")
        assert r.get("doc_type") == "gt.giao_an"

    def test_sgk_suy_sgk_sgk(self, h):
        r = h.apply_rules("Sách giáo khoa Toán mầm non lớp 1", "https://example.com/doc")
        assert r.get("doc_type") == "sgk.sgk"
        assert r.get("source_tier") == 2

    def test_bai_tap_suy_sgk_sbt(self, h):
        r = h.apply_rules("Vở bài tập chữ cái tiếng Việt mầm non", "https://example.com/doc")
        assert r.get("doc_type") == "sgk.sbt"

    def test_nang_cao_suy_bt_nang_cao(self, h):
        r = h.apply_rules("Bài tập nâng cao Toán dành cho mầm non lớp lá", "https://example.com/doc")
        assert r.get("doc_type") == "bt.nang_cao"

    def test_thong_tu_suy_pl_thong_tu(self, h):
        r = h.apply_rules("Thông tư 17/2009/TT-BGDDT", "https://example.com/doc")
        assert r.get("doc_type") == "pl.thong_tu"
        assert r.get("source_tier") == 3


# ─────────────────────────────────────────────────────────────
# Age band rules
# ─────────────────────────────────────────────────────────────
class TestAgeBandRules:
    def test_nha_tre_suy_age_34(self, h):
        r = h.apply_rules("Giáo án nhà trẻ 3-4 tuổi", "https://example.com/doc")
        assert "34" in r.get("age_bands", [])

    def test_4_tuoi_suy_age_45(self, h):
        r = h.apply_rules("Tài liệu phát triển cho trẻ 4 tuổi", "https://example.com/doc")
        assert "45" in r.get("age_bands", [])

    def test_lop_la_suy_age_56(self, h):
        r = h.apply_rules("Giáo án Toán lớp lá", "https://example.com/doc")
        assert "56" in r.get("age_bands", [])

    def test_5_6_suy_age_56(self, h):
        r = h.apply_rules("Làm quen chữ cái trẻ 5-6 tuổi", "https://example.com/doc")
        assert "56" in r.get("age_bands", [])

    def test_lop_1_suy_age_g1(self, h):
        r = h.apply_rules("Sách giáo khoa Tiếng Việt mầm non lớp 1", "https://example.com/doc")
        assert "g1_hk1" in r.get("age_bands", [])


# ─────────────────────────────────────────────────────────────
# Domain rules
# ─────────────────────────────────────────────────────────────
class TestDomainRules:
    def test_moet_suy_tier_3_va_thong_tu(self, h):
        r = h.apply_rules("Document", "https://moet.gov.vn/vbdb/thong-tu-51.pdf")
        assert r.get("source_tier") == 3
        assert r.get("doc_type") == "pl.thong_tu"

    def test_hoc10_suy_tier_2(self, h):
        r = h.apply_rules("SGK Toán", "https://hoc10.vn/sgk-toan-lop1")
        assert r.get("source_tier") == 2

    def test_giaovienmamnon_suy_tier_1(self, h):
        r = h.apply_rules("Mẹo dạy trẻ", "https://giaovienmamnon.com/meo-day")
        assert r.get("source_tier") == 1


# ─────────────────────────────────────────────────────────────
# Doc group auto-inference
# ─────────────────────────────────────────────────────────────
class TestDocGroupInference:
    def test_doc_group_tu_dong_suy_tu_doc_type(self, h):
        r = h.apply_rules("Giáo án hát múa trẻ 4 tuổi", "https://example.com/doc")
        assert r.get("doc_group") == "GT"  # gt.giao_an → GT

    def test_truyen_tho_suy_doc_group_BT(self, h):
        r = h.apply_rules("Truyện tranh Ba Chú Heo Con", "https://example.com/doc")
        assert r.get("doc_group") == "BT"  # bt.truyen_tho → BT

    def test_thong_tu_suy_doc_group_PL(self, h):
        r = h.apply_rules("Thông tư 01/2021 Bộ GD", "https://moet.gov.vn/vbdb/tt01")
        assert r.get("doc_group") == "PL"

    def test_skkn_suy_doc_group_KN(self, h):
        r = h.apply_rules("SKKN Kinh nghiệm dạy tạo hình", "https://mamnon.com/skkn")
        assert r.get("doc_group") == "KN"


# ─────────────────────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_ten_hash_khong_co_keyword_tra_ve_rong(self, h):
        """File từ URL trực tiếp (tên là SHA256) không nên suy được gì từ tên."""
        r = h.apply_rules("853d3f8b2d8eee560985225759e784ef865a0b1c6b41892af53ad9ac1f9f397b", "https://example.com/doc")
        assert r.get("linh_vucs", []) == []
        assert r.get("age_bands", []) == []

    def test_khong_trung_lap_linh_vuc(self, h):
        """Tài liệu có nhiều keyword cùng lĩnh vực → không bị trùng lặp."""
        r = h.apply_rules("Truyện thơ đồng dao kể chuyện văn học", "https://example.com/doc")
        linh_vucs = r.get("linh_vucs", [])
        assert len(linh_vucs) == len(set(linh_vucs)), "Bị trùng lặp linh_vucs"

    def test_da_linh_vuc_duoc_phep(self, h):
        """Tài liệu bao trùm nhiều lĩnh vực được phép có nhiều linh_vuc."""
        r = h.apply_rules("Toán kết hợp âm nhạc tạo hình sáng tạo", "https://example.com/doc")
        assert len(r.get("linh_vucs", [])) >= 2
