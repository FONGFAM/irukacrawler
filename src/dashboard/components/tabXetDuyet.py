import hashlib

import pandas as pd
import streamlit as st

from src.dashboard.utils import (
    MANIFEST_PATH, MAP_AGE_BAND, MAP_DOC_TYPE, MAP_LINH_VUC, tai_du_lieu,
    hien_thi_xem_truoc, phan_loai_url
)
from src.taxonomy import (
    VALID_SUB_DOMAIN_IDS,
    VALID_SKILL_IDS,
    VALID_SERIES_CODES
)

# ─────────────────────────────────────────────────────────────────
# Helpers: lưu phê duyệt
# ─────────────────────────────────────────────────────────────────

def luu_phe_duyet(idx_goc, url):
    chon_lv = st.session_state.get("duyet_lv")
    chon_ab = st.session_state.get("duyet_ab")
    chon_dt = st.session_state.get("duyet_dt")

    chon_sd = st.session_state.get("duyet_sd", [])
    chon_sk = st.session_state.get("duyet_sk", [])
    chon_se = st.session_state.get("duyet_se", "")

    df_raw = pd.DataFrame()
    if MANIFEST_PATH.exists() and MANIFEST_PATH.stat().st_size > 0:
        df_raw = pd.read_csv(MANIFEST_PATH)

    if not df_raw.empty:
        # Ép kiểu các cột sang object để tránh lỗi TypeError khi Pandas gán chuỗi vào cột đang bị hiểu là float64 (do toàn NaN)
        for col in ["linh_vuc", "age_band", "doc_type", "sub_domain_ids", "skill_ids", "series_code", "doc_code"]:
            if col in df_raw.columns:
                df_raw[col] = df_raw[col].astype(object)
                
        df_raw.at[idx_goc, "linh_vuc"] = chon_lv
        df_raw.at[idx_goc, "age_band"] = chon_ab
        df_raw.at[idx_goc, "doc_type"] = chon_dt
        df_raw.at[idx_goc, "sub_domain_ids"] = ",".join(chon_sd) if chon_sd else ""
        df_raw.at[idx_goc, "skill_ids"] = ",".join(chon_sk) if chon_sk else ""
        df_raw.at[idx_goc, "series_code"] = chon_se
        
    df_raw.at[idx_goc, "need_manual"] = False
    df_raw.at[idx_goc, "status"] = "exported"

    short_hash = hashlib.md5(str(url).encode()).hexdigest()[:4].upper()
    lv_m = {"nhan_thuc": "NT", "ngon_ngu": "NN", "tham_my": "TM", "the_chat": "TC", "tinh_cam_xh": "TX"}.get(chon_lv, "XX")
    dt_m = chon_dt.split(".")[-1].upper()[:3] if "." in chon_dt else chon_dt[:3].upper()
    df_raw.at[idx_goc, "doc_code"] = f"DOC-{lv_m}-{chon_ab}-{dt_m}-{short_hash}"

    df_raw.to_csv(MANIFEST_PATH, index=False, encoding="utf-8")
    tai_du_lieu.clear()
    st.session_state.duyet_thanh_cong = True





# ─────────────────────────────────────────────────────────────────
# Main render
# ─────────────────────────────────────────────────────────────────

def render_tab_xet_duyet():
    if st.session_state.pop("duyet_thanh_cong", False):
        st.toast("Đã phê duyệt tài liệu thành công!", icon="✅")

    df_raw_csv = pd.DataFrame()
    if MANIFEST_PATH.exists():
        try:
            df_raw_csv = pd.read_csv(MANIFEST_PATH)
        except pd.errors.EmptyDataError:
            pass

    if df_raw_csv.empty or "need_manual" not in df_raw_csv.columns:
        st.info("Chưa có dữ liệu.", icon=":material/info:")
        return

    df_can_duyet_raw = df_raw_csv[df_raw_csv["need_manual"] == True]
    if df_can_duyet_raw.empty:
        st.success("Tuyệt vời! Không có tài liệu nào cần duyệt tay.", icon=":material/celebration:")
        return

    # Header
    col_h, col_badge = st.columns([4, 1])
    with col_h:
        st.subheader(":material/fact_check: Xét duyệt tài liệu", anchor=False)
    with col_badge:
        st.badge(f"{len(df_can_duyet_raw)} chờ duyệt", color="orange", icon=":material/pending:")

    df_hien_thi = tai_du_lieu()
    df_can_duyet_ht = df_hien_thi[df_hien_thi["Cần duyệt"] == True]
    if df_can_duyet_ht.empty:
        return

    chon = st.selectbox(
        "Chọn tài liệu cần xét duyệt",
        options=df_can_duyet_ht["Tên tài liệu"].tolist(),
        key="chon_tai_lieu_duyet",
        label_visibility="collapsed",
        placeholder="🔍 Chọn tài liệu để xem và phân loại...",
    )

    hang_ht = df_can_duyet_ht[df_can_duyet_ht["Tên tài liệu"] == chon].iloc[0]
    url = hang_ht.get("Đường dẫn gốc", "")

    hang_goc_rows = df_raw_csv[df_raw_csv["source_url"] == url]
    if hang_goc_rows.empty:
        return
    hang_goc = hang_goc_rows.iloc[0]
    hash_name = str(hang_goc.get("name", ""))
    loai = phan_loai_url(url)

    ICON_LOAI = {"youtube": ":material/smart_display:", "pdf": ":material/picture_as_pdf:", "docx": ":material/description:", "web": ":material/language:"}
    NHAN_LOAI = {"youtube": "YouTube", "pdf": "PDF", "docx": "Word/DOCX", "web": "Trang web"}

    col_panel, col_viewer = st.columns([1, 3], gap="medium")

    # ── Cột trái: thông tin + form phân loại ──
    with col_panel:
        with st.container(border=True):
            st.markdown(f"**{chon[:55]}{'...' if len(chon) > 55 else ''}**")
            st.caption(f"{ICON_LOAI.get(loai)} {NHAN_LOAI.get(loai)}")
            st.link_button(":material/open_in_new: Mở nguồn gốc", url, use_container_width=True)
            st.markdown("---")
            tier = hang_goc.get("source_tier", "?")
            uploaded_at = str(hang_goc.get("uploaded_at", ""))[:10]
            st.markdown(f":material/grade: **Độ uy tín:** `{tier}`")
            st.markdown(f":material/calendar_today: **Tải về:** `{uploaded_at}`")

        st.write("")

        with st.form("form_xet_duyet", border=True):
            st.markdown("##### :material/tune: Phân loại tài liệu")

            options_lv = list(MAP_LINH_VUC.keys())
            idx_lv = options_lv.index(hang_goc["linh_vuc"]) if hang_goc["linh_vuc"] in options_lv else 0
            st.selectbox("Lĩnh vực phát triển", options=options_lv, index=idx_lv,
                         format_func=lambda x: MAP_LINH_VUC.get(x, x), key="duyet_lv")

            options_ab = list(MAP_AGE_BAND.keys())
            idx_ab = options_ab.index(hang_goc["age_band"]) if hang_goc["age_band"] in options_ab else 0
            st.selectbox("Độ tuổi áp dụng", options=options_ab, index=idx_ab,
                         format_func=lambda x: MAP_AGE_BAND.get(x, x), key="duyet_ab")

            options_dt = list(MAP_DOC_TYPE.keys())
            idx_dt = options_dt.index(hang_goc["doc_type"]) if hang_goc["doc_type"] in options_dt else 0
            st.selectbox("Loại tài liệu", options=options_dt, index=idx_dt,
                         format_func=lambda x: MAP_DOC_TYPE.get(x, x), key="duyet_dt")

            with st.expander("Phân loại nâng cao (Tuỳ chọn)"):
                raw_sd = str(hang_goc.get("sub_domain_ids", ""))
                sd_list = [s.strip() for s in raw_sd.split(",")] if raw_sd and raw_sd != "nan" else []
                sd_list = [s for s in sd_list if s in VALID_SUB_DOMAIN_IDS]

                raw_sk = str(hang_goc.get("skill_ids", ""))
                sk_list = [s.strip() for s in raw_sk.split(",")] if raw_sk and raw_sk != "nan" else []
                sk_list = [s for s in sk_list if s in VALID_SKILL_IDS]

                raw_se = str(hang_goc.get("series_code", ""))
                se_val = raw_se if raw_se and raw_se != "nan" and raw_se in VALID_SERIES_CODES else ""

                st.multiselect("Chủ đề con (Sub-domain)", options=sorted(VALID_SUB_DOMAIN_IDS), default=sd_list, key="duyet_sd")
                st.multiselect("Kỹ năng (Skills)", options=sorted(VALID_SKILL_IDS), default=sk_list, key="duyet_sk")
                
                options_se = [""] + sorted(VALID_SERIES_CODES)
                idx_se = options_se.index(se_val) if se_val in options_se else 0
                st.selectbox("Bộ sách (Series)", options=options_se, index=idx_se, key="duyet_se", format_func=lambda x: x if x else "(Không chọn)")

            st.write("")
            idx_goc = hang_goc.name
            submitted = st.form_submit_button(
                "Phê duyệt & lưu", type="primary",
                icon=":material/done_all:", use_container_width=True,
            )
            if submitted:
                luu_phe_duyet(idx_goc, url)
                st.rerun()

    # ── Cột phải: xem tài liệu gốc ──
    with col_viewer:
        st.markdown("##### :material/preview: Tài liệu gốc")
        hien_thi_xem_truoc(url, hash_name)
