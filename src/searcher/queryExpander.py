"""
QueryExpander: Tự động sinh biến thể câu truy vấn từ từ khoá gốc
dựa vào từ điển đồng nghĩa lĩnh vực Giáo dục Mầm non Việt Nam.
"""

import re
from typing import List
# pyrefly: ignore [missing-import]
from loguru import logger

# ─────────────────────────────────────────────────────────────
# Từ điển đồng nghĩa theo lĩnh vực GDMN
# ─────────────────────────────────────────────────────────────

DOC_TYPE_SYNONYMS: dict = {
    "giáo án": ["bài giảng", "kế hoạch giáo dục", "tiết học", "hoạt động học"],
    "bài giảng": ["giáo án", "kế hoạch giáo dục", "tiết học"],
    "video": ["clip", "bài học video", "tiết dạy minh họa"],
    "tài liệu": ["học liệu", "tư liệu", "tài nguyên dạy học"],
}

AGE_SYNONYMS: dict = {
    "mầm non": ["mẫu giáo", "nhà trẻ"],
    "3-4 tuổi": ["trẻ 3 tuổi", "lớp mầm", "nhà trẻ"],
    "4-5 tuổi": ["trẻ 4 tuổi", "lớp chồi", "mẫu giáo nhỡ"],
    "5-6 tuổi": ["trẻ 5 tuổi", "lớp lá", "mẫu giáo lớn"],
    "lớp lá": ["5-6 tuổi", "mẫu giáo lớn", "trẻ 5 tuổi"],
    "lớp chồi": ["4-5 tuổi", "mẫu giáo nhỡ", "trẻ 4 tuổi"],
    "lớp mầm": ["3-4 tuổi", "nhà trẻ", "trẻ 3 tuổi"],
}

TOPIC_SYNONYMS: dict = {
    "kể chuyện": ["đọc truyện", "kể truyện", "văn học"],
    "đọc truyện": ["kể chuyện", "kể truyện", "văn học"],
    "âm nhạc": ["hát", "múa hát", "nghe nhạc", "ca hát"],
    "tạo hình": ["vẽ", "thủ công", "mĩ thuật mầm non"],
    "thể dục": ["vận động", "thể chất", "bài tập thể chất"],
    "toán": ["làm quen với toán", "nhận biết số", "đếm số"],
    "tiếng việt": ["ngôn ngữ", "làm quen chữ cái", "tiền đọc viết"],
    "khoa học": ["khám phá", "tìm hiểu môi trường", "khám phá tự nhiên"],
}

ALL_SYNONYM_MAPS = [DOC_TYPE_SYNONYMS, AGE_SYNONYMS, TOPIC_SYNONYMS]


def expand_query(base_query: str, max_variants: int = 4, shuffle: bool = True, offset: int = 0) -> List[str]:
    """
    Sinh biến thể câu truy vấn từ query gốc.
    
    Args:
        base_query: Câu truy vấn gốc, VD: "giáo án kể chuyện mầm non 5-6 tuổi"
        max_variants: Số biến thể tối đa (bao gồm query gốc)
        shuffle: Có trộn ngẫu nhiên các biến thể hay không (deterministic shuffle)
        offset: Vị trí bắt đầu lấy các biến thể (dùng để đổi mới kết quả tìm kiếm)
    
    Returns:
        Danh sách biến thể (query gốc luôn ở đầu)
    """
    base_norm = base_query.lower().strip()
    candidates = []

    for synonym_map in ALL_SYNONYM_MAPS:
        for keyword, synonyms in synonym_map.items():
            if keyword.lower() in base_norm:
                for syn in synonyms:
                    pattern = re.compile(re.escape(keyword), re.IGNORECASE)
                    new_query = pattern.sub(syn, base_query)
                    if new_query.lower() != base_query.lower() and new_query not in candidates:
                        candidates.append(new_query)

    if shuffle:
        import random
        # Sử dụng seed cố định dựa trên base_query để đảm bảo kết quả shuffle 
        # nhất quán trên cùng một query gốc, giúp phân trang offset hoạt động chuẩn.
        random.Random(base_query).shuffle(candidates)

    # Chọn phân khúc ứng viên dựa trên offset
    selected_candidates = candidates[offset:offset + max_variants - 1]
    variants = [base_query] + selected_candidates

    logger.info(f"QueryExpander: '{base_query}' (offset={offset}) -> {len(variants)} biến thể (tổng số ứng viên: {len(candidates)})")
    return variants
