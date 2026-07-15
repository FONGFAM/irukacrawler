import streamlit as st
import pandas as pd
import sys
from pathlib import Path

# ─────────────────────────────────────────────────────────────
# Cấu hình hằng số
# ─────────────────────────────────────────────────────────────
MANIFEST_PATH = Path("data/export/manifest.csv")
PYTHON_BIN    = sys.executable

MAP_LINH_VUC = {
    "nhan_thuc": "Nhận thức", "ngon_ngu": "Ngôn ngữ",
    "tham_my": "Thẩm mỹ", "the_chat": "Thể chất",
    "tinh_cam_xh": "Tình cảm - Xã hội", "chung": "Chung"
}

MAP_AGE_BAND = {
    "34": "3–4 tuổi", "45": "4–5 tuổi",
    "56": "5–6 tuổi", "g1_hk1": "Lớp 1 (HK1)", "g1_hk2": "Lớp 1 (HK2)", "chung": "Chung (Mọi độ tuổi)"
}

MAP_DOC_TYPE = {
    "pl.chuong_trinh": "Chương trình (PL)", "pl.chuan_5t": "Chuẩn 5 tuổi (PL)",
    "pl.thong_tu": "Thông tư (PL)", "pl.cong_van": "Công văn (PL)",
    "sgk.sgk": "Sách GK (SGK)", "sgk.sbt": "Sách BT (SGK)",
    "sgk.sgv": "Sách GV (SGK)", "sgk.tap_to": "Tập tô (SGK)",
    "gt.truong": "GT Trường (GT)", "gt.quoc_te": "GT Quốc tế (GT)", "gt.giao_an": "Giáo án (GT)",
    "bt.nang_cao": "Nâng cao (BT)", "bt.bo_tro": "Bổ trợ (BT)",
    "bt.truyen_tho": "Truyện/Thơ (BT)", "bt.ky_nang": "Kỹ năng (BT)",
    "bt.phieu_bai_tap": "Phiếu bài tập (BT)", "bt.tro_choi": "Trò chơi (BT)",
    "kn.kinh_nghiem": "Kinh nghiệm (KN)", "kn.skkn": "Sáng kiến KN (KN)",
    "kn.meo_day": "Mẹo dạy (KN)", "kn.du_gio": "Dự giờ (KN)",
    "nc.nghien_cuu": "Nghiên cứu (NC)", "nc.bai_bao": "Bài báo (NC)",
    "nc.tap_huan": "Tập huấn (NC)", "nc.ct_nuoc_ngoai": "CT Nước ngoài (NC)",
    "md.hinh_anh": "Hình ảnh (MD)", "md.am_thanh": "Âm thanh (MD)", "md.video": "Video (MD)",
    "khac": "Khác"
}

MAP_SUB_DOMAIN = {
    "nt.toan": "Toán học (NT)", "nt.kpkh": "Khám phá khoa học (NT)", "nt.kpxh": "Khám phá xã hội (NT)",
    "nn.doc_viet": "Đọc viết (NN)", "nn.nghe_noi": "Nghe nói (NN)", "nn.van_hoc": "Văn học (NN)",
    "tm.tao_hinh": "Tạo hình (TM)", "tm.am_nhac": "Âm nhạc (TM)",
    "tc.van_dong": "Vận động (TC)", "tc.dinh_duong": "Dinh dưỡng sức khỏe (TC)",
    "tx.tinh_cam": "Tình cảm (TX)", "tx.kn_xh": "Kỹ năng xã hội (TX)"
}

MAP_LEVELS = {
    "lv01": "Mức 1: Nhận biết",
    "lv02": "Mức 2: Vận dụng",
    "lv03": "Mức 3: Nâng cao sáng tạo"
}

# ─────────────────────────────────────────────────────────────
# Hàm tiện ích dùng chung
# ─────────────────────────────────────────────────────────────

@st.cache_data(ttl=30)
def tai_du_lieu() -> pd.DataFrame:
    """Đọc file kết quả (manifest.csv) và cache 30 giây."""
    if not MANIFEST_PATH.exists() or MANIFEST_PATH.stat().st_size == 0:
        return pd.DataFrame()
    try:
        df = pd.read_csv(MANIFEST_PATH)
    except pd.errors.EmptyDataError:
        return pd.DataFrame()
    try:
        if "uploaded_at" in df.columns:
            df["uploaded_at"] = pd.to_datetime(df["uploaded_at"], errors="coerce")
            
        # Chuyển đổi tên thân thiện
        if "linh_vuc" in df.columns:
            df["linh_vuc"] = df["linh_vuc"].map(lambda x: MAP_LINH_VUC.get(str(x), str(x)))
        if "age_band" in df.columns:
            df["age_band"] = df["age_band"].map(lambda x: MAP_AGE_BAND.get(str(x), str(x)))
        if "doc_type" in df.columns:
            df["doc_type"] = df["doc_type"].map(lambda x: MAP_DOC_TYPE.get(str(x), str(x)))
            
        # Parse JSON and boolean fields
        if "need_manual" in df.columns:
            df["need_manual"] = df["need_manual"].astype(str).str.lower() == "true"
            
        # Rename columns to friendly names globally
        df = df.rename(columns={
            "doc_code": "Mã tài liệu",
            "name": "Tên tài liệu",
            "linh_vuc": "Lĩnh vực",
            "age_band": "Độ tuổi",
            "doc_type": "Loại tài liệu",
            "source_tier": "Độ uy tín",
            "status": "Trạng thái",
            "source_url": "Đường dẫn gốc",
            "need_manual": "Cần duyệt",
            "uploaded_at": "Ngày tải"
        })
        
        if "Trạng thái" in df.columns:
            df["Trạng thái"] = df["Trạng thái"].map({"need_manual": "Cần duyệt", "exported": "Hoàn thành"}).fillna(df["Trạng thái"])
            
        # Xử lý các giá trị kỹ thuật khó hiểu
        if "Mã tài liệu" in df.columns:
            df["Mã tài liệu"] = df["Mã tài liệu"].replace("NEED_MANUAL", "Chưa cấp mã")
            
        if "Tên tài liệu" in df.columns and "Đường dẫn gốc" in df.columns:
            # Nếu tên tài liệu là chuỗi hash (độ dài 64), lấy tên file từ URL
            def fix_name(row):
                name = str(row.get("Tên tài liệu", ""))
                if len(name) == 64 and name.isalnum(): # Giả định là mã SHA-256
                    url = str(row.get("Đường dẫn gốc", ""))
                    if url and "/" in url:
                        return url.split("/")[-1].split("?")[0] or "Tài liệu không tên"
                return name
            df["Tên tài liệu"] = df.apply(fix_name, axis=1)
            
        return df
    except Exception as e:
        st.error(f"Lỗi khi đọc dữ liệu: {e}")
        return pd.DataFrame()


def to_mau_log(dong: str) -> str:
    """Tô màu dòng log theo mức độ (loguru format)."""
    dong = dong.replace("<", "&lt;").replace(">", "&gt;")
    if "| ERROR" in dong or "| CRITICAL" in dong:
        return f'<span style="color:#ff7b72">{dong}</span>'
    if "| SUCCESS" in dong:
        return f'<span style="color:#3fb950">{dong}</span>'
    if "| WARNING" in dong:
        return f'<span style="color:#d29922">{dong}</span>'
    if "| INFO" in dong:
        return f'<span style="color:#79c0ff">{dong}</span>'
    return f'<span style="color:#8b949e">{dong}</span>'


def hien_thi_log(cac_dong: list[str]) -> None:
    """Hiển thị log dạng terminal đen có cuộn."""
    noi_dung = "\n".join(to_mau_log(d) for d in cac_dong[-80:])
    st.markdown(
        f"""<div style="
            background:#0d1117; color:#c9d1d9;
            font-family:'Fira Code',monospace; font-size:0.78rem;
            padding:0.8rem 1rem; border-radius:8px;
            border:1px solid #30363d;
            max-height:380px; overflow-y:auto;
            white-space:pre-wrap; word-break:break-all;
        ">{noi_dung}</div>""",
        unsafe_allow_html=True,
    )
