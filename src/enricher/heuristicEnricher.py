"""
heuristicEnricher.py — Suy metadata từ URL + tên file bằng luật cứng.

Áp dụng Bảng quy đổi 5.6 trong tài liệu DevOps:
08-07-2026__dev-ops__plan-he-thong-cao-tai-lieu-tham-khao.md § 5.6
"""
from typing import Dict, Any
from urllib.parse import urlparse
import urllib.parse
import unicodedata
import re
# pyrefly: ignore [missing-import]
from loguru import logger

from src.taxonomy import (
    DOMAIN_TIER_MAP,
    DOMAIN_DOCTYPE_MAP,
    DOC_TYPE_TO_GROUP,
)

def remove_accents(input_str: str) -> str:
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    return u"".join([c for c in nfkd_form if not unicodedata.combining(c)]).lower()

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
        url_decoded = urllib.parse.unquote(url).lower().replace("-", " ").replace("_", " ").replace("/", " ")
        name_lower = (name.lower() + " " + url_decoded).strip()
        name_no_accents = remove_accents(name_lower)
        domain = urllib.parse.urlparse(url).netloc

        metadata: Dict[str, Any] = {
            "linh_vucs": [],
            "age_bands": [],
            "doc_type": "",
            "doc_group": "",
            "sub_domain_ids": [],
            "source_tier": 0,
        }

        def has_kw(kws):
            return any(remove_accents(kw) in name_no_accents for kw in kws)

        def has_regex(patterns):
            return any(re.search(p, name_no_accents) for p in patterns)

        # ── 0. MÀNG LỌC PHỦ ĐỊNH (Exclusion Layer) ───────────────────────
        poison_kws_hard = [
            "lớp 2", "lớp 3", "lớp 4", "lớp 5", "lớp 6", "lớp 7", "lớp 8", "lớp 9", "lớp 10", "lớp 11", "lớp 12",
            "tiếng việt 2", "tiếng việt 3", "tiếng việt 4", "tiếng việt 5",
            "toán 2", "toán 3", "toán 4", "toán 5",
            "thcs", "thpt", "trung học", "đại học", "cao đẳng",
            "grade 2", "grade 3", "grade 4", "grade 5"
        ]

        poison_kws_soft = [
            "lớp 1", "tiếng việt 1", "toán 1", "tiểu học", "grade 1"
        ]

        whitelist_kws = [
            "mầm non", "mẫu giáo", "nhà trẻ", "lớp mầm", "lớp chồi", "lớp lá",
            "3-4 tuổi", "4-5 tuổi", "5-6 tuổi", "trẻ 3 tuổi", "trẻ 4 tuổi", "trẻ 5 tuổi",
            "học kỳ 1", "học kỳ 2", "hk1", "hk2", "hk 1", "hk 2", "hki", "hkii",
            "lớp 1 học kỳ", "lớp 1 hk", "lớp một học kỳ"
        ]

        # 1. HARD POISON check: Luôn luôn loại bỏ
        if has_kw(poison_kws_hard):
            metadata["doc_type"] = "khac"
            metadata["doc_group"] = "KHAC"
            return metadata

        # 2. WHITELIST check
        is_preschool = has_kw(whitelist_kws)

        # 3. SOFT POISON check: Loại bỏ nếu không có whitelist đi kèm
        if not is_preschool and has_kw(poison_kws_soft):
            metadata["doc_type"] = "khac"
            metadata["doc_group"] = "KHAC"
            return metadata


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
        if has_kw(["toán", "làm quen toán", "số lượng", "hình học"]):
            self._add_linh_vuc(metadata, "nhan_thuc", "nt.toan")

        # Nhận thức — Khám phá Khoa học
        if has_kw(["khám phá khoa học", "kpkh", "khoa học tự nhiên",
                                             "thí nghiệm", "động vật", "thực vật"]):
            self._add_linh_vuc(metadata, "nhan_thuc", "nt.kpkh")

        # Nhận thức — Khám phá xã hội
        if has_kw(["khám phá xã hội", "kpxh", "xã hội", "nghề nghiệp",
                                             "giao thông", "gia đình"]):
            self._add_linh_vuc(metadata, "nhan_thuc", "nt.kpxh")

        # Ngôn ngữ — Đọc, Viết, Chữ cái
        if has_kw(["chữ cái", "tập đọc", "tập viết", "làm quen chữ",
                                             "đọc viết", "tiếng việt", "âm vần", "bảng chữ"]):
            self._add_linh_vuc(metadata, "ngon_ngu", "nn.doc_viet")

        # Ngôn ngữ — Nghe, Nói
        if has_kw(["nghe nói", "nghe-nói", "phát triển ngôn ngữ",
                                             "giao tiếp", "hội thoại"]):
            self._add_linh_vuc(metadata, "ngon_ngu", "nn.nghe_noi")

        # Ngôn ngữ — Văn học
        if has_kw(["kể chuyện", "truyện", "thơ", "đồng dao",
                                             "văn học", "câu chuyện", "truyện tranh"]):
            self._add_linh_vuc(metadata, "ngon_ngu", "nn.van_hoc")

        # Thẩm mỹ — Tạo hình
        if has_kw(["tạo hình", "vẽ", "nặn", "cắt", "dán",
                                             "mỹ thuật", "tô màu", "nghệ thuật tạo hình"]):
            self._add_linh_vuc(metadata, "tham_my", "tm.tao_hinh")

        # Thẩm mỹ — Âm nhạc
        if has_kw(["âm nhạc", "hát", "múa", "nhạc", "vận động âm nhạc",
                                             "nghe nhạc", "bài hát"]):
            self._add_linh_vuc(metadata, "tham_my", "tm.am_nhac")

        # Thể chất — Vận động
        if has_kw(["thể dục", "vận động", "thể chất", "thể thao",
                                             "rèn luyện thân thể", "phát triển thể lực"]):
            self._add_linh_vuc(metadata, "the_chat", "tc.van_dong")

        # Thể chất — Dinh dưỡng
        if has_kw(["dinh dưỡng", "ăn uống", "thực phẩm", "vệ sinh",
                                             "an toàn thực phẩm", "sức khoẻ", "sức khỏe"]):
            self._add_linh_vuc(metadata, "the_chat", "tc.dinh_duong")

        # Tình cảm - Xã hội — Tình cảm
        if has_kw(["tình cảm", "cảm xúc", "yêu thương", "thân thiện"]):
            self._add_linh_vuc(metadata, "tinh_cam_xh", "tx.tinh_cam")

        # Tình cảm - Xã hội — Kỹ năng xã hội
        if has_kw(["kỹ năng sống", "kỹ năng xã hội", "ứng xử",
                                             "phép lịch sự", "tự phục vụ"]):
            self._add_linh_vuc(metadata, "tinh_cam_xh", "tx.kn_xh")

        # ── 3. Suy doc_type từ Tên ───────────────────────────────────────
        
        # Nhóm Nghiên cứu & Pháp lý (Ưu tiên cao nhất để không bị nhầm thành giáo án hay bổ trợ)
        if has_kw(["thông tư", "quyết định", "nghị định"]):
            metadata["doc_type"] = "pl.thong_tu"
            metadata["source_tier"] = max(metadata["source_tier"], 3)
        elif has_kw(["chương trình gdmn", "chương trình giáo dục mầm non",
                                               "vbhn", "chuẩn phát triển"]):
            metadata["doc_type"] = "pl.chuong_trinh"
            metadata["source_tier"] = max(metadata["source_tier"], 3)
        elif has_kw(["chuẩn 5 tuổi", "chuẩn phát triển trẻ 5 tuổi", "bộ chuẩn"]):
            metadata["doc_type"] = "pl.chuan_5t"
            metadata["source_tier"] = max(metadata["source_tier"], 3)
        elif has_kw(["công văn", "chỉ thị", "kế hoạch số"]):
            metadata["doc_type"] = "pl.cong_van"
            metadata["source_tier"] = max(metadata["source_tier"], 3)
        elif has_kw(["nghiên cứu", "luận văn", "luận án", "nghiên cứu khoa học"]):
            metadata["doc_type"] = "nc.nghien_cuu"
        elif has_kw(["bài báo", "tạp chí", "journal", "article", "vjol", "tapchi"]):
            metadata["doc_type"] = "nc.bai_bao"
        elif has_kw(["tập huấn", "bồi dưỡng giáo viên"]):
            metadata["doc_type"] = "nc.tap_huan"
        elif has_kw(["chương trình nước ngoài", "giáo dục quốc tế"]):
            metadata["doc_type"] = "nc.ct_nuoc_ngoai"
            
        # Nhóm Giáo án, SKKN (Mức độ phổ biến cao)
        elif has_kw(["sáng kiến kinh nghiệm", "skkn"]):
            metadata["doc_type"] = "kn.skkn"
            metadata["source_tier"] = max(metadata["source_tier"], 1)
        elif has_kw(["giáo án", "kế hoạch tổ chức hoạt động", "bài giảng"]):
            metadata["doc_type"] = "gt.giao_an"
            metadata["source_tier"] = max(metadata["source_tier"], 2)
        elif has_kw(["kế hoạch giáo dục", "kế hoạch giảng dạy", "kế hoạch năm học", "kế hoạch tháng"]):
            metadata["doc_type"] = "gt.truong"
            metadata["source_tier"] = max(metadata["source_tier"], 2)
        elif has_kw(["dự giờ", "đánh giá tiết dạy"]):
            metadata["doc_type"] = "kn.du_gio"
            metadata["source_tier"] = max(metadata["source_tier"], 1)
        elif has_kw(["kinh nghiệm", "mẹo dạy", "mẹo"]):
            metadata["doc_type"] = "kn.kinh_nghiem"
            metadata["source_tier"] = max(metadata["source_tier"], 1)

        # Nhóm SGK & Sách bài tập
        elif has_kw(["sgk", "sách giáo khoa"]):
            metadata["doc_type"] = "sgk.sgk"
            metadata["source_tier"] = max(metadata["source_tier"], 2)
        elif has_kw(["sách giáo viên", "hướng dẫn giáo viên"]):
            metadata["doc_type"] = "sgk.sgv"
            metadata["source_tier"] = max(metadata["source_tier"], 2)
        elif has_kw(["nâng cao", "bài tập nâng cao"]):
            metadata["doc_type"] = "bt.nang_cao"
        elif has_kw(["bổ trợ", "tài liệu bổ trợ", "worksheet", "phiếu bài tập", "phiếu ôn tập"]):
            metadata["doc_type"] = "bt.bo_tro"
        elif has_kw(["kỹ năng", "kỹ năng mềm"]):
            metadata["doc_type"] = "bt.ky_nang"
        elif has_kw(["sách bài tập", "vở bài tập", "bài tập"]):
            metadata["doc_type"] = "sgk.sbt"
            metadata["source_tier"] = max(metadata["source_tier"], 2)
        elif has_kw(["tập tô", "vở tập tô", "tô chữ"]):
            metadata["doc_type"] = "sgk.tap_to"
            metadata["source_tier"] = max(metadata["source_tier"], 2)

        # Nhóm Media, Truyện Thơ, Bổ trợ
        elif has_kw(["truyện tranh", "truyện cổ tích", "tập thơ", "thơ ca"]):
            metadata["doc_type"] = "bt.truyen_tho"
        elif has_kw(["tranh tô màu", "hình ảnh", "flashcard", "thẻ học", "tranh ảnh"]):
            metadata["doc_type"] = "md.hinh_anh"
        elif has_kw(["video", "hoạt hình", "clip"]):
            metadata["doc_type"] = "md.video"
        elif has_kw(["âm thanh", "mp3", "audio", "nhạc beat"]):
            metadata["doc_type"] = "md.am_thanh"
        elif has_kw(["quốc tế", "montessori", "reggio emilia", "waldorf", "steam", "stem"]):
            metadata["doc_type"] = "gt.quoc_te"

        # ── 4. Suy Age Band từ Tên ──────────────────────────────────────
        if has_kw(["nhà trẻ"]) or (has_regex([r"(?<!-)\b3\s*tuoi\b", r"(?<!lop\s)3\s*-\s*4", r"(?<!lop)3\s*-\s*4"]) and not has_regex([r"3\s*-\s*4\s*thang"])):
            if "34" not in metadata["age_bands"]:
                metadata["age_bands"].append("34")

        if (has_regex([r"(?<!-)\b4\s*tuoi\b", r"(?<!lop\s)4\s*-\s*5", r"(?<!lop)4\s*-\s*5"]) and not has_regex([r"4\s*-\s*5\s*thang"])):
            if "45" not in metadata["age_bands"]:
                metadata["age_bands"].append("45")

        if has_kw(["lớp lá", "mẫu giáo lớn"]) or (has_regex([r"(?<!-)\b5\s*tuoi\b", r"(?<!lop\s)5\s*-\s*6", r"(?<!lop)5\s*-\s*6"]) and not has_regex([r"5\s*-\s*6\s*thang"])):
            if "56" not in metadata["age_bands"]:
                metadata["age_bands"].append("56")

        is_lop1 = has_kw(["gdpt", "tiểu học"]) or has_regex([r"\blop\s*1\b"])
        is_hk1 = has_regex([r"\bhoc\s*ky\s*1\b", r"\bhk\s*1\b", r"\bhki\b", r"\bki\s*1\b"])
        is_hk2 = has_regex([r"\bhoc\s*ky\s*2\b", r"\bhk\s*2\b", r"\bhkii\b", r"\bki\s*2\b"])

        if is_lop1:
            if is_hk1:
                if "g1_hk1" not in metadata["age_bands"]:
                    metadata["age_bands"].append("g1_hk1")
            elif is_hk2:
                if "g1_hk2" not in metadata["age_bands"]:
                    metadata["age_bands"].append("g1_hk2")
            else:
                if "g1_hk1" not in metadata["age_bands"] and "g1_hk2" not in metadata["age_bands"]:
                    metadata["age_bands"].append("g1_hk1") # Default to HK1 if not specified

        # Nếu không khớp cụ thể tuổi nào nhưng có từ khóa mầm non/mẫu giáo chung chung
        if not metadata["age_bands"] and has_kw(["mầm non", "mẫu giáo", "gdmn", "preschool"]):
            metadata["age_bands"] = ["34", "45", "56"]

        # ── 5. Suy Bộ sách (series_code) từ Tên ────────────────────────
        if has_kw(["cánh diều"]):
            metadata["series_code"] = "canh-dieu"
        elif has_kw(["kết nối tri thức"]):
            metadata["series_code"] = "ket-noi-tri-thuc"
        elif has_kw(["chân trời sáng tạo"]):
            metadata["series_code"] = "chan-troi-sang-tao"
        elif has_kw(["cùng học để phát triển"]):
            metadata["series_code"] = "cung-hoc-de-phat-trien"
        elif has_kw(["vì sự bình đẳng"]):
            metadata["series_code"] = "vi-su-binh-dang"

        # ── 6. Suy Ngôn ngữ (language) ─────────────────────────────────
        if has_kw(["tiếng anh", "english", "alphabet"]):
            metadata["language"] = "en"
            
        # ── 7. Tự động suy doc_group từ doc_type ─────────────────────────
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
