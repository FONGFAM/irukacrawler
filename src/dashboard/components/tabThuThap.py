import streamlit as st
import os
import subprocess
from pathlib import Path
from src.dashboard.utils import PYTHON_BIN, hien_thi_log, tai_du_lieu

def render_tab_thu_thap():
    st.subheader("Nhập từ khoá để thu thập tài liệu")

    # ── Hướng dẫn nhanh (thu gọn) ───────────────────────────
    with st.expander(":material/help: Hướng dẫn sử dụng", icon=":material/help:"):
        st.markdown("""
**Cách dùng:**
1. Nhập từ khoá tìm kiếm vào ô bên dưới (mỗi dòng một chủ đề).
2. Chọn nguồn tìm kiếm và số lượng kết quả mong muốn.
3. Nhấn **Bắt đầu thu thập** và chờ hệ thống xử lý.
4. Kết quả sẽ xuất hiện ở tab **Danh sách tài liệu** sau khi hoàn thành.

**Lưu ý:**
- Mỗi từ khoá trên một dòng (ví dụ: *giáo án toán mầm non*).
- Hệ thống tự động phân loại tài liệu theo lĩnh vực, độ tuổi và loại tài liệu.
- Tài liệu cần duyệt thêm sẽ được gắn cờ ⚠️ để người quản trị xem lại.
""")

    # ── Form nhập liệu ───────────────────────────────────────
    with st.form("form_tim_kiem", border=True):
        tu_khoa = st.text_area(
            "Từ khoá tìm kiếm",
            value="giáo án kể chuyện mầm non 5-6 tuổi",
            height=100,
            placeholder="Mỗi dòng một chủ đề, ví dụ:\ngiáo án Toán mầm non\nSKKN tạo hình trẻ 4 tuổi\nchương trình GDMN Bộ GD",
            help="Hệ thống sẽ tìm kiếm tài liệu PDF/DOCX liên quan trên internet cho từng chủ đề.",
        )

        col_cfg1, col_cfg2, col_cfg3 = st.columns(3)
        with col_cfg1:
            nguon = st.selectbox(
                "Nguồn tìm kiếm",
                options=["tavily", "exa", "youtube"],
                format_func=lambda x: "Tavily (khuyên dùng)" if x == "tavily" else ("Exa (học thuật)" if x == "exa" else "YouTube (Video)"),
                help="Tavily phù hợp cho PDF/DOCX giáo án. Exa tốt hơn cho tài liệu nghiên cứu. YouTube để tải video phụ đề.",
            )
        with col_cfg2:
            so_ket_qua = st.slider(
                "Số kết quả / chủ đề",
                min_value=1, max_value=15, value=5,
                help="Số lượng tài liệu tìm kiếm cho mỗi từ khoá. Nhiều hơn thì mất thêm thời gian.",
            )
        with col_cfg3:
            song_song = st.slider(
                "Tải đồng thời",
                min_value=1, max_value=8, value=3,
                help="Số tài liệu tải xuống cùng lúc. Nếu gặp lỗi mạng, giảm xuống 1-2.",
            )

        btn_bat_dau = st.form_submit_button(
            "Bắt đầu thu thập",
            type="primary",
            icon=":material/download:",
        )

    # ── Xử lý khi nhấn nút ──────────────────────────────────
    if btn_bat_dau:
        danh_sach_tu_khoa = [q.strip() for q in tu_khoa.splitlines() if q.strip()]
        if not danh_sach_tu_khoa:
            st.error("Vui lòng nhập ít nhất một từ khoá.", icon=":material/error:")
        else:
            st.session_state.log_chay = []
            st.session_state.trang_thai = "dang_chay"

            lenh = [
                PYTHON_BIN, "-m", "src.main",
                "--queries", ",".join(danh_sach_tu_khoa),
                "--provider", nguon,
                "--limit",    str(so_ket_qua),
                "--semaphore", str(song_song),
            ]

            vung_log  = st.empty()
            vung_status = st.empty()

            with st.status(
                f"Đang thu thập tài liệu cho **{len(danh_sach_tu_khoa)} chủ đề**…",
                expanded=True,
            ) as hop_trang_thai:

                st.write(f":material/search: Từ khoá: {', '.join(danh_sach_tu_khoa)}")
                st.write(f":material/settings: Nguồn: `{nguon}` — {so_ket_qua} kết quả/chủ đề — {song_song} luồng song song")

                cac_dong: list[str] = []
                dem_thanh_cong = 0
                dem_loi = 0

                try:
                    moi_truong = os.environ.copy()
                    moi_truong["PYTHONPATH"] = str(Path.cwd())

                    tien_trinh = subprocess.Popen(
                        lenh,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT,
                        text=True,
                        encoding="utf-8",
                        errors="replace",
                        env=moi_truong,
                        cwd=str(Path.cwd()),
                    )

                    for dong_raw in tien_trinh.stdout:  # type: ignore[union-attr]
                        dong = dong_raw.rstrip()
                        cac_dong.append(dong)
                        st.session_state.log_chay = cac_dong.copy()

                        if "| SUCCESS" in dong:
                            dem_thanh_cong += 1
                        elif "| ERROR" in dong:
                            dem_loi += 1
                        elif "| WARNING" in dong and ("Cần duyệt tay" in dong or "chuyển duyệt tay" in dong):
                            dem_can_duyet += 1

                        if "===STATS===" in dong:
                            try:
                                import json
                                stats_str = dong.split("===STATS===")[1].strip()
                                st.session_state.last_stats = json.loads(stats_str)
                            except:
                                pass

                        # Cập nhật bảng log theo thời gian thực
                        vung_log.empty()
                        with vung_log:
                            hien_thi_log(cac_dong)

                    tien_trinh.wait()
                    ma_thoat = tien_trinh.returncode

                    st.session_state.trang_thai = "xong" if ma_thoat == 0 else "loi"
                    # Xoá cache để tab thống kê & danh sách tải lại dữ liệu mới
                    tai_du_lieu.clear()

                    if ma_thoat == 0:
                        hop_trang_thai.update(
                            label=f"Hoàn thành! ✅ {dem_thanh_cong} tải xong | ⚠️ {dem_can_duyet} cần duyệt",
                            state="complete",
                        )
                        st.toast(f"Thu thập xong! {dem_thanh_cong} tài liệu được lưu.", icon=":material/check_circle:")
                        
                        # Hiển thị số liệu trực quan
                        if "last_stats" in st.session_state:
                            s = st.session_state.last_stats
                            st.success("Báo cáo kết quả thu thập:")
                            c1, c2, c3, c4 = st.columns(4)
                            c1.metric("🔍 Tìm thấy", f"{s.get('total_searched', 0)} links")
                            c2.metric("❌ Bỏ qua / Lỗi", f"{s.get('failed', 0) + s.get('deduplicated', 0)} links", help="Bao gồm link trùng lặp, ngoài phạm vi, hoặc bị chặn tải.")
                            c3.metric("✅ Tải & Convert thành công", f"{s.get('success', 0)} tài liệu")
                            c4.metric("⚠️ Cần duyệt tay", f"{s.get('manual', 0)} tài liệu")
                            
                    else:
                        hop_trang_thai.update(label="Có lỗi xảy ra trong quá trình thu thập.", state="error")

                except Exception as e:
                    hop_trang_thai.update(label=f"Lỗi khởi chạy: {e}", state="error")
                    st.session_state.trang_thai = "loi"

    # ── Hiển thị lại log nếu đã có kết quả trước đó ─────────
    elif st.session_state.log_chay:
        trang_thai = st.session_state.trang_thai
        nhan_hien_thi = {
            "xong": ":green-badge[✅ Hoàn thành]",
            "loi":  ":red-badge[❌ Có lỗi]",
            "cho":  "",
        }.get(trang_thai, "")

        st.markdown(f"**Nhật ký lần chạy trước** {nhan_hien_thi}")
        hien_thi_log(st.session_state.log_chay)

        def xoa_nhat_ky():
            st.session_state.log_chay = []
            st.session_state.trang_thai = "cho"
            
        st.button("Xoá nhật ký", icon=":material/delete:", on_click=xoa_nhat_ky)

    else:
        # Trạng thái ban đầu — hướng dẫn bằng thẻ thông tin
        with st.container(border=True):
            col_a, col_b = st.columns(2)
            with col_a:
                st.markdown("""
**:material/search: Tìm kiếm thông minh**
Hệ thống tự động tìm PDF, DOCX từ hàng nghìn trang giáo dục uy tín trên internet.
""")
            with col_b:
                st.markdown("""
**:material/category: Phân loại tự động**
Mỗi tài liệu được gắn nhãn lĩnh vực, độ tuổi và loại tài liệu theo chuẩn GDMN.
""")
            col_c, col_d = st.columns(2)
            with col_c:
                st.markdown("""
**:material/verified: Kiểm tra chất lượng**
Lọc tự động tài liệu rác, quá ngắn hoặc không thuộc phạm vi giáo dục mầm non.
""")
            with col_d:
                st.markdown("""
**:material/folder: Lưu kho có cấu trúc**
Tài liệu được lưu theo thư mục R2 (7 vùng) để dễ tra cứu và quản lý sau này.
""")
