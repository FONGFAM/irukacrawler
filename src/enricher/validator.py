# pyrefly: ignore [missing-import]
from loguru import logger
import os

class Validator:
    def __init__(self, max_size_mb: int = 5, min_chars: int = 500):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.min_chars = min_chars
        
        self.valid_linh_vucs = {"nhan_thuc", "ngon_ngu", "tham_my", "the_chat", "tinh_cam_xh"}

    def validate_file(self, md_path: str) -> bool:
        """Kiểm tra kích thước file và độ dài"""
        try:
            size = os.path.getsize(md_path)
            if size > self.max_size_bytes:
                logger.warning(f"File too large: {md_path} ({size} bytes)")
                return False
                
            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            if len(content) < self.min_chars:
                logger.warning(f"File too small/junk: {md_path} ({len(content)} chars)")
                return False
                
            return True
        except Exception as e:
            logger.error(f"Error validating file {md_path}: {e}")
            return False

    def validate_metadata(self, metadata) -> bool:
        """Kiểm tra tính hợp lệ của metadata 4 chiều"""
        if not metadata.is_valid():
            logger.warning("Metadata validation failed: Missing required fields")
            return False
            
        # Kiểm tra tính hợp lệ của linh_vucs
        for lv in metadata.linh_vucs:
            if lv not in self.valid_linh_vucs:
                logger.warning(f"Invalid linh_vuc: {lv}")
                return False
                
        return True
