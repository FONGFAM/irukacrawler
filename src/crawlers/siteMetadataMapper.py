"""
siteMetadataMapper.py — Metadata override cho từng nguồn.

Cách tiếp cận tối giản: Map domain → metadata override.
Không cần viết class crawler riêng cho từng site.
BaseCrawler generic + metadata override đủ xử lý 90% trường hợp.

Khi cần xử lý đặc thù (VD: moet.gov.vn cần extract PDF từ trang danh sách),
sẽ phát triển thành crawler chuyên biệt sau.

Nguồn tham chiếu: 08-07-2026__dev-ops__plan-he-thong-cao-tai-lieu-tham-khao.md § 4.1
"""
from typing import Dict, Any, Optional
from urllib.parse import urlparse


def get_metadata_override(url: str) -> Dict[str, Any]:
    """Trả về metadata override cho URL dựa trên domain.

    Args:
        url: URL cần kiểm tra.

    Returns:
        Dict chứa metadata (source_tier, doc_type, ...) hoặc rỗng nếu không có.
    """
    domain = urlparse(url).netloc.lower()

    for site_domain, meta in SITE_METADATA_MAP.items():
        if site_domain in domain:
            return meta

    return {}


def get_site_name(url: str) -> Optional[str]:
    """Lấy tên thân thiện của site từ URL."""
    domain = urlparse(url).netloc.lower()

    for site_domain, info in SITE_INFO.items():
        if site_domain in domain:
            return info["name"]

    return None


# ─────────────────────────────────────────────────────────────
# Bản đồ domain → metadata override
# ─────────────────────────────────────────────────────────────
# Tham chiếu Spec §4.1:
#   Nhóm A — 3⭐ (Bộ GD, Sở GD, Pháp lý)
#   Nhóm B — 2⭐ (SGK, Giáo trình chính thống)
#   Nhóm C — 1–2⭐ (Kinh nghiệm GV, Blog chuyên môn)
#   Nhóm D — 1⭐ (Bổ trợ, Sáng tạo) — chưa implement

SITE_METADATA_MAP: Dict[str, Dict[str, Any]] = {
    # ── Nhóm A: 3⭐ (Bộ GD, Sở GD, Pháp lý) ──────────────────
    "moet.gov.vn": {
        "source_tier": 3,
        "doc_type": "pl.thong_tu",
    },
    "csdl.hcm.edu.vn": {
        "source_tier": 3,
    },
    "hanoi.edu.vn": {
        "source_tier": 3,
    },

    # ── Nhóm B: 2⭐ (SGK, Giáo trình chính thống) ─────────────
    # Spec: hoc10, vietjack, taphuan.csdl, sachmem
    "hoc10.vn": {
        "source_tier": 2,
    },
    "vietjack.com": {
        "source_tier": 2,
    },
    "sachmem.vn": {
        "source_tier": 2,
    },
    "nxbgd.vn": {
        "source_tier": 2,
    },
    "taphuan.csdl.edu.vn": {
        "source_tier": 2,   # §4.1 Nhóm B
        "doc_type": "nc.tap_huan",
    },

    # ── Nhóm C: 1–2⭐ (Kinh nghiệm GV, Blog chuyên môn) ──────
    # Spec: giaovienmamnon, mamnon, kinderart (tiếng Anh)
    "giaovienmamnon.com": {
        "source_tier": 1,
    },
    "mamnon.com": {
        "source_tier": 1,
    },
    "kinderart.com": {
        "source_tier": 1,
    },
    "giaoanmamnon.com": {
        "source_tier": 1,
    },

    # ── Nhóm D: 1⭐ (Bổ trợ, Sáng tạo) — chưa implement ─────
    # Spec: pinterest, teacherspayteachers (FREE), twinkl.com.vn
    # (Bỏ qua trong demo — cần xử lý đặc thù)
}


# ─────────────────────────────────────────────────────────────
# Thông tin site cho Dashboard / Logging
# ─────────────────────────────────────────────────────────────

SITE_INFO: Dict[str, Dict[str, str]] = {
    # Nhóm A
    "moet.gov.vn":           {"name": "Bộ GD-ĐT",        "tier": "3⭐", "group": "A"},
    "csdl.hcm.edu.vn":      {"name": "Sở GD TP.HCM",    "tier": "3⭐", "group": "A"},
    "hanoi.edu.vn":         {"name": "Sở GD Hà Nội",    "tier": "3⭐", "group": "A"},
    # Nhóm B
    "hoc10.vn":             {"name": "Hoc10 (Cánh Diều)","tier": "2⭐", "group": "B"},
    "vietjack.com":         {"name": "VietJack",        "tier": "2⭐", "group": "B"},
    "sachmem.vn":           {"name": "Sách Mềm",        "tier": "2⭐", "group": "B"},
    "nxbgd.vn":             {"name": "NXB Giáo Dục",    "tier": "2⭐", "group": "B"},
    "taphuan.csdl.edu.vn":  {"name": "Tập huấn Bộ GD",  "tier": "2⭐", "group": "B"},
    # Nhóm C
    "giaovienmamnon.com":   {"name": "Giáo Viên MN",    "tier": "1–2⭐", "group": "C"},
    "mamnon.com":           {"name": "Mầm Non.com",     "tier": "1–2⭐", "group": "C"},
    "kinderart.com":        {"name": "KinderArt",       "tier": "1–2⭐", "group": "C"},
    "giaoanmamnon.com":     {"name": "Giáo Án MN",      "tier": "1⭐", "group": "D"},
}