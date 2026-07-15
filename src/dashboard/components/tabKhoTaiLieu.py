import streamlit as st
import pandas as pd
from datetime import datetime
from src.dashboard.utils import tai_du_lieu, MANIFEST_PATH

def render_tab_kho_tai_lieu():
    df = tai_du_lieu()

    if df.empty:
        st.info("Chưa có dữ liệu.", icon=":material/info:")
        return

    # Chỉ lấy những tài liệu đã được duyệt (need_manual == False) và đã export thành phẩm
    # df_hien_thi chứa các cột tiếng Việt: "Mã tài liệu", "Tên tài liệu", ... và "Cần duyệt"
    if "Trạng thái" in df.columns:
        df_thanh_pham = df[(df["Cần duyệt"] == False) & (df["Trạng thái"] == "Hoàn thành")]
    else:
        df_thanh_pham = df[df["Cần duyệt"] == False]
    if df_thanh_pham.empty:
        st.info("Chưa có tài liệu nào được phê duyệt thành phẩm.", icon=":material/info:")
    else:
        st.subheader(f"Kho Thành Phẩm — {len(df_thanh_pham):,} bản ghi đã duyệt")

        # Tìm kiếm nhanh
        tim_kiem = st.text_input(
            "Tìm kiếm trong kho thành phẩm",
            placeholder="Nhập tên tài liệu, loại, URL…",
            label_visibility="collapsed",
        )
        if tim_kiem:
            mask = df_thanh_pham.apply(lambda col: col.astype(str).str.contains(tim_kiem, case=False, na=False)).any(axis=1)
            hien_thi = df_thanh_pham[mask]
        else:
            hien_thi = df_thanh_pham

        # Bảng dữ liệu hiển thị toàn bộ các trường
        st.dataframe(hien_thi, hide_index=True, height=450)

        # Hành động
        with st.container(horizontal=True):
            if MANIFEST_PATH.exists():
                df_raw = pd.DataFrame()
                if MANIFEST_PATH.stat().st_size > 0:
                    df_raw = pd.read_csv(MANIFEST_PATH)
                df_export = df_raw.iloc[hien_thi.index]
                csv_data = df_export.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "Tải xuống CSV để import vào IruKa",
                    data=csv_data,
                    file_name=f"iruka_thanhpham_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    icon=":material/download:",
                    type="primary"
                )
