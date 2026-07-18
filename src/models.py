# pyrefly: ignore [missing-import]
from pydantic import BaseModel, Field, model_validator
from typing import List, Optional
from datetime import datetime
from src.taxonomy import (
    DOC_TYPE_TO_GROUP,
    VALID_SUB_DOMAIN_IDS,
    VALID_SKILL_IDS,
    VALID_SERIES_CODES
)
class DocumentMetadata(BaseModel):
    name: str = Field(..., description="Tiêu đề tài liệu")
    source_url: str = Field(..., description="URL gốc của tài liệu")
    crawled_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    
    # Bắt buộc (4 chiều phân loại IruKa)
    linh_vucs: List[str] = Field(default_factory=list, description="nhan_thuc, ngon_ngu, tham_my, the_chat, tinh_cam_xh")
    sub_domain_ids: List[str] = Field(default_factory=list, description="IDs lĩnh vực nhỏ")
    source_tier: Optional[int] = Field(None, description="Độ tin cậy: 1 (Kinh nghiệm), 2 (SGK), 3 (Luật)")
    game_assets_potential: Optional[str] = Field(None, description="Tóm tắt về các yếu tố có thể dùng làm game")
    human_verified: bool = Field(False, description="Đã được con người duyệt chưa")
    
    # Tuỳ chọn hoặc phụ thuộc doc_type
    doc_group: str = Field("", description="PL, SGK, GT, BT, KN, NC, MD")
    age_bands: List[str] = Field(default_factory=list, description="34, 45, 56, g1")
    doc_type: str = Field("", description="VD: sgk.sgk, pl.thong_tu")
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
        """Kiểm tra xem đã đủ 4 chiều phân loại chưa.
        Đối với Pháp lý (PL) và Nghiên cứu (NC), có thể không cần age_bands hoặc linh_vucs."""
        if self.doc_type == "khac" or DOC_TYPE_TO_GROUP.get(self.doc_type, "") == "KHAC":
            return True
            
        if not self.doc_type or self.source_tier not in [1, 2, 3]:
            return False
            
        group = DOC_TYPE_TO_GROUP.get(self.doc_type, "")
        if group in ["PL", "NC"]:
            return True
            
        return all([
            len(self.linh_vucs) > 0,
            len(self.age_bands) > 0,
        ])

    @model_validator(mode='after')
    def infer_doc_group(self) -> 'DocumentMetadata':
        """Tự động suy doc_group từ doc_type nếu chưa được gán."""
        if self.doc_type and not self.doc_group:
            self.doc_group = DOC_TYPE_TO_GROUP.get(self.doc_type, "")
        return self
        
    @model_validator(mode='after')
    def clean_invalid_ids(self) -> 'DocumentMetadata':
        """Lọc bỏ các sub_domain_ids và skill_ids không hợp lệ do LLM bịa ra."""
        self.sub_domain_ids = [s for s in self.sub_domain_ids if s in VALID_SUB_DOMAIN_IDS]
        self.skill_ids = [s for s in self.skill_ids if s in VALID_SKILL_IDS]
        if self.series_code and self.series_code not in VALID_SERIES_CODES:
            self.series_code = ""
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
