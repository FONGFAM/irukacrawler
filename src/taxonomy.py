"""
taxonomy.py — Chuẩn phân loại IruKa (Single Source of Truth)

Mọi module trong hệ thống (Heuristic, Validator, LLM Enricher, Exporter)
đều PHẢI dùng các hằng số từ file này thay vì hardcode.

Nguồn tham chiếu: 08-07-2026__dev-ops__plan-he-thong-cao-tai-lieu-tham-khao.md § 5
"""
from typing import Dict, Set

# ─────────────────────────────────────────────────────────────
# 5.1 · 4 chiều bắt buộc
# ─────────────────────────────────────────────────────────────

VALID_LINH_VUCS: Set[str] = {
    "nhan_thuc",
    "ngon_ngu",
    "tham_my",
    "the_chat",
    "tinh_cam_xh",
}

VALID_AGE_BANDS: Set[str] = {"34", "45", "56", "g1_hk1", "g1_hk2"}

VALID_SOURCE_TIERS: Set[int] = {1, 2, 3}

# ─────────────────────────────────────────────────────────────
# 5.2 · 25 doc_type chia 7 nhóm
# ─────────────────────────────────────────────────────────────

VALID_DOC_TYPES: Set[str] = {
    # PL — Pháp lý & Chuẩn
    "pl.chuong_trinh", "pl.chuan_5t", "pl.thong_tu", "pl.cong_van",
    # SGK — SGK & Học liệu chính thống
    "sgk.sgk", "sgk.sbt", "sgk.sgv", "sgk.tap_to",
    # GT — Giáo trình & CT trường
    "gt.truong", "gt.quoc_te", "gt.giao_an",
    # BT — Bổ trợ & Nâng cao
    "bt.nang_cao", "bt.bo_tro", "bt.truyen_tho", "bt.ky_nang", "bt.phieu_bai_tap", "bt.tro_choi",
    # KN — Kinh nghiệm & Nội bộ
    "kn.kinh_nghiem", "kn.skkn", "kn.meo_day", "kn.du_gio",
    # NC — Nghiên cứu & Tham khảo
    "nc.nghien_cuu", "nc.bai_bao", "nc.tap_huan", "nc.ct_nuoc_ngoai",
    # MD — Media
    "md.hinh_anh", "md.am_thanh", "md.video",
    # Fallback
    "khac",
}

# Map doc_type → doc_group (tự động suy doc_group)
DOC_TYPE_TO_GROUP: Dict[str, str] = {
    "pl.chuong_trinh": "PL", "pl.chuan_5t": "PL",
    "pl.thong_tu": "PL",    "pl.cong_van": "PL",

    "sgk.sgk": "SGK", "sgk.sbt": "SGK",
    "sgk.sgv": "SGK", "sgk.tap_to": "SGK",

    "gt.truong": "GT", "gt.quoc_te": "GT", "gt.giao_an": "GT",

    "bt.nang_cao": "BT", "bt.bo_tro": "BT",
    "bt.truyen_tho": "BT", "bt.ky_nang": "BT",
    "bt.phieu_bai_tap": "BT", "bt.tro_choi": "BT",

    "kn.kinh_nghiem": "KN", "kn.skkn": "KN",
    "kn.meo_day": "KN",     "kn.du_gio": "KN",

    "nc.nghien_cuu": "NC", "nc.bai_bao": "NC",
    "nc.tap_huan": "NC",   "nc.ct_nuoc_ngoai": "NC",

    "md.hinh_anh": "MD", "md.am_thanh": "MD", "md.video": "MD",

    "khac": "KHAC",
}

# Map doc_group → Zone R2
DOC_GROUP_TO_ZONE: Dict[str, str] = {
    "PL":   "01_PL_phap_ly",
    "SGK":  "02_SGK_hoc_lieu",
    "GT":   "03_GT_giao_trinh_truong",
    "BT":   "04_BT_bo_tro_nang_cao",
    "KN":   "05_KN_kinh_nghiem",
    "NC":   "06_NC_nghien_cuu",
    "MD":   "07_MD_media",
    "KHAC": "00_Khac",
}

# ─────────────────────────────────────────────────────────────
# 5.3 · sub_domain_ids — 12 giá trị
# ─────────────────────────────────────────────────────────────

VALID_SUB_DOMAIN_IDS: Set[str] = {
    # Nhận thức
    "nt.toan", "nt.kpkh", "nt.kpxh",
    # Ngôn ngữ
    "nn.doc_viet", "nn.nghe_noi", "nn.van_hoc",
    # Thẩm mỹ
    "tm.tao_hinh", "tm.am_nhac",
    # Thể chất
    "tc.van_dong", "tc.dinh_duong",
    # Tình cảm-XH
    "tx.tinh_cam", "tx.kn_xh",
}

# ─────────────────────────────────────────────────────────────
# 5.5 · level_ids — 3 giá trị
# ─────────────────────────────────────────────────────────────

VALID_LEVEL_IDS: Set[str] = {"lv01", "lv02", "lv03"}

# ─────────────────────────────────────────────────────────────
# Domain → source_tier (Nhóm A/B/C theo Plan § 4.1)
# ─────────────────────────────────────────────────────────────

DOMAIN_TIER_MAP: Dict[str, int] = {
    # Nhóm A — 3⭐ (Bộ GD, Sở GD)
    "moet.gov.vn": 3,
    "csdl.hcm.edu.vn": 3,
    "hanoi.edu.vn": 3,
    "taphuan.csdl.edu.vn": 3,

    # Nhóm B — 2⭐ (SGK chính thống)
    "hoc10.vn": 2,
    "vietjack.com": 2,
    "sachmem.vn": 2,
    "nxbgd.vn": 2,

    # Nhóm C — 1⭐ (Blog GV, kinh nghiệm)
    "giaovienmamnon.com": 1,
    "mamnon.com": 1,
    "kinderart.com": 1,
    "giaoanmamnon.com": 1,
}

# ─────────────────────────────────────────────────────────────
# Domain → doc_type override (nếu domain xác định rõ loại tài liệu)
# ─────────────────────────────────────────────────────────────

DOMAIN_DOCTYPE_MAP: Dict[str, str] = {
    "moet.gov.vn": "pl.thong_tu",
    "taphuan.csdl.edu.vn": "nc.tap_huan",
}

# ─────────────────────────────────────────────────────────────
# 5.6 · Kỹ năng và Bộ sách (Dùng cho Enrichment Nâng cao)
# ─────────────────────────────────────────────────────────────

VALID_SKILL_IDS: Set[str] = {
    # Toán (nt.toan)
    "math.sk01", "math.sk02", "math.sk03", "math.sk04",
    # Khám phá (nt.kpkh, nt.kpxh)
    "sci.sk01", "sci.sk02", "soc.sk01",
    # Ngôn ngữ (nn.doc_viet, nn.nghe_noi, nn.van_hoc)
    "lit.sk01", "lit.sk02", "lit.sk03",
    # Tạo hình, Âm nhạc
    "art.sk01", "mus.sk01",
    # Thể chất
    "phy.sk01", "phy.sk02",
    # KNXH
    "sel.sk01", "sel.sk02"
}

VALID_SERIES_CODES: Set[str] = {
    "canh-dieu",
    "ket-noi-tri-thuc",
    "chan-troi-sang-tao",
    "cung-hoc-de-phat-trien",
    "vi-su-binh-dang"
}
