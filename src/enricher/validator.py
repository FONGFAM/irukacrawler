"""
validator.py — Kiểm soát chất lượng tài liệu trước khi export.

Checklist theo Plan § 2.6 / § 3.2:
- File .md: tồn tại, > 500 ký tự, < 5MB, chất lượng nội dung
- Metadata: đủ 4 chiều, các giá trị thuộc danh mục chuẩn IruKa
- Các giá trị lạ (không thuộc taxonomy) → tự động lọc bỏ (không block)
"""
import os
from typing import Optional
# pyrefly: ignore [missing-import]
from loguru import logger

from src.taxonomy import (
    VALID_LINH_VUCS,
    VALID_AGE_BANDS,
    VALID_DOC_TYPES,
    VALID_SUB_DOMAIN_IDS,
    VALID_LEVEL_IDS,
    VALID_SOURCE_TIERS,
)


class Validator:
    """Kiểm tra chất lượng file và metadata trước khi xuất kho."""

    def __init__(self, max_size_mb: int = 5, min_chars: int = 500):
        self.max_size_bytes = max_size_mb * 1024 * 1024
        self.min_chars = min_chars

    # ── File validation ────────────────────────────────────────────────────

    def validate_file(self, md_path: Optional[str]) -> bool:
        """Kiểm tra file .md tồn tại, đủ độ dài và không vượt kích thước.
        Kiểm tra thêm chất lượng nội dung (tỷ lệ chữ/số).

        Args:
            md_path: Đường dẫn tới file Markdown đã convert.

        Returns:
            True nếu file hợp lệ, False nếu không.
        """
        if not md_path:
            logger.warning("validate_file: md_path là None.")
            return False
        try:
            if not os.path.exists(md_path):
                logger.warning(f"File không tồn tại: {md_path}")
                return False

            size = os.path.getsize(md_path)
            if size > self.max_size_bytes:
                logger.warning(f"File vượt 5MB: {md_path} ({size / 1024 / 1024:.1f} MB)")
                return False

            with open(md_path, "r", encoding="utf-8") as f:
                content = f.read()

            if len(content) < self.min_chars:
                logger.warning(
                    f"File quá ngắn (rác?): {md_path} ({len(content)} ký tự < {self.min_chars})"
                )
                return False

            # Kiểm tra chất lượng nội dung: ít nhất 30% ký tự là chữ cái hoặc số
            # (tránh file toàn dấu cách / ký tự đặc biệt)
            alpha_count = sum(c.isalpha() or c.isdigit() for c in content)
            if len(content) > 0 and (alpha_count / len(content)) < 0.3:
                logger.warning(
                    f"File chất lượng thấp (rác?): {md_path} "
                    f"(chỉ {alpha_count}/{len(content)} = {alpha_count/len(content)*100:.0f}% là chữ/số)"
                )
                return False

            return True
        except Exception as e:
            logger.error(f"Lỗi khi validate file {md_path}: {e}")
            return False

    # ── Metadata validation ────────────────────────────────────────────────

    def validate_metadata(self, metadata) -> bool:
        """Kiểm tra và tự động làm sạch metadata theo chuẩn IruKa.

        - Lọc bỏ giá trị lạ trong linh_vucs, age_bands, sub_domain_ids, level_ids.
        - Kiểm tra doc_type thuộc 25 loại; nếu không → gán 'khac'.
        - Sau khi lọc, kiểm tra còn đủ 4 chiều bắt buộc không.

        Args:
            metadata: Object DocumentMetadata.

        Returns:
            True nếu đủ 4 chiều sau khi làm sạch, False nếu vẫn thiếu.
        """
        # ── Lọc linh_vucs ─────────────────────────────────────────────────
        invalid_lv = [lv for lv in metadata.linh_vucs if lv not in VALID_LINH_VUCS]
        if invalid_lv:
            logger.warning(f"Lọc bỏ linh_vuc không hợp lệ: {invalid_lv}")
        metadata.linh_vucs = [lv for lv in metadata.linh_vucs if lv in VALID_LINH_VUCS]

        # ── Lọc age_bands ─────────────────────────────────────────────────
        invalid_ab = [ab for ab in metadata.age_bands if ab not in VALID_AGE_BANDS]
        if invalid_ab:
            logger.warning(f"Lọc bỏ age_band không hợp lệ: {invalid_ab}")
        metadata.age_bands = [ab for ab in metadata.age_bands if ab in VALID_AGE_BANDS]

        # ── Kiểm tra doc_type ─────────────────────────────────────────────
        if metadata.doc_type and metadata.doc_type not in VALID_DOC_TYPES:
            logger.warning(
                f"doc_type '{metadata.doc_type}' không nằm trong 25 loại hợp lệ → gán 'khac'"
            )
            metadata.doc_type = "khac"

        # ── Kiểm tra source_tier ──────────────────────────────────────────
        if metadata.source_tier not in VALID_SOURCE_TIERS:
            logger.warning(
                f"source_tier={metadata.source_tier} không hợp lệ (phải là 1, 2, hoặc 3)"
            )
            # Không reset — để is_valid() phát hiện và flag need_manual

        # ── Lọc sub_domain_ids (không bắt buộc nhưng phải đúng danh mục) ─
        invalid_sub = [s for s in metadata.sub_domain_ids if s not in VALID_SUB_DOMAIN_IDS]
        if invalid_sub:
            logger.warning(f"Lọc bỏ sub_domain_id không hợp lệ: {invalid_sub}")
        metadata.sub_domain_ids = [s for s in metadata.sub_domain_ids if s in VALID_SUB_DOMAIN_IDS]

        if not metadata.sub_domain_ids:
            logger.warning(f"sub_domain_ids rỗng sau khi lọc: {metadata.name}")

        # ── Lọc level_ids (tuỳ chọn) ──────────────────────────────────────
        invalid_lv_ids = [l for l in metadata.level_ids if l not in VALID_LEVEL_IDS]
        if invalid_lv_ids:
            logger.warning(f"Lọc bỏ level_id không hợp lệ: {invalid_lv_ids}")
        metadata.level_ids = [l for l in metadata.level_ids if l in VALID_LEVEL_IDS]

        # ── Kiểm tra đủ 4 chiều bắt buộc ─────────────────────────────────
        if not metadata.is_valid():
            missing = []
            if not metadata.linh_vucs:
                missing.append("linh_vucs")
            if not metadata.age_bands:
                missing.append("age_bands")
            if not metadata.doc_type:
                missing.append("doc_type")
            if metadata.source_tier not in VALID_SOURCE_TIERS:
                missing.append(f"source_tier (hiện tại: {metadata.source_tier})")
            logger.warning(f"Metadata thiếu 4 chiều — cần duyệt tay: {missing} | doc: {metadata.name}")
            return False

        return True