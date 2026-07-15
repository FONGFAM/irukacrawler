# pyrefly: ignore [missing-import]
import streamlit as st

# Import các components sau khi cấu hình trang
st.set_page_config(
    page_title="THU THẬP TÀI LIỆU GIÁO DỤC",
    page_icon=":material/collections_bookmark:",
    layout="wide",
)

# ─────────────────────────────────────────────────────────────
# Load CSS tùy chỉnh (ghi đè style container chính)
# ─────────────────────────────────────────────────────────────
import pathlib

_css_file = pathlib.Path(__file__).parent / "assets" / "style.css"
if _css_file.exists():
    st.markdown(
        f"<style>{_css_file.read_text(encoding='utf-8')}</style>",
        unsafe_allow_html=True,
    )

from src.dashboard.components.tabThuThap import render_tab_thu_thap
from src.dashboard.components.tabThongKe import render_tab_thong_ke
from src.dashboard.components.tabDanhSach import render_tab_danh_sach
from src.dashboard.components.tabKhoTaiLieu import render_tab_kho_tai_lieu

# ─────────────────────────────────────────────────────────────
# Khởi tạo session state
# ─────────────────────────────────────────────────────────────
if "log_chay" not in st.session_state:
    st.session_state.log_chay = []
if "trang_thai" not in st.session_state:
    st.session_state.trang_thai = "cho"   # "cho" | "dang_chay" | "xong" | "loi"


# ─────────────────────────────────────────────────────────────
# Tiêu đề ứng dụng
# ─────────────────────────────────────────────────────────────
st.title(":material/collections_bookmark: Thu thập tài liệu giáo dục")
st.caption("Tự động tìm kiếm, tải về và phân loại tài liệu mầm non theo chuẩn Chương trình GDMN.")


pg_thu_thap = st.Page(render_tab_thu_thap, title="Tìm & Thu thập", icon=":material/play_circle:", url_path="thu_thap")
pg_thong_ke = st.Page(render_tab_thong_ke, title="Thống kê", icon=":material/bar_chart:", url_path="thong_ke")
pg_danh_sach = st.Page(render_tab_danh_sach, title="Danh sách & Duyệt", icon=":material/fact_check:", url_path="danh_sach")
pg_kho = st.Page(render_tab_kho_tai_lieu, title="Kho Thành Phẩm", icon=":material/library_books:", url_path="kho_tai_lieu")

pg = st.navigation([pg_thu_thap, pg_thong_ke, pg_danh_sach, pg_kho])

pg.run()
