import streamlit as st
import pandas as pd
import hashlib
from urllib.parse import urlparse
from src.dashboard.utils import tai_du_lieu, MANIFEST_PATH, MAP_LINH_VUC, MAP_AGE_BAND, MAP_DOC_TYPE
from src.dashboard.components.viewer import render_document_preview

@st.dialog("📝 Duyệt tài liệu", width="large")
def popup_duyet_tai_lieu(idx_goc, url, ten_goi_y, linh_vuc, age_band, doc_type, source_tier, sub_domains="", levels="", local_path="", uploaded_at=""):
    df_raw = pd.DataFrame()
    if MANIFEST_PATH.exists() and MANIFEST_PATH.stat().st_size > 0:
        df_raw = pd.read_csv(MANIFEST_PATH)
        
    domain = urlparse(str(url)).netloc if str(url).startswith("http") else "Local File"
    col_h1, col_h2, col_h3, col_h4 = st.columns([1.5, 1.5, 1.5, 1])
    with col_h1:
        st.write(" ") 
    with col_h2:
        date_str = str(uploaded_at).split("T")[0] if pd.notnull(uploaded_at) and str(uploaded_at).strip() else "Mới đây"
        st.markdown(f"📅 **Crawled:** {date_str}")
    with col_h3:
        st.markdown(f"🌐 **Nguồn:** {domain}")
    with col_h4:
        st.link_button("Chi tiết nguồn ↗", str(url), use_container_width=True)
        
    st.divider()
    
    # Swap layout: Trái 1 (Form), Phải 1.8 (Preview) giống hình ảnh mẫu
    col_form, col_preview = st.columns([1, 1.8], gap="large")
    
    with col_form:
        st.markdown("### Thông tin tài liệu")
        with st.form("form_xet_duyet", border=False):
            ten_moi = st.text_area("Tên tài liệu", value=ten_goi_y, height=80)
            
            options_lv = list(MAP_LINH_VUC.keys())
            idx_lv = options_lv.index(linh_vuc) if linh_vuc in options_lv else 0
            chon_lv = st.selectbox("Lĩnh vực chính *", options=options_lv, index=idx_lv, format_func=lambda x: MAP_LINH_VUC.get(x, x))
            
            options_dt = list(MAP_DOC_TYPE.keys())
            idx_dt = options_dt.index(doc_type) if doc_type in options_dt else 0
            chon_dt = st.selectbox("Loại tài liệu *", options=options_dt, index=idx_dt, format_func=lambda x: MAP_DOC_TYPE.get(x, x))
            
            options_ab = list(MAP_AGE_BAND.keys())
            idx_ab = options_ab.index(age_band) if age_band in options_ab else 0
            chon_ab = st.selectbox("Độ tuổi *", options=options_ab, index=idx_ab, format_func=lambda x: MAP_AGE_BAND.get(x, x))
            
            chon_tier = st.selectbox("Tier Uy Tín *", options=[1, 2, 3], index=[1, 2, 3].index(int(source_tier)) if pd.notnull(source_tier) and int(source_tier) in [1, 2, 3] else 0)
            
            # Lĩnh vực con
            from src.dashboard.utils import MAP_SUB_DOMAIN, MAP_LEVELS
            sub_rev = {v: k for k, v in MAP_SUB_DOMAIN.items()}
            sub_opts = list(MAP_SUB_DOMAIN.values())
            sub_defs = [MAP_SUB_DOMAIN[s.strip()] for s in str(sub_domains).split(",") if s.strip() in MAP_SUB_DOMAIN]
            chon_subs_lbl = st.pills("Sub-domain *", options=sub_opts, default=sub_defs, selection_mode="multi", key=f"sub_{idx_goc}")
            # Ensure it is a list even if pill returns None
            if not chon_subs_lbl: chon_subs_lbl = []
            chon_subs = [sub_rev[lbl] for lbl in chon_subs_lbl]
            
            # Mức độ
            lvl_rev = {v: k for k, v in MAP_LEVELS.items()}
            lvl_opts = list(MAP_LEVELS.values())
            lvl_defs = [MAP_LEVELS[s.strip()] for s in str(levels).split(",") if s.strip() in MAP_LEVELS]
            chon_levels_lbl = st.pills("Mức độ (Tùy chọn)", options=lvl_opts, default=lvl_defs, selection_mode="multi", key=f"lvl_{idx_goc}")
            if not chon_levels_lbl: chon_levels_lbl = []
            chon_levels = [lvl_rev[lbl] for lbl in chon_levels_lbl]

            ghi_chu = st.text_area("Ghi chú", placeholder="Nhập ghi chú (Lý do chấp nhận / từ chối)...", height=100)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                submitted = st.form_submit_button("Chấp nhận", type="primary", use_container_width=True)
            with col_btn2:
                btn_reject = st.form_submit_button("Từ chối", use_container_width=True)

        if submitted:
            if not df_raw.empty:
                # Ép kiểu dữ liệu để tránh lỗi pandas khi assign (vd: age_band bị infer thành int64)
                for col in ["linh_vuc", "age_band", "doc_type", "sub_domain_ids", "level_ids"]:
                    if col in df_raw.columns:
                        df_raw[col] = df_raw[col].astype(str)
                
                df_raw.at[idx_goc, "name"] = ten_moi
                df_raw.at[idx_goc, "linh_vuc"] = chon_lv
                df_raw.at[idx_goc, "age_band"] = chon_ab
                df_raw.at[idx_goc, "doc_type"] = chon_dt
                df_raw.at[idx_goc, "source_tier"] = int(chon_tier)
                df_raw.at[idx_goc, "sub_domain_ids"] = ",".join(chon_subs)
                df_raw.at[idx_goc, "level_ids"] = ",".join(chon_levels)
                df_raw.at[idx_goc, "need_manual"] = False
                df_raw.at[idx_goc, "status"] = "exported"
                
                short_hash = hashlib.md5(str(url).encode()).hexdigest()[:4].upper()
                lv_m = {"nhan_thuc": "NT", "ngon_ngu": "NN", "tham_my": "TM", "the_chat": "TC", "tinh_cam_xh": "TX"}.get(chon_lv, "XX")
                dt_m = chon_dt.split(".")[-1].upper()[:3] if "." in chon_dt else chon_dt[:3].upper()
                df_raw.at[idx_goc, "doc_code"] = f"DOC-{lv_m}-{chon_ab}-{dt_m}-{short_hash}"
                
                df_raw.to_csv(MANIFEST_PATH, index=False, encoding="utf-8-sig")
                tai_du_lieu.clear()
                st.session_state.duyet_thanh_cong = True
                st.rerun()
                
        if btn_reject:
            if not df_raw.empty:
                df_raw.at[idx_goc, "status"] = "rejected"
                df_raw.at[idx_goc, "need_manual"] = False
                df_raw.to_csv(MANIFEST_PATH, index=False, encoding="utf-8-sig")
                tai_du_lieu.clear()
                st.toast("Đã từ chối tài liệu.", icon="❌")
                st.rerun()
                
    with col_preview:
        st.markdown("### Xem trước tài liệu")
        hash_name = hashlib.sha256(str(url).encode()).hexdigest()
        render_document_preview(url, hash_name, local_path)

def render_tab_danh_sach():
    # CSS Custom cho Popup giống thiết kế mẫu (buttons màu xanh, đỏ)
    st.markdown("""
        <style>
        /* Tùy chỉnh màu nút trong form duyệt */
        div[data-testid="stForm"] button[kind="primary"] {
            background-color: #16a34a; /* Xanh lá */
            color: white;
            border: none;
            font-weight: 600;
        }
        div[data-testid="stForm"] button[kind="secondary"] {
            background-color: #ef4444; /* Đỏ */
            color: white;
            border: none;
            font-weight: 600;
        }
        </style>
    """, unsafe_allow_html=True)

    if st.session_state.pop("duyet_thanh_cong", False):
        st.toast("Đã phê duyệt tài liệu thành công! Tài liệu đã được chuyển sang Kho Thành Phẩm.", icon="✅")

    df = tai_du_lieu()

    if df.empty:
        st.info("Chưa có dữ liệu. Vui lòng quay lại tab Tìm & Thu thập.", icon=":material/info:")
        return

    # Chỉ hiển thị các file CẦN DUYỆT ở tab này (bản nháp/chờ duyệt)
    # df["Cần duyệt"] được tính trong utils.py dựa vào cột need_manual
    df_can_duyet = df[df["Cần duyệt"] == True]

    if df_can_duyet.empty:
        st.success("Tuyệt vời! Không có tài liệu nào đang chờ duyệt.", icon=":material/celebration:")
    else:
        st.subheader(f"Danh sách chờ duyệt — {len(df_can_duyet):,} bản ghi")
        
        # Bảng dữ liệu có on_select để kích hoạt popup
        cot_hien_thi = ["Mã tài liệu", "Tên tài liệu", "Lĩnh vực", "Độ tuổi", "Loại tài liệu", "Độ uy tín"]
        cot_co_san = [c for c in cot_hien_thi if c in df_can_duyet.columns]
        
        st.info("💡 **Hướng dẫn:** Click chọn một hàng trong bảng dưới đây để mở Popup chỉnh sửa và phê duyệt tài liệu.")
        event = st.dataframe(
            df_can_duyet[cot_co_san], 
            hide_index=True, 
            height=400,
            selection_mode="single-row",
            on_select="rerun"
        )
        
        if event.selection.rows:
            selected_row_idx = event.selection.rows[0]
            # Lấy index thực tế của dòng trong df_can_duyet
            real_index = df_can_duyet.index[selected_row_idx]
            
            # Lấy dòng nguyên gốc từ MANIFEST_PATH
            df_raw = pd.DataFrame()
            if MANIFEST_PATH.exists() and MANIFEST_PATH.stat().st_size > 0:
                df_raw = pd.read_csv(MANIFEST_PATH)
                
            if not df_raw.empty and real_index in df_raw.index:
                hang_goc = df_raw.loc[real_index]
                
                url = hang_goc.get("source_url", "")
                ten_goi_y = hang_goc.get("name", "")
                linh_vuc = hang_goc.get("linh_vuc", "")
                age_band = hang_goc.get("age_band", "")
                doc_type = hang_goc.get("doc_type", "")
                source_tier = hang_goc.get("source_tier", 1)
                sub_domains = hang_goc.get("sub_domain_ids", "")
                levels = hang_goc.get("level_ids", "")
                local_path = hang_goc.get("local_path", "")
                uploaded_at = hang_goc.get("uploaded_at", "")
                
                # Gọi thẳng hàm popup để hiển thị luôn khi người dùng chọn dòng
                popup_duyet_tai_lieu(real_index, url, ten_goi_y, linh_vuc, age_band, doc_type, source_tier, sub_domains, levels, local_path, uploaded_at)
