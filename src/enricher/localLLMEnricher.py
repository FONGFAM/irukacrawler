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

    async def analyze_document(self, name: str, url: str, preview: str, user_query: str = "") -> Optional[Dict[str, Any]]:
        """Dùng LLM để phân loại tài liệu theo chuẩn IruKa.

        Args:
            name: Tên tài liệu.
            url: URL gốc.
            preview: 1000 ký tự đầu nội dung file MD.
            user_query: Truy vấn tìm kiếm gốc của người dùng.

        Returns:
            Dict metadata hợp lệ, hoặc None nếu thất bại.
        """
        prompt = f"""Bạn là chuyên gia phân loại tài liệu giáo dục mầm non Việt Nam theo VBHN 01/2021.
Người dùng đang tìm kiếm tài liệu với yêu cầu chính xác là: "{user_query}"
Phân tích thông tin dưới đây và trả về JSON hợp lệ, KHÔNG giải thích thêm. Bắt buộc phải có trường "reasoning" ở dòng đầu tiên để lập luận chi tiết trước khi chốt nhãn. Lập luận phải đánh giá xem tài liệu này có BÁM SÁT yêu cầu "{user_query}" không. Nếu KHÔNG bám sát hoặc lạc đề, bắt buộc phải chọn doc_type="khac".

DANH MỤC HỢP LỆ (chỉ được chọn giá trị trong danh sách, không tự chế):
- linh_vucs: [{_LINH_VUCS_STR}] (Ví dụ: nhan_thuc = Toán, Khám phá; ngon_ngu = Văn học, Chữ cái; tham_my = Tạo hình, Âm nhạc; the_chat = Vận động, Dinh dưỡng; tinh_cam_xh = Kỹ năng sống)
- age_bands: [{_AGE_BANDS_STR}] (Ví dụ: 34 = 3-4 tuổi, 45 = 4-5 tuổi, 56 = 5-6 tuổi, g1_hk1 = Lớp 1 HK1, g1_hk2 = Lớp 1 HK2)
- doc_type (chọn đúng 1): [{_DOC_TYPES_STR}, khac] 
  + Gợi ý: pl.* (Pháp lý/Thông tư); sgk.* (Sách giáo khoa/Tập tô cho trẻ); gt.giao_an (Giáo án của CÔ GIÁO); gt.truong (Giáo trình đại học); bt.bo_tro (Bài tập/Phiếu bài tập cho TRẺ); bt.truyen_tho (Truyện/Thơ); kn.* (Sáng kiến kinh nghiệm/Mẹo dạy); nc.* (Nghiên cứu/Bài báo).
  + CHÚ Ý: Phải phân biệt rõ Giáo án (gt.giao_an - tài liệu hướng dẫn cô giáo lên lớp) và Bài tập (bt.bo_tro - phiếu bài tập để trẻ làm đồ chơi, tập tô).
  + LƯU Ý VỀ MỤC TIÊU LÕI (GAME DESIGN): Đích đến cuối cùng của hệ thống là sử dụng các tài liệu này để LÀM GAME GIÁO DỤC (Educational Games) cho trẻ nhỏ. Đánh giá cực kỳ cao các tài liệu có yếu tố tương tác: Phiếu bài tập, Trò chơi, Hoạt động trải nghiệm, Câu đố, Giáo án điện tử. Nếu tài liệu chỉ là lý thuyết suông tẻ nhạt, rác, không có khả năng chuyển thể thành trò chơi, cân nhắc gán doc_type là "khac".
  + LƯU Ý TUYỆT ĐỐI VỀ ĐỘ TUỔI: Hệ thống CHỈ lấy Mầm non và Lớp 1 (dưới 7 tuổi). "5 tuổi" (Mầm non) KHÁC VỚI "Lớp 5" (Tiểu học - 10 tuổi). Nếu tài liệu dành cho độ tuổi NGOÀI 7 TUỔI (VD: Lớp 2, Lớp 3, Lớp 4, Lớp 5, Lớp 6, Tiểu học, THCS...) thì BẮT BUỘC chọn doc_type là "khac" và trả về mảng age_bands rỗng [].
- sub_domain_ids: [{_SUB_DOMAINS_STR}] (Toán: nt.toan, Khoa học: nt.kpkh, XH: nt.kpxh, Đọc/Viết: nn.doc_viet, Nghe/Nói: nn.nghe_noi, Văn học: nn.van_hoc, Vẽ/Nặn: tm.tao_hinh, Nhạc: tm.am_nhac, Thể dục: tc.van_dong)
- source_tier: 1 (blog/kinh nghiệm GV), 2 (SGK/giáo trình), 3 (Bộ GD/luật)

Định dạng JSON cần trả về:
{{
    "reasoning": "<Trình bày suy nghĩ từng bước: Xác định độ tuổi? Xác định loại tài liệu (giáo án hay bài tập)? Xác định lĩnh vực?>",
    "suggested_name": "<Tên tài liệu rõ ràng, có nghĩa, dựa vào nội dung>",
    "linh_vucs": ["<từ danh sách>"],
    "age_bands": ["<từ danh sách>"],
    "doc_type": "<từ danh sách>",
    "sub_domain_ids": ["<từ danh sách>"],
    "source_tier": <1 hoặc 2 hoặc 3>,
    "game_assets_potential": "<Tóm tắt 1-2 câu về việc có thể dùng gì ở tài liệu này để làm Game (VD: có câu hỏi trắc nghiệm, có hình ảnh đẹp, có kịch bản chơi... khuyết thì để trống)>"
}}


VÍ DỤ 1 (Giáo án Toán):
{{
    "reasoning": "Tài liệu hướng dẫn cô giáo cách tổ chức hoạt động đếm đến 5 cho trẻ 5-6 tuổi. Thuộc lĩnh vực nhận thức toán học. Là giáo án của giáo viên.",
    "suggested_name": "Giáo án phát triển nhận thức: Đếm đến 5, nhận biết số 5",
    "linh_vucs": ["nhan_thuc"],
    "age_bands": ["56"],
    "doc_type": "gt.giao_an",
    "sub_domain_ids": ["nt.toan"],
    "source_tier": 1
}}

VÍ DỤ 2 (Phiếu bài tập):
{{
    "reasoning": "Tài liệu là các trang để trẻ em tự tô màu và vẽ nối các con vật, dành cho lứa tuổi 3-4 tuổi. Thuộc mảng tạo hình thẩm mỹ. Đây là bài tập bổ trợ.",
    "suggested_name": "Phiếu bài tập tạo hình: Tô màu con vật",
    "linh_vucs": ["tham_my"],
    "age_bands": ["34"],
    "doc_type": "bt.bo_tro",
    "sub_domain_ids": ["tm.tao_hinh"],
    "source_tier": 1
}}

Tiêu đề: {name}
URL: {url}
Trích đoạn nội dung (đã tăng độ dài context):
{preview[:2500]}
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

    async def generate_smart_queries(self, user_query: str) -> list[str]:
        """[Pass 0] Sinh ra 3 câu truy vấn tìm kiếm tối ưu."""
        prompt = f"""Bạn là một chuyên gia thiết kế Game Giáo dục Mầm non. Người dùng muốn tìm tài liệu với chủ đề: "{user_query}".
Hãy sinh ra đúng 3 câu truy vấn tìm kiếm (search queries) bằng ngôn ngữ tự nhiên, phù hợp cho công cụ tìm kiếm như Exa hoặc Google.

YÊU CẦU BẮT BUỘC:
1. Mỗi truy vấn phải có cụm từ "mầm non" HOẶC "mầm non trẻ em" hoặc "lớp mầm" để định hướng đúng.
2. Ưu tiên tìm tài liệu dạng file (giáo án, phiếu bài tập, kế hoạch dạy học) của TRƯỜNG MẦM NON Việt Nam.
3. KHÔNG tìm tài liệu tôn giáo, tiểu học lớn (lớp 3, lớp 4, lớp 5), đại học, hoặc trang wiki.
4. Viết bằng ngôn ngữ tự nhiên tiếng Việt, không dùng toán tử tìm kiếm như "filetype:" hay "site:".

CHỈ trả về JSON List chứa 3 chuỗi, ví dụ:
[
  "giáo án {user_query} lớp mầm non 3-4 tuổi file pdf",
  "kế hoạch dạy học {user_query} cho trẻ mầm non tải về",
  "phiếu bài tập {user_query} mầm non tiếng Việt"
]
"""
        try:
            response = await self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.5},
                format="json",
            )
            content = response["message"]["content"].strip()
            queries = json.loads(content)
            if isinstance(queries, list):
                return queries
            return [user_query]
        except Exception as e:
            logger.error(f"Lỗi sinh smart queries: {e}")
            return [user_query, f"{user_query} trò chơi", f"{user_query} bài tập"]

    async def evaluate_relevance(self, preview_text: str, user_query: str, url: str = "") -> int:
        """[Pass 1] Trạm gác: Chấm điểm độ liên quan (0-100). Dưới 35 điểm sẽ bị loại."""
        # Fast-path: domain whitelist - ưu tiên các trang giáo dục mầm non rõ ràng
        edu_domains = ["edu.vn", "mamnon", "thuviengiaoan", "giaoan", "moet.gov", "hoc10"]
        if url and any(d in url.lower() for d in edu_domains):
            # Nếu text quá ngắn (file ảnh) thì vẫn đánh dấu cần OCR
            real_text = preview_text.replace("[Ảnh: (Bị lược bỏ trong quá trình cào)]", "").strip()
            if len(real_text) < 100:
                logger.warning(f"File có thể là ảnh scan, text quá ngắn: {len(real_text)} ký tự")
                return 0
            logger.info(f"Fast-path EDU domain: bỏ qua Gatekeeper LLM, cho điểm 75")
            return 75
            
        prompt = f"""Bạn là một chuyên gia kiểm định tài liệu giáo dục mầm non Việt Nam.
Yêu cầu tìm kiếm gốc của người dùng là: "{user_query}"

Nhiệm vụ: Đánh giá xem đoạn văn bản dưới đây có xuất phát từ một tài liệu LIÊN QUAN ĐẾN GIÁO DỤC MẦM NON (trẻ dưới 7 tuổi) hay không.
Lưu ý quan trọng:
- Tài liệu KHÔNG cần hoàn toàn khớp với yêu cầu - chỉ cần liên quan đến giáo dục mầm non là đạt.
- Kế hoạch chuyên môn, báo cáo, công văn của trường mầm non → ĐÂY LÀ TÀI LIỆU HỢP LỆ, cho điểm ≥ 60.
- Giáo án dạy học, phiếu bài tập, truyện/thơ cho trẻ mầm non → cho điểm ≥ 70.
- Bài nghiên cứu về giáo dục mầm non → cho điểm ≥ 55.
- Rác hoàn toàn (quảng cáo, tôn giáo, tin tức không liên quan) → cho điểm 0.
- Tài liệu dành cho Tiểu học lớp 2+ trở lên → cho điểm 0.
- Tài liệu không phải tiếng Việt → cho điểm 0.

Định dạng JSON trả về bắt buộc:
{{
  "reasoning": "<Giải thích ngắn: Tài liệu này là gì? Có liên quan mầm non không?>",
  "score": <số nguyên từ 0 đến 100>
}}

Văn bản cần chấm:
{preview_text[:2000]}
"""
        try:
            response = await self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.0},
                format="json",
            )
            content = response["message"]["content"].strip()
            data = json.loads(content)
            return int(data.get("score", 0))
        except Exception as e:
            logger.error(f"Lỗi chấm điểm relevance: {e}")
            return 100  # Fail-open if LLM fails
