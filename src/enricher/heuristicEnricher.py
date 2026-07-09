"""
heuristicEnricher.py — Suy metadata từ URL + tên file bằng luật cứng.

Áp dụng Bảng quy đổi 5.6 trong tài liệu DevOps:
08-07-2026__dev-ops__plan-he-thong-cao-tai-lieu-tham-khao.md § 5.6
"""
from typing import Dict, Any
from urllib.parse import urlparse
# pyrefly: ignore [missing-import]
from loguru import logger

from src.taxonomy import (
    DOMAIN_TIER_MAP,
    DOMAIN_DOCTYPE_MAP,
    DOC_TYPE_TO_GROUP,
)


class HeuristicEnricher:
    """Suy luận metadata tài liệu từ URL và tên file bằng luật cứng."""

    def apply_rules(self, name: str, url: str) -> Dict[str, Any]:
        """Áp dụng bảng quy đổi 5.6 để suy 4 chiều phân loại.

        Args:
            name: Tên tài liệu (file stem hoặc tiêu đề trang).
            url: URL gốc của tài liệu.

        Returns:
            Dict metadata (chỉ chứa các key có giá trị khác rỗng).
        """
        name_lower = name.lower()
        domain = urlparse(url).netloc

        metadata: Dict[str, Any] = {
            "linh_vucs": [],
            "age_bands": [],
            "doc_type": "",
            "doc_group": "",
            "sub_domain_ids": [],
            "source_tier": 0,
        }

        # ── 1. Suy từ Domain ─────────────────────────────────────────────
        for domain_key, tier in DOMAIN_TIER_MAP.items():
            if domain_key in domain:
                metadata["source_tier"] = tier
                break

        for domain_key, dtype in DOMAIN_DOCTYPE_MAP.items():
            if domain_key in domain:
                metadata["doc_type"] = dtype
                break

        # ── 2. Suy Lĩnh vực + Sub-domain từ Tên ─────────────────────────

        # Nhận thức — Toán
        if any(kw in name_lower for kw in ["toán", "làm quen toán", "số lượng", "hình học"]):
            self._add_linh_vuc(metadata, "nhan_thuc", "nt.toan")

        # Nhận thức — Khám phá Khoa học
        if any(kw in name_lower for kw in ["khám phá khoa học", "kpkh", "khoa học tự nhiên",
                                             "thí nghiệm", "động vật", "thực vật"]):
            self._add_linh_vuc(metadata, "nhan_thuc", "nt.kpkh")

        # Nhận thức — Khám phá xã hội
        if any(kw in name_lower for kw in ["khám phá xã hội", "kpxh", "xã hội", "nghề nghiệp",
                                             "giao thông", "gia đình"]):
            self._add_linh_vuc(metadata, "nhan_thuc", "nt.kpxh")

        # Ngôn ngữ — Đọc, Viết, Chữ cái
        if any(kw in name_lower for kw in ["chữ cái", "tập đọc", "tập viết", "làm quen chữ",
                                             "đọc viết", "tiếng việt", "âm vần", "bảng chữ"]):
            self._add_linh_vuc(metadata, "ngon_ngu", "nn.doc_viet")

        # Ngôn ngữ — Nghe, Nói
        if any(kw in name_lower for kw in ["nghe nói", "nghe-nói", "phát triển ngôn ngữ",
                                             "giao tiếp", "hội thoại"]):
            self._add_linh_vuc(metadata, "ngon_ngu", "nn.nghe_noi")

        # Ngôn ngữ — Văn học
        if any(kw in name_lower for kw in ["kể chuyện", "truyện", "thơ", "đồng dao",
                                             "văn học", "câu chuyện", "truyện tranh"]):
            self._add_linh_vuc(metadata, "ngon_ngu", "nn.van_hoc")
            if not metadata["doc_type"]:
                metadata["doc_type"] = "bt.truyen_tho"

        # Thẩm mỹ — Tạo hình
        if any(kw in name_lower for kw in ["tạo hình", "vẽ", "nặn", "cắt", "dán",
                                             "mỹ thuật", "tô màu", "nghệ thuật tạo hình"]):
            self._add_linh_vuc(metadata, "tham_my", "tm.tao_hinh")

        # Thẩm mỹ — Âm nhạc
        if any(kw in name_lower for kw in ["âm nhạc", "hát", "múa", "nhạc", "vận động âm nhạc",
                                             "nghe nhạc", "bài hát"]):
            self._add_linh_vuc(metadata, "tham_my", "tm.am_nhac")

        # Thể chất — Vận động
        if any(kw in name_lower for kw in ["thể dục", "vận động", "thể chất", "thể thao",
                                             "rèn luyện thân thể", "phát triển thể lực"]):
            self._add_linh_vuc(metadata, "the_chat", "tc.van_dong")

        # Thể chất — Dinh dưỡng
        if any(kw in name_lower for kw in ["dinh dưỡng", "ăn uống", "thực phẩm", "vệ sinh",
                                             "an toàn thực phẩm", "sức khoẻ", "sức khỏe"]):
            self._add_linh_vuc(metadata, "the_chat", "tc.dinh_duong")

        # Tình cảm - Xã hội — Tình cảm
        if any(kw in name_lower for kw in ["tình cảm", "cảm xúc", "yêu thương", "thân thiện"]):
            self._add_linh_vuc(metadata, "tinh_cam_xh", "tx.tinh_cam")

        # Tình cảm - Xã hội — Kỹ năng xã hội
        if any(kw in name_lower for kw in ["kỹ năng sống", "kỹ năng xã hội", "ứng xử",
                                             "phép lịch sự", "tự phục vụ"]):
            self._add_linh_vuc(metadata, "tinh_cam_xh", "tx.kn_xh")

        # ── 3. Suy doc_type từ Tên ───────────────────────────────────────

        if any(kw in name_lower for kw in ["thông tư", "quyết định", "nghị định"]):
            metadata["doc_type"] = "pl.thong_tu"
            metadata["source_tier"] = max(metadata["source_tier"], 3)

        elif any(kw in name_lower for kw in ["chương trình gdmn", "chương trình giáo dục mầm non",
                                               "vbhn", "chuẩn phát triển"]):
            metadata["doc_type"] = "pl.chuong_trinh"
            metadata["source_tier"] = max(metadata["source_tier"], 3)

        elif any(kw in name_lower for kw in ["sáng kiến kinh nghiệm", "skkn"]):
            metadata["doc_type"] = "kn.skkn"
            metadata["source_tier"] = max(metadata["source_tier"], 1)

        elif any(kw in name_lower for kw in ["kinh nghiệm", "mẹo dạy", "mẹo"]):
            if not metadata["doc_type"]:
                metadata["doc_type"] = "kn.kinh_nghiem"
                metadata["source_tier"] = max(metadata["source_tier"], 1)

        elif any(kw in name_lower for kw in ["dự giờ", "đánh giá tiết dạy"]):
            metadata["doc_type"] = "kn.du_gio"
            metadata["source_tier"] = max(metadata["source_tier"], 1)

        elif "giáo án" in name_lower:
            if not metadata["doc_type"]:
                metadata["doc_type"] = "gt.giao_an"
                metadata["source_tier"] = max(metadata["source_tier"], 2)

        elif any(kw in name_lower for kw in ["sgk", "sách giáo khoa"]):
            if not metadata["doc_type"]:
                metadata["doc_type"] = "sgk.sgk"
                metadata["source_tier"] = max(metadata["source_tier"], 2)

        elif any(kw in name_lower for kw in ["nâng cao", "bài tập nâng cao"]):
            if not metadata["doc_type"]:
                metadata["doc_type"] = "bt.nang_cao"

        elif any(kw in name_lower for kw in ["sách bài tập", "vở bài tập", "bài tập"]):
            if not metadata["doc_type"]:
                metadata["doc_type"] = "sgk.sbt"
                metadata["source_tier"] = max(metadata["source_tier"], 2)

        elif any(kw in name_lower for kw in ["sách giáo viên", "hướng dẫn giáo viên"]):
            if not metadata["doc_type"]:
                metadata["doc_type"] = "sgk.sgv"
                metadata["source_tier"] = max(metadata["source_tier"], 2)

        elif any(kw in name_lower for kw in ["bổ trợ", "tài liệu bổ trợ"]):
            if not metadata["doc_type"]:
                metadata["doc_type"] = "bt.bo_tro"

        elif any(kw in name_lower for kw in ["kỹ năng", "kỹ năng mềm"]):
            if not metadata["doc_type"]:
                metadata["doc_type"] = "bt.ky_nang"

        elif any(kw in name_lower for kw in ["nghiên cứu", "luận văn", "luận án"]):
            if not metadata["doc_type"]:
                metadata["doc_type"] = "nc.nghien_cuu"

        elif any(kw in name_lower for kw in ["bài báo", "tạp chí"]):
            if not metadata["doc_type"]:
                metadata["doc_type"] = "nc.bai_bao"

        elif any(kw in name_lower for kw in ["tập huấn", "bồi dưỡng giáo viên"]):
            if not metadata["doc_type"]:
                metadata["doc_type"] = "nc.tap_huan"

        # ── 4. Suy Age Band từ Tên ──────────────────────────────────────
        if any(kw in name_lower for kw in ["3 tuổi", "3-4", "nhà trẻ"]):
            if "34" not in metadata["age_bands"]:
                metadata["age_bands"].append("34")

        if any(kw in name_lower for kw in ["4 tuổi", "4-5"]):
            if "45" not in metadata["age_bands"]:
                metadata["age_bands"].append("45")

        if any(kw in name_lower for kw in ["5 tuổi", "5-6", "lớp lá", "mẫu giáo lớn"]):
            if "56" not in metadata["age_bands"]:
                metadata["age_bands"].append("56")

        if any(kw in name_lower for kw in ["lớp 1", "gdpt", "tiểu học"]):
            if "g1" not in metadata["age_bands"]:
                metadata["age_bands"].append("g1")

        # ── 5. Tự động suy doc_group từ doc_type ─────────────────────────
        if metadata["doc_type"] and not metadata["doc_group"]:
            metadata["doc_group"] = DOC_TYPE_TO_GROUP.get(metadata["doc_type"], "")

        logger.debug(f"Heuristic kết quả cho '{name}': {metadata}")

        # Lọc bỏ các field rỗng / giá trị 0
        return {k: v for k, v in metadata.items() if v}

    # ── Helper ─────────────────────────────────────────────────────────────

    def _add_linh_vuc(self, metadata: Dict[str, Any], linh_vuc: str, sub_domain: str) -> None:
        """Thêm linh_vuc và sub_domain_id nếu chưa có (tránh trùng lặp)."""
        if linh_vuc not in metadata["linh_vucs"]:
            metadata["linh_vucs"].append(linh_vuc)
        if sub_domain not in metadata["sub_domain_ids"]:
            metadata["sub_domain_ids"].append(sub_domain)
