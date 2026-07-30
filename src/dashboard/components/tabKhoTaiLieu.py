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

        # ── Phân trang: tính sẵn, bảng trước, selector sau
        PAGE_SIZE = 20
        tong_trang = max(1, (len(hien_thi) - 1) // PAGE_SIZE + 1)
        page_key = "page_kho"
        trang_hien_tai = st.session_state.get(page_key, 1)
        start_row = (trang_hien_tai - 1) * PAGE_SIZE
        df_trang = hien_thi.iloc[start_row: start_row + PAGE_SIZE]

        # Bảng dữ liệu hiển thị toàn bộ các trường
        st.dataframe(df_trang, hide_index=True, height=450)

        # ── Phân trang nằm DƯỚI bảng
        col_pg1, col_pg2 = st.columns([3, 1])
        with col_pg1:
            st.caption(f"Tìm thấy {len(hien_thi)} bản ghi — trang {trang_hien_tai}/{tong_trang}")
        with col_pg2:
            st.number_input(
                f"Trang (/ {tong_trang})",
                min_value=1, max_value=tong_trang, value=trang_hien_tai, step=1,
                key=page_key,
                label_visibility="collapsed",
            )

        # Hành động — xuất CSV dựa trên trang hiển thị hiện tại (df_trang) hoặc toàn bộ (hien_thi)
        with st.container(horizontal=True):
            # Lấy các cột quan trọng
            if not hien_thi.empty:
                csv_data = hien_thi.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    "Tải xuống CSV thành phẩm",
                    data=csv_data,
                    file_name=f"thanhpham_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                    mime="text/csv",
                    icon=":material/download:",
                    type="primary"
                )
