import json
import os
# pyrefly: ignore [missing-import]
from loguru import logger
# pyrefly: ignore [missing-import]
import ollama
from typing import Optional, Dict, Any

class LocalLLMEnricher:
    def __init__(self):
        self.model = os.getenv("OLLAMA_MODEL", "llama3")
        self.client = ollama.Client(host=os.getenv("OLLAMA_HOST", "http://localhost:11434"))

    def analyze_document(self, name: str, url: str, preview: str) -> Optional[Dict[str, Any]]:
        """Sử dụng Local LLM để trích xuất metadata"""
        prompt = f"""Bạn là chuyên gia phân loại tài liệu giáo dục mầm non Việt Nam.
Dựa vào thông tin sau, hãy trả về kết quả dưới dạng JSON hợp lệ (không giải thích thêm).

Yêu cầu định dạng JSON:
{{
    "linh_vucs": ["có thể chọn nhiều lĩnh vực nếu tài liệu bao quát rộng: nhan_thuc, ngon_ngu, tham_my, the_chat, tinh_cam_xh"],
    "age_band": ["chọn 1 trong: 34, 45, 56, g1"],
    "doc_type": "1 loại tài liệu",
    "source_tier": 1
}}

Tiêu đề: {name}
URL: {url}
Nội dung trích đoạn:
{preview[:1000]}
"""

        try:
            logger.info(f"Đang gọi {self.model} qua Ollama để phân tích: {name}")
            response = self.client.chat(
                model=self.model,
                messages=[{'role': 'user', 'content': prompt}],
                options={'temperature': 0.0} # Để output json ổn định hơn
            )
            
            content = response['message']['content'].strip()
            
            # Cắt bỏ các đoạn text dư thừa trước và sau JSON (nếu model không tuân thủ hoàn toàn)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            return json.loads(content)
        except Exception as e:
            logger.error(f"Lỗi khi gọi Local LLM: {e}")
            return None
