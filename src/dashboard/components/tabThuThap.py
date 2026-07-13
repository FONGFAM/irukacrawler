import streamlit as st
import os
import subprocess
from pathlib import Path
from src.dashboard.utils import PYTHON_BIN, hien_thi_log, tai_du_lieu

# ── Preset Từ Khoá (Ma trận ưu tiên) ─────────────────────────
PRESET_DOT_1 = [
    "giáo án làm quen với toán mầm non 5-6 tuổi",
    "bài giảng số đếm toán lớp lá",
    "skkn phát triển nhận thức toán trẻ 5 tuổi",
    "giáo án làm quen chữ cái tiếng việt lớp lá",
    "skkn phát triển ngôn ngữ chữ cái 5-6 tuổi",
    "giáo án chuẩn bị cho trẻ vào lớp 1 môn toán",
    "tài liệu luyện viết chữ cái tiếng việt lớp 1",
    "bài tập toán tư duy lớp 1"
]

PRESET_DOT_2 = [
    "giáo án làm quen với toán mầm non 4-5 tuổi",
    "bài giảng toán nhận biết hình khối lớp chồi",
    "giáo án toán nhận biết to nhỏ 3-4 tuổi",
    "giáo án phát triển ngôn ngữ trẻ 4-5 tuổi",
    "bài giảng truyện kể mầm non lớp chồi",
    "skkn phát triển ngôn ngữ mầm non 3-4 tuổi"
]

PRESET_DOT_3 = [
    "giáo án tạo hình mầm non 5-6 tuổi",
    "bài giảng âm nhạc mầm non",
    "kế hoạch giáo dục thể chất mầm non",
    "giáo án khám phá khoa học xã hội mầm non",
    "skkn âm nhạc lớp lá",
    "tài liệu mĩ thuật mầm non"
]

def apply_preset(preset_list):
    st.session_state.tu_khoa_input = "\n".join(preset_list)

def render_tab_thu_thap():
    if "tu_khoa_input" not in st.session_state:
        st.session_state.tu_khoa_input = "giáo án kể chuyện mầm non 5-6 tuổi"
        
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

    # ── Chọn Chiến dịch nhanh ────────────────────────────────
    st.markdown("**🎯 Chiến dịch ưu tiên (Theo kế hoạch hệ thống):**")
    col_p1, col_p2, col_p3 = st.columns(3)
    with col_p1:
        st.button("🔥 Đợt 1 (Toán & TV Lá, Lớp 1)", on_click=apply_preset, args=(PRESET_DOT_1,), use_container_width=True, help="Đặc biệt ưu tiên: Toán và Làm quen chữ cái cho trẻ 5-6 tuổi chuẩn bị vào lớp 1.")
    with col_p2:
        st.button("⭐ Đợt 2 (Toán & TV 3-5 tuổi)", on_click=apply_preset, args=(PRESET_DOT_2,), use_container_width=True, help="Ưu tiên cao: Toán và Ngôn ngữ cho trẻ 3-5 tuổi.")
    with col_p3:
        st.button("Đợt 3 (Các môn khác)", on_click=apply_preset, args=(PRESET_DOT_3,), use_container_width=True, help="Ưu tiên mở rộng: Tạo hình, Âm nhạc, Thể chất, Khám phá.")

    # ── Form nhập liệu ───────────────────────────────────────
    with st.form("form_tim_kiem", border=True):
        tu_khoa = st.text_area(
            "Từ khoá tìm kiếm (Mỗi dòng một chủ đề)",
            key="tu_khoa_input",
            height=180,
            placeholder="Mỗi dòng một chủ đề, ví dụ:\ngiáo án Toán mầm non\nSKKN tạo hình trẻ 4 tuổi",
            help="Hệ thống sẽ tìm kiếm tài liệu trên internet cho từng chủ đề. Bạn có thể tự gõ hoặc bấm các chiến dịch bên trên để điền tự động.",
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

                col_st1, col_st2 = st.columns([3, 1])
                with col_st1:
                    st.write(f":material/search: Từ khoá: {', '.join(danh_sach_tu_khoa)}")
                    st.write(f":material/settings: Nguồn: `{nguon}` — {so_ket_qua} kết quả/chủ đề — {song_song} luồng song song")
                with col_st2:
                    # Nút bấm này nếu được click sẽ buộc Streamlit re-run script, 
                    # ngắt thread hiện tại và kích hoạt khối `finally` bên dưới để kill process.
                    st.button("⏹️ Dừng thu thập", key="btn_stop_crawler", type="primary", use_container_width=True)

                cac_dong: list[str] = []
                dem_thanh_cong = 0
                dem_loi = 0
                dem_can_duyet = 0

                tien_trinh = None
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

                    try:
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
                    finally:
                        # Đảm bảo process bị kill nếu user bấm nút Dừng hoặc rời khỏi trang
                        if tien_trinh and tien_trinh.poll() is None:
                            tien_trinh.terminate()
                            tien_trinh.wait()
                            cac_dong.append("⚠️ TIẾN TRÌNH ĐÃ BỊ HỦY BỞI NGƯỜI DÙNG.")
                            st.session_state.log_chay = cac_dong.copy()
                            st.session_state.trang_thai = "loi"

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
