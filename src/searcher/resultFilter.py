import re
from typing import List, Dict, Any
from loguru import logger
from src.enricher.heuristicEnricher import remove_accents

class ResultFilter:
    # Danh sách từ khoá ngoài phạm vi (cấp tiểu học trở lên)
    OUT_OF_SCOPE = [
        "lớp 2", "lớp 3", "lớp 4", "lớp 5", "lớp 6", "lớp 7", "lớp 8", "lớp 9", "lớp 10", "lớp 11", "lớp 12",
        "tiếng việt 2", "tiếng việt 3", "tiếng việt 4", "tiếng việt 5",
        "toán 2", "toán 3", "toán 4", "toán 5",
        "thcs", "thpt", "trung học", "đại học", "cao đẳng",
        "grade 2", "grade 3", "grade 4", "grade 5",
    ]

    # Các từ khóa cụ thể cho lớp 1 nhưng KHÔNG có context mầm non hoặc học kỳ của lớp 1
    # Nếu chỉ có "lớp 1", "tiếng việt 1", "toán 1" mà KHÔNG đi kèm với mầm non/học kỳ -> loại bỏ
    GRADE_1_POISON = [
        "lớp 1", "tiếng việt 1", "toán 1", "sách giáo khoa lớp 1", "sgk lớp 1"
    ]

    # Từ khoá khẳng định mầm non hoặc học kỳ lớp 1 hợp lệ (whitelist)
    WHITELIST = [
        "mầm non", "mẫu giáo", "nhà trẻ", "lớp mầm", "lớp chồi", "lớp lá",
        "3-4 tuổi", "4-5 tuổi", "5-6 tuổi", "trẻ 3 tuổi", "trẻ 4 tuổi", "trẻ 5 tuổi",
        "học kỳ 1", "học kỳ 2", "hk1", "hk2", "hk 1", "hk 2", "hki", "hkii",
        "lớp 1 học kỳ", "lớp 1 hk", "lớp một học kỳ"
    ]

    # Các định dạng file rác hoặc các URL cdn/assets
    SPAM_URL_PATTERNS = [
        r"\.(jpg|jpeg|png|gif|svg|ico|css|js|woff|woff2|ttf|eot)$",
        r"/(assets|static|cdn|images|css|js|themes)/",
        r"(google\.com/search|facebook\.com|twitter\.com|linkedin\.com|pinterest\.com)"
    ]

    def __init__(self):
        # Tạo danh sách đã chuẩn hoá (bỏ dấu) để so khớp nhanh
        self.whitelist_norm = [remove_accents(w) for w in self.WHITELIST]
        self.out_of_scope_norm = [remove_accents(o) for o in self.OUT_OF_SCOPE]
        self.grade1_poison_norm = [remove_accents(g) for g in self.GRADE_1_POISON]

    def is_spam_url(self, url: str) -> bool:
        url_lower = url.lower()
        for pattern in self.SPAM_URL_PATTERNS:
            if re.search(pattern, url_lower):
                return True
        return False

    def filter(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Lọc danh sách các kết quả tìm kiếm.
        Mỗi kết quả là một dict chứa: 'url' và 'title' (có thể trống).
        Trả về danh sách các kết quả hợp lệ.
        """
        filtered_results = []
        
        for item in results:
            url = item.get("url", "")
            title = item.get("title", "")
            
            if not url:
                continue
                
            # 1. Kiểm tra URL spam
            if self.is_spam_url(url):
                logger.debug(f"ResultFilter: Loại bỏ URL spam/tài nguyên tĩnh: {url}")
                continue

            # Chuẩn hoá tiêu đề và URL để tìm kiếm từ khoá
            title_norm = remove_accents(title.lower()) if title else ""
            
            import urllib.parse
            url_decoded = urllib.parse.unquote(url).lower().replace("-", " ").replace("_", " ").replace("/", " ")
            url_norm = remove_accents(url_decoded)
            
            # Kết hợp thông tin từ cả tiêu đề và URL để quét
            combined_norm = f"{title_norm} {url_norm}".strip()

            # 2. Kiểm tra Whitelist
            has_whitelist = any(w in combined_norm for w in self.whitelist_norm)
            
            if has_whitelist:
                # Nếu có từ khóa whitelist (ví dụ: "mầm non", "5-6 tuổi" hoặc "lớp 1 học kỳ 1") -> Giữ lại
                filtered_results.append(item)
                continue

            # 3. Kiểm tra các lớp học lớn (lớp 2, 3, 4, 5, thcs, thpt...)
            has_out_of_scope = any(o in combined_norm for o in self.out_of_scope_norm)
            if has_out_of_scope:
                logger.warning(f"ResultFilter: Loại bỏ kết quả ngoài mầm non (phát hiện lớp lớn): {title} ({url})")
                continue

            # 4. Kiểm tra Lớp 1 chung chung (không có whitelist đi kèm)
            has_g1_poison = any(g in combined_norm for g in self.grade1_poison_norm)
            if has_g1_poison:
                logger.warning(f"ResultFilter: Loại bỏ tài liệu lớp 1 chung chung (thiếu context mầm non/học kỳ): {title} ({url})")
                continue

            # 5. Nếu không dính poison và không có whitelist cụ thể -> Giữ để xử lý tiếp bằng Heuristic/LLM ở bước sau
            filtered_results.append(item)

        return filtered_results
