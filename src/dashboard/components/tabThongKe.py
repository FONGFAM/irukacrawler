import streamlit as st
import plotly.express as px
from datetime import datetime
from src.dashboard.utils import tai_du_lieu

def render_tab_thong_ke():
    df = tai_du_lieu()

    if df.empty:
        st.info(
            "Chưa có dữ liệu. Hãy chạy thu thập ở tab **Tìm & Thu thập** trước.",
            icon=":material/info:",
        )
    else:
        # Bộ lọc nhanh trong sidebar
        with st.sidebar:
            st.subheader(":material/filter_list: Bộ lọc")
            loc_trang_thai = st.multiselect(
                "Trạng thái",
                options=df["Trạng thái"].unique().tolist() if "Trạng thái" in df.columns else [],
                default=df["Trạng thái"].unique().tolist() if "Trạng thái" in df.columns else [],
            )
            _tier_options = sorted([x for x in df["Độ uy tín"].dropna().unique().tolist() if str(x) not in ("", "nan")]) if "Độ uy tín" in df.columns else []
            def _format_tier(x):
                try:
                    return {1: "⭐ Tier 1 — Blog/GV", 2: "⭐⭐ Tier 2 — SGK/GT", 3: "⭐⭐⭐ Tier 3 — Bộ GD"}.get(int(float(x)), str(x))
                except:
                    return "Không rõ"

            loc_tier = st.multiselect(
                "Mức độ uy tín (Tier)",
                options=_tier_options,
                default=_tier_options,
                format_func=_format_tier,
            )
            st.caption(f"Cập nhật lúc: {datetime.now().strftime('%H:%M:%S')}")
            def lam_moi_du_lieu():
                tai_du_lieu.clear()
                
            st.button("Làm mới dữ liệu", icon=":material/refresh:", on_click=lam_moi_du_lieu)

        fdf = df.copy()
        if loc_trang_thai and "Trạng thái" in fdf.columns:
            fdf = fdf[fdf["Trạng thái"].isin(loc_trang_thai)]
        if loc_tier and "Độ uy tín" in fdf.columns:
            fdf = fdf[fdf["Độ uy tín"].isin(loc_tier)]

        # KPIs
        st.subheader("Tổng quan")
        tong = len(fdf)
        can_duyet = len(fdf[fdf["Trạng thái"] == "Cần duyệt"]) if "Trạng thái" in fdf.columns else 0
        thanh_cong = tong - can_duyet
        ty_le = thanh_cong / tong * 100 if tong > 0 else 0
        tier3 = len(fdf[fdf["Độ uy tín"].astype(str) == "3"]) if "Độ uy tín" in fdf.columns else 0

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Tổng tài liệu đã thu thập", tong)
        c2.metric("Tự động phân loại thành công", thanh_cong, f"{ty_le:.0f}%")
        c3.metric("Cần kiểm tra thủ công", can_duyet)
        c4.metric("Tài liệu Bộ GD (chất lượng cao)", tier3)

        # Biểu đồ
        st.subheader("Phân bố tài liệu")
        hang1_t1, hang1_t2 = st.columns(2)

        with hang1_t1:
            if "Độ uy tín" in fdf.columns:
                tc = fdf["Độ uy tín"].value_counts().reset_index()
                tc.columns = ["Tier", "Số lượng"]
                tc["Nhãn"] = tc["Tier"].map({1: "Tier 1 — Blog/GV", 2: "Tier 2 — SGK/GT", 3: "Tier 3 — Bộ GD"})
                fig = px.pie(tc, values="Số lượng", names="Nhãn", hole=0.45,
                             title="Phân bố theo mức uy tín nguồn",
                             color_discrete_sequence=["#58a6ff", "#3fb950", "#d29922"])
                st.plotly_chart(fig)

        with hang1_t2:
            if "Lĩnh vực" in fdf.columns:
                lc = fdf["Lĩnh vực"].value_counts().reset_index()
                lc.columns = ["Lĩnh vực", "Số lượng"]
                fig = px.bar(lc, x="Lĩnh vực", y="Số lượng", text="Số lượng",
                             title="Phân bố theo lĩnh vực giáo dục",
                             color_discrete_sequence=["#58a6ff"])
                fig.update_traces(textposition="outside")
                st.plotly_chart(fig)

        hang2_t1, hang2_t2 = st.columns(2)
        with hang2_t1:
            if "Độ tuổi" in fdf.columns:
                ac = fdf["Độ tuổi"].value_counts().reset_index()
                ac.columns = ["Độ tuổi", "Số lượng"]
                fig = px.bar(ac, x="Độ tuổi", y="Số lượng", text="Số lượng",
                             title="Phân bố theo độ tuổi",
                             color_discrete_sequence=["#3fb950"])
                fig.update_traces(textposition="outside")
                st.plotly_chart(fig)

        with hang2_t2:
            if "Loại tài liệu" in fdf.columns:
                dtc = fdf["Loại tài liệu"].value_counts().head(8).reset_index()
                dtc.columns = ["Loại tài liệu", "Số lượng"]
                fig = px.bar(dtc, x="Số lượng", y="Loại tài liệu", orientation="h",
                             title="Top loại tài liệu phổ biến",
                             color="Số lượng", color_continuous_scale="Blues")
                st.plotly_chart(fig)
