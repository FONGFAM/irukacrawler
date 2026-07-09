"""
localLLMEnricher.py — Suy metadata bằng LLM local (Ollama).

Chỉ được gọi khi HeuristicEnricher không đủ 4 chiều.
Prompt dùng danh sách taxonomy chuẩn để LLM không tự chế loại.
"""
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

# pyrefly: ignore [missing-import]
from loguru import logger
# pyrefly: ignore [missing-import]
import ollama
from pydantic import ValidationError

from src.models import DocumentMetadata
from src.taxonomy import (
    VALID_LINH_VUCS,
    VALID_AGE_BANDS,
    VALID_DOC_TYPES,
    VALID_SUB_DOMAIN_IDS,
)

# Chuỗi danh sách dùng trong prompt — build 1 lần lúc import
_LINH_VUCS_STR = ", ".join(sorted(VALID_LINH_VUCS))
_AGE_BANDS_STR = ", ".join(sorted(VALID_AGE_BANDS))
_SUB_DOMAINS_STR = ", ".join(sorted(VALID_SUB_DOMAIN_IDS))
# Loại bỏ 'khac' khỏi gợi ý (LLM không nên chọn 'khac' nếu có thể)
_DOC_TYPES_STR = ", ".join(sorted(VALID_DOC_TYPES - {"khac"}))


class LocalLLMEnricher:
    """Trích xuất metadata tài liệu bằng Ollama LLM."""

    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.client = ollama.AsyncClient(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

    async def analyze_document(self, name: str, url: str, preview: str) -> Optional[Dict[str, Any]]:
        """Dùng LLM để phân loại tài liệu theo chuẩn IruKa.

        Args:
            name: Tên tài liệu.
            url: URL gốc.
            preview: 1000 ký tự đầu nội dung file MD.

        Returns:
            Dict metadata hợp lệ, hoặc None nếu thất bại.
        """
        prompt = f"""Bạn là chuyên gia phân loại tài liệu giáo dục mầm non Việt Nam theo VBHN 01/2021.
Phân tích thông tin dưới đây và trả về JSON hợp lệ, KHÔNG giải thích thêm.

DANH MỤC HỢP LỆ (chỉ được chọn giá trị trong danh sách, không tự chế):
- linh_vucs: [{_LINH_VUCS_STR}] (Ví dụ: nhan_thuc = Toán, Khám phá; ngon_ngu = Văn học, Chữ cái; tham_my = Tạo hình, Âm nhạc; the_chat = Vận động, Dinh dưỡng; tinh_cam_xh = Kỹ năng sống)
- age_bands: [{_AGE_BANDS_STR}] (Ví dụ: 34 = 3-4 tuổi, 45 = 4-5 tuổi, 56 = 5-6 tuổi, g1_hk1 = Lớp 1 HK1, g1_hk2 = Lớp 1 HK2)
- doc_type (chọn đúng 1): [{_DOC_TYPES_STR}, khac] 
  + Gợi ý: pl.* (Pháp lý/Thông tư); sgk.* (Sách giáo khoa/Tập tô cho trẻ); gt.giao_an (Giáo án); gt.truong (Giáo trình); bt.bo_tro (Bài tập bổ trợ); bt.truyen_tho (Truyện/Thơ); kn.* (Sáng kiến kinh nghiệm/Mẹo dạy); nc.* (Nghiên cứu/Bài báo/Giáo trình dạy sinh viên/Tập huấn GV).
  + CHÚ Ý: Nếu tài liệu là của HỌC SINH phổ thông (Lớp 2 đến Lớp 12, THCS, THPT) thì BẮT BUỘC chọn doc_type là "khac". Nếu là giáo trình đại học/cao đẳng DẠY VỀ MẦM NON thì chọn "nc.nghien_cuu" hoặc "nc.tap_huan".
- sub_domain_ids: [{_SUB_DOMAINS_STR}] (Toán: nt.toan, Khoa học: nt.kpkh, XH: nt.kpxh, Đọc/Viết: nn.doc_viet, Nghe/Nói: nn.nghe_noi, Văn học: nn.van_hoc, Vẽ/Nặn: tm.tao_hinh, Nhạc: tm.am_nhac, Thể dục: tc.van_dong)
- source_tier: 1 (blog/kinh nghiệm GV), 2 (SGK/giáo trình), 3 (Bộ GD/luật)

Định dạng JSON cần trả về:
{{
    "linh_vucs": ["<từ danh sách>"],
    "age_bands": ["<từ danh sách>"],
    "doc_type": "<từ danh sách>",
    "sub_domain_ids": ["<từ danh sách>"],
    "source_tier": <1 hoặc 2 hoặc 3>
}}

VÍ DỤ TRẢ VỀ:
{{
    "linh_vucs": ["nhan_thuc"],
    "age_bands": ["56"],
    "doc_type": "gt.giao_an",
    "sub_domain_ids": ["nt.toan"],
    "source_tier": 1
}}

Tiêu đề: {name}
URL: {url}
Trích 1200 ký tự đầu nội dung:
{preview[:1200]}
"""

        try:
            logger.info(f"Đang gọi {self.model} qua Ollama để phân tích: {name}")
            response = await self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.0},
                format="json",
            )

            content = response["message"]["content"].strip()

            # Cắt bỏ markdown code block nếu model vẫn bọc (phòng thủ)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            data = json.loads(content)

            # Bổ sung các trường bắt buộc cho Pydantic
            data["name"] = name
            data["source_url"] = url
            if "crawled_at" not in data:
                data["crawled_at"] = datetime.now().isoformat()

            # Validate cấu trúc bằng Pydantic — nếu sai schema → None
            try:
                DocumentMetadata(**data)
                return data
            except ValidationError as ve:
                logger.error(f"LLM trả về dữ liệu sai cấu trúc Pydantic: {ve}")
                return None

        except json.JSONDecodeError as e:
            logger.error(f"Lỗi parse JSON từ LLM: {e}")
            return None
        except Exception as e:
            logger.error(f"Lỗi khi gọi Local LLM: {e}")
            return None
