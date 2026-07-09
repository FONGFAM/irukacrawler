from typing import Dict, Any
from urllib.parse import urlparse
# pyrefly: ignore [missing-import]
from loguru import logger

class HeuristicEnricher:
    def __init__(self):
        pass

    def apply_rules(self, name: str, url: str) -> Dict[str, Any]:
        """Suy luận metadata dựa trên luật cứng (Bảng 5.6)"""
        name_lower = name.lower()
        domain = urlparse(url).netloc
        
        metadata = {
            "linh_vucs": [],
            "age_bands": [],
            "doc_type": "",
            "sub_domain_ids": [],
            "source_tier": 0
        }

        # Suy luận từ URL Domain
        if "moet.gov.vn" in domain:
            metadata["doc_type"] = "pl.thong_tu"
            metadata["source_tier"] = 3
        
        # Suy luận từ Tên
        if any(kw in name_lower for kw in ["toán", "làm quen toán"]):
            metadata["linh_vucs"].append("nhan_thuc")
            metadata["sub_domain_ids"].append("nt.toan")
            
        if any(kw in name_lower for kw in ["chữ cái", "tập đọc", "tập viết"]):
            metadata["linh_vucs"].append("ngon_ngu")
            metadata["sub_domain_ids"].append("nn.doc_viet")
            
        if any(kw in name_lower for kw in ["kể chuyện", "truyện", "thơ", "đồng dao"]):
            metadata["linh_vucs"].append("ngon_ngu")
            metadata["sub_domain_ids"].append("nn.van_hoc")
            metadata["doc_type"] = metadata.get("doc_type") or "bt.truyen_tho"

        if any(kw in name_lower for kw in ["tạo hình", "vẽ", "mỹ thuật", "âm nhạc", "hát", "múa"]):
            metadata["linh_vucs"].append("tham_my")
            if any(kw in name_lower for kw in ["tạo hình", "vẽ", "mỹ thuật"]):
                metadata["sub_domain_ids"].append("tm.tao_hinh")
            else:
                metadata["sub_domain_ids"].append("tm.am_nhac")

        if any(kw in name_lower for kw in ["thể dục", "vận động", "thể chất"]):
            metadata["linh_vucs"].append("the_chat")
            metadata["sub_domain_ids"].append("tc.van_dong")
            
        if any(kw in name_lower for kw in ["thông tư", "chương trình gdmn"]):
            metadata["doc_type"] = "pl.chuong_trinh"
            metadata["source_tier"] = max(metadata.get("source_tier", 0), 3)
            
        # Doc Types
        if any(kw in name_lower for kw in ["sgk", "sách giáo khoa"]):
            metadata["doc_type"] = "sgk.sgk"
            metadata["source_tier"] = max(metadata["source_tier"], 2)
            
        if any(kw in name_lower for kw in ["bài tập", "vở bài tập"]):
            metadata["doc_type"] = "sgk.sbt"
            metadata["source_tier"] = max(metadata["source_tier"], 2)
            
        if "giáo án" in name_lower:
            metadata["doc_type"] = "gt.giao_an"
            metadata["source_tier"] = max(metadata["source_tier"], 2)
            
        # Age bands
        if any(kw in name_lower for kw in ["3 tuổi", "3-4"]):
            metadata["age_bands"].append("34")
        if any(kw in name_lower for kw in ["4 tuổi", "4-5"]):
            metadata["age_bands"].append("45")
        if any(kw in name_lower for kw in ["5 tuổi", "5-6", "lá"]):
            metadata["age_bands"].append("56")
        if any(kw in name_lower for kw in ["lớp 1", "gdpt"]):
            metadata["age_bands"].append("g1")
            
        logger.debug(f"Heuristic rules applied for {name}: {metadata}")
        
        # Lọc bớt các field rỗng
        return {k: v for k, v in metadata.items() if v}
