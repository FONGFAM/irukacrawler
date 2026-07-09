# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import datetime
from src.taxonomy import DOC_TYPE_TO_GROUP

class DocumentMetadata(BaseModel):
    name: str = Field(..., description="Tiêu đề tài liệu")
    source_url: str = Field(..., description="URL gốc của tài liệu")
    crawled_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Bắt buộc (4 chiều phân loại IruKa)
    linh_vucs: List[str] = Field(default_factory=list, description="nhan_thuc, ngon_ngu, tham_my, the_chat, tinh_cam_xh")
    age_bands: List[str] = Field(default_factory=list, description="34, 45, 56, g1")
    doc_type: str = Field("", description="VD: sgk.sgk, pl.thong_tu")
    source_tier: int = Field(0, description="1, 2, hoặc 3")
    
    # Tuỳ chọn hoặc phụ thuộc doc_type
    doc_group: str = Field("", description="PL, SGK, GT, BT, KN, NC, MD")
    sub_domain_ids: List[str] = Field(default_factory=list)
    skill_ids: List[str] = Field(default_factory=list)
    level_ids: List[str] = Field(default_factory=list)
    
    # Thông tin nguồn gốc
    series_code: str = Field("", description="VD: canh-dieu, ket-noi-tri-thuc")
    origin_country: str = Field("vn")
    language: str = Field("vi")
    school_readiness: bool = Field(False)
    license: str = Field("public-web")

    def is_valid(self) -> bool:
        """Kiểm tra xem đã đủ 4 chiều phân loại chưa"""
        return all([
            len(self.linh_vucs) > 0,
            len(self.age_bands) > 0,
            bool(self.doc_type),
            self.source_tier in [1, 2, 3]
        ])

    @model_validator(mode='after')
    def infer_doc_group(self) -> 'DocumentMetadata':
        """Tự động suy doc_group từ doc_type nếu chưa được gán."""
        if self.doc_type and not self.doc_group:
            self.doc_group = DOC_TYPE_TO_GROUP.get(self.doc_type, "")
        return self

class DocumentDTO(BaseModel):
    metadata: DocumentMetadata
    raw_file_path: Optional[str] = None
    converted_md_path: Optional[str] = None
    doc_code: Optional[str] = None
    need_manual: bool = False
    
    def to_markdown(self, content: str) -> str:
        """Chuyển thành file Markdown chuẩn với Frontmatter"""
        yaml_lines = ["---"]
        for key, value in self.metadata.model_dump().items():
            if isinstance(value, list):
                # Format list as YAML array
                items = ", ".join([f'"{item}"' for item in value])
                yaml_lines.append(f"{key}: [{items}]")
            elif isinstance(value, str):
                yaml_lines.append(f'{key}: "{value}"')
            elif isinstance(value, bool):
                yaml_lines.append(f"{key}: {'true' if value else 'false'}")
            else:
                yaml_lines.append(f"{key}: {value}")
        yaml_lines.append("---")
        frontmatter = "\n".join(yaml_lines)
        return f"{frontmatter}\n\n{content}"
