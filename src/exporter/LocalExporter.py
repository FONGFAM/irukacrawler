import os
import shutil
import csv
from pathlib import Path
from typing import List
# pyrefly: ignore [missing-import]
from loguru import logger
from ..models import DocumentDTO
from ..taxonomy import DOC_GROUP_TO_ZONE
from ..enricher.validator import Validator

class LocalExporter:
    def __init__(self, export_dir: str = "data/export/kho-tai-lieu"):
        self.export_dir = Path(export_dir)
        self.manifest_path = self.export_dir.parent / "manifest.csv"
        
        # Tạo file manifest nếu chưa có hoặc rỗng
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.manifest_path.exists() or self.manifest_path.stat().st_size == 0:
            with open(self.manifest_path, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "doc_code", "name", "source_url", "local_path", 
                    "linh_vuc", "age_band", "doc_type", "source_tier", 
                    "uploaded_at", "status", "need_manual"
                ])

    def _determine_zone(self, doc_group: str) -> str:
        return DOC_GROUP_TO_ZONE.get(doc_group.upper(), "00_Khac")

    def _generate_doc_code(self, meta) -> str:
        """Sinh mã tài liệu (VD: DOC-NN-56-SGK-0001)"""
        # Đây là bản demo đơn giản, thực tế cần check DB để lấy số sequence
        lv2 = "XX"
        if meta.linh_vucs:
            lv_map = {
                "nhan_thuc": "NT", "ngon_ngu": "NN", "tham_my": "TM", 
                "the_chat": "TC", "tinh_cam_xh": "TX"
            }
            lv2 = lv_map.get(meta.linh_vucs[0], "XX")
            
        age = meta.age_bands[0] if meta.age_bands else "xx"
        nhom = meta.doc_group if meta.doc_group else "XX"
        
        # Sinh chuỗi ngẫu nhiên 4 ký tự thay cho sequence (trong local standalone)
        import random
        seq = f"{random.randint(1, 9999):04d}"
        
        return f"DOC-{lv2}-{age}-{nhom}-{seq}"

    def export(self, doc: DocumentDTO) -> bool:
        """Lưu file vào đúng cấu trúc và ghi manifest.
        
        Gọi validate_metadata() trước export để đảm bảo metadata sạch.
        """
        try:
            meta = doc.metadata
            
            # Validate lại metadata trước khi export (sửa lỗi: trước đây không validate lại)
            v = Validator()
            if not doc.need_manual and not v.validate_metadata(meta):
                logger.warning(f"Export: metadata không hợp lệ, gắn need_manual: {meta.name}")
                doc.need_manual = True
            
            # Sinh mã nếu chưa có
            if not doc.doc_code and not doc.need_manual:
                doc.doc_code = self._generate_doc_code(meta)
                
            doc_code = doc.doc_code or "NEED_MANUAL"
            
            # Đường dẫn: kho-tai-lieu/{zone}/{origin}/{series}/{age_band}/{linh_vuc}/
            zone = self._determine_zone(meta.doc_group)
            origin = meta.origin_country or "vn"
            series = meta.series_code or "chung"
            age = meta.age_bands[0] if meta.age_bands else "chung"
            linh_vuc = meta.linh_vucs[0] if meta.linh_vucs else "chung"
            
            # Xử lý file name
            import re
            safe_name = re.sub(r'[^a-zA-Z0-9]+', '-', meta.name.lower()).strip('-')
            slug = f"{doc_code}__{safe_name}.md"
            
            target_dir = self.export_dir / zone / origin / series / age / linh_vuc
            target_dir.mkdir(parents=True, exist_ok=True)
            
            target_path = target_dir / slug
            
            # Đọc file converted và chèn Frontmatter
            with open(doc.converted_md_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            final_content = doc.to_markdown(content)
            
            with open(target_path, "w", encoding="utf-8") as f:
                f.write(final_content)
                
            logger.success(f"Exported to: {target_path}")
            
            # Ghi manifest
            with open(self.manifest_path, "a", encoding="utf-8", newline="") as f:
                writer = csv.writer(f)
                status = "need_manual" if doc.need_manual else "exported"
                writer.writerow([
                    doc_code, meta.name, meta.source_url, str(target_path),
                    linh_vuc, age, meta.doc_type, meta.source_tier,
                    meta.crawled_at, status, doc.need_manual
                ])
                
            return True
        except Exception as e:
            logger.error(f"Error exporting doc {doc.metadata.name}: {e}")
            return False