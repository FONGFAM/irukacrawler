import streamlit as st
from datetime import datetime
from src.dashboard.utils import tai_du_lieu, MANIFEST_PATH, hien_thi_xem_truoc

def render_tab_danh_sach():
    df = tai_du_lieu()

    if df.empty:
        st.info("Chưa có dữ liệu.", icon=":material/info:")
    else:
        st.subheader(f"Kho tài liệu — {len(df):,} bản ghi")

        # Tìm kiếm nhanh
        tim_kiem = st.text_input(
            "Tìm kiếm trong danh sách",
            placeholder="Nhập tên tài liệu, loại, URL…",
            label_visibility="collapsed",
        )
        if tim_kiem:
            mask = df.apply(lambda col: col.astype(str).str.contains(tim_kiem, case=False, na=False)).any(axis=1)
            hien_thi = df[mask]
        else:
            hien_thi = df

        # Bảng dữ liệu
        cot_hien_thi = ["Mã tài liệu", "Tên tài liệu", "Lĩnh vực", "Độ tuổi", "Loại tài liệu", "Độ uy tín", "Trạng thái"]
        cot_co_san = [c for c in cot_hien_thi if c in hien_thi.columns]
        st.dataframe(hien_thi[cot_co_san], hide_index=True, height=380)

        # Hành động
        with st.container(horizontal=True):
            if MANIFEST_PATH.exists():
                import pandas as pd
                df_raw = pd.DataFrame()
                if MANIFEST_PATH.stat().st_size > 0:
                    df_raw = pd.read_csv(MANIFEST_PATH)
                df_export = df_raw.iloc[hien_thi.index]
                csv_data = df_export.to_csv(index=False).encode("utf-8")
                st.download_button(
                    "Tải xuống CSV",
                    data=csv_data,
                    file_name=f"iruka_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    icon=":material/download:",
                )

        # Chi tiết một tài liệu
        st.subheader("Xem chi tiết")
        if "Tên tài liệu" in hien_thi.columns and not hien_thi.empty:
            ma_chon = st.selectbox(
                "Chọn tài liệu để xem chi tiết",
                options=["— Chọn tài liệu —"] + hien_thi["Tên tài liệu"].dropna().tolist(),
                label_visibility="collapsed",
            )
            if ma_chon != "— Chọn tài liệu —":
                hang = hien_thi[hien_thi["Tên tài liệu"] == ma_chon].iloc[0]
                url = hang.get("Đường dẫn gốc", "")
                
                # Lấy hash_name từ file manifest gốc để render file local
                hash_name = ""
                if MANIFEST_PATH.exists() and url:
                    import pandas as pd
                    try:
                        df_r = pd.read_csv(MANIFEST_PATH)
                        hang_goc_rows = df_r[df_r["source_url"] == url]
                        if not hang_goc_rows.empty:
                            hash_name = str(hang_goc_rows.iloc[0].get("name", ""))
                    except Exception:
                        pass
                
                col_panel, col_viewer = st.columns([1, 2], gap="medium")
                with col_panel:
                    with st.container(border=True):
                        st.markdown(f"**Tên:** {hang.get('Tên tài liệu', '—')}")
                        st.markdown(f"**Mã:** `{hang.get('Mã tài liệu', '—')}`")
                        st.markdown(f"**Loại:** `{hang.get('Loại tài liệu', '—')}`")
                        st.markdown(f"**Lĩnh vực:** `{hang.get('Lĩnh vực', '—')}`")
                        st.markdown(f"**Độ tuổi:** `{hang.get('Độ tuổi', '—')}`")
                        st.markdown(f"**Tier:** `{hang.get('Độ uy tín', '—')}`")
                        
                        if url and str(url).startswith("http"):
                            st.link_button(":material/open_in_new: Mở nguồn gốc", url, use_container_width=True)
                        
                        need_m = str(hang.get("Cần duyệt", "False")).lower() == "true"
                        if need_m:
                            st.badge("Cần duyệt tay", color="orange", icon=":material/warning:")
                        else:
                            st.badge("Phân loại tự động", color="green", icon=":material/check_circle:")
                
                with col_viewer:
                    st.markdown("##### :material/preview: Xem trước tài liệu")
                    if hash_name or (url and "youtube" in url.lower()):
                        hien_thi_xem_truoc(url, hash_name)
                    else:
                        st.info("Không có dữ liệu xem trước.")
