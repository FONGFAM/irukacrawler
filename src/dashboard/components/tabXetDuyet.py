import streamlit as st
import pandas as pd
import hashlib
from src.dashboard.utils import MANIFEST_PATH, MAP_LINH_VUC, MAP_AGE_BAND, MAP_DOC_TYPE, tai_du_lieu

def luu_phe_duyet(idx_goc, url):
    chon_lv = st.session_state.get("duyet_lv")
    chon_ab = st.session_state.get("duyet_ab")
    chon_dt = st.session_state.get("duyet_dt")
    
    df_raw = pd.DataFrame()
    if MANIFEST_PATH.exists() and MANIFEST_PATH.stat().st_size > 0:
        df_raw = pd.read_csv(MANIFEST_PATH)
        
    if not df_raw.empty:
        df_raw.at[idx_goc, "linh_vuc"] = chon_lv
        df_raw.at[idx_goc, "age_band"] = chon_ab
        df_raw.at[idx_goc, "doc_type"] = chon_dt
    df_raw.at[idx_goc, "need_manual"] = False
    df_raw.at[idx_goc, "status"] = "exported"
    
    short_hash = hashlib.md5(str(url).encode()).hexdigest()[:4].upper()
    lv_m = {"nhan_thuc": "NT", "ngon_ngu": "NN", "tham_my": "TM", "the_chat": "TC", "tinh_cam_xh": "TX"}.get(chon_lv, "XX")
    dt_m = chon_dt.split(".")[-1].upper()[:3] if "." in chon_dt else chon_dt[:3].upper()
    df_raw.at[idx_goc, "doc_code"] = f"DOC-{lv_m}-{chon_ab}-{dt_m}-{short_hash}"
    
    df_raw.to_csv(MANIFEST_PATH, index=False, encoding="utf-8")
    tai_du_lieu.clear()
    st.session_state.duyet_thanh_cong = True

def render_tab_xet_duyet():
    if st.session_state.pop("duyet_thanh_cong", False):
        st.toast("Đã phê duyệt tài liệu thành công!", icon="✅")
        
    df_raw = pd.DataFrame()
    if MANIFEST_PATH.exists():
        try:
            df_raw = pd.read_csv(MANIFEST_PATH)
        except pd.errors.EmptyDataError:
            pass
    
    if df_raw.empty or "need_manual" not in df_raw.columns:
        st.info("Chưa có dữ liệu.", icon=":material/info:")
    else:
        df_can_duyet_raw = df_raw[df_raw["need_manual"] == True]
        if df_can_duyet_raw.empty:
            st.success("Tuyệt vời! Không có tài liệu nào cần duyệt tay.", icon=":material/celebration:")
        else:
            st.subheader(f"Có {len(df_can_duyet_raw)} tài liệu cần duyệt", divider=True)
            
            df_hien_thi = tai_du_lieu()
            df_can_duyet_ht = df_hien_thi[df_hien_thi["Cần duyệt"] == True]
            
            if not df_can_duyet_ht.empty:
                chon = st.selectbox(
                    "Chọn tài liệu cần xét duyệt",
                    options=df_can_duyet_ht["Tên tài liệu"].tolist(),
                    key="chon_tai_lieu_duyet"
                )
                
                hang_ht = df_can_duyet_ht[df_can_duyet_ht["Tên tài liệu"] == chon].iloc[0]
                url = hang_ht.get("Đường dẫn gốc", "")
                
                hang_goc = df_raw[df_raw["source_url"] == url]
                if not hang_goc.empty:
                    hang_goc = hang_goc.iloc[0]
                    st.write(f"**Đường dẫn gốc:** [{url}]({url})")
                    
                    with st.form("form_xet_duyet", border=True):
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            options_lv = list(MAP_LINH_VUC.keys())
                            idx_lv = options_lv.index(hang_goc["linh_vuc"]) if hang_goc["linh_vuc"] in options_lv else 0
                            st.selectbox("Lĩnh vực", options=options_lv, index=idx_lv, format_func=lambda x: MAP_LINH_VUC.get(x, x), key="duyet_lv")
                            
                        with col2:
                            options_ab = list(MAP_AGE_BAND.keys())
                            idx_ab = options_ab.index(hang_goc["age_band"]) if hang_goc["age_band"] in options_ab else 0
                            st.selectbox("Độ tuổi", options=options_ab, index=idx_ab, format_func=lambda x: MAP_AGE_BAND.get(x, x), key="duyet_ab")
                            
                        with col3:
                            options_dt = list(MAP_DOC_TYPE.keys())
                            idx_dt = options_dt.index(hang_goc["doc_type"]) if hang_goc["doc_type"] in options_dt else 0
                            st.selectbox("Loại tài liệu", options=options_dt, index=idx_dt, format_func=lambda x: MAP_DOC_TYPE.get(x, x), key="duyet_dt")
                            
                        idx_goc = hang_goc.name
                        st.form_submit_button(
                            "Lưu & Phê duyệt", 
                            type="primary", 
                            icon=":material/done_all:",
                            on_click=luu_phe_duyet,
                            args=(idx_goc, url)
                        )
