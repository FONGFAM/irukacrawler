# pyrefly: ignore [missing-import]
import streamlit as st
import pandas as pd
# pyrefly: ignore [missing-import]
import plotly.express as px
import os
from pathlib import Path

# Cấu hình trang
st.set_page_config(
    page_title="IruKa Crawler Dashboard",
    page_icon="🐬",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Đường dẫn tới file manifest
MANIFEST_PATH = Path("data/export/manifest.csv")

def load_data():
    if not MANIFEST_PATH.exists():
        return pd.DataFrame()
    
    try:
        df = pd.read_csv(MANIFEST_PATH)
        # Chuyển đổi timestamp
        if 'uploaded_at' in df.columns:
            df['uploaded_at'] = pd.to_datetime(df['uploaded_at'], errors='coerce')
        return df
    except Exception as e:
        st.error(f"Lỗi khi đọc file dữ liệu: {e}")
        return pd.DataFrame()

def main():
    st.title("🐬 IruKa Crawler - Quản trị Dữ liệu")
    st.markdown("Dashboard theo dõi tiến độ cào và đánh giá chất lượng phân loại tài liệu (Giai đoạn 3).")

    df = load_data()
    
    if df.empty:
        st.warning(f"Chưa có dữ liệu. Vui lòng chạy Crawler trước để sinh file `{MANIFEST_PATH}`.")
        return

    # Sidebar cho các bộ lọc
    st.sidebar.header("🔍 Bộ lọc (Filters)")
    
    # Lọc theo trạng thái
    status_filter = st.sidebar.multiselect(
        "Trạng thái (Status)",
        options=df['status'].unique() if 'status' in df.columns else [],
        default=df['status'].unique() if 'status' in df.columns else []
    )
    
    # Lọc theo Nguồn uy tín (Tier)
    tier_filter = st.sidebar.multiselect(
        "Nguồn uy tín (Source Tier)",
        options=df['source_tier'].unique() if 'source_tier' in df.columns else [],
        default=df['source_tier'].unique() if 'source_tier' in df.columns else []
    )
    
    # Áp dụng bộ lọc
    filtered_df = df.copy()
    if 'status' in filtered_df.columns and status_filter:
        filtered_df = filtered_df[filtered_df['status'].isin(status_filter)]
    if 'source_tier' in filtered_df.columns and tier_filter:
        filtered_df = filtered_df[filtered_df['source_tier'].isin(tier_filter)]

    # 1. TỔNG QUAN (KPIs)
    st.header("📊 Tổng quan (KPIs)")
    col1, col2, col3, col4 = st.columns(4)
    
    total_docs = len(filtered_df)
    need_manual = len(filtered_df[filtered_df.get('need_manual') == True]) if 'need_manual' in filtered_df.columns else 0
    success_docs = total_docs - need_manual
    
    # Tính tỷ lệ tự động
    auto_rate = (success_docs / total_docs * 100) if total_docs > 0 else 0
    
    with col1:
        st.metric("Tổng tài liệu đã quét", total_docs)
    with col2:
        st.metric("Tự động thành công", success_docs, f"{auto_rate:.1f}%")
    with col3:
        st.metric("Cần duyệt tay (Lỗi/Thiếu)", need_manual, f"-{(need_manual/total_docs*100):.1f}%" if total_docs > 0 else "0%")
    with col4:
        tiers = filtered_df['source_tier'].value_counts()
        tier_3_count = tiers.get(3, 0)
        st.metric("Tài liệu Tier 3 (Chất lượng cao)", tier_3_count)

    st.divider()

    # 2. BIỂU ĐỒ THỐNG KÊ
    st.header("📈 Phân tích Phân loại")
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("Phân bố theo Nhóm Nguồn (Tier)")
        if 'source_tier' in filtered_df.columns:
            tier_counts = filtered_df['source_tier'].value_counts().reset_index()
            tier_counts.columns = ['Tier', 'Số lượng']
            fig1 = px.pie(tier_counts, values='Số lượng', names='Tier', hole=0.4, 
                          color_discrete_sequence=px.colors.sequential.Teal)
            st.plotly_chart(fig1, use_container_width=True)

    with col_chart2:
        st.subheader("Phân bố theo Lĩnh vực (Lĩnh Vực)")
        if 'linh_vuc' in filtered_df.columns:
            lv_counts = filtered_df['linh_vuc'].value_counts().reset_index()
            lv_counts.columns = ['Lĩnh Vực', 'Số lượng']
            fig2 = px.bar(lv_counts, x='Lĩnh Vực', y='Số lượng', text='Số lượng',
                          color='Lĩnh Vực', color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig2, use_container_width=True)
            
    col_chart3, col_chart4 = st.columns(2)
    with col_chart3:
        st.subheader("Phân bố theo Độ tuổi (Age Band)")
        if 'age_band' in filtered_df.columns:
            age_counts = filtered_df['age_band'].value_counts().reset_index()
            age_counts.columns = ['Độ tuổi', 'Số lượng']
            fig3 = px.bar(age_counts, x='Độ tuổi', y='Số lượng', text='Số lượng',
                          color='Độ tuổi', color_discrete_sequence=px.colors.qualitative.Set2)
            st.plotly_chart(fig3, use_container_width=True)
            
    with col_chart4:
        st.subheader("Tỷ lệ Trạng thái (Thành công / Cần duyệt)")
        if 'status' in filtered_df.columns:
            st_counts = filtered_df['status'].value_counts().reset_index()
            st_counts.columns = ['Trạng thái', 'Số lượng']
            fig4 = px.pie(st_counts, values='Số lượng', names='Trạng thái',
                          color='Trạng thái', color_discrete_map={'exported':'#2ECC71', 'need_manual':'#E74C3C'})
            st.plotly_chart(fig4, use_container_width=True)

    st.divider()

    # 3. BẢNG DỮ LIỆU (RAW DATA)
    st.header("📋 Chi tiết Tài liệu (Raw Data)")
    st.markdown("Bạn có thể tải xuống CSV hoặc lọc trực tiếp trên bảng này.")
    
    # Cấu hình cột hiển thị
    display_columns = ['doc_code', 'name', 'linh_vuc', 'age_band', 'doc_type', 'source_tier', 'status', 'source_url']
    available_cols = [c for c in display_columns if c in filtered_df.columns]
    
    st.dataframe(
        filtered_df[available_cols],
        use_container_width=True,
        hide_index=True
    )

if __name__ == "__main__":
    main()
