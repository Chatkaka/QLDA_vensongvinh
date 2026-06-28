import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import pandas as pd
import datetime
import json
import io

# Import local modules
import database
import business_logic
import exporter
import ai_service

# Initialize database on startup
database.init_db()

def get_package_id_by_bsc(bsc_code):
    if not bsc_code:
        return None
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM packages WHERE bsc_code = ?", (bsc_code.strip(),))
    row = cursor.fetchone()
    conn.close()
    return row[0] if row else None


# --- Page Config ---
st.set_page_config(
    page_title="Hệ thống Kiểm soát Gói thầu Thi công",
    page_icon="🖥️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Custom Styling ---
st.markdown("""
<style>
    /* Premium style system */
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background-color: #f8fafc;
        color: #1e293b;
    }
    
    /* Top Banner Gradient */
    .top-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #3b82f6 100%);
        padding: 2.5rem;
        border-radius: 16px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.2);
    }
    
    .top-banner h1 {
        color: white !important;
        font-family: 'Outfit', sans-serif !important;
        font-weight: 800 !important;
        font-size: 2.3rem !important;
        margin: 0 !important;
        letter-spacing: -0.03em;
    }
    
    .top-banner p {
        color: #dbeafe !important;
        margin: 8px 0 0 0 !important;
        font-size: 1.1rem;
        font-weight: 500;
    }
    
    /* Premium Metric Card */
    .metric-card {
        padding: 1.25rem;
        border-radius: 12px;
        background: white;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -2px rgba(0, 0, 0, 0.05);
        border: 1px solid #f1f5f9;
        border-left: 5px solid #cbd5e1;
        transition: all 0.25s ease-in-out;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
    }
    .metric-red { border-left-color: #ef4444; background: linear-gradient(180deg, #ffffff 0%, #fef2f2 100%); }
    .metric-orange { border-left-color: #f97316; background: linear-gradient(180deg, #ffffff 0%, #fff7ed 100%); }
    .metric-yellow { border-left-color: #eab308; background: linear-gradient(180deg, #ffffff 0%, #fefce8 100%); }
    .metric-green { border-left-color: #22c55e; background: linear-gradient(180deg, #ffffff 0%, #f0fdf4 100%); }
    
    /* Warnings Card Layout */
    .warning-item {
        background: white; 
        padding: 1.25rem; 
        border-radius: 10px; 
        margin-bottom: 1rem; 
        border: 1px solid #f1f5f9;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
        transition: all 0.2s ease;
    }
    .warning-item:hover {
        border-color: #cbd5e1;
    }
    
    .badge {
        padding: 5px 12px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 700;
        display: inline-block;
        letter-spacing: 0.05em;
    }
    .badge-red { background-color: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
    .badge-orange { background-color: #ffedd5; color: #9a3412; border: 1px solid #fed7aa; }
    .badge-yellow { background-color: #fef9c3; color: #854d0e; border: 1px solid #fef08a; }
    .badge-green { background-color: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
    
    /* Styled Forms */
    .stForm {
        background-color: white !important;
        border-radius: 12px !important;
        padding: 1.5rem !important;
        border: 1px solid #e2e8f0 !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02) !important;
    }
</style>
""", unsafe_allow_html=True)

# --- Người dùng hiện tại & Phân quyền ---
def load_users():
    try:
        conn = database.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, Ma_NV, Ho_Ten, Chuc_Vu, Vai_Tro, Email, Xem, Them_HD, Sua, Xoa_HD, Sua_CDT_BD, Cap_Nhat_CDT FROM nhan_su ORDER BY Ho_Ten ASC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error loading users: {e}")
        return []

# --- Kiểm tra Đăng nhập & Tự động Đăng nhập từ URL ---
if 'current_user' not in st.session_state or st.session_state['current_user'] is None:
    qp = st.query_params
    if 'uid' in qp:
        uid_val = qp['uid']
        users_list = load_users()
        matched_u = next((u for u in users_list if str(u['Ma_NV']).strip() == str(uid_val).strip()), None)
        if matched_u:
            st.session_state['current_user'] = matched_u

if 'current_user' not in st.session_state or st.session_state['current_user'] is None:
    # Render Login Page
    st.sidebar.markdown("# 🖥️ HỆ THỐNG KIỂM SOÁT")
    st.sidebar.markdown("### Closed-Loop Procurement & Construction")
    st.sidebar.divider()
    st.sidebar.info("🔑 Vui lòng đăng nhập ở màn hình chính để tiếp tục.")
    
    # Main area login card
    c_left, c_mid, c_right = st.columns([1, 2, 1])
    with c_mid:
        st.markdown("<br><br><br>", unsafe_allow_html=True)
        # Stylized card
        st.markdown("""
        <div style="text-align: center; margin-bottom: 20px;">
            <span style="font-size: 3rem;">🖥️</span>
            <h2 style="margin-top: 10px; color: #1e293b; font-family: 'Outfit', sans-serif;">HỆ THỐNG KIỂM SOÁT KHÉP KÍN</h2>
            <p style="color: #64748b; font-size: 0.9rem;">Vòng đời Gói thầu thi công & Tư vấn giải pháp AI</p>
        </div>
        """, unsafe_allow_html=True)
        
        with st.container(border=True):
            st.markdown("<h4 style='text-align: center; margin-top: 0; color: #0f172a;'>🔐 ĐĂNG NHẬP</h4>", unsafe_allow_html=True)
            
            users_list = load_users()
            if users_list:
                selected_user_login = st.selectbox(
                    "👤 Chọn tài khoản nhân sự:",
                    options=users_list,
                    format_func=lambda x: f"{x['Ho_Ten']} ({x['Chuc_Vu']})"
                )
                
                pwd_input = st.text_input("🔑 Nhập Mã nhân viên (Mật khẩu):", type="password", placeholder="Ví dụ: 38, 58, 80...")
                
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🚀 ĐĂNG NHẬP", use_container_width=True, type="primary"):
                    if pwd_input and pwd_input.strip() == str(selected_user_login.get('Ma_NV')).strip():
                        st.session_state['current_user'] = selected_user_login
                        st.query_params['uid'] = selected_user_login['Ma_NV']
                        st.success("🎉 Đăng nhập thành công! Đang tải hệ thống...")
                        st.rerun()
                    else:
                        st.error("❌ Mã nhân viên (mật khẩu) không đúng. Vui lòng kiểm tra lại.")
            else:
                st.error("⚠️ Không thể tải danh sách nhân viên từ cơ sở dữ liệu.")
                
        st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.75rem; margin-top: 30px;'>© 2026 Phòng Kinh tế Kế hoạch BQLDA</p>", unsafe_allow_html=True)
    st.stop()

# --- Khi đã Đăng nhập thành công ---
curr_user = st.session_state['current_user']
is_admin = (curr_user.get('Chuc_Vu') == 'Admin' or curr_user.get('Vai_Tro') == 'admin2' or curr_user.get('Ho_Ten') == 'Hồ Nghĩa Chất' or curr_user.get('Ma_NV') == '38')


# --- Xử lý sửa ô trực tiếp (Inline Editing Hook) ---
if st.query_params:
    qp = st.query_params
    
    # --- Edit Row Form trigger ---
    if 'edit_row_id_form' in qp:
        try:
            edit_form_id = int(qp['edit_row_id_form'])
            st.session_state['show_edit_form'] = True
            st.session_state['edit_project_id'] = edit_form_id
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi khi mở biểu mẫu sửa: {e}")

    # --- Delete Row trigger ---
    if 'delete_row_id' in qp:
        try:
            delete_id = int(qp['delete_row_id'])
            username = curr_user.get('Ho_Ten', 'Ẩn danh')
            has_delete_perm = is_admin or (curr_user.get('Xoa_HD') == 1)
            if not has_delete_perm:
                st.error("⚠️ Bạn không có quyền xóa hạng mục.")
            else:
                conn = database.get_connection()
                cursor = conn.cursor()
                cursor.execute("SELECT package_name, bsc_code FROM packages WHERE id = ?", (delete_id,))
                row_info = cursor.fetchone()
                if row_info:
                    hm_name = row_info[0]
                    bsc_code = row_info[1]
                    cursor.execute("DELETE FROM packages WHERE id = ?", (delete_id,))
                    conn.commit()
                    database.log_action(username, "Xóa", "packages", delete_id, f"Xóa hạng mục '{hm_name}' (Mã BSC: {bsc_code}) qua nút xóa dòng")
                conn.close()
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi khi thực hiện xóa: {e}")

    if 'edit_row_id' in qp and 'edit_col' in qp:
        try:
            edit_id = int(qp['edit_row_id'])
            edit_col = qp['edit_col']
            new_val = qp.get('edit_val', '')
            
            username = curr_user.get('Ho_Ten', 'Ẩn danh')
            
            conn = database.get_connection()
            cursor = conn.cursor()
            
            has_edit_perm = is_admin or (curr_user.get('Sua') == 1)
            if not has_edit_perm:
                st.error("⚠️ Bạn không có quyền chỉnh sửa dữ liệu.")
                conn.close()
            else:
                # 1. Nếu là sửa tiến độ tuần (T1_KH, T1_KQ...)
                if edit_col.startswith('T') and len(edit_col) >= 5 and edit_col[1].isdigit() and (edit_col.endswith('KH') or edit_col.endswith('KQ')):
                    week = int(edit_col[1])
                    col_type = 'planned_progress' if edit_col.endswith('KH') else 'actual_progress'
                    try:
                        val_float = float(new_val) / 100.0 if new_val else 0.0  # Streamlit UI hiển thị %, DB lưu float 0-1
                        cursor.execute("SELECT id, planned_progress, actual_progress FROM progress_tracking WHERE package_id = ? AND report_week = ?", (edit_id, week))
                        week_row = cursor.fetchone()
                        if week_row:
                            cursor.execute(f"""
                                UPDATE progress_tracking 
                                SET {col_type} = ?, 
                                    variance = (CASE WHEN ? = 'actual_progress' THEN ? ELSE actual_progress END) - 
                                               (CASE WHEN ? = 'planned_progress' THEN ? ELSE planned_progress END)
                                WHERE id = ?
                            """, (val_float, col_type, val_float, col_type, val_float, week_row[0]))
                        else:
                            kh_val = val_float if col_type == 'planned_progress' else 0.0
                            kq_val = val_float if col_type == 'actual_progress' else 0.0
                            cursor.execute("""
                                INSERT INTO progress_tracking (package_id, report_week, planned_progress, actual_progress, variance)
                                VALUES (?, ?, ?, ?, ?)
                            """, (edit_id, week, kh_val, kq_val, kq_val - kh_val))
                        conn.commit()
                        database.log_action(username, "Sửa trực tiếp tiến độ tuần", "progress_tracking", edit_id,
                                            f"Cập nhật tiến độ tuần {week} ({'Kế hoạch' if col_type == 'planned_progress' else 'Thực tế'}) thành {val_float*100:.1f}%")
                    except ValueError:
                        pass
                else:
                    # 2. Sửa các cột thông tin của packages
                    col_mapping = {
                        'TT': 'package_code',
                        'Ma_BSC': 'bsc_code',
                        'Goi_thau': 'goi_thau_pl',
                        'Nhom_CT': 'project_group',
                        'Hang_muc': 'package_name',
                        'Phu_trach': 'person_in_charge',
                        'Ngay_BD_YC': 'plan_start_date',
                        'Ngay_KT_YC': 'plan_end_date',
                        'Ngan_sach': 'cdt_budget',
                        'Gia_tri_HDCU': 'contract_value',
                        'Ngay_BD_Khoi_Cong': 'actual_start_date',
                        'kh_hstktc': 'kh_hstktc', 'tt_hstktc': 'tt_hstktc', 'tt_specs': 'tt_specs', 'tt_boq': 'tt_boq',
                        'kh_lcnt': 'kh_lcnt', 'tt_lcnt': 'tt_lcnt', 'kh_hdcu': 'kh_hdcu', 'tt_hdcu': 'tt_hdcu',
                        'kh_khcu': 'kh_khcu', 'tt_khcu': 'tt_khcu', 'kh_plhd': 'kh_plhd', 'tt_plhd': 'tt_plhd',
                        'kh_khtk': 'kh_khtk', 'tt_khtk': 'tt_khtk', 'kh_thang': 'kh_thang', 'kq_thang': 'kq_thang'
                    }
                    edit_col_clean = 'Hang_muc' if edit_col == 'Hang_muc_formatted' else edit_col
                    db_col = col_mapping.get(edit_col_clean, edit_col_clean)
                    
                    cursor.execute(f"SELECT {db_col}, package_name FROM packages WHERE id = ?", (edit_id,))
                    row_info = cursor.fetchone()
                    if row_info:
                        old_val = row_info[0]
                        hm_name = row_info[1]
                        if db_col in ('cdt_budget', 'contract_value'):
                            try:
                                val_float = float(new_val) if new_val else None
                                cursor.execute(f"UPDATE packages SET {db_col} = ? WHERE id = ?", (val_float, edit_id))
                                old_disp = f"{old_val} tỷ" if old_val is not None else "Trống"
                                new_disp = f"{val_float} tỷ" if val_float is not None else "Trống"
                                database.log_action(username, "Sửa trực tiếp ô", "packages", edit_id,
                                                    f"Thay đổi {edit_col} của hạng mục '{hm_name}' từ {old_disp} thành {new_disp}")
                            except ValueError:
                                pass
                        elif db_col in ('kh_thang', 'kq_thang'):
                            try:
                                val_float = float(new_val) / 100.0 if new_val else 0.0
                                cursor.execute(f"UPDATE packages SET {db_col} = ? WHERE id = ?", (val_float, edit_id))
                                database.log_action(username, "Sửa trực tiếp ô", "packages", edit_id,
                                                    f"Thay đổi {edit_col} của hạng mục '{hm_name}' thành {val_float*100:.1f}%")
                            except ValueError:
                                pass
                        else:
                            cursor.execute(f"UPDATE packages SET {db_col} = ? WHERE id = ?", (new_val, edit_id))
                            old_disp = old_val if old_val is not None else "Trống"
                            new_disp = new_val if new_val is not None else "Trống"
                            database.log_action(username, "Sửa trực tiếp ô", "packages", edit_id,
                                                f"Thay đổi {edit_col} của hạng mục '{hm_name}' từ '{old_disp}' thành '{new_disp}'")
                        conn.commit()
                conn.close()
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Lỗi khi sửa đổi trực tiếp: {e}")
# Sidebar layout when logged in
st.sidebar.markdown("# 🖥️ HỆ THỐNG KIỂM SOÁT")
st.sidebar.markdown("### Closed-Loop Procurement & Construction")
st.sidebar.divider()

# Show user info
st.sidebar.success(f"👤 Xin chào, **{curr_user['Ho_Ten']}**!")
if is_admin:
    st.sidebar.info("🔓 **Quyền hạn:** Toàn quyền (Admin)")
else:
    perms = []
    if curr_user.get('Xem') == 1: perms.append("Xem")
    if curr_user.get('Them_HD') == 1: perms.append("Thêm mới")
    if curr_user.get('Sua') == 1: perms.append("Sửa")
    if curr_user.get('Xoa_HD') == 1: perms.append("Xóa")
    perms_str = ", ".join(perms) if perms else "Không có quyền"
    st.sidebar.info(f"🔒 **Quyền hạn:** {perms_str}")

# ONLY display Gemini API Key if the user is Admin (Chuc_Vu == 'Admin' or Vai_Tro == 'admin2')
if is_admin:
    api_key_env = os.environ.get("GEMINI_API_KEY", "")
    api_key_input = st.sidebar.text_input(
        "🔑 Google Gemini API Key",
        type="password",
        value=st.session_state.get('gemini_api_key', api_key_env),
        help="Nhập API Key của bạn để sử dụng Trợ lý AI và Cố vấn Rủi ro."
    )
    if api_key_input:
        st.session_state['gemini_api_key'] = api_key_input
    else:
        st.session_state['gemini_api_key'] = api_key_env
else:
    # Set the key silently from the environment variable if not admin
    st.session_state['gemini_api_key'] = os.environ.get("GEMINI_API_KEY", "")

# Google Drive Sync status check
try:
    import gdrive_sync
    has_gdrive_file = os.path.exists("gdrive_credentials.json")
    has_gdrive_secret = ("GDRIVE_SERVICE_ACCOUNT" in st.secrets) or ("gdrive_service_account" in st.secrets)
    has_gdrive = has_gdrive_file or has_gdrive_secret
    
    if has_gdrive:
        status, err = gdrive_sync.get_sync_status()
        if status == "Thành công":
            st.sidebar.success("☁️ Google Drive Sync: Đang hoạt động (Đồng bộ OK)")
        elif status in ("Thất bại", "Lỗi cấu hình", "Lỗi thư viện"):
            st.sidebar.error(f"❌ Google Drive Sync: {status}\n\nChi tiết: `{err}`")
        else:
            st.sidebar.info(f"☁️ Google Drive Sync: {status}")
    else:
        st.sidebar.warning("⚠️ Google Drive Sync: Chưa cấu hình")
        with st.sidebar.expander("ℹ️ Hướng dẫn kết nối Google Drive (20TB)"):
            st.markdown("""
            Để đồng bộ cơ sở dữ liệu và file Excel lên Google Drive (Có 2 cách):
            
            **Cách 1: Lưu file trực tiếp (Dành cho chạy cục bộ / Local)**
            1. Tải tệp khóa JSON credentials về máy tính của bạn.
            2. Đặt tên tệp là **`gdrive_credentials.json`**.
            3. Di chuyển tệp này vào thư mục gốc của dự án (cạnh tệp `app.py`).
            4. *(Lưu ý: Tệp này đã được thêm vào `.gitignore` để tránh bị đẩy lên GitHub công khai).*
            
            **Cách 2: Sử dụng Streamlit Secrets (Dành cho Streamlit Cloud)**
            1. Tạo một thư mục trên Google Drive của bạn, chia sẻ quyền truy cập thư mục đó cho email của Service Account (quyền Editor).
            2. Trong Streamlit Cloud, vào **Settings -> Secrets**, cấu hình hai thông số:
               ```toml
               GDRIVE_FOLDER_ID = "ID_THU_MUC_GOOGLE_DRIVE"
               GDRIVE_SERVICE_ACCOUNT = '''{
                 "type": "service_account",
                 ...
               }'''
               ```
            """)
except Exception:
    pass

# Logout button
if st.sidebar.button("🚪 Đăng xuất", type="secondary", use_container_width=True):
    st.session_state['current_user'] = None
    st.session_state['gemini_api_key'] = None
    st.query_params.clear()
    st.rerun()

st.sidebar.divider()

def check_permission(permission_type):
    # curr_user is already loaded above
    if not curr_user:
        return False
    if is_admin:
        return True
    return curr_user.get(permission_type) == 1

# Navigation
menu_options = [
    "📊 Dashboard Điều hành",
    "📋 Bảng Tổng hợp (Master)",
    "📂 01. Hồ sơ Tiền khởi công",
    "📅 02. Kế hoạch Tháng/Tuần",
    "⚠️ 03. Quản lý Phát sinh",
    "🚚 04. Cung ứng Đặc thù",
    "🚀 05. Bù Tiến độ",
    "🤖 Trợ lý AI Thông minh"
]
if is_admin:
    menu_options.append("👥 Quản lý Nhân sự")

choice = st.sidebar.radio("📌 Phân hệ chức năng", menu_options)

st.sidebar.divider()
st.sidebar.info(
    "💡 **Hệ thống Kiểm soát Khép kín** giúp liên kết kế hoạch, tiến độ, chi phí và "
    "cung ứng đặc thù dựa trên Mã BSC của từng gói thầu."
)

# Helper function to load projects list for dropdowns
def load_ma_bsc_options():
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, bsc_code AS Ma_BSC, package_name AS Hang_muc FROM packages WHERE bsc_code IS NOT NULL AND bsc_code != ''")
    rows = cursor.fetchall()
    conn.close()
    return [{"id": r[0], "Ma_BSC": r[1], "Hang_muc": r[2]} for r in rows]

def load_goi_thau_options():
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT goi_thau_pl AS Goi_thau FROM packages WHERE goi_thau_pl IS NOT NULL AND goi_thau_pl != ''")
    existing_gts = [r[0] for r in cursor.fetchall()]
    conn.close()
    default_gts = [f"PL{i:02d}" for i in range(1, 31)]
    all_gts = sorted(list(set(existing_gts + default_gts)))
    return all_gts

def load_personnel_options():
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT Ho_Ten FROM nhan_su ORDER BY Ho_Ten ASC")
    ns_names = [r[0] for r in cursor.fetchall()]
    cursor.execute("SELECT DISTINCT person_in_charge AS Phu_trach FROM packages WHERE person_in_charge IS NOT NULL AND person_in_charge != ''")
    existing_pts = [r[0] for r in cursor.fetchall()]
    conn.close()
    all_pts = sorted(list(set(ns_names + existing_pts)))
    return all_pts

def load_contractor_options():
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT created_by AS Nguoi_lap FROM pre_construction_docs WHERE created_by IS NOT NULL AND created_by != ''")
    existing_contrs = [r[0] for r in cursor.fetchall()]
    conn.close()
    default_contrs = ['HĐLCNT', 'Tổng thầu', 'Nhà thầu phụ', 'An Dương', 'HĐLCNT / Tổng thầu']
    all_contrs = sorted(list(set(existing_contrs + default_contrs)))
    return all_contrs

def load_dvt_options():
    conn = database.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT DISTINCT unit AS DVT FROM special_procurements WHERE unit IS NOT NULL AND unit != ''")
    existing_dvts = [r[0] for r in cursor.fetchall()]
    conn.close()
    default_dvts = ['Bộ', 'Cái', 'Tấn', 'Mét', 'M2', 'M3', 'Lô', 'Kg', 'Chiếc']
    all_dvts = sorted(list(set(existing_dvts + default_dvts)))
    return all_dvts

# --- Pandas Styling Helper Functions ---
def style_master_rows(df):
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    has_bsc_col = "Mã BSC" in df.columns
    for idx in df.index:
        is_wbs = False
            
        if is_wbs:
            for col in df.columns:
                styles.loc[idx, col] = 'background-color: #f1f5f9; color: #475569; font-weight: bold; font-style: italic;'
        else:
            for col in df.columns:
                val = df.loc[idx, col]
                val_str = str(val).strip() if val is not None else ""
                
                # 1. Color warning column
                if col == "Cảnh báo":
                    if "🔴" in val_str:
                        styles.loc[idx, col] = 'background-color: #fee2e2; color: #b91c1c; font-weight: bold;'
                    elif "🟠" in val_str:
                        styles.loc[idx, col] = 'background-color: #ffedd5; color: #c2410c; font-weight: bold;'
                    elif "🟡" in val_str:
                        styles.loc[idx, col] = 'background-color: #fefce8; color: #a16207; font-weight: bold;'
                    elif "🟢" in val_str:
                        styles.loc[idx, col] = 'background-color: #f0fdf4; color: #15803d; font-weight: bold;'
                
                # 2. Status columns
                elif col in ("ĐK1 HSKT đủ", "ĐK2 HĐCU ký", "ĐK3 KHTK duyệt", "ĐIỀU KIỆN ĐỦ", 
                             "TT HSTKTC", "TT SPECS", "TT BOQ/KL", "TT LCNT", "TT Ký HĐCU", "Khởi công"):
                    if val_str in ("✔", "Đã phát hành", "Đã cấp", "Đã bàn giao", "Đã ký", "Đã CU", "Đã duyệt", "Hoàn thiện", "ĐỦ ĐIỀU KIỆN"):
                        styles.loc[idx, col] = 'background-color: #f0fdf4; color: #166534; font-weight: 500;'
                    elif val_str in ("✘", "Chưa có TK", "Chưa có", "Chưa bàn giao", "Chưa LCNT", "Chưa CU", "Chưa trình", "CHƯA ĐỦ ĐK"):
                        styles.loc[idx, col] = 'background-color: #fee2e2; color: #991b1b; font-weight: 500;'
                    elif any(word in val_str for word in ("Đang", "Chờ", "Theo đợt", "Điều chỉnh")):
                        styles.loc[idx, col] = 'background-color: #fefce8; color: #854d0e; font-weight: 500;'
                        
                # 3. Numeric cells color formatting (soft styling)
                elif "% HĐ/NS (Tính)" in col:
                    try:
                        num_val = float(val) if val not in ("", None) else 0.0
                        if num_val > 100.0:
                            styles.loc[idx, col] = 'color: #b91c1c; font-weight: 700;'
                        else:
                            styles.loc[idx, col] = 'color: #15803d; font-weight: 500;'
                    except ValueError:
                        pass
    return styles

def style_subtable_rows(df):
    styles = pd.DataFrame('', index=df.index, columns=df.columns)
    for col in df.columns:
        for idx in df.index:
            val = df.loc[idx, col]
            val_str = str(val).strip() if val is not None else ""
            
            # Highlight statuses
            if col in ("TT_duyet", "TT_lap", "Dat_YCKT_CDT", "TT_Phe_duyet", "TT_Trien_khai", "Trong_Ngoai_HDCU", "TT_cung_ung"):
                if val_str in ("Đã duyệt", "Đã lập", "Có", "Trong HĐCU", "Đã hoàn thành", "Đã ký", "Đã CU"):
                    styles.loc[idx, col] = 'background-color: #f0fdf4; color: #166534; font-weight: 500;'
                elif val_str in ("Chưa lập", "Từ chối", "Chưa", "Ngoài HĐCU", "Từ chối duyệt", "Đóng"):
                    styles.loc[idx, col] = 'background-color: #fee2e2; color: #991b1b; font-weight: 500;'
                elif any(word in val_str for word in ("Đang", "Chờ", "Đang sửa đổi", "Đang thực hiện", "Nháp")):
                    styles.loc[idx, col] = 'background-color: #fefce8; color: #854d0e; font-weight: 500;'
                    
            # Highlight values
            elif col in ("Gia_tri_phat_sinh", "Muc_cham_ngay"):
                try:
                    num_val = float(val) if val not in ("", None) else 0.0
                    if num_val > 0:
                        styles.loc[idx, col] = 'color: #b91c1c; font-weight: 600;'
                except ValueError:
                    pass
    return styles


def render_dataframe_html(df, column_config, key_suffix=""):
    # Vietnamese headers lookup dictionary to auto-translate database columns
    vietnamese_headers = {
        "id": "ID",
        "ma_bsc": "Mã BSC",
        "hang_muc": "Hạng mục",
        "loai_ho_so": "Loại hồ sơ",
        "ten_san_pham": "Tên sản phẩm",
        "link_luu_tru": "Link lưu trữ",
        "ngay_ht": "Ngày hoàn thành",
        "nguoi_lap": "Người lập",
        "nguoi_duyet": "Người duyệt",
        "tt_duyet": "Trạng thái duyệt",
        "thang": "Tháng",
        "loai_tai_lieu": "Loại tài liệu",
        "noi_dung_chinh": "Nội dung chính",
        "dat_yckt_cdt": "Đạt YCKT CĐT?",
        "link_tai_lieu": "Link tài liệu",
        "tt_lap": "TT Lập",
        "ngay_duyet": "Ngày duyệt",
        "ma_ps": "Mã phát sinh",
        "ngay_ps": "Ngày phát sinh",
        "loai": "Phân loại",
        "mo_ta": "Mô tả chi tiết",
        "nguyen_nhan": "Nguyên nhân",
        "de_xuat_xu_ly": "Đề xuất xử lý",
        "gia_tri_phat_sinh": "Giá trị PS (tỷ)",
        "anh_huong_td": "Ảnh hưởng TD (ngày)",
        "link_ho_so": "Link hồ sơ",
        "tt_phe_duyet": "TT Phê duyệt",
        "noi_dung_dieu_chinh": "Nội dung điều chỉnh",
        "ghi_chu": "Ghi chú",
        "ma_yc": "Mã yêu cầu",
        "ngay_yc": "Ngày yêu cầu",
        "loai_yc": "Tính chất",
        "vat_tu_thiet_bi": "Vật tư / Thiết bị",
        "noi_dung_yeu_cau": "Mô tả / Lý do",
        "kl": "Khối lượng",
        "dvt": "Đơn vị tính",
        "trong_ngoai_hdcu": "Phạm vi HĐ",
        "ngay_can": "Ngày cần vật tư",
        "tt_cung_ung": "TT Cung ứng",
        "ngay_phat_hien": "Ngày phát hiện chậm",
        "muc_cham_ngay": "Số ngày trễ",
        "phuong_an": "Giải pháp bù",
        "chi_tiet_giai_phap": "Kế hoạch chi tiết",
        "moc_cam_ket_ht": "Hạn chót cam kết",
        "link_phuong_an": "Link phương án",
        "kq_thuc_hien_bu": "Đánh giá kết quả bù",
        "tt_trien_khai": "TT Triển khai"
    }

    html = []

    css = """
    <style>
        .table-wrapper {
            width: 100%;
            max-height: 500px; /* Constrain height to force vertical scrollbar inside container */
            overflow-y: auto; /* Vertically scrollable */
            overflow-x: hidden; /* Avoid horizontal scrolling */
            border-radius: 12px;
            box-shadow: 0 4px 15px -3px rgba(0, 0, 0, 0.05), 0 2px 6px -2px rgba(0, 0, 0, 0.05);
            border: 1px solid #e2e8f0;
            margin-bottom: 2rem;
            background: white;
        }
        .styled-table {
            width: 100%;
            border-collapse: collapse;
            font-family: 'Inter', sans-serif;
            font-size: 0.775rem;
            color: #334155;
            table-layout: fixed;
        }
        .styled-table th {
            background-color: #f8fafc !important; /* Premium light slate grey background */
            color: #475569 !important; /* Soft slate text */
            font-weight: 700;
            text-align: left;
            padding: 8px 10px;
            position: sticky;
            top: 0;
            z-index: 10;
            border-bottom: 2px solid #e2e8f0;
            font-size: 0.725rem;
            text-transform: uppercase;
            letter-spacing: 0.02em;
            word-wrap: break-word;
            white-space: normal;
            line-height: 1.25;
        }
        /* Sticky header border bottom fix when scrolling */
        .styled-table th::after {
            content: '';
            position: absolute;
            left: 0;
            bottom: 0;
            width: 100%;
            border-bottom: 2px solid #e2e8f0;
        }
        .styled-table td {
            padding: 8px 10px;
            border-bottom: 1px solid #f1f5f9;
            vertical-align: middle;
            word-wrap: break-word;
            white-space: normal;
            line-height: 1.35;
            color: #334155;
        }
        .styled-table tr:hover {
            background-color: #f8fafc !important;
        }
        .styled-table tr.wbs-row {
            background-color: #f8fafc !important;
            font-weight: bold;
            color: #475569;
        }
        .styled-table tr.wbs-row td {
            font-style: italic;
        }
        /* Custom badges */
        .status-badge {
            padding: 4px 8px;
            border-radius: 6px;
            font-size: 0.725rem;
            font-weight: 600;
            display: inline-block;
            text-align: center;
            line-height: 1.2;
        }
        .badge-green { background-color: #dcfce7; color: #15803d; border: 1px solid #bbf7d0; }
        .badge-red { background-color: #fee2e2; color: #b91c1c; border: 1px solid #fca5a5; }
        .badge-yellow { background-color: #fefce8; color: #a16207; border: 1px solid #fef08a; }
        .badge-orange { background-color: #ffedd5; color: #c2410c; border: 1px solid #fed7aa; }

        /* Link button style */
        .btn-link {
            display: inline-flex;
            align-items: center;
            background-color: #f0fdf4;
            color: #166534;
            border: 1px solid #bbf7d0;
            padding: 3px 6px;
            border-radius: 4px;
            text-decoration: none;
            font-size: 0.725rem;
            font-weight: 500;
            transition: all 0.2s;
        }
        .btn-link:hover {
            background-color: #dcfce7;
            color: #14532d;
            border-color: #86efac;
        }
    </style>
    """
    html.append(css)
    html.append('<div class="table-wrapper">')
    html.append('<table class="styled-table">')

    cols_to_render = []
    for col in df.columns:
        col_lower = col.lower()
        # Find if it is hidden in column_config (case-insensitive)
        cfg_key = None
        for k in column_config.keys():
            if k and k.lower() == col_lower:
                cfg_key = k
                break
        if cfg_key and column_config[cfg_key] is None:
            continue
        cols_to_render.append(col)

    total_cols = len(cols_to_render)
    default_pct = int(100 / max(total_cols, 1))

    # Custom widths for sub-table labels to prevent wrapping overflow
    col_pcts = {
        "Mã BSC": "10%",
        "Hạng mục": "18%",
        "Loại hồ sơ": "10%",
        "Tên hồ sơ / văn bản": "22%",
        "Link lưu trữ": "12%",
        "Ngày hoàn thành": "10%",
        "Người lập": "9%",
        "Người duyệt": "9%",
        "Trạng thái duyệt": "10%",
        # Sổ 02
        "Tháng": "7%",
        "Loại tài liệu": "12%",
        "Nội dung chính": "20%",
        "Đạt YCKT CĐT?": "10%",
        "Link tài liệu": "10%",
        "TT Lập": "9%",
        "TT Duyệt": "9%",
        "Ngày duyệt": "10%",
        # Sổ 03
        "Mã PS": "8%",
        "Ngày PS": "8%",
        "Phân loại": "12%",
        "Mô tả chi tiết": "18%",
        "Nguyên nhân": "13%",
        "Đề xuất xử lý": "13%",
        "Giá trị PS (tỷ)": "9%",
        "Ảnh hưởng TD (ngày)": "9%",
        "Link hồ sơ": "10%",
        "TT Phê duyệt": "10%",
        "Nội dung điều chỉnh": "15%",
        "Ghi chú": "10%",
        # Sổ 04
        "Mã YC": "8%",
        "Ngày yêu cầu": "9%",
        "Tính chất": "8%",
        "Vật tư / Thiết bị": "18%",
        "Mô tả / Lý do": "18%",
        "Khối lượng": "8%",
        "ĐVT": "5%",
        "Giá trị (tỷ)": "8%",
        "Phạm vi HĐ": "10%",
        "Link tài liệu kỹ thuật": "10%",
        "TT Cung ứng": "10%",
        "Ngày cần vật tư": "10%",
        # Sổ 05
        "Ngày phát hiện chậm": "11%",
        "Số ngày trễ": "9%",
        "Nguyên nhân chậm trễ": "18%",
        "Giải pháp bù": "18%",
        "Kế hoạch chi tiết": "18%",
        "Hạn chót cam kết": "10%",
        "Link phương án": "10%",
        "Đánh giá kết quả bù": "15%",
        "TT Triển khai": "10%"
    }

    html.append('<colgroup>')
    for col in cols_to_render:
        col_lower = col.lower()
        label = vietnamese_headers.get(col_lower, col)
        
        cfg_key = None
        for k in column_config.keys():
            if k and k.lower() == col_lower:
                cfg_key = k
                break
                
        if cfg_key:
            cfg = column_config[cfg_key]
            if cfg is not None:
                if isinstance(cfg, str):
                    label = cfg
                elif hasattr(cfg, 'label') and cfg.label:
                    label = cfg.label
                elif hasattr(cfg, 'title') and cfg.title and not callable(cfg.title):
                    label = cfg.title

        width_str = f"{default_pct}%"
        if label in col_pcts:
            width_str = col_pcts[label]
        elif cfg_key:
            cfg = column_config[cfg_key]
            if cfg and hasattr(cfg, 'width') and cfg.width:
                width_str = f"{max(int(cfg.width / 12), 4)}%"

        html.append(f'<col style="width: {width_str};">')
    html.append('</colgroup>')

    html.append('<thead><tr>')
    for col in cols_to_render:
        col_lower = col.lower()
        label = vietnamese_headers.get(col_lower, col)
        
        cfg_key = None
        for k in column_config.keys():
            if k and k.lower() == col_lower:
                cfg_key = k
                break
                
        if cfg_key:
            cfg = column_config[cfg_key]
            if cfg is not None:
                if isinstance(cfg, str):
                    label = cfg
                elif hasattr(cfg, 'label') and cfg.label:
                    label = cfg.label
                elif hasattr(cfg, 'title') and cfg.title and not callable(cfg.title):
                    label = cfg.title

        html.append(f'<th>{label}</th>')
    html.append('</tr></thead>')

    html.append('<tbody>')
    for idx, row in df.iterrows():
        is_wbs = False

        row_class = 'class="wbs-row"' if is_wbs else ""
        html.append(f'<tr {row_class}>')

        for col in cols_to_render:
            val = row[col]
            val_str = str(val).strip() if val is not None else ""
            col_lower = col.lower()

            cell_val = ""
            cfg_key = None
            for k in column_config.keys():
                if k and k.lower() == col_lower:
                    cfg_key = k
                    break
            
            cfg = column_config[cfg_key] if cfg_key else None
            label = vietnamese_headers.get(col_lower, col)
            if cfg is not None:
                if isinstance(cfg, str):
                    label = cfg
                elif hasattr(cfg, 'label') and cfg.label:
                    label = cfg.label
                elif hasattr(cfg, 'title') and cfg.title and not callable(cfg.title):
                    label = cfg.title
            
            is_link = False
            if cfg is not None and type(cfg).__name__ == "LinkColumn":
                is_link = True

            if is_link:
                if val_str and val_str.lower() != 'none' and val_str.lower() != 'nan':
                    disp_text = "Xem tài liệu 📄"
                    if cfg and hasattr(cfg, 'display_text') and cfg.display_text:
                        disp_text = cfg.display_text
                    cell_val = f'<a href="{val_str}" target="_blank" class="btn-link">{disp_text}</a>'
                else:
                    cell_val = ""
            elif col_lower in ("tt_duyet", "tt_lap", "dat_yckt_cdt", "tt_phe_duyet", "tt_trien_khai", "trong_ngoai_hdcu", "tt_cung_ung"):
                # Clean value mapping in Vietnamese
                val_clean = val_str
                if val_str in ("Đã duyệt", "Đã lập", "Có", "Trong HĐCU", "Đã hoàn thành", "Đã ký", "Đã CU"):
                    cell_val = f'<span class="status-badge badge-green">{val_clean}</span>'
                elif val_str in ("Chưa lập", "Từ chối", "Chưa", "Ngoài HĐCU", "Từ chối duyệt", "Đóng"):
                    cell_val = f'<span class="status-badge badge-red">{val_clean}</span>'
                elif any(word in val_str for word in ("Đang", "Chờ", "Đang sửa đổi", "Đang thực hiện", "Nháp")):
                    cell_val = f'<span class="status-badge badge-yellow">{val_clean}</span>'
                else:
                    cell_val = val_clean
            elif col_lower in ("gia_tri_phat_sinh", "gia_tri_dinh_muc", "kl"):
                try:
                    num_val = float(val) if val not in ("", None) else 0.0
                    if num_val > 0:
                        if "giá trị" in label.lower() or "tỷ" in label.lower() or col_lower == "gia_tri_phat_sinh":
                            cell_val = f"<b>{num_val:,.2f} tỷ</b>"
                        else:
                            cell_val = f"{num_val:,.2f}"
                    else:
                        cell_val = ""
                except ValueError:
                    cell_val = val_str
            elif col_lower in ("muc_cham_ngay", "anh_huong_td"):
                try:
                    num_val = int(float(val)) if val not in ("", None) else 0
                    if num_val > 0:
                        cell_val = f'<span style="color: #b91c1c; font-weight: bold;">{num_val} ngày trễ</span>'
                    else:
                        cell_val = ""
                except ValueError:
                    cell_val = val_str
            else:
                cell_val = val_str

            html.append(f'<td>{cell_val}</td>')
        html.append('</tr>')

    html.append('</tbody>')
    html.append('</table>')
    html.append('</div>')

    st.markdown("".join(html), unsafe_allow_html=True)



# --- TOP BANNER (RENDER ON EVERY PAGE) ---
st.markdown("""
<div class="top-banner">
    <h1>HỆ THỐNG KIỂM SOÁT KHÉP KÍN VÒNG ĐỜI GÓI THẦU (v1)</h1>
    <p>Dự án KĐT Ven sông Vinh | Tự động hóa tính toán & Tư vấn giải pháp AI</p>
</div>
""", unsafe_allow_html=True)

# --- 1. DASHBOARD VIEW ---
if choice == "📊 Dashboard Điều hành":
    st.write("## 📊 Dashboard Tổng quan Hệ thống")
    
    projects = business_logic.get_all_projects_calculated()
    active_projects = [p for p in projects if p['Ma_BSC']]
    
    count_red = sum(1 for p in active_projects if p['Co_Canh_bao'] == 'RED')
    count_orange = sum(1 for p in active_projects if p['Co_Canh_bao'] == 'ORANGE')
    count_yellow = sum(1 for p in active_projects if p['Co_Canh_bao'] == 'YELLOW')
    count_green = sum(1 for p in active_projects if p['Co_Canh_bao'] == 'GREEN')
    
    # Render KPI Cards
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <div style="font-size: 0.8rem; color: #64748b; font-weight: 700; letter-spacing: 0.05em;">TỔNG HẠNG MỤC THEO DÕI</div>
            <div style="font-size: 2.3rem; font-weight: 800; color: #0f172a; margin-top: 5px;">{len(active_projects)}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col2:
        st.markdown(f"""
        <div class="metric-card metric-red">
            <div style="font-size: 0.8rem; color: #b91c1c; font-weight: 700; letter-spacing: 0.05em;">🔴 CẢNH BÁO ĐỎ</div>
            <div style="font-size: 2.3rem; font-weight: 800; color: #991b1b; margin-top: 5px;">{count_red}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col3:
        st.markdown(f"""
        <div class="metric-card metric-orange">
            <div style="font-size: 0.8rem; color: #c2410c; font-weight: 700; letter-spacing: 0.05em;">🟠 CẢNH BÁO CAM</div>
            <div style="font-size: 2.3rem; font-weight: 800; color: #9a3412; margin-top: 5px;">{count_orange}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col4:
        st.markdown(f"""
        <div class="metric-card metric-yellow">
            <div style="font-size: 0.8rem; color: #a16207; font-weight: 700; letter-spacing: 0.05em;">🟡 CẢNH BÁO VÀNG</div>
            <div style="font-size: 2.3rem; font-weight: 800; color: #854d0e; margin-top: 5px;">{count_yellow}</div>
        </div>
        """, unsafe_allow_html=True)
        
    with col5:
        st.markdown(f"""
        <div class="metric-card metric-green">
            <div style="font-size: 0.8rem; color: #15803d; font-weight: 700; letter-spacing: 0.05em;">🟢 BÌNH THƯỜNG</div>
            <div style="font-size: 2.3rem; font-weight: 800; color: #166534; margin-top: 5px;">{count_green}</div>
        </div>
        """, unsafe_allow_html=True)
        
    st.divider()
    
    # Financial metrics totals
    total_budget = sum(p['Ngan_sach'] for p in projects if p['Ngan_sach'])
    total_contract = sum(p['Gia_tri_HDCU'] for p in projects if p['Gia_tri_HDCU'])
    total_cost_calc = sum(p['Total_Cost'] for p in active_projects)
    
    st.write("### 💰 Phân tích Ngân sách & Chi phí Hệ thống")
    fcol1, fcol2, fcol3 = st.columns(3)
    with fcol1:
        st.metric("Tổng Ngân sách Kế hoạch", f"{total_budget:,.2f} tỷ VNĐ")
    with fcol2:
        st.metric("Tổng Hợp đồng Cung ứng", f"{total_contract:,.2f} tỷ VNĐ")
    with fcol3:
        st.metric("Tổng Chi phí Thực tế Lũy kế", f"{total_cost_calc:,.2f} tỷ VNĐ", delta=f"{total_cost_calc - total_contract:,.2f} tỷ phát sinh")

    st.divider()
    
    # Action Header
    ecol1, ecol2 = st.columns([8, 2])
    with ecol1:
        st.write("### 📌 Danh sách các hạng mục cảnh báo cần xử lý (RED/ORANGE)")
    with ecol2:
        # Excel Export Button
        try:
            excel_stream = exporter.get_excel_report_stream()
            st.download_button(
                label="📥 Xuất báo cáo Excel (.xlsx)",
                data=excel_stream,
                file_name=f"Bao_Cao_Kiem_Soat_Du_An_{datetime.date.today().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="btn_export_excel",
                use_container_width=True
            )
        except Exception as e:
            st.error(f"Lỗi xuất Excel: {e}")

    # Show delayed or budget overrun projects
    critical_projects = [p for p in active_projects if p['Co_Canh_bao'] in ('RED', 'ORANGE')]
    
    if not critical_projects:
        st.success("🎉 Hệ thống hoạt động tốt! Không có rủi ro Đỏ hoặc Cam nào được phát hiện.")
    else:
        for p in critical_projects:
            color_badge = "badge-red" if p['Co_Canh_bao'] == 'RED' else "badge-orange"
            text_color = "🔴 ĐỎ" if p['Co_Canh_bao'] == 'RED' else "🟠 CAM"
            
            st.markdown(f"""
            <div class="warning-item">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span style="font-size: 1.1rem; font-weight: 700; color: #1e3a8a;">{p['Hang_muc']} (Mã BSC: {p['Ma_BSC']})</span>
                    <span class="badge {color_badge}">{text_color}</span>
                </div>
                <div style="margin-top: 8px; font-size: 0.9rem; color: #475569;">
                    <strong>Phụ trách:</strong> {p['Phu_trach']} | 
                    <strong>Nhóm:</strong> {p['Nhom_CT']} | 
                    <strong>Ngân sách:</strong> {p['Ngan_sach'] or 0.0:.2f} tỷ | 
                    <strong>Tổng chi thực tế:</strong> {p['Total_Cost'] or 0.0:.2f} tỷ
                </div>
                <div style="margin-top: 8px; color: #dc2626; font-weight: 600; font-size: 0.9rem; background-color: #fff5f5; padding: 8px 12px; border-radius: 6px; border: 1px solid #fee2e2;">
                    ⚠️ Chi tiết: {p['Canh_bao_Text']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Gemini AI Solutions
            with st.expander(f"🤖 Đề xuất Phương án & Biện pháp Đẩy nhanh Tiến độ (Gemini AI) cho {p['Ma_BSC']}"):
                if st.button("💡 Tạo giải pháp xử lý rủi ro xây dựng", key=f"risk_btn_{p['id']}"):
                    with st.spinner("Gemini AI đang tổng hợp giải pháp kỹ thuật xây dựng nâng cao..."):
                        try:
                            solutions = ai_service.get_risk_advisor_solutions(p, st.session_state.get('gemini_api_key'))
                            st.markdown(solutions)
                        except Exception as ex:
                            st.error(f"Lỗi: {ex}")

# --- 2. MASTER TABLE VIEW ---
elif choice == "📋 Bảng Tổng hợp (Master)":
    st.write("## 📋 Bảng Tổng hợp Master (BANG TONG HOP)")
    
    projects = business_logic.get_all_projects_calculated()
    
    # Filter/Group by Nhóm CT
    nhom_ct_list = sorted(list(set([p['Nhom_CT'] for p in projects if p['Nhom_CT']])))
    
    # Import Excel data expander
    with st.expander("📥 Nhập dữ liệu từ file Excel (Import)"):
        st.write("Tải lên file Excel để cập nhật toàn bộ cơ sở dữ liệu. Lưu ý: Thao tác này sẽ xóa sạch dữ liệu cũ và cập nhật lại theo file mới.")
        curr_user = st.session_state.get('current_user') or {}
        role = curr_user.get('Vai_Tro')
        is_admin = (curr_user.get('Chuc_Vu') == 'Admin' or role == 'admin2' or curr_user.get('Ho_Ten') == 'Hồ Nghĩa Chất' or curr_user.get('Ma_NV') == '38')
        is_ktkh_qltk = (role in ('KTKH', 'QLTK'))
        has_import_perm = is_admin or is_ktkh_qltk or check_permission('Them_HD')
        if not has_import_perm:
            st.warning("⚠️ Bạn không có quyền nhập dữ liệu từ Excel.")
        
        uploaded_file = st.file_uploader(
            "Chọn file Excel (.xlsx, .xls)", 
            type=["xlsx", "xls"], 
            disabled=not has_import_perm, 
            key="excel_file_uploader"
        )
        
        if uploaded_file is not None and has_import_perm:
            if st.button("🚀 Xác nhận Import", key="btn_confirm_import", type="primary"):
                with st.spinner("Đang xử lý dữ liệu file Excel..."):
                    try:
                        # Overwrite local master Excel file with uploaded content
                        with open(database.EXCEL_PATH, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                            
                        conn = database.get_connection()
                        database.seed_from_excel(conn, uploaded_file)
                        conn.close()
                        
                        # Log action (automatically triggers project_control.db upload to Google Drive)
                        database.log_action(curr_user.get('Ho_Ten', 'Ẩn danh'), "Import Excel", "packages", 0, "Nhập dữ liệu dự án từ file Excel uploader")
                        
                        # Trigger background Excel file upload to Google Drive
                        try:
                            import gdrive_sync
                            import threading
                            threading.Thread(target=gdrive_sync.upload_to_gdrive, args=(database.EXCEL_PATH, "TDG_Masterfile BQLDA_v1_20260623.xlsx"), daemon=True).start()
                        except Exception:
                            pass
                            
                        st.success("🎉 Nhập dữ liệu từ file Excel thành công!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Lỗi khi import file Excel: {e}")

    # Add new item
    with st.expander("➕ Thêm mới Hạng mục công việc"):
        with st.form("add_project_form"):
            curr_user = st.session_state.get('current_user') or {}
            role = curr_user.get('Vai_Tro')
            is_admin = (curr_user.get('Chuc_Vu') == 'Admin' or role == 'admin2' or curr_user.get('Ho_Ten') == 'Hồ Nghĩa Chất' or curr_user.get('Ma_NV') == '38')
            has_add_perm = is_admin or (check_permission('Them_HD') and role in ('KTKH', 'QLTK'))

            c1, c2, c3 = st.columns(3)
            with c1:
                new_tt = st.text_input("Mã TT (Ví dụ: 3, 2.1, 2.2.1)", disabled=not has_add_perm)
                new_ma_bsc = st.text_input("Mã BSC *", disabled=not has_add_perm)
                
                # Searchable dropdown for Goi_thau
                gts = load_goi_thau_options()
                selected_gt = st.selectbox("Gói thầu (PL)", gts + ["- Khác (Nhập mới) -"], index=gts.index("PL10") if "PL10" in gts else 0, disabled=not has_add_perm)
                if selected_gt == "- Khác (Nhập mới) -":
                    new_goi_thau = st.text_input("Nhập tên Gói thầu mới *")
                else:
                    new_goi_thau = selected_gt
            with c2:
                new_nhom_ct = st.selectbox("Nhóm công trình", ["Hạ tầng kỹ thuật", "Xây dựng dân dụng", "Công trình phục vụ KD"], disabled=not has_add_perm)
                new_hang_muc = st.text_input("Tên Hạng mục / Công việc *", disabled=not has_add_perm)
                
                # Searchable dropdown for Phu_trach
                pts = load_personnel_options()
                selected_pt = st.selectbox("Kỹ sư Phụ trách", pts + ["- Khác (Nhập mới) -"], disabled=not has_add_perm)
                if selected_pt == "- Khác (Nhập mới) -":
                    new_phu_trach = st.text_input("Nhập tên Kỹ sư Phụ trách mới *")
                else:
                    new_phu_trach = selected_pt
            with c3:
                new_ngan_sach = st.number_input("Ngân sách phê duyệt (tỷ)", min_value=0.0, step=0.1, disabled=not (is_admin or role == 'BQLDA'))
                new_ngay_bd = st.date_input("Ngày bắt đầu (Yêu cầu CĐT)", value=None, disabled=not has_add_perm)
                new_ngay_kt = st.date_input("Ngày kết thúc (Yêu cầu CĐT)", value=None, disabled=not has_add_perm)
                
            if not has_add_perm:
                st.warning("⚠️ Bạn không có quyền thêm mới hạng mục.")
            submitted = st.form_submit_button("Lưu Hạng mục", disabled=not has_add_perm)
            if submitted:
                if not has_add_perm:
                    st.error("⚠️ Bạn không có quyền thực hiện hành động này.")
                elif not new_hang_muc:
                    st.error("Vui lòng nhập Tên Hạng mục / Công việc.")
                else:
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    
                    bd_str = new_ngay_bd.strftime('%Y-%m-%d') if new_ngay_bd else None
                    kt_str = new_ngay_kt.strftime('%Y-%m-%d') if new_ngay_kt else None
                    
                    parent_code = None
                    if new_tt and '.' in new_tt:
                        parent_code = new_tt[:new_tt.rfind('.')]
                    cursor.execute("""
                        INSERT INTO packages (package_code, parent_code, bsc_code, goi_thau_pl, package_name, project_group, person_in_charge, plan_start_date, plan_end_date, cdt_budget)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (new_tt, parent_code, new_ma_bsc, new_goi_thau, new_hang_muc, new_nhom_ct, new_phu_trach, bd_str, kt_str, new_ngan_sach))
                    conn.commit()
                    database.log_action(curr_user.get('Ho_Ten', 'Ẩn danh'), "Thêm mới", "packages", new_tt, f"Thêm hạng mục mới '{new_hang_muc}' (Mã BSC: {new_ma_bsc})")
                    conn.close()
                    st.success("Đã thêm hạng mục mới thành công!")
                    st.rerun()

    # Edit item section
    with st.expander("✏️ Cập nhật chi tiết Hạng mục công việc"):
        edit_proj_options = [f"{p['id']} - [{p['TT']}] {p['Hang_muc']}" for p in projects]
        selected_proj_to_edit = st.selectbox("Chọn Hạng mục cần chỉnh sửa:", ["-- Chọn Hạng mục --"] + edit_proj_options)
        if selected_proj_to_edit != "-- Chọn Hạng mục --":
            p_id = int(selected_proj_to_edit.split(" - ")[0])
            matched_proj = next((p for p in projects if p['id'] == p_id), None)
            if matched_proj:
                st.session_state['show_edit_form'] = True
                st.session_state['edit_project_id'] = matched_proj['id']
                st.info(f"Đã chọn: {matched_proj['Hang_muc']}. Vui lòng cuộn xuống dưới cùng để cập nhật chi tiết.")

    # Delete item section
    with st.expander("🗑️ Xóa Hạng mục công việc"):
        del_proj_options = [f"{p['id']} - [{p['TT']}] {p['Hang_muc']}" for p in projects]
        selected_proj_to_del = st.selectbox("Chọn Hạng mục cần xóa vĩnh viễn:", ["-- Chọn Hạng mục --"] + del_proj_options)
        if selected_proj_to_del != "-- Chọn Hạng mục --":
            p_id_del = int(selected_proj_to_del.split(" - ")[0])
            matched_proj_del = next((p for p in projects if p['id'] == p_id_del), None)
            if matched_proj_del:
                curr_user = st.session_state.get('current_user') or {}
                role = curr_user.get('Vai_Tro')
                is_admin = (curr_user.get('Chuc_Vu') == 'Admin' or role == 'admin2' or curr_user.get('Ho_Ten') == 'Hồ Nghĩa Chất' or curr_user.get('Ma_NV') == '38')
                has_delete_perm = is_admin or check_permission('Xoa_HD')
                if not has_delete_perm:
                    st.warning("⚠️ Bạn không có quyền xóa hạng mục.")
                if st.button("❌ Xác nhận xóa vĩnh viễn hạng mục này", key="btn_confirm_del_proj", type="primary", disabled=not has_delete_perm):
                    if not has_delete_perm:
                        st.error("⚠️ Bạn không có quyền thực hiện hành động này.")
                    else:
                        conn = database.get_connection()
                        cursor = conn.cursor()
                        cursor.execute("DELETE FROM packages WHERE id = ?", (p_id_del,))
                        conn.commit()
                        database.log_action(curr_user.get('Ho_Ten', 'Ẩn danh'), "Xóa", "packages", p_id_del, f"Xóa hạng mục '{matched_proj_del['Hang_muc']}' (Mã BSC: {matched_proj_del['Ma_BSC']})")
                        conn.close()
                        st.success(f"Đã xóa thành công hạng mục '{matched_proj_del['Hang_muc']}'!")
                        st.rerun()

    # Dynamic Tabs for grouped views - MATCHING THE RED HIGHLIGHT IN IMAGES AND UX SMOOTHNESS
    st.write("### 📑 Bộ lọc các cột theo chức năng kiểm soát")
    
    st.markdown("""
    <style>
        /* Custom styling for st.segmented_control to look like a premium tab bar */
        div[data-testid="stSegmentedControl"] {
            background-color: #f1f5f9 !important;
            padding: 6px !important;
            border-radius: 12px !important;
            border: 1px solid #cbd5e1 !important;
            gap: 12px !important;
            display: inline-flex !important;
            margin-bottom: 12px !important;
        }
        div[data-testid="stSegmentedControl"] button {
            background-color: transparent !important;
            border: none !important;
            color: #475569 !important;
            font-weight: 600 !important;
            border-radius: 8px !important;
            padding: 8px 16px !important;
            font-size: 0.82rem !important;
            transition: all 0.2s ease !important;
            box-shadow: none !important;
        }
        div[data-testid="stSegmentedControl"] button:hover {
            color: #ef4444 !important;
            background-color: rgba(239, 68, 68, 0.05) !important;
        }
        div[data-testid="stSegmentedControl"] button[aria-checked="true"] {
            background-color: #ffffff !important;
            color: #ef4444 !important;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -1px rgba(0, 0, 0, 0.04) !important;
            font-weight: 700 !important;
            border: 1px solid rgba(239, 68, 68, 0.1) !important;
        }
        
        /* Hide default label of segmented controls for clean look */
        div[data-testid="stSegmentedControl"] label {
            display: none !important;
        }
        
        /* Layout spacing */
        .control-label {
            font-size: 0.82rem;
            font-weight: 700;
            color: #475569;
            margin-top: 16px;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
    </style>
    """, unsafe_allow_html=True)

    # 1. Cấp độ hiển thị
    st.markdown('<div class="control-label">Cấp độ hiển thị:</div>', unsafe_allow_html=True)
    st.segmented_control(
        "CẤP ĐỘ HIỂN THỊ:",
        options=["Cấp công trình", "Cấp chi tiết"],
        default="Cấp chi tiết",
        key="global_display_level"
    )
    
    # 2. Tab chức năng Master
    st.markdown('<div class="control-label">Mục kiểm soát chức năng:</div>', unsafe_allow_html=True)
    active_master_tab = st.segmented_control(
        "TAB CHỨC NĂNG MASTER:",
        options=[
            "🔴 A. Đầu vào CĐT",
            "🚚 B. Cung ứng & Hợp đồng",
            "📅 C. Kế hoạch Triển khai",
            "⚡ D. Chốt chặn Khởi công",
            "💰 E. Ngân sách & Chi phí",
            "📊 G. Quản lý Thi công",
            "🗂️ Tất cả dữ liệu"
        ],
        default="🔴 A. Đầu vào CĐT",
        key="active_master_tab"
    )
    # WBS Tree indent formatting
    def format_wbs_name(hang_muc, tt):
        return hang_muc

    # Master Column configuration
    master_column_config = {
        "TT": st.column_config.TextColumn("TT", width=60),
        "Nhóm công trình": st.column_config.TextColumn("Nhóm công trình", width=140),
        "Mã BSC": st.column_config.TextColumn("Mã BSC", width=120),
        "Hạng mục / Công việc": st.column_config.TextColumn("Hạng mục / Công việc", width=350),
        "Phụ trách": st.column_config.TextColumn("Phụ trách", width=120),
        "Ngày BD (YC CĐT)": st.column_config.DateColumn("Ngày BD (YC CĐT)", format="YYYY-MM-DD", width=120),
        "Ngày KT (YC CĐT)": st.column_config.DateColumn("Ngày KT (YC CĐT)", format="YYYY-MM-DD", width=120),
        "Ngân sách (tỷ)": st.column_config.NumberColumn("Ngân sách (tỷ)", format="%.2f tỷ", width=110),
        "KH phát hành HSTKTC": st.column_config.DateColumn("KH phát hành HSTKTC", format="YYYY-MM-DD", width=140),
        "TT HSTKTC": st.column_config.TextColumn("TT HSTKTC", width=110),
        "TT SPECS": st.column_config.TextColumn("TT SPECS", width=100),
        "TT BOQ/KL": st.column_config.TextColumn("TT BOQ/KL", width=110),
        "KH LCNT": st.column_config.DateColumn("KH LCNT", format="YYYY-MM-DD", width=110),
        "TT LCNT": st.column_config.TextColumn("TT LCNT", width=100),
        "KH Ký HĐCU": st.column_config.DateColumn("KH Ký HĐCU", format="YYYY-MM-DD", width=110),
        "TT Ký HĐCU": st.column_config.TextColumn("TT Ký HĐCU", width=110),
        "Giá trị HĐCU (tỷ)": st.column_config.NumberColumn("Giá trị HĐCU (tỷ)", format="%.2f tỷ", width=130),
        "% HĐ/NS (Tính)": st.column_config.NumberColumn("% HĐ/NS (Tính)", format="%.1f%%", width=110),
        "ĐK1 HSKT đủ": st.column_config.TextColumn("ĐK1 HSKT đủ", width=105),
        "ĐK2 HĐCU ký": st.column_config.TextColumn("ĐK2 HĐCU ký", width=105),
        "ĐK3 KHTK duyệt": st.column_config.TextColumn("ĐK3 KHTK duyệt", width=120),
        "ĐIỀU KIỆN ĐỦ": st.column_config.TextColumn("ĐIỀU KIỆN ĐỦ", width=140),
        "NGÀY KHỞI CÔNG": st.column_config.DateColumn("NGÀY KHỞI CÔNG", format="YYYY-MM-DD", width=130),
        "HS tiền KC (duyệt)": st.column_config.NumberColumn("HS tiền KC (duyệt)", format="%d bộ", width=130),
        "Lũy kế HĐ A-B": st.column_config.NumberColumn("Lũy kế HĐ A-B", format="%.2f tỷ", width=135),
        "Lũy kế Phát sinh B-B'": st.column_config.NumberColumn("Lũy kế Phát sinh B-B'", format="%.2f tỷ", width=140),
        "Tổng Chi phí Thực tế": st.column_config.NumberColumn("Tổng Chi phí Thực tế", format="%.2f tỷ", width=140),
        "Cảnh báo": st.column_config.TextColumn("Cảnh báo", width=140),
        "KH KLCV Tháng": st.column_config.ProgressColumn("KH Tháng", min_value=0.0, max_value=100.0, format="%.1f%%", width=120),
        "KQ KLCV Thực tế": st.column_config.ProgressColumn("KQ Thực tế", min_value=0.0, max_value=100.0, format="%.1f%%", width=120),
        "Đánh giá & Giải pháp Tháng": st.column_config.TextColumn("Đánh giá & Giải pháp Tháng", width=250),
        "T1 KQ": st.column_config.NumberColumn("T1 KQ", format="%.1f%%", width=85),
        "T2 KQ": st.column_config.NumberColumn("T2 KQ", format="%.1f%%", width=85),
        "T3 KQ": st.column_config.NumberColumn("T3 KQ", format="%.1f%%", width=85),
        "T4 KQ": st.column_config.NumberColumn("T4 KQ", format="%.1f%%", width=85),
        "Gói thầu (PL)": st.column_config.TextColumn("Gói thầu (PL)", width=110),
        "Ngày BD": st.column_config.DateColumn("Ngày BD", format="YYYY-MM-DD", width=120),
        "Ngày KT": st.column_config.DateColumn("Ngày KT", format="YYYY-MM-DD", width=120),
        "Khởi công": st.column_config.TextColumn("Khởi công", width=130),
    }

    # Sort and group projects by Gói thầu (PL) in a parent-child structure
    def build_parent_child_rows(proj_list):
        import re
        def parse_tt(tt_val):
            if not tt_val:
                return (999999,)
            parts = re.split(r'[.-]', str(tt_val))
            res = []
            for p_part in parts:
                p_part = p_part.strip()
                try:
                    res.append(float(p_part))
                except ValueError:
                    res.append(p_part)
            return tuple(res)
        
        # Sort projects by TT numerically/hierarchically
        sorted_projs = sorted(proj_list, key=lambda x: parse_tt(x.get('TT')))
        
        hierarchical = []
        for p_item in sorted_projs:
            tt_str = str(p_item.get('TT') or '').strip()
            level = 1
            if '.' in tt_str:
                parts = tt_str.split('.')
                level = len(parts)
            
            # Check if this item has children
            has_children = False
            for other in sorted_projs:
                other_tt = str(other.get('TT') or '').strip()
                if other_tt != tt_str and other_tt.startswith(tt_str + '.'):
                    has_children = True
                    break
            
            child_row = dict(p_item)
            child_row['wbs_level'] = level
            child_row['has_children'] = has_children
            hierarchical.append(child_row)
        return hierarchical

    projects_sorted = build_parent_child_rows(projects)

    def render_project_grid(proj_list, cols_to_show, key_suffix=""):
        display_level = st.session_state.get('global_display_level', 'Cấp chi tiết')
        
        # User permissions for action buttons
        curr_user = st.session_state.get('current_user') or {}
        role = curr_user.get('Vai_Tro')
        is_admin = (curr_user.get('Chuc_Vu') == 'Admin' or role == 'admin2' or curr_user.get('Ho_Ten') == 'Hồ Nghĩa Chất' or curr_user.get('Ma_NV') == '38')
        can_sua = is_admin or (curr_user.get('Sua') == 1)
        can_xoa = is_admin or (curr_user.get('Xoa_HD') == 1)
        curr_ma_nv = str(curr_user.get('Ma_NV') or '').strip()

        # Copy cols_to_show and add Thao_tac column
        cols_to_show = dict(cols_to_show)
        cols_to_show["Thao_tac"] = "Thao tác"

        col_widths_map = {
            "a": ["4%", "10%", "8%", "18%", "8%", "9%", "9%", "8%", "9%", "5%", "5%", "5%"],
            "b": ["4%", "10%", "9%", "22%", "10%", "8%", "10%", "8%", "8%", "8%"],
            "c": ["4%", "10%", "9%", "22%", "8%", "8%", "8%", "10%", "10%", "8%"],
            "d": ["4%", "11%", "9%", "23%", "8%", "10%", "10%", "12%", "10%"],
            "g": ["4%", "10%", "8%", "18%", "9%", "9%", "15%", "5%", "5%", "5%", "7%"],
            "all": ["4%", "10%", "8%", "8%", "18%", "8%", "8%", "8%", "8%", "9%", "9%"]
        }
        
        orig_widths = col_widths_map.get(key_suffix, [f"{int(100/(len(cols_to_show)-1))}%"] * (len(cols_to_show)-1))
        widths = list(orig_widths) + ["110px"]
        html = []
        
        css = """
        <style>
            .table-container {
                width: 100%;
                max-height: 550px;
                overflow-y: auto;
                overflow-x: auto;
                border-radius: 12px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
                border: 1px solid #cbd5e1;
                margin-bottom: 2rem;
                background: white;
            }
            .master-table {
                width: 100%;
                border-collapse: collapse;
                font-family: 'Outfit', 'Inter', sans-serif;
                font-size: 0.775rem;
                color: #1e293b;
                table-layout: fixed;
            }
            .master-table th {
                background-color: #1e293b !important;
                color: #ffffff !important;
                font-weight: 700;
                text-align: center;
                padding: 12px 10px;
                position: sticky;
                top: 0;
                z-index: 10;
                border: 1px solid #334155;
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.03em;
                word-wrap: break-word;
                white-space: normal;
                line-height: 1.3;
            }
            .master-table td {
                padding: 10px 12px;
                border: 1px solid #cbd5e1;
                vertical-align: middle;
                word-wrap: break-word;
                white-space: normal;
                line-height: 1.4;
                color: #334155;
            }
            .master-table tr:hover {
                background-color: #f1f5f9 !important;
                cursor: default;
            }
            /* Styling for Parent Row */
            .master-table tr.wbs-row-style {
                background-image: linear-gradient(to right, #f8fafc, #eff6ff) !important;
                font-weight: 700;
                color: #1e3a8a !important;
            }
            .master-table tr.wbs-row-style td {
                border-bottom: 2px solid #93c5fd;
                border-top: 2px solid #93c5fd;
                color: #1e3a8a !important;
                font-size: 0.8rem;
            }
            
            /* Column-specific styles */
            .master-table td:first-child {
                font-weight: 700;
                color: #4f46e5;
                background-color: #faf5ff;
                text-align: center;
            }
            .master-table td.bsc-cell {
                font-weight: 700;
                color: #0d9488;
                text-align: center;
                background-color: #f0fdfa;
            }
            
            .num-budget {
                color: #0f766e;
                font-weight: 700;
                font-size: 0.8rem;
            }
            .date-cell {
                color: #475569;
                font-size: 0.75rem;
                font-weight: 600;
                text-align: center;
                display: block;
            }
            
            /* Badges styling */
            .master-badge {
                padding: 5px 10px;
                border-radius: 20px;
                font-size: 0.7rem;
                font-weight: 700;
                display: inline-block;
                text-align: center;
                line-height: 1.2;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
            }
            .master-badge-green { background-color: #dcfce7; color: #166534; border: 1px solid #bbf7d0; }
            .master-badge-red { background-color: #fee2e2; color: #991b1b; border: 1px solid #fca5a5; }
            .master-badge-yellow { background-color: #fefce8; color: #854d0e; border: 1px solid #fef08a; }
            .master-badge-orange { background-color: #ffedd5; color: #9a3412; border: 1px solid #fed7aa; }

            /* Custom progress bar */
            .html-progress-container {
                width: 100%;
                background-color: #e2e8f0;
                border-radius: 10px;
                overflow: hidden;
                height: 8px;
                margin-top: 6px;
                border: 1px solid #cbd5e1;
            }
            .html-progress-fill {
                height: 100%;
                border-radius: 10px;
            }
            .html-progress-text {
                font-size: 0.725rem;
                font-weight: 700;
                color: #475569;
            }

            /* Toggle Button */
            .toggle-btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 20px;
                height: 20px;
                border-radius: 50%;
                background-color: #3b82f6;
                color: #ffffff !important;
                border: 1px solid #2563eb;
                cursor: pointer;
                font-weight: 800;
                font-size: 0.95rem;
                margin-right: 10px;
                user-select: none;
                box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
                transition: all 0.2s ease-in-out;
                line-height: 1;
            }
            .toggle-btn:hover {
                background-color: #1d4ed8;
                border-color: #1e40af;
                transform: scale(1.1);
                box-shadow: 0 4px 8px rgba(59, 130, 246, 0.5);
            }
            .wbs-level2-row {
                background-color: #ffffff !important;
            }
            .wbs-level3-row {
                background-color: #fafcfc !important;
            }
            .wbs-level3-row td {
                color: #475569 !important;
            }

            /* Action Buttons in Rows */
            .action-btn {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                padding: 4px 8px;
                font-size: 0.725rem;
                font-weight: 600;
                border-radius: 4px;
                border: none;
                cursor: pointer;
                transition: all 0.2s ease;
                text-decoration: none;
            }
            .action-btn[disabled] {
                opacity: 0.4;
                cursor: not-allowed;
                pointer-events: none;
            }
            .btn-edit {
                background-color: #eff6ff;
                color: #2563eb;
                border: 1px solid #bfdbfe;
            }
            .btn-edit:hover {
                background-color: #2563eb;
                color: #ffffff;
            }
            .btn-delete {
                background-color: #fef2f2;
                color: #dc2626;
                border: 1px solid #fca5a5;
            }
            .btn-delete:hover {
                background-color: #dc2626;
                color: #ffffff;
            }
        </style>
        """
        html.append(css)
        html.append('<div class="table-container">')
        html.append('<table class="master-table">')
        
        html.append('<colgroup>')
        for idx, col_name in enumerate(cols_to_show.values()):
            w = widths[idx] if idx < len(widths) else "auto"
            html.append(f'<col style="width: {w};">')
        html.append('</colgroup>')
        
        html.append('<thead><tr>')
        for col_name in cols_to_show.values():
            html.append(f'<th>{col_name}</th>')
        html.append('</tr></thead>')
        
        html.append('<tbody>')
        for p in proj_list:
            is_wbs = p.get('has_children', False)
            level = p.get('wbs_level', 1)
            tt_str = str(p.get('TT') or '').strip()
            pkg = p.get('Goi_thau') or ""
            base_pkg = pkg.split('.')[0] if '.' in pkg else pkg
            
            # CSS classes and style based on WBS Level
            initial_style = 'style="display: none;"' if (display_level == "Cấp công trình" and level > 1) else ""
            
            if level == 1:
                tr_class = 'class="wbs-row-style"'
            elif level == 2:
                tr_class = f'class="child-row-{base_pkg}-{key_suffix} wbs-level2-row"'
            else:
                parent_prefix = tt_str[:tt_str.rfind('.')].replace('.', '_')
                tr_class = f'class="child-row-level3-{parent_prefix}-{key_suffix} child-row-{base_pkg}-{key_suffix} wbs-level3-row"'
                
            tr_attrs = f'data-tt="{tt_str}" data-level="{level}" data-parent="{base_pkg}" {initial_style}'
            html.append(f'<tr {tr_class} {tr_attrs}>')
            
            for col_key, col_name in cols_to_show.items():
                val = ""
                is_empty_parent = (level == 1 and is_wbs and not p.get('Ma_BSC'))
                
                if col_key == "Ma_BSC" and not p['Ma_BSC']:
                    val = ""
                elif col_key == "Hang_muc_formatted":
                    padding_left_val = (level - 1) * 20
                    indent_symbol = '<span style="color: #94a3b8; margin-right: 6px; font-weight: bold; font-size: 0.85rem;">└─</span>' if level > 1 else ''
                    
                    if is_wbs:
                        btn_symbol = "+" if (display_level == "Cấp công trình" and level == 1) else "−"
                        click_action = f"toggleLevel1('{tt_str}', '{key_suffix}')" if level == 1 else f"toggleLevel2('{tt_str}', '{key_suffix}')"
                        btn_id = f"btn-toggle-{tt_str.replace('.', '_')}-{key_suffix}"
                        
                        val = f"""
                        <div style="padding-left: {padding_left_val}px; display: flex; align-items: center;">
                            {indent_symbol}
                            <span id="{btn_id}" class="toggle-btn" onclick="{click_action}">{btn_symbol}</span>
                            <b style="color: #1e3a8a; font-size: 0.8rem;">{p['Hang_muc'].strip()}</b>
                        </div>
                        """
                    else:
                        val = f"""
                        <div style="padding-left: {padding_left_val}px; display: flex; align-items: center;">
                            {indent_symbol}
                            <span style="color: #334155; {'font-weight: 700;' if level == 1 else ''}">{p['Hang_muc'].strip()}</span>
                        </div>
                        """
                elif col_key in ("DK1_HSKT", "DK2_HDCU", "DK3_KHTK"):
                    chk = "N/A" if is_wbs else ("✔" if p[col_key] else "✘")
                    if chk == "✔":
                        val = '<span style="color: #166534; font-weight: bold; font-size: 1rem;">✔</span>'
                    elif chk == "✘":
                        val = '<span style="color: #b91c1c; font-weight: bold; font-size: 1rem;">✘</span>'
                    else:
                        val = chk
                elif col_key == "Dieu_kien_du":
                    dk_val = "---" if is_wbs else p[col_key]
                    if dk_val == "ĐỦ ĐIỀU KIỆN":
                        val = '<span class="master-badge master-badge-green">ĐỦ ĐIỀU KIỆN</span>'
                    elif dk_val == "CHƯA ĐỦ ĐK":
                        val = '<span class="master-badge master-badge-red">CHƯA ĐỦ ĐK</span>'
                    else:
                        val = dk_val
                elif col_key == "Co_Canh_bao":
                    if is_wbs:
                        val = "---"
                    else:
                        warning_val = p[col_key]
                        if warning_val == 'RED':
                            val = '<span class="master-badge master-badge-red">🔴 ĐỎ (Rủi ro)</span>'
                        elif warning_val == 'ORANGE':
                            val = '<span class="master-badge master-badge-orange">🟠 CAM (Theo dõi)</span>'
                        elif warning_val == 'YELLOW':
                            val = '<span class="master-badge master-badge-yellow">🟡 VÀNG (Chậm nhẹ)</span>'
                        else:
                            val = '<span class="master-badge master-badge-green">🟢 XANH (Bình thường)</span>'
                elif col_key in ("KH_Thang", "KQ_Thang"):
                    if is_wbs:
                        val = ""
                    else:
                        pct = p[col_key] * 100 if p[col_key] is not None else 0.0
                        bar_color = "#22c55e" if col_key == "KQ_Thang" else "#3b82f6"
                        val = f"""
                        <span class="html-progress-text">{pct:.1f}%</span>
                        <div class="html-progress-container">
                            <div class="html-progress-fill" style="width: {min(pct, 100.0)}%; background-color: {bar_color};"></div>
                        </div>
                        """
                elif col_key in ("T1_KQ", "T2_KQ", "T3_KQ", "T4_KQ", "Percent_HDCU_NS"):
                    pct = p[col_key] * 100 if p[col_key] is not None else None
                    if pct is not None:
                        if col_key == "Percent_HDCU_NS" and pct > 100.0:
                            val = f'<span style="color: #b91c1c; font-weight: bold;">{pct:.1f}%</span>'
                        else:
                            val = f'{pct:.1f}%'
                    else:
                        val = ""
                elif col_key in ("Ngan_sach", "Gia_tri_HDCU", "Luy_ke_HDCU", "Luy_ke_Phat_sinh", "Total_Cost"):
                    num = p[col_key]
                    try:
                        if num is not None and str(num).strip() != "" and str(num).lower() != "nan":
                            val = f"<b>{float(num):,.2f} tỷ</b>"
                        else:
                            val = ""
                    except Exception:
                        val = ""
                elif col_key in ("TT_HSTKTC", "TT_SPECS", "TT_BOQ", "TT_LCNT", "TT_Ky_HDCU", "TT_KHTK"):
                    status_str = str(p[col_key]).strip() if p[col_key] else ""
                    if status_str in ("Đã phát hành", "Đã cấp", "Đã bàn giao", "Đã ký", "Đã CU", "Đã duyệt", "Hoàn thiện"):
                        val = f'<span class="master-badge master-badge-green">{status_str}</span>'
                    elif status_str in ("Chưa có TK", "Chưa có", "Chưa bàn giao", "Chưa LCNT", "Chưa CU", "Chưa trình"):
                        val = f'<span class="master-badge master-badge-red">{status_str}</span>'
                    elif any(word in status_str for word in ("Đang", "Chờ", "Theo đợt", "Điều chỉnh")):
                        val = f'<span class="master-badge master-badge-yellow">{status_str}</span>'
                    else:
                        val = status_str
                elif col_key == "Thao_tac":
                    if is_wbs:
                        val = ""
                    else:
                        edit_dis = "" if can_sua else "disabled title='Bạn không có quyền sửa'"
                        del_dis = "" if can_xoa else "disabled title='Bạn không có quyền xóa'"
                        val = f'''
                        <div style="display: flex; gap: 4px; justify-content: center; align-items: center;">
                            <button class="action-btn btn-edit" {edit_dis} onclick="event.stopPropagation(); window.parent.location.href = window.parent.location.origin + '/?uid={curr_ma_nv}&edit_row_id_form={p["id"]}';">✏️ Sửa</button>
                            <button class="action-btn btn-delete" {del_dis} onclick="event.stopPropagation(); if(confirm('Bạn có chắc chắn muốn xóa vĩnh viễn hạng mục này?')) {{ window.parent.location.href = window.parent.location.origin + '/?uid={curr_ma_nv}&delete_row_id={p["id"]}'; }}">🗑️ Xóa</button>
                        </div>
                        '''
                elif col_key.startswith("Ngay"):
                    item = p[col_key]
                    val = f'<span class="date-cell">{item}</span>' if item else ""
                else:
                    item = p[col_key]
                    val = item if item is not None else ""

                td_class = ""
                if col_key == "Ma_BSC" and not is_wbs and p['Ma_BSC']:
                    td_class = ' class="bsc-cell"'

                # Add data attributes for inline cell editing if it's not a parent row
                data_attrs = ""
                if not is_wbs:
                    data_attrs = f' data-id="{p["id"]}" data-col="{col_key}"'

                html.append(f'<td{td_class}{data_attrs}>{val}</td>')
            html.append('</tr>')
            
        html.append('</tbody>')
        html.append('</table>')
        html.append('</div>')
        
        # Clean JS script tag for the iframe container
        js = """
        <script>
        if (typeof window.toggleLevel1 !== 'function') {
            window.toggleLevel1 = function(parentTt, suffix) {
                var rows = document.querySelectorAll('.child-row-' + parentTt.split('.')[0] + '-' + suffix);
                var btn = document.getElementById('btn-toggle-' + parentTt.replace(/\./g, '_') + '-' + suffix);
                if (!rows || rows.length === 0) return;

                var isHidden = false;
                for (var i = 0; i < rows.length; i++) {
                    var row = rows[i];
                    var tt = row.getAttribute('data-tt');
                    if (tt && tt !== parentTt && tt.startsWith(parentTt + '.')) {
                        isHidden = (row.style.display === 'none' || window.getComputedStyle(row).display === 'none');
                        break;
                    }
                }

                for (var i = 0; i < rows.length; i++) {
                    var row = rows[i];
                    var tt = row.getAttribute('data-tt');
                    if (tt && tt !== parentTt && tt.startsWith(parentTt + '.')) {
                        row.style.display = isHidden ? '' : 'none';
                    }
                }

                if (btn) {
                    btn.innerHTML = isHidden ? '−' : '+';
                }
            };
        }

        if (typeof window.toggleLevel2 !== 'function') {
            window.toggleLevel2 = function(parentTt, suffix) {
                var rows = document.querySelectorAll('.child-row-' + parentTt.split('.')[0] + '-' + suffix);
                var btn = document.getElementById('btn-toggle-' + parentTt.replace(/\./g, '_') + '-' + suffix);
                if (!rows || rows.length === 0) return;

                var isHidden = false;
                for (var i = 0; i < rows.length; i++) {
                    var row = rows[i];
                    var tt = row.getAttribute('data-tt');
                    if (tt && tt !== parentTt && tt.startsWith(parentTt + '.')) {
                        isHidden = (row.style.display === 'none' || window.getComputedStyle(row).display === 'none');
                        break;
                    }
                }

                for (var i = 0; i < rows.length; i++) {
                    var row = rows[i];
                    var tt = row.getAttribute('data-tt');
                    if (tt && tt !== parentTt && tt.startsWith(parentTt + '.')) {
                        row.style.display = isHidden ? '' : 'none';
                    }
                }

                if (btn) {
                    btn.innerHTML = isHidden ? '−' : '+';
                }
            };
        }

        function initInlineEdit() {
            var cells = document.querySelectorAll('td[data-id][data-col]');
            cells.forEach(function(cell) {
                if (cell.querySelector('.toggle-btn')) return;

                cell.title = "Kích đúp để sửa trực tiếp";
                cell.addEventListener('dblclick', function() {
                    if (cell.querySelector('input')) return;

                    var oldVal = cell.textContent.trim();
                    var colName = cell.getAttribute('data-col');
                    if (colName === 'Hang_muc_formatted') {
                        oldVal = oldVal.replace(/^↳\s*/, '');
                    }
                    if (colName === 'Ngan_sach' && oldVal.endsWith(' tỷ')) {
                        oldVal = oldVal.replace(' tỷ', '').trim().replace(/,/g, '');
                    }

                    var input = document.createElement('input');
                    input.type = 'text';
                    input.value = oldVal;
                    input.style.width = '100%';
                    input.style.boxSizing = 'border-box';
                    input.style.padding = '4px';
                    input.style.fontFamily = 'inherit';
                    input.style.fontSize = 'inherit';
                    input.style.border = '2px solid #3b82f6';
                    input.style.borderRadius = '4px';
                    input.style.outline = 'none';

                    cell.innerHTML = '';
                    cell.appendChild(input);
                    input.focus();
                    input.select();

                    function save() {
                        var newVal = input.value.trim();
                        var rowId = cell.getAttribute('data-id');
                        if (newVal !== oldVal) {
                            var newSearch = '?uid=' + encodeURIComponent('{curr_ma_nv}') + '&edit_row_id=' + rowId + '&edit_col=' + colName + '&edit_val=' + encodeURIComponent(newVal);
                            window.parent.location.href = window.parent.location.origin + '/' + newSearch;
                        } else {
                            restore();
                        }
                    }

                    function restore() {
                        cell.innerHTML = '';
                        if (colName === 'Ngan_sach' && oldVal !== '') {
                            cell.innerHTML = '<span class="num-budget">' + parseFloat(oldVal).toFixed(2) + ' tỷ</span>';
                        } else if (colName.startsWith('Ngay') && oldVal !== '') {
                            cell.innerHTML = '<span class="date-cell">' + oldVal + '</span>';
                        } else {
                            cell.textContent = oldVal;
                        }
                    }

                    input.addEventListener('blur', save);
                    input.addEventListener('keydown', function(e) {
                        if (e.key === 'Enter') {
                            input.removeEventListener('blur', save);
                            save();
                        }
                        if (e.key === 'Escape') {
                            input.removeEventListener('blur', save);
                            restore();
                        }
                    });
                });
            });
        }

        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', initInlineEdit);
        } else {
            initInlineEdit();
        }
        </script>
        """
        html.append(js)

        # Render inside an iframe using components.html for native Javascript execution on Streamlit Cloud
        import streamlit.components.v1 as components
        iframe_height = min(600, len(projects_sorted) * 45 + 100)
        components.html("".join(html), height=iframe_height, scrolling=True)


    # Render Master Table dynamically based on the selected active_master_tab
    if active_master_tab == "🔴 A. Đầu vào CĐT":
        cols_a = {
            "TT": "TT",
            "Nhom_CT": "Nhóm công trình",
            "Ma_BSC": "Mã BSC",
            "Hang_muc_formatted": "Hạng mục / Công việc",
            "Phu_trach": "Phụ trách",
            "Ngay_BD_YC": "Ngày BD (YC CĐT)",
            "Ngay_KT_YC": "Ngày KT (YC CĐT)",
            "Ngan_sach": "Ngân sách (tỷ)",
            "KH_phat_hanh_HSTKTC": "KH phát hành HSTKTC",
            "TT_HSTKTC": "TT HSTKTC",
            "TT_SPECS": "TT SPECS",
            "TT_BOQ": "TT BOQ/KL"
        }
        render_project_grid(projects_sorted, cols_a, "a")
        
    elif active_master_tab == "🚚 B. Cung ứng & Hợp đồng":
        cols_b = {
            "TT": "TT",
            "Nhom_CT": "Nhóm công trình",
            "Ma_BSC": "Mã BSC",
            "Hang_muc_formatted": "Hạng mục / Công việc",
            "KH_LCNT": "KH LCNT",
            "TT_LCNT": "TT LCNT",
            "KH_Ky_HDCU": "KH Ký HĐCU",
            "TT_Ky_HDCU": "TT Ký HĐCU",
            "Gia_tri_HDCU": "Giá trị HĐCU (tỷ)",
            "Percent_HDCU_NS": "% HĐ/NS (Tính)"
        }
        render_project_grid(projects_sorted, cols_b, "b")

    elif active_master_tab == "📅 C. Kế hoạch Triển khai":
        cols_tab_c = {
            "TT": "TT",
            "Nhom_CT": "Nhóm công trình",
            "Ma_BSC": "Mã BSC",
            "Hang_muc_formatted": "Hạng mục / Công việc",
            "KH_ky_PLHD": "KH Ký PLHĐ CĐT",
            "TT_Ky_PLHD": "TT Ký PLHĐ CĐT",
            "KH_PD_KHTK": "KH PD KHTK",
            "TT_KHTK": "TT KHTK"
        }
        render_project_grid(projects_sorted, cols_tab_c, "tab_c")

    elif active_master_tab == "⚡ D. Chốt chặn Khởi công":
        cols_c = {
            "TT": "TT",
            "Nhom_CT": "Nhóm công trình",
            "Ma_BSC": "Mã BSC",
            "Hang_muc_formatted": "Hạng mục / Công việc",
            "DK1_HSKT": "ĐK1 HSKT đủ",
            "DK2_HDCU": "ĐK2 HĐCU ký",
            "DK3_KHTK": "ĐK3 KHTK duyệt",
            "Dieu_kien_du": "ĐIỀU KIỆN ĐỦ",
            "Ngay_BD_Khoi_Cong": "NGÀY BĐ KHỞI CÔNG",
            "Approved_HSo_Count": "HS tiền KC (duyệt)"
        }
        render_project_grid(projects_sorted, cols_c, "c")

    elif active_master_tab == "💰 E. Ngân sách & Chi phí":
        cols_d = {
            "TT": "TT",
            "Nhom_CT": "Nhóm công trình",
            "Ma_BSC": "Mã BSC",
            "Hang_muc_formatted": "Hạng mục / Công việc",
            "Ngan_sach": "Ngân sách (tỷ)",
            "Luy_ke_HDCU": "Lũy kế HĐ A-B",
            "Luy_ke_Phat_sinh": "Lũy kế Phát sinh B-B`",
            "Total_Cost": "Tổng Chi phí Thực tế",
            "Co_Canh_bao": "Cảnh báo"
        }
        render_project_grid(projects_sorted, cols_d, "d")

    elif active_master_tab == "📊 G. Quản lý Thi công":
        cols_g = {
            "TT": "TT",
            "Nhom_CT": "Nhóm công trình",
            "Ma_BSC": "Mã BSC",
            "Hang_muc_formatted": "Hạng mục / Công việc",
            "KH_Thang": "KH KLCV Tháng",
            "KQ_Thang": "KQ KLCV Thực tế",
            "Danh_gia_Thang": "Đánh giá & Giải pháp Tháng",
            "T1_KQ": "T1 KQ",
            "T2_KQ": "T2 KQ",
            "T3_KQ": "T3 KQ",
            "T4_KQ": "T4 KQ"
        }
        render_project_grid(projects_sorted, cols_g, "g")

    else:
        cols_all = {
            "TT": "TT",
            "Nhom_CT": "Nhóm công trình",
            "Ma_BSC": "Mã BSC",
            "Goi_thau": "Gói thầu (PL)",
            "Hang_muc_formatted": "Hạng mục / Công việc",
            "Phu_trach": "Phụ trách",
            "Ngay_BD_YC": "Ngày BD",
            "Ngay_KT_YC": "Ngày KT",
            "Ngan_sach": "Ngân sách (tỷ)",
            "Dieu_kien_du": "Khởi công",
            "Co_Canh_bao": "Cảnh báo"
        }
        render_project_grid(projects_sorted, cols_all, "all")

    # Unified     # Form updating details (Redesigned to be tabs based and super smooth)
    if st.session_state.get('show_edit_form') and st.session_state.get('edit_project_id'):
        p_id = st.session_state['edit_project_id']
        proj = business_logic.get_project_by_id(p_id)

        curr_user = st.session_state.get('current_user') or {}
        role = curr_user.get('Vai_Tro')
        is_admin = (curr_user.get('Chuc_Vu') == 'Admin' or role == 'admin2' or curr_user.get('Ho_Ten') == 'Hồ Nghĩa Chất' or curr_user.get('Ma_NV') == '38')
        has_sua = (curr_user.get('Sua') == 1)

        # Enforce role-based access control (RBAC) per section
        can_edit_A = is_admin or (has_sua and role in ('KTKH', 'QLTK'))
        can_edit_B = is_admin or (has_sua and role == 'KTKH')
        can_edit_D = is_admin or (has_sua and role == 'BQLDA')
        can_edit_E = is_admin or (has_sua and role == 'BQLDA')
        can_edit_G = is_admin or (has_sua and role == 'BQLDA')

        has_edit_perm = can_edit_A or can_edit_B or can_edit_D or can_edit_E or can_edit_G

        st.divider()
        st.markdown(f"### ✏️ Biểu mẫu Cập nhật chi tiết: **{proj['Hang_muc']}**")

        with st.form("edit_project_detail_form"):
            # Sub-tabs inside the edit form for cleanliness
            etab1, etab2, etab2_c, etab3 = st.tabs(["📋 Định danh & Đầu vào CĐT", "🚚 Cung ứng & Hợp đồng", "📅 Kế hoạch Triển khai", "🚀 Tiến độ Thi công"])

            with etab1:
                col_e1, col_e2 = st.columns(2)
                with col_e1:
                    e_tt = st.text_input("Mã TT", value=proj['TT'] or "", disabled=not can_edit_A)
                    e_ma_bsc = st.text_input("Mã BSC", value=proj['Ma_BSC'] or "", disabled=not can_edit_A)
                    # Searchable dropdown for Goi_thau
                    gts = load_goi_thau_options()
                    curr_gt = proj['Goi_thau'] or ""
                    gts_options = gts + ["- Khác (Nhập mới) -"]
                    if curr_gt not in gts:
                        gts_options = [curr_gt] + gts_options

                    selected_gt = st.selectbox("Gói thầu", gts_options, index=gts_options.index(curr_gt) if curr_gt in gts_options else 0, disabled=not can_edit_A)
                    if selected_gt == "- Khác (Nhập mới) -":
                        e_goi_thau = st.text_input("Nhập tên Gói thầu mới *")
                    else:
                        e_goi_thau = selected_gt

                    # Searchable dropdown for Phu_trach
                    pts = load_personnel_options()
                    curr_pt = proj['Phu_trach'] or ""
                    pts_options = pts + ["- Khác (Nhập mới) -"]
                    if curr_pt not in pts:
                        pts_options = [curr_pt] + pts_options

                    selected_pt = st.selectbox("Người phụ trách", pts_options, index=pts_options.index(curr_pt) if curr_pt in pts_options else 0, disabled=not can_edit_A)
                    if selected_pt == "- Khác (Nhập mới) -":
                        e_phu_trach = st.text_input("Nhập tên Người phụ trách mới *")
                    else:
                        e_phu_trach = selected_pt
                with col_e2:
                    e_ngay_bd = st.date_input("Ngày BĐ (YC CĐT)", value=datetime.datetime.strptime(proj['Ngay_BD_YC'], '%Y-%m-%d').date() if proj['Ngay_BD_YC'] else None, disabled=not can_edit_A)
                    e_ngay_kt = st.date_input("Ngày KT (YC CĐT)", value=datetime.datetime.strptime(proj['Ngay_KT_YC'], '%Y-%m-%d').date() if proj['Ngay_KT_YC'] else None, disabled=not can_edit_A)
                    e_ngan_sach = st.number_input("Ngân sách (tỷ)", min_value=0.0, value=proj['Ngan_sach'] or 0.0, step=0.1, disabled=not can_edit_E)

            with etab2:
                col_e3, col_e4 = st.columns(2)
                with col_e3:
                    st.write("**Hồ sơ Thiết kế & Khảo sát:**")
                    e_kh_hstk = st.date_input("KH phát hành HSTKTC", value=datetime.datetime.strptime(proj['KH_phat_hanh_HSTKTC'], '%Y-%m-%d').date() if proj['KH_phat_hanh_HSTKTC'] else None, disabled=not can_edit_A)
                    e_tt_hstk = st.selectbox("TT HSTKTC", ["Chưa có TK", "Đang TK", "Điều chỉnh TK", "Đã phát hành", "Hoàn thiện"], index=["Chưa có TK", "Đang TK", "Điều chỉnh TK", "Đã phát hành", "Hoàn thiện"].index(proj['TT_HSTKTC'] or "Chưa có TK"), disabled=not can_edit_A)
                    e_tt_specs = st.selectbox("TT SPECS", ["Chưa có", "Đang lập", "Đã cấp"], index=["Chưa có", "Đang lập", "Đã cấp"].index(proj['TT_SPECS'] or "Chưa có"), disabled=not can_edit_A)
                    e_tt_boq = st.selectbox("TT BOQ/KL", ["Chưa bàn giao", "Đang lập", "Điều chỉnh", "Đã bàn giao"], index=["Chưa bàn giao", "Đang lập", "Điều chỉnh", "Đã bàn giao"].index(proj['TT_BOQ'] or "Chưa bàn giao"), disabled=not can_edit_A)
                with col_e4:
                    st.write("**Hợp đồng Cung ứng:**")
                    e_kh_lcnt = st.date_input("KH LCNT", value=datetime.datetime.strptime(proj['KH_LCNT'], '%Y-%m-%d').date() if proj['KH_LCNT'] else None, disabled=not can_edit_B)
                    e_tt_lcnt = st.selectbox("TT LCNT", ["Chưa LCNT", "Đang mời thầu", "Đang đánh giá", "Đã có KQ", "Đã ký"], index=["Chưa LCNT", "Đang mời thầu", "Đang đánh giá", "Đã có KQ", "Đã ký"].index(proj['TT_LCNT'] or "Chưa LCNT"), disabled=not can_edit_B)
                    e_kh_hdcu = st.date_input("KH Ký HĐCU", value=datetime.datetime.strptime(proj['KH_Ky_HDCU'], '%Y-%m-%d').date() if proj['KH_Ky_HDCU'] else None, disabled=not can_edit_B)
                    e_tt_hdcu = st.selectbox("TT Ký HĐCU", ["Chưa CU", "Đang trình ký", "Đã CU", "Theo đợt TC"], index=["Chưa CU", "Đang trình ký", "Đã CU", "Theo đợt TC"].index(proj['TT_Ky_HDCU'] or "Chưa CU"), disabled=not can_edit_B)
                    e_val_hdcu = st.number_input("Giá trị HĐ Cung ứng (tỷ)", min_value=0.0, value=proj['Gia_tri_HDCU'] or 0.0, step=0.1, disabled=not can_edit_E)

            with etab2_c:
                col_ec1, col_ec2 = st.columns(2)
                with col_ec1:
                    e_kh_ky_plhd = st.date_input("KH Ký PLHĐ CĐT", value=datetime.datetime.strptime(proj['KH_ky_PLHD'], '%Y-%m-%d').date() if proj['KH_ky_PLHD'] else None, disabled=not can_edit_A)
                    e_tt_ky_plhd = st.selectbox("TT Ký PLHĐ CĐT", ["Chưa ký", "Đang trình ký", "Đã ký PLHĐ"], index=["Chưa ký", "Đang trình ký", "Đã ký PLHĐ"].index(proj['TT_Ky_PLHD'] or "Chưa ký"), disabled=not can_edit_A)
                with col_ec2:
                    e_kh_pd_khtk = st.date_input("KH PD KHTK", value=datetime.datetime.strptime(proj['KH_PD_KHTK'], '%Y-%m-%d').date() if proj['KH_PD_KHTK'] else None, disabled=not can_edit_A)
                    e_tt_khtk = st.selectbox("TT KHTK (C)", ["Chưa trình", "Đang duyệt", "Đã duyệt"], index=["Chưa trình", "Đang duyệt", "Đã duyệt"].index(proj['TT_KHTK'] or "Chưa trình"), disabled=not can_edit_A)

            with etab3:
                col_e5, col_e6 = st.columns(2)
                with col_e5:
                    st.write("**Thời gian & Kế hoạch:**")
                    e_ngay_kc = st.date_input("Ngày Khởi công", value=datetime.datetime.strptime(proj['Ngay_BD_Khoi_Cong'], '%Y-%m-%d').date() if proj['Ngay_BD_Khoi_Cong'] else None, disabled=not can_edit_D)
                    e_tt_khtk = st.selectbox("TT KHTK", ["Chưa trình", "Đang duyệt", "Đã duyệt"], index=["Chưa trình", "Đang duyệt", "Đã duyệt"].index(proj['TT_KHTK'] or "Chưa trình"), disabled=not can_edit_D)
                    e_kh_thang_pct = st.number_input("Kế hoạch sản lượng tháng (%)", min_value=0.0, max_value=100.0, value=float((proj['KH_Thang'] or 0.0) * 100), disabled=not can_edit_G)
                    e_kh_thang = e_kh_thang_pct / 100.0
                    e_kq_thang_pct = st.number_input("Kết quả sản lượng thực tế (%)", min_value=0.0, max_value=100.0, value=float((proj['KQ_Thang'] or 0.0) * 100), disabled=not can_edit_G)
                    e_kq_thang = e_kq_thang_pct / 100.0
                with col_e6:
                    st.write("**Phân tích Tiến độ:**")
                    e_danh_gia = st.text_area("Đánh giá tiến độ & giải pháp hành động", value=proj['Danh_gia_Thang'] or "", disabled=not can_edit_G)
 
            has_edit_perm = can_edit_A or can_edit_B or can_edit_D or can_edit_E or can_edit_G
            if not has_edit_perm:
                st.warning("⚠️ Bạn không có quyền chỉnh sửa hạng mục này.")
            submitted_edit = st.form_submit_button("Lưu thay đổi", disabled=not has_edit_perm)
            if submitted_edit:
                if not has_edit_perm:
                    st.error("⚠️ Bạn không có quyền thực hiện hành động này.")
                conn = database.get_connection()
                cursor = conn.cursor()
                
                bd_str = e_ngay_bd.strftime('%Y-%m-%d') if e_ngay_bd else None
                kt_str = e_ngay_kt.strftime('%Y-%m-%d') if e_ngay_kt else None
                kh_hstk_str = e_kh_hstk.strftime('%Y-%m-%d') if e_kh_hstk else None
                kh_lcnt_str = e_kh_lcnt.strftime('%Y-%m-%d') if e_kh_lcnt else None
                kh_hdcu_str = e_kh_hdcu.strftime('%Y-%m-%d') if e_kh_hdcu else None
                kc_str = e_ngay_kc.strftime('%Y-%m-%d') if e_ngay_kc else None
                
                kh_ky_plhd_str = e_kh_ky_plhd.strftime('%Y-%m-%d') if e_kh_ky_plhd else None
                kh_pd_khtk_str = e_kh_pd_khtk.strftime('%Y-%m-%d') if e_kh_pd_khtk else None

                parent_code = None
                if e_tt and '.' in e_tt:
                    parent_code = e_tt[:e_tt.rfind('.')]
                cursor.execute("""
                    UPDATE packages
                    SET package_code = ?, parent_code = ?, bsc_code = ?, goi_thau_pl = ?, person_in_charge = ?, plan_start_date = ?, plan_end_date = ?, cdt_budget = ?,
                        kh_hstktc = ?, tt_hstktc = ?, tt_specs = ?, tt_boq = ?,
                        kh_lcnt = ?, tt_lcnt = ?, kh_hdcu = ?, tt_hdcu = ?, contract_value = ?,
                        kh_plhd = ?, tt_plhd = ?, kh_khtk = ?, tt_khtk = ?,
                        actual_start_date = ?, kh_thang = ?, kq_thang = ?, dg_thang = ?
                    WHERE id = ?
                """, (
                    e_tt, parent_code, e_ma_bsc, e_goi_thau, e_phu_trach, bd_str, kt_str, e_ngan_sach,
                    kh_hstk_str, e_tt_hstk, e_tt_specs, e_tt_boq,
                    kh_lcnt_str, e_tt_lcnt, kh_hdcu_str, e_tt_hdcu, e_val_hdcu,
                    kh_ky_plhd_str, e_tt_ky_plhd, kh_pd_khtk_str, e_tt_khtk,
                    kc_str, e_kh_thang, e_kq_thang, e_danh_gia, p_id
                ))
                
                conn.commit()
                database.log_action(curr_user.get('Ho_Ten', 'Ẩn danh'), "Cập nhật", "packages", p_id, f"Cập nhật chi tiết hạng mục '{proj['Hang_muc']}' (Mã BSC: {proj['Ma_BSC']})")
                conn.close()
                st.success("Đã lưu các thay đổi cho hạng mục thành công!")
                st.session_state['show_edit_form'] = False
                st.rerun()

# --- 3. SUB-TABLE 01: HỒ SƠ TIỀN KHỞI CÔNG ---
elif choice == "📂 01. Hồ sơ Tiền khởi công":
    st.write("## 📂 Sổ 01 - Hồ sơ Tiền khởi công")
    st.write("Quản lý danh sách các hồ sơ đầu vào bắt buộc duyệt trước khi Khởi công.")
    
    bsc_options = load_ma_bsc_options()
    
    with st.expander("➕ Thêm mới Hồ sơ"):
        with st.form("add_hso_form"):
            c1, c2 = st.columns(2)
            with c1:
                sel_bsc = st.selectbox("Dự án liên kết (Mã BSC)", [f"{opt['Ma_BSC']} - {opt['Hang_muc']}" for opt in bsc_options])
                h_loai = st.selectbox("Loại hồ sơ", ['HSTKTC', 'SPECS', 'BOQ/KL', 'KQ LCNT', 'HĐCU', 'PD KHCU', 'Ký PLHĐ', 'PD KHTK'])
                h_ten = st.text_input("Tên tài liệu / Số hiệu văn bản *")
                h_link = st.text_input("Đường dẫn lưu trữ (LINK)")
            with c2:
                h_ngay = st.date_input("Ngày ký / hoàn thành", value=datetime.date.today())
                pts = load_personnel_options()
                sel_lap = st.selectbox("Kỹ sư lập", pts + ["- Khác (Nhập mới) -"])
                if sel_lap == "- Khác (Nhập mới) -":
                    h_nguoi_lap = st.text_input("Nhập tên Kỹ sư lập mới *")
                else:
                    h_nguoi_lap = sel_lap
                
                sel_duyet = st.selectbox("Kỹ sư duyệt", pts + ["- Khác (Nhập mới) -"])
                if sel_duyet == "- Khác (Nhập mới) -":
                    h_nguoi_duyet = st.text_input("Nhập tên Kỹ sư duyệt mới *")
                else:
                    h_nguoi_duyet = sel_duyet
                h_tt = st.selectbox("Trạng thái duyệt", ['Chưa lập', 'Đang lập', 'Chờ duyệt', 'Đã duyệt', 'Từ chối'], index=3)
                
            has_add_perm = is_admin or (check_permission('Them_HD') and curr_user.get('Vai_Tro') in ('KTKH', 'QLTK'))
            if not has_add_perm:
                st.warning("⚠️ Bạn không có quyền thêm mới hồ sơ.")
            submitted_hso = st.form_submit_button("Lưu Hồ sơ", disabled=not has_add_perm)
            if submitted_hso:
                if not has_add_perm:
                    st.error("⚠️ Bạn không có quyền thực hiện hành động này.")
                elif not h_ten:
                    st.error("Vui lòng nhập Tên hồ sơ.")
                else:
                    ma_bsc_val = sel_bsc.split(" - ")[0]
                    pkg_id = get_package_id_by_bsc(ma_bsc_val)
                    ngay_str = h_ngay.strftime('%Y-%m-%d') if h_ngay else None
                    
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    if pkg_id:
                        cursor.execute("""
                            INSERT INTO pre_construction_docs (package_id, doc_type, doc_name, file_url, status, uploaded_at, created_by, approved_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (pkg_id, h_loai, h_ten, h_link, h_tt, ngay_str, h_nguoi_lap, h_nguoi_duyet))
                    conn.commit()
                    conn.close()
                    st.success("Thêm mới hồ sơ thành công!")
                    st.rerun()

    conn = database.get_connection()
    df_hso = pd.read_sql_query("""
        SELECT d.id, p.bsc_code AS Ma_BSC, p.package_name AS Hang_muc, d.doc_type AS Loai_ho_so,
               d.doc_name AS Ten_san_pham, d.file_url AS Link_luu_tru, d.uploaded_at AS Ngay_HT,
               d.created_by AS Nguoi_lap, d.approved_by AS Nguoi_duyet, d.status AS TT_duyet
        FROM pre_construction_docs d
        JOIN packages p ON d.package_id = p.id
    """, conn)
    conn.close()
    
    hso_column_config = {
        "id": None,
        "Ma_BSC": st.column_config.TextColumn("Mã BSC", width=120),
        "Hang_muc": st.column_config.TextColumn("Hạng mục", width=200),
        "Loai_ho_so": st.column_config.TextColumn("Loại hồ sơ", width=110),
        "Ten_san_pham": st.column_config.TextColumn("Tên hồ sơ / văn bản", width=300),
        "Link_luu_tru": st.column_config.LinkColumn("Link lưu trữ", width=180, display_text="Xem tài liệu 📄"),
        "Ngay_HT": st.column_config.DateColumn("Ngày hoàn thành", format="YYYY-MM-DD", width=130),
        "Nguoi_lap": st.column_config.TextColumn("Người lập", width=120),
        "Nguoi_duyet": st.column_config.TextColumn("Người duyệt", width=120),
        "TT_duyet": st.column_config.TextColumn("Trạng thái duyệt", width=130)
    }
    
    render_dataframe_html(df_hso, hso_column_config, "hso_tienkc")

# --- 4. SUB-TABLE 02: KẾ HOẠCH THÁNG/TUẦN ---
elif choice == "📅 02. Kế hoạch Tháng/Tuần":
    st.write("## 📅 Sổ 02 - Kế hoạch Triển khai Tháng/Tuần")
    st.write("Kiểm soát việc trình duyệt 5 tài liệu bắt buộc theo tuần/tháng.")
    
    bsc_options = load_ma_bsc_options()
    
    with st.expander("➕ Trình duyệt Kế hoạch Mới"):
        with st.form("add_kh_form"):
            c1, c2 = st.columns(2)
            with c1:
                sel_bsc = st.selectbox("Chọn dự án (Mã BSC)", [f"{opt['Ma_BSC']} - {opt['Hang_muc']}" for opt in bsc_options])
                kh_thang = st.text_input("Tháng kiểm soát (Ví dụ: 06/2026)", value="06/2026")
                kh_loai = st.selectbox("Loại tài liệu kế hoạch", ['Biện pháp thi công', 'Kế hoạch cung ứng', 'Biểu đồ nhân lực', 'Biểu đồ máy móc thiết bị', 'Biểu đồ cung ứng'])
                kh_nd = st.text_input("Nội dung đệ trình chính *")
                kh_yckt = st.selectbox("Đạt yêu cầu kỹ thuật CĐT?", ['Có', 'Chưa', 'Đang sửa đổi'], index=0)
            with c2:
                kh_link = st.text_input("LINK tài liệu đính kèm")
                kh_tt_lap = st.selectbox("Trạng thái lập", ['Chưa lập', 'Đang lập', 'Đã lập'], index=2)
                kh_tt_duyet = st.selectbox("Trạng thái duyệt", ['Chưa lập', 'Đang lập', 'Chờ duyệt', 'Đã duyệt', 'Từ chối'], index=3)
                contrs = load_contractor_options()
                sel_contr = st.selectbox("Nhà thầu lập", contrs + ["- Khác (Nhập mới) -"])
                if sel_contr == "- Khác (Nhập mới) -":
                    kh_nguoi_lap = st.text_input("Nhập tên Nhà thầu lập mới *")
                else:
                    kh_nguoi_lap = sel_contr
                
                pts = load_personnel_options()
                sel_duyet = st.selectbox("Cán bộ duyệt", pts + ["- Khác (Nhập mới) -"])
                if sel_duyet == "- Khác (Nhập mới) -":
                    kh_nguoi_duyet = st.text_input("Nhập tên Cán bộ duyệt mới *")
                else:
                    kh_nguoi_duyet = sel_duyet
                kh_ngay_duyet = st.date_input("Ngày phê duyệt", value=datetime.date.today())
                
            has_add_perm = is_admin or (check_permission('Them_HD') and curr_user.get('Vai_Tro') in ('KTKH', 'BQLDA'))
            if not has_add_perm:
                st.warning("⚠️ Bạn không có quyền thêm mới kế hoạch.")
            submitted_kh = st.form_submit_button("Lưu Kế hoạch", disabled=not has_add_perm)
            if submitted_kh:
                if not has_add_perm:
                    st.error("⚠️ Bạn không có quyền thực hiện hành động này.")
                elif not kh_nd:
                    st.error("Vui lòng điền Nội dung đệ trình chính.")
                else:
                    ma_bsc_val = sel_bsc.split(" - ")[0]
                    pkg_id = get_package_id_by_bsc(ma_bsc_val)
                    
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    if pkg_id:
                        cursor.execute("SELECT id, bptc_status, manpower_chart_status, machinery_chart_status, cashflow_plan_status, material_plan_status FROM monthly_weekly_plans WHERE package_id = ? AND plan_period = ?", (pkg_id, kh_thang))
                        plan_row = cursor.fetchone()
                        
                        col_map = {
                            'Biện pháp thi công': 'bptc_status',
                            'Biểu đồ nhân lực': 'manpower_chart_status',
                            'Biểu đồ máy móc thiết bị': 'machinery_chart_status',
                            'Biểu đồ cung ứng': 'cashflow_plan_status',
                            'Kế hoạch dòng tiền': 'cashflow_plan_status',
                            'Kế hoạch cung ứng': 'material_plan_status',
                            'Kế hoạch vật tư': 'material_plan_status'
                        }
                        db_col = col_map.get(kh_loai, 'bptc_status')
                        
                        if plan_row:
                            cursor.execute(f"UPDATE monthly_weekly_plans SET {db_col} = ? WHERE id = ?", (kh_tt_duyet, plan_row['id']))
                        else:
                            vals = {'bptc': 'Chưa lập', 'manpower': 'Chưa lập', 'machinery': 'Chưa lập', 'cashflow': 'Chưa lập', 'material': 'Chưa lập'}
                            if db_col == 'bptc_status': vals['bptc'] = kh_tt_duyet
                            elif db_col == 'manpower_chart_status': vals['manpower'] = kh_tt_duyet
                            elif db_col == 'machinery_chart_status': vals['machinery'] = kh_tt_duyet
                            elif db_col == 'cashflow_plan_status': vals['cashflow'] = kh_tt_duyet
                            elif db_col == 'material_plan_status': vals['material'] = kh_tt_duyet
                            
                            cursor.execute("""
                                INSERT INTO monthly_weekly_plans (package_id, plan_period, bptc_status, manpower_chart_status, machinery_chart_status, cashflow_plan_status, material_plan_status)
                                VALUES (?, ?, ?, ?, ?, ?, ?)
                            """, (pkg_id, kh_thang, vals['bptc'], vals['manpower'], vals['machinery'], vals['cashflow'], vals['material']))
                    conn.commit()
                    conn.close()
                    st.success("Trình kế hoạch thành công!")
                    st.rerun()

    conn = database.get_connection()
    raw_kh = pd.read_sql_query("""
        SELECT m.id, p.bsc_code AS Ma_BSC, p.package_name AS Hang_muc, m.plan_period AS Thang,
               m.bptc_status, m.manpower_chart_status, m.machinery_chart_status,
               m.cashflow_plan_status, m.material_plan_status
        FROM monthly_weekly_plans m
        JOIN packages p ON m.package_id = p.id
    """, conn)
    conn.close()
    
    kh_flat_list = []
    for idx, m in raw_kh.iterrows():
        doc_types = [
            ('Biện pháp thi công', m['bptc_status']),
            ('Biểu đồ nhân lực', m['manpower_chart_status']),
            ('Biểu đồ máy móc thiết bị', m['machinery_chart_status']),
            ('Biểu đồ cung ứng', m['cashflow_plan_status']),
            ('Kế hoạch vật tư', m['material_plan_status'])
        ]
        for doc_type, status in doc_types:
            kh_flat_list.append({
                'id': m['id'],
                'Ma_BSC': m['Ma_BSC'],
                'Hang_muc': m['Hang_muc'],
                'Thang': m['Thang'],
                'Loai_tai_lieu': doc_type,
                'Noi_dung_chinh': 'Báo cáo kế hoạch chi tiết',
                'Dat_YCKT_CDT': 'Có' if status == 'Đã duyệt' else 'Chưa',
                'Link_tai_lieu': None,
                'TT_lap': 'Đã lập' if status != 'Chưa lập' else 'Chưa lập',
                'TT_duyet': status,
                'Nguoi_lap': 'Tổng thầu',
                'Nguoi_duyet': 'CĐT',
                'Ngay_duyet': datetime.date(2026, 6, 24).strftime('%Y-%m-%d') if status == 'Đã duyệt' else None
            })
    df_kh = pd.DataFrame(kh_flat_list) if kh_flat_list else pd.DataFrame(columns=['id', 'Ma_BSC', 'Hang_muc', 'Thang', 'Loai_tai_lieu', 'Noi_dung_chinh', 'Dat_YCKT_CDT', 'Link_tai_lieu', 'TT_lap', 'TT_duyet', 'Nguoi_lap', 'Nguoi_duyet', 'Ngay_duyet'])
    
    kh_column_config = {
        "id": None,
        "Ma_BSC": st.column_config.TextColumn("Mã BSC", width=120),
        "Hang_muc": st.column_config.TextColumn("Hạng mục", width=200),
        "Thang": st.column_config.TextColumn("Tháng", width=90),
        "Loai_tai_lieu": st.column_config.TextColumn("Loại tài liệu", width=180),
        "Noi_dung_chinh": st.column_config.TextColumn("Nội dung chính", width=280),
        "Dat_YCKT_CDT": st.column_config.TextColumn("Đạt YCKT CĐT?", width=130),
        "Link_tai_lieu": st.column_config.LinkColumn("Link tài liệu", width=150, display_text="Xem kế hoạch 📄"),
        "TT_lap": st.column_config.TextColumn("TT Lập", width=100),
        "TT_duyet": st.column_config.TextColumn("TT Duyệt", width=110),
        "Nguoi_lap": st.column_config.TextColumn("Người lập", width=120),
        "Nguoi_duyet": st.column_config.TextColumn("Người duyệt", width=120),
        "Ngay_duyet": st.column_config.DateColumn("Ngày duyệt", format="YYYY-MM-DD", width=120)
    }
    
    render_dataframe_html(df_kh, kh_column_config, "kh_thang_tuan")

# --- 5. SUB-TABLE 03: QUẢN LÝ PHÁT SINH ---
elif choice == "⚠️ 03. Quản lý Phát sinh":
    st.title("⚠️ Sổ 03 - Phát sinh & Sai khác")
    
    bsc_options = load_ma_bsc_options()
    
    with st.expander("➕ Báo cáo Phát sinh"):
        with st.form("add_ps_form"):
            c1, c2 = st.columns(2)
            with c1:
                ps_ma = st.text_input("Mã Phát sinh (Ví dụ: PS.CT01.03) *")
                sel_bsc = st.selectbox("Mã BSC ảnh hưởng", [f"{opt['Ma_BSC']} - {opt['Hang_muc']}" for opt in bsc_options])
                ps_ngay = st.date_input("Ngày lập phiếu", value=datetime.date.today())
                ps_loai = st.selectbox("Phân loại phát sinh", ['Phát sinh khối lượng', 'Sai khác thiết kế', 'Biện pháp thi công phát sinh', 'Khác'])
                ps_mota = st.text_area("Chi tiết mô tả")
                ps_nguyennhan = st.text_area("Nguyên nhân cốt lõi")
            with c2:
                ps_dexuat = st.text_area("Đề xuất hướng xử lý")
                ps_giatri = st.number_input("Giá trị dự toán phát sinh (tỷ)", min_value=0.0, step=0.1)
                ps_tg = st.number_input("Thời gian chậm tiến độ dự kiến (ngày)", min_value=0, step=1)
                ps_link = st.text_input("LINK văn bản phát sinh")
                ps_tt = st.selectbox("Trạng thái duyệt", ['Chờ duyệt', 'Đã duyệt', 'Nháp'])
                pts = load_personnel_options()
                sel_duyet = st.selectbox("Cán bộ thẩm định/duyệt", pts + ["- Khác (Nhập mới) -"])
                if sel_duyet == "- Khác (Nhập mới) -":
                    ps_nguoi_duyet = st.text_input("Nhập tên Cán bộ duyệt mới *")
                else:
                    ps_nguoi_duyet = sel_duyet
                
            has_add_perm = is_admin or (check_permission('Them_HD') and curr_user.get('Vai_Tro') == 'BQLDA')
            if not has_add_perm:
                st.warning("⚠️ Bạn không có quyền báo cáo phát sinh.")
            submitted_ps = st.form_submit_button("Lưu Đệ trình", disabled=not has_add_perm)
            if submitted_ps:
                if not has_add_perm:
                    st.error("⚠️ Bạn không có quyền thực hiện hành động này.")
                elif not ps_ma:
                    st.error("Vui lòng nhập Mã phát sinh.")
                else:
                    ma_bsc_val = sel_bsc.split(" - ")[0]
                    pkg_id = get_package_id_by_bsc(ma_bsc_val)
                    ngay_str = ps_ngay.strftime('%Y-%m-%d') if ps_ngay else None
                    
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    if pkg_id:
                        cursor.execute("""
                            INSERT INTO cost_variations (package_id, variation_code, variation_date, variation_type, description, reason, proposal, variation_value, delay_days_impact, status, approved_by, approved_at, adjusted_content, note)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (pkg_id, ps_ma, ngay_str, ps_loai, ps_mota, ps_nguyennhan, ps_dexuat, ps_giatri, ps_tg, ps_tt, ps_nguoi_duyet, '', '', ''))
                    conn.commit()
                    conn.close()
                    st.success("Đệ trình thành công!")
                    st.rerun()

    conn = database.get_connection()
    df_ps = pd.read_sql_query("""
        SELECT v.id, v.variation_code AS Ma_PS, p.bsc_code AS Ma_BSC, p.package_name AS Hang_muc,
               v.variation_date AS Ngay_PS, v.variation_type AS Loai, v.description AS Mo_ta,
               v.reason AS Nguyen_nhan, v.proposal AS De_xuat_xu_ly, v.variation_value AS Gia_tri_phat_sinh,
               v.delay_days_impact AS Anh_huong_TD, v.status AS TT_Phe_duyet, v.approved_by AS Nguoi_duyet,
               v.approved_at AS Ngay_duyet, v.adjusted_content AS Noi_dung_dieu_chinh, v.note AS Ghi_chu,
               '' AS Link_ho_so
        FROM cost_variations v
        JOIN packages p ON v.package_id = p.id
    """, conn)
    conn.close()
    
    ps_column_config = {
        "id": None,
        "Ma_PS": st.column_config.TextColumn("Mã PS", width=110),
        "Ma_BSC": st.column_config.TextColumn("Mã BSC", width=120),
        "Hang_muc": st.column_config.TextColumn("Hạng mục", width=200),
        "Ngay_PS": st.column_config.DateColumn("Ngày PS", format="YYYY-MM-DD", width=110),
        "Loai": st.column_config.TextColumn("Phân loại", width=160),
        "Mo_ta": st.column_config.TextColumn("Mô tả chi tiết", width=250),
        "Nguyen_nhan": st.column_config.TextColumn("Nguyên nhân", width=200),
        "De_xuat_xu_ly": st.column_config.TextColumn("Đề xuất xử lý", width=200),
        "Gia_tri_phat_sinh": st.column_config.NumberColumn("Giá trị PS (tỷ)", format="%.2f tỷ", width=120),
        "Anh_huong_TD": st.column_config.NumberColumn("Ảnh hưởng TD (ngày)", format="%d ngày", width=140),
        "Link_ho_so": st.column_config.LinkColumn("Link hồ sơ", width=150, display_text="Xem hồ sơ phát sinh 📄"),
        "TT_Phe_duyet": st.column_config.TextColumn("TT Phê duyệt", width=125),
        "Nguoi_duyet": st.column_config.TextColumn("Người duyệt", width=120),
        "Ngay_duyet": st.column_config.DateColumn("Ngày duyệt", format="YYYY-MM-DD", width=110),
        "Noi_dung_dieu_chinh": st.column_config.TextColumn("Nội dung điều chỉnh", width=200),
        "Ghi_chu": st.column_config.TextColumn("Ghi chú", width=150)
    }
    
    render_dataframe_html(df_ps, ps_column_config, "phat_sinh")

# --- 6. SUB-TABLE 04: CUNG ỨNG ĐẶC THÙ ---
elif choice == "🚚 04. Cung ứng Đặc thù":
    st.title("🚚 Sổ 04 - Cung ứng Vật tư Đặc thù / Đột xuất")
    
    bsc_options = load_ma_bsc_options()
    
    with st.expander("➕ Yêu cầu Mua sắm Đặc thù"):
        with st.form("add_cu_form"):
            c1, c2 = st.columns(2)
            with c1:
                cu_ma = st.text_input("Mã yêu cầu (Ví dụ: YC.CT01.03) *")
                sel_bsc = st.selectbox("Mã BSC gói thầu", [f"{opt['Ma_BSC']} - {opt['Hang_muc']}" for opt in bsc_options])
                cu_ngay = st.date_input("Ngày đệ trình mua sắm", value=datetime.date.today())
                cu_loai = st.selectbox("Tính chất đệ trình", ['Đặc thù', 'Đột xuất', 'Thay thế vật liệu'])
                cu_vt = st.text_input("Tên vật tư / Thiết bị *")
                cu_lydo = st.text_area("Đặc tả yêu cầu & Lý do thay đổi")
            with c2:
                cu_kl = st.number_input("Khối lượng yêu cầu", min_value=0.0, step=1.0)
                dvts = load_dvt_options()
                sel_dvt = st.selectbox("Đơn vị tính (ĐVT)", dvts + ["- Khác (Nhập mới) -"], index=dvts.index("Bộ") if "Bộ" in dvts else 0)
                if sel_dvt == "- Khác (Nhập mới) -":
                    cu_dvt = st.text_input("Nhập đơn vị tính mới *")
                else:
                    cu_dvt = sel_dvt
                
                cu_gia = st.number_input("Giá trị dự toán (tỷ)", min_value=0.0, step=0.01)
                cu_trong_ngoai = st.selectbox("Trong/Ngoài phạm vi HĐCU", ['Trong HĐCU', 'Ngoài HĐCU'])
                cu_link = st.text_input("LINK tài liệu kỹ thuật")
                cu_tt = st.selectbox("Trạng thái duyệt đệ trình", ['Chờ duyệt', 'Đã duyệt'])
                
                pts = load_personnel_options()
                sel_duyet = st.selectbox("Người duyệt", pts + ["- Khác (Nhập mới) -"])
                if sel_duyet == "- Khác (Nhập mới) -":
                    cu_nguoi_duyet = st.text_input("Nhập tên Người duyệt mới *")
                else:
                    cu_nguoi_duyet = sel_duyet
                
            has_add_perm = is_admin or (check_permission('Them_HD') and curr_user.get('Vai_Tro') == 'KTKH')
            if not has_add_perm:
                st.warning("⚠️ Bạn không có quyền đệ trình yêu cầu cung ứng.")
            submitted_cu = st.form_submit_button("Lưu Yêu cầu", disabled=not has_add_perm)
            if submitted_cu:
                if not has_add_perm:
                    st.error("⚠️ Bạn không có quyền thực hiện hành động này.")
                elif not cu_ma or not cu_vt:
                    st.error("Vui lòng nhập đầy đủ Mã yêu cầu và Tên vật tư.")
                else:
                    ma_bsc_val = sel_bsc.split(" - ")[0]
                    pkg_id = get_package_id_by_bsc(ma_bsc_val)
                    ngay_str = cu_ngay.strftime('%Y-%m-%d') if cu_ngay else None
                    
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    if pkg_id:
                        cursor.execute("""
                            INSERT INTO special_procurements (package_id, req_code, request_date, req_type, material_name, quantity, unit, estimated_value, contract_scope, supply_status, file_url, status, approved_by)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (pkg_id, cu_ma, ngay_str, cu_loai, cu_vt, cu_kl, cu_dvt, cu_gia, cu_trong_ngoai, 'Chưa cung ứng', cu_link, cu_tt, cu_nguoi_duyet))
                    conn.commit()
                    conn.close()
                    st.success("Đã ghi nhận yêu cầu cung ứng vật tư!")
                    st.rerun()

    conn = database.get_connection()
    df_cu = pd.read_sql_query("""
        SELECT s.id, s.req_code AS Ma_YC, p.bsc_code AS Ma_BSC, p.package_name AS Hang_muc,
               s.request_date AS Ngay_YC, s.req_type AS Loai_YC, s.material_name AS Vat_tu_thiet_bi,
               s.note AS Noi_dung_yeu_cau, s.quantity AS KL, s.unit AS DVT, s.estimated_value AS Gia_tri_phat_sinh,
               s.contract_scope AS Trong_Ngoai_HDCU, s.file_url AS Link_ho_so, s.status AS TT_Phe_duyet,
               s.approved_by AS Nguoi_duyet, s.needed_date AS Ngay_can, s.supply_status AS TT_cung_ung,
               s.note AS Ghi_chu
        FROM special_procurements s
        JOIN packages p ON s.package_id = p.id
    """, conn)
    conn.close()
    
    cu_column_config = {
        "id": None,
        "Ma_YC": st.column_config.TextColumn("Mã YC", width=110),
        "Ma_BSC": st.column_config.TextColumn("Mã BSC", width=120),
        "Hang_muc": st.column_config.TextColumn("Hạng mục", width=200),
        "Ngay_YC": st.column_config.DateColumn("Ngày yêu cầu", format="YYYY-MM-DD", width=120),
        "Loai_YC": st.column_config.TextColumn("Tính chất", width=110),
        "Vat_tu_thiet_bi": st.column_config.TextColumn("Vật tư / Thiết bị", width=200),
        "Noi_dung_yeu_cau": st.column_config.TextColumn("Mô tả / Lý do", width=220),
        "KL": st.column_config.NumberColumn("Khối lượng", format="%.2f", width=110),
        "DVT": st.column_config.TextColumn("ĐVT", width=80),
        "Gia_tri_phat_sinh": st.column_config.NumberColumn("Giá trị (tỷ)", format="%.2f tỷ", width=110),
        "Trong_Ngoai_HDCU": st.column_config.TextColumn("Phạm vi HĐ", width=130),
        "Link_ho_so": st.column_config.LinkColumn("Link hồ sơ", width=140, display_text="Xem tài liệu kỹ thuật 📄"),
        "TT_Phe_duyet": st.column_config.TextColumn("TT Phê duyệt", width=120),
        "Nguoi_duyet": st.column_config.TextColumn("Người duyệt", width=120),
        "Ngay_can": st.column_config.DateColumn("Ngày cần vật tư", format="YYYY-MM-DD", width=120),
        "TT_cung_ung": st.column_config.TextColumn("TT Cung ứng", width=120),
        "Ghi_chu": st.column_config.TextColumn("Ghi chú", width=150)
    }
    
    render_dataframe_html(df_cu, cu_column_config, "cu_dac_thu")

# --- 7. SUB-TABLE 05: BÙ TIỀN ĐỘ ---
elif choice == "🚀 05. Bù Tiến độ":
    st.title("🚀 Sổ 05 - Phương án Bù Tiến độ")
    
    bsc_options = load_ma_bsc_options()
    
    with st.expander("➕ Thiết lập Phương án Bù Tiến độ"):
        with st.form("add_bu_form"):
            c1, c2 = st.columns(2)
            with c1:
                sel_bsc = st.selectbox("Chọn dự án bị chậm", [f"{opt['Ma_BSC']} - {opt['Hang_muc']}" for opt in bsc_options])
                bu_ngay = st.date_input("Ngày lập phương án", value=datetime.date.today())
                bu_cham = st.number_input("Số ngày bị trễ (ngày)", min_value=1.0, step=1.0)
                bu_nguyennhan = st.text_area("Nguyên nhân cốt lõi chậm trễ")
                bu_pa = st.text_input("Tên giải pháp bù nhanh *")
            with c2:
                bu_chitiet = st.text_area("Kế hoạch triển khai chi tiết")
                bu_moc = st.date_input("Hạn cuối cam kết bù xong")
                bu_link = st.text_input("LINK phương án được duyệt")
                bu_tt_duyet = st.selectbox("Tình trạng duyệt phương án", ['Chờ duyệt', 'Đã duyệt'])
                pts = load_personnel_options()
                sel_duyet = st.selectbox("Cán bộ duyệt", pts + ["- Khác (Nhập mới) -"])
                if sel_duyet == "- Khác (Nhập mới) -":
                    bu_nguoi = st.text_input("Nhập tên Cán bộ duyệt mới *")
                else:
                    bu_nguoi = sel_duyet
                bu_kq = st.text_input("Đánh giá kết quả thực hiện bù")
                bu_tt_trienkhai = st.selectbox("Trạng thái triển khai", ['Đang thực hiện', 'Đã hoàn thành', 'Đóng'])
                
            has_add_perm = is_admin or (check_permission('Them_HD') and curr_user.get('Vai_Tro') == 'BQLDA')
            if not has_add_perm:
                st.warning("⚠️ Bạn không có quyền thiết lập phương án bù tiến độ.")
            submitted_bu = st.form_submit_button("Lưu Phương án", disabled=not has_add_perm)
            if submitted_bu:
                if not has_add_perm:
                    st.error("⚠️ Bạn không có quyền thực hiện hành động này.")
                elif not bu_pa:
                    st.error("Vui lòng điền Tên giải pháp bù.")
                else:
                    ma_bsc_val = sel_bsc.split(" - ")[0]
                    pkg_id = get_package_id_by_bsc(ma_bsc_val)
                    ngay_str = bu_ngay.strftime('%Y-%m-%d') if bu_ngay else None
                    moc_str = bu_moc.strftime('%Y-%m-%d') if bu_moc else None
                    
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    if pkg_id:
                        cursor.execute("""
                            INSERT INTO delay_mitigations (package_id, delay_days, delay_reason, mitigation_plan, plan_detail, commit_date, status, approved_by, evaluation, mitigation_status, file_url, note)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (pkg_id, bu_cham, bu_nguyennhan, bu_pa, bu_chitiet, moc_str, bu_tt_duyet, bu_nguoi, bu_kq, bu_tt_trienkhai, bu_link, ''))
                    conn.commit()
                    conn.close()
                    st.success("Thiết lập phương án bù tiến độ thành công!")
                    st.rerun()

    conn = database.get_connection()
    df_bu = pd.read_sql_query("""
        SELECT d.id, p.bsc_code AS Ma_BSC, p.package_name AS Hang_muc, '' AS Ngay_phat_hien,
               d.delay_days AS Muc_cham_ngay, d.delay_reason AS Nguyen_nhan, d.mitigation_plan AS Phuong_an,
               d.plan_detail AS Chi_tiet_giai_phap, d.commit_date AS Moc_cam_ket_HT, d.file_url AS Link_phuong_an,
               d.status AS TT_duyet, d.approved_by AS Nguoi_duyet, d.evaluation AS KQ_thuc_hien_bu,
               d.mitigation_status AS TT_Trien_khai, d.note AS Ghi_chu
        FROM delay_mitigations d
        JOIN packages p ON d.package_id = p.id
    """, conn)
    conn.close()
    
    bu_column_config = {
        "id": None,
        "Ma_BSC": st.column_config.TextColumn("Mã BSC", width=120),
        "Hang_muc": st.column_config.TextColumn("Hạng mục", width=200),
        "Ngay_phat_hien": st.column_config.DateColumn("Ngày phát hiện chậm", format="YYYY-MM-DD", width=150),
        "Muc_cham_ngay": st.column_config.NumberColumn("Số ngày trễ", format="%d ngày trễ", width=120),
        "Nguyen_nhan": st.column_config.TextColumn("Nguyên nhân chậm trễ", width=220),
        "Phuong_an": st.column_config.TextColumn("Giải pháp bù", width=220),
        "Chi_tiet_giai_phap": st.column_config.TextColumn("Kế hoạch chi tiết", width=250),
        "Moc_cam_ket_HT": st.column_config.DateColumn("Hạn chót cam kết", format="YYYY-MM-DD", width=140),
        "Link_phuong_an": st.column_config.LinkColumn("Link phương án", width=140, display_text="Xem phương án bù 📄"),
        "TT_duyet": st.column_config.TextColumn("TT Duyệt", width=110),
        "Nguoi_duyet": st.column_config.TextColumn("Người duyệt", width=120),
        "KQ_thuc_hien_bu": st.column_config.TextColumn("Đánh giá kết quả bù", width=200),
        "TT_Trien_khai": st.column_config.TextColumn("TT Triển khai", width=130),
        "Ghi_chu": st.column_config.TextColumn("Ghi chú", width=150)
    }
    
    render_dataframe_html(df_bu, bu_column_config, "bu_tien_do")
# --- 8. AI ASSISTANT VIEW ---
elif choice == "🤖 Trợ lý AI Thông minh":
    st.title("🤖 Trợ lý AI Phân tích Báo cáo Xây dựng")
    
    st.info(
        "Nhập báo cáo tiến độ tuần bằng ngôn ngữ tự nhiên từ công trường. Trợ lý AI sẽ: \n"
        "1. Tự động đối chiếu Mã BSC và phân tích nội dung báo cáo.\n"
        "2. Tự động cập nhật tiến độ tuần tương ứng vào Bảng Master chính.\n"
        "3. Tự động chèn hồ sơ, kế hoạch, phát sinh, cung ứng đặc thù, hoặc phương án bù tiến độ vào các sổ 01 - 05 tương ứng."
    )
    
    raw_report = st.text_area(
        "📝 Nhập báo cáo thô của tuần:",
        height=150,
        placeholder="Ví dụ: Báo cáo hạng mục CT-01 Nhà mẫu tuần này đã đạt 22%, chậm 3% do mưa bão lớn kéo dài và nền đất bị sụt yếu. Công trường đang phải bố trí tăng ca đêm để lấy lại tiến độ."
    )
    
    if st.button("🚀 Phân tích & Đồng bộ vào Hệ thống", type="primary"):
        if not raw_report:
            st.warning("Vui lòng nhập báo cáo trước.")
        else:
            with st.spinner("AI đang giải trình và liên kết dữ liệu hệ thống..."):
                try:
                    projects = business_logic.get_all_projects_calculated()
                    parsed_json = ai_service.parse_raw_report(
                        raw_report, 
                        projects, 
                        st.session_state.get('gemini_api_key')
                    )
                    
                    st.success("🤖 Phân tích AI hoàn tất!")
                    st.json(parsed_json)
                    
                    actions = parsed_json.get("actions", [])
                    if not actions:
                        st.info("🤖 Không tìm thấy hành động đồng bộ dữ liệu nào phù hợp từ báo cáo thô.")
                    else:
                        conn = database.get_connection()
                        cursor = conn.cursor()
                        
                        for act in actions:
                            a_type = act.get("type")
                            ma_bsc_matched = act.get("ma_bsc")
                            
                            # Skip if Ma_BSC is not found
                            if ma_bsc_matched:
                                # Verify project exists
                                cursor.execute("SELECT package_name FROM packages WHERE bsc_code = ?", (ma_bsc_matched,))
                                res_p = cursor.fetchone()
                                if not res_p:
                                    st.warning(f"⚠️ Mã BSC '{ma_bsc_matched}' không tồn tại trong Bảng Tổng hợp Master. Bỏ qua hành động này.")
                                    continue
                                hang_muc_matched = res_p[0]
                                
                                if a_type == "update_master_progress":
                                    week_index = act.get("week_index")
                                    week_kq = act.get("week_kq")
                                    if week_index in [1, 2, 3, 4]:
                                        pkg_id = get_package_id_by_bsc(ma_bsc_matched)
                                        if pkg_id:
                                            cursor.execute("SELECT id FROM progress_tracking WHERE package_id = ? AND report_week = ?", (pkg_id, week_index))
                                            pt_row = cursor.fetchone()
                                            if pt_row:
                                                cursor.execute("""
                                                    UPDATE progress_tracking 
                                                    SET actual_progress = ?, variance = actual_progress - planned_progress 
                                                    WHERE id = ?
                                                """, (week_kq, pt_row[0]))
                                            else:
                                                cursor.execute("""
                                                    INSERT INTO progress_tracking (package_id, report_week, planned_progress, actual_progress, variance)
                                                    VALUES (?, ?, 0.0, ?, ?)
                                                """, (pkg_id, week_index, week_kq, week_kq))
                                        st.write(f"✅ Đã tự động cập nhật tiến độ Tuần {week_index} của dự án '{hang_muc_matched}' ({ma_bsc_matched}) đạt {week_kq*100:.1f}%.")
                                
                                elif a_type == "insert_hso_tienkc":
                                    pkg_id = get_package_id_by_bsc(ma_bsc_matched)
                                    if pkg_id:
                                        cursor.execute("""
                                            INSERT INTO pre_construction_docs (package_id, doc_type, doc_name, file_url, status, uploaded_at, created_by, approved_by)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (
                                            pkg_id,
                                            act.get("loai_ho_so", "HSTKTC"),
                                            act.get("ten_san_pham", "Tài liệu tự động từ AI"),
                                            act.get("link_luu_tru"),
                                            act.get("tt_duyet", "Đã duyệt"),
                                            datetime.date.today().strftime('%Y-%m-%d'),
                                            act.get("nguoi_lap", "AI Assistant"),
                                            act.get("nguoi_duyet")
                                        ))
                                    st.write(f"✅ Đã tự động thêm Hồ sơ mới: '{act.get('ten_san_pham')}' cho dự án '{hang_muc_matched}'.")
                                
                                elif a_type == "insert_kh_thang_tuan":
                                    pkg_id = get_package_id_by_bsc(ma_bsc_matched)
                                    if pkg_id:
                                        kh_loai_doc = act.get("loai_tai_lieu", "Biện pháp thi công")
                                        kh_tt_status = act.get("tt_duyet", "Đã duyệt")
                                        kh_thang_p = act.get("thang", "06/2026")
                                        
                                        cursor.execute("SELECT id, bptc_status, manpower_chart_status, machinery_chart_status, cashflow_plan_status, material_plan_status FROM monthly_weekly_plans WHERE package_id = ? AND plan_period = ?", (pkg_id, kh_thang_p))
                                        plan_row = cursor.fetchone()
                                        
                                        col_map = {
                                            'Biện pháp thi công': 'bptc_status',
                                            'Biểu đồ nhân lực': 'manpower_chart_status',
                                            'Biểu đồ máy móc thiết bị': 'machinery_chart_status',
                                            'Biểu đồ cung ứng': 'cashflow_plan_status',
                                            'Kế hoạch dòng tiền': 'cashflow_plan_status',
                                            'Kế hoạch cung ứng': 'material_plan_status',
                                            'Kế hoạch vật tư': 'material_plan_status'
                                        }
                                        db_col = col_map.get(kh_loai_doc, 'bptc_status')
                                        
                                        if plan_row:
                                            cursor.execute(f"UPDATE monthly_weekly_plans SET {db_col} = ? WHERE id = ?", (kh_tt_status, plan_row['id']))
                                        else:
                                            vals = {'bptc': 'Chưa lập', 'manpower': 'Chưa lập', 'machinery': 'Chưa lập', 'cashflow': 'Chưa lập', 'material': 'Chưa lập'}
                                            if db_col == 'bptc_status': vals['bptc'] = kh_tt_status
                                            elif db_col == 'manpower_chart_status': vals['manpower'] = kh_tt_status
                                            elif db_col == 'machinery_chart_status': vals['machinery'] = kh_tt_status
                                            elif db_col == 'cashflow_plan_status': vals['cashflow'] = kh_tt_status
                                            elif db_col == 'material_plan_status': vals['material'] = kh_tt_status
                                            
                                            cursor.execute("""
                                                INSERT INTO monthly_weekly_plans (package_id, plan_period, bptc_status, manpower_chart_status, machinery_chart_status, cashflow_plan_status, material_plan_status)
                                                VALUES (?, ?, ?, ?, ?, ?, ?)
                                            """, (pkg_id, kh_thang_p, vals['bptc'], vals['manpower'], vals['machinery'], vals['cashflow'], vals['material']))
                                    st.write(f"✅ Đã tự động lập Kế hoạch đệ trình: '{act.get('noi_dung_chinh')}' cho dự án '{hang_muc_matched}'.")
                                
                                elif a_type == "insert_phat_sinh":
                                    pkg_id = get_package_id_by_bsc(ma_bsc_matched)
                                    if pkg_id:
                                        cursor.execute("""
                                            INSERT INTO cost_variations (package_id, variation_code, variation_date, variation_type, description, reason, proposal, variation_value, delay_days_impact, status, approved_by)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (
                                            pkg_id,
                                            act.get("ma_ps", f"PS.AI.{datetime.date.today().strftime('%m%d%H%M')}"),
                                            datetime.date.today().strftime('%Y-%m-%d'),
                                            act.get("loai", "Khác"),
                                            act.get("mo_ta", "Tự động từ AI"),
                                            act.get("nguyen_nhan"),
                                            act.get("de_xuat_xu_ly"),
                                            act.get("gia_tri_phat_sinh", 0.0),
                                            act.get("anh_huong_td", 0.0),
                                            act.get("tt_phe_duyet", "Chờ duyệt"),
                                            act.get("nguoi_duyet")
                                        ))
                                    st.write(f"✅ Đã tự động báo cáo Phát sinh: '{act.get('ma_ps')}' trị giá {act.get('gia_tri_phat_sinh', 0.0)} tỷ cho dự án '{hang_muc_matched}'.")
                                
                                elif a_type == "insert_cu_dac_thu":
                                    pkg_id = get_package_id_by_bsc(ma_bsc_matched)
                                    if pkg_id:
                                        cursor.execute("""
                                            INSERT INTO special_procurements (package_id, req_code, request_date, req_type, material_name, quantity, unit, estimated_value, contract_scope, file_url, status, approved_by)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (
                                            pkg_id,
                                            act.get("ma_yc", f"YC.AI.{datetime.date.today().strftime('%m%d%H%M')}"),
                                            datetime.date.today().strftime('%Y-%m-%d'),
                                            act.get("loai_yc", "Đột xuất"),
                                            act.get("vat_tu_thiet_bi", "Vật tư"),
                                            act.get("kl", 1.0),
                                            act.get("dvt", "Bộ"),
                                            act.get("gia_tri_phat_sinh", 0.0),
                                            act.get("trong_ngoai_hdcu", "Ngoài HĐCU"),
                                            act.get("link_ho_so"),
                                            act.get("tt_phe_duyet", "Chờ duyệt"),
                                            act.get("nguoi_duyet")
                                        ))
                                    st.write(f"✅ Đã tự động lập yêu cầu Cung ứng đặc thù: '{act.get('vat_tu_thiet_bi')}' cho dự án '{hang_muc_matched}'.")
                                
                                elif a_type == "insert_bu_tien_do":
                                    pkg_id = get_package_id_by_bsc(ma_bsc_matched)
                                    if pkg_id:
                                        cursor.execute("""
                                            INSERT INTO delay_mitigations (package_id, delay_days, delay_reason, mitigation_plan, plan_detail, commit_date, status, approved_by, evaluation, mitigation_status, file_url)
                                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                        """, (
                                            pkg_id,
                                            act.get("muc_cham_ngay", 5.0),
                                            act.get("nguyen_nhan", "AI Phát hiện chậm trễ"),
                                            act.get("phuong_an", "Giải pháp bù tiến độ"),
                                            act.get("chi_tiet_giai_phap"),
                                            act.get("moc_cam_ket_ht") or datetime.date.today().strftime('%Y-%m-%d'),
                                            act.get("tt_duyet", "Chờ duyệt"),
                                            act.get("nguoi_duyet"),
                                            act.get("kq_thuc_hien_bu"),
                                            act.get("tt_trien_khai", "Đang thực hiện"),
                                            act.get("link_phuong_an")
                                        ))
                                    st.write(f"✅ Đã tự động thiết lập Phương án bù tiến độ (Sổ 05) cho dự án '{hang_muc_matched}' ở trạng thái '{act.get('tt_trien_khai', 'Đang thực hiện')}'.")
                        
                        conn.commit()
                        conn.close()
                        st.success("🎉 Hệ thống đã được đồng bộ dữ liệu tự động thành công!")
                except Exception as ex:
                    st.error(f"Lỗi: {ex}")

# --- 9. PERSONNEL & PERMISSIONS MANAGEMENT ---
elif choice == "👥 Quản lý Nhân sự":
    if not is_admin:
        st.error("⚠️ Bạn không có quyền truy cập chức năng này.")
        st.stop()
    st.write("## 👥 Quản lý Danh sách Nhân sự & Phân quyền")
    
    conn = database.get_connection()
    df_ns = pd.read_sql_query("SELECT id, Ma_NV, Ho_Ten, Chuc_Vu, Vai_Tro, Email, Xem, Them_HD, Sua, Xoa_HD, Sua_CDT_BD, Cap_Nhat_CDT FROM nhan_su", conn)
    conn.close()
    
    # 1. Filter dropdown matching your screen
    positions = sorted(list(set(df_ns['Chuc_Vu'].dropna().tolist())))
    filter_options = ["Tất cả Nhân sự"] + positions
    
    c_f1, c_f2 = st.columns([8, 2])
    with c_f1:
        sel_filter = st.selectbox("Lọc theo loại:", filter_options, key="sel_filter_personnel")
    
    if sel_filter != "Tất cả Nhân sự":
        df_ns = df_ns[df_ns['Chuc_Vu'] == sel_filter]
        
    # Render personnel table
    def render_personnel_html(df):
        html = []
        css = """
        <style>
            .ns-container {
                width: 100%;
                overflow-x: auto;
                border-radius: 12px;
                box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -4px rgba(0, 0, 0, 0.05);
                border: 1px solid #cbd5e1;
                margin-bottom: 2rem;
                background: white;
            }
            .ns-table {
                width: 100%;
                border-collapse: collapse;
                font-family: 'Outfit', 'Inter', sans-serif;
                font-size: 0.775rem;
                color: #1e293b;
                table-layout: fixed;
            }
            .ns-table th {
                background-color: #1e293b !important;
                color: #ffffff !important;
                font-weight: 700;
                text-align: center;
                padding: 10px 8px;
                position: sticky;
                top: 0;
                z-index: 10;
                border: 1px solid #334155;
                font-size: 0.75rem;
                text-transform: uppercase;
                letter-spacing: 0.03em;
                word-wrap: break-word;
                white-space: normal;
                line-height: 1.3;
            }
            .ns-table td {
                padding: 10px 12px;
                border: 1px solid #cbd5e1;
                vertical-align: middle;
                word-wrap: break-word;
                white-space: normal;
                line-height: 1.4;
                color: #334155;
            }
            .ns-table tr:hover {
                background-color: #f1f5f9 !important;
            }
            .ns-badge-co {
                color: #166534;
                font-weight: 700;
                display: inline-flex;
                align-items: center;
                gap: 4px;
                background-color: #dcfce7;
                border: 1px solid #bbf7d0;
                padding: 4px 8px;
                border-radius: 12px;
            }
            .ns-badge-khong {
                color: #991b1b;
                font-weight: 700;
                display: inline-flex;
                align-items: center;
                gap: 4px;
                background-color: #fee2e2;
                border: 1px solid #fca5a5;
                padding: 4px 8px;
                border-radius: 12px;
            }
            .ns-btn-sua {
                background-color: #fef9c3;
                color: #854d0e;
                border: 1px solid #fef08a;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 0.725rem;
                font-weight: 700;
                display: inline-block;
                cursor: pointer;
            }
            .ns-btn-xoa {
                background-color: #fee2e2;
                color: #b91c1c;
                border: 1px solid #fca5a5;
                padding: 4px 8px;
                border-radius: 6px;
                font-size: 0.725rem;
                font-weight: 700;
                display: inline-block;
                cursor: pointer;
            }
        </style>
        """
        html.append(css)
        html.append('<div class="ns-container">')
        html.append('<table class="ns-table">')
        
        # Colgroup for widths
        html.append('<colgroup>')
        widths = ["6%", "14%", "10%", "8%", "18%", "8%", "7%", "8%", "8%", "8%", "11%"]
        for w in widths:
            html.append(f'<col style="width: {w};">')
        html.append('</colgroup>')
        
        # Headers
        html.append('<thead><tr>')
        headers = ["Mã NV", "Họ & Tên", "Chức vụ", "Vai trò", "Email", "Xem", "Thêm mới", "Sửa", "Xóa", "Thao tác"]
        for h in headers:
            html.append(f'<th>{h}</th>')
        html.append('</tr></thead>')
        
        # Body
        html.append('<tbody>')
        for idx, row in df.iterrows():
            html.append('<tr>')
            html.append(f'<td style="color: #6366f1; font-weight: 700;">{row["Ma_NV"]}</td>')
            html.append(f'<td><b>{row["Ho_Ten"]}</b></td>')
            html.append(f'<td style="color: #64748b;">{row["Chuc_Vu"]}</td>')
            html.append(f'<td style="color: #64748b;">{row["Vai_Tro"]}</td>')
            html.append(f'<td style="color: #64748b; font-size: 0.75rem;">{row["Email"]}</td>')
            
            # Permissions
            perm_cols = ["Xem", "Them_HD", "Sua", "Xoa_HD"]
            for col in perm_cols:
                if row[col] == 1:
                    html.append('<td><span class="ns-badge-co">🟢 Có</span></td>')
                else:
                    html.append('<td><span class="ns-badge-khong">🔴 Không</span></td>')
                    
            # Actions
            html.append(f'<td><span class="ns-btn-sua">Sửa</span> <span class="ns-btn-xoa">Xóa</span></td>')
            html.append('</tr>')
            
        html.append('</tbody>')
        html.append('</table>')
        html.append('</div>')
        
        return "".join(html)

    # Render HTML Personnel table
    st.markdown(render_personnel_html(df_ns), unsafe_allow_html=True)
    
    st.write("---")
    st.write("⚙️ *Hành động nhanh cho Danh sách Nhân sự:*")
    
    # 2. Add New Personnel
    with st.expander("➕ Thêm Nhân viên mới"):
        with st.form("add_ns_form"):
            c1, c2 = st.columns(2)
            with c1:
                add_ma = st.text_input("Mã Nhân viên (Mã NV) *")
                add_ten = st.text_input("Họ & Tên *")
                add_chuc = st.text_input("Chức vụ")
                add_vai = st.text_input("Vai trò")
                add_email = st.text_input("Email")
            with c2:
                st.write("**Phân quyền chức năng:**")
                add_xem = st.checkbox("Xem", value=True)
                add_them = st.checkbox("Thêm mới", value=False)
                add_sua = st.checkbox("Sửa", value=False)
                add_xoa = st.checkbox("Xóa", value=False)
                
            has_add_perm = check_permission('Them_HD')
            if not has_add_perm:
                st.warning("⚠️ Bạn không có quyền thêm mới nhân sự.")
            btn_add_ns = st.form_submit_button("Lưu nhân sự", disabled=not has_add_perm)
            if btn_add_ns:
                if not has_add_perm:
                    st.error("⚠️ Bạn không có quyền thực hiện hành động này.")
                elif not add_ma or not add_ten:
                    st.error("Vui lòng nhập Mã NV và Họ & Tên.")
                else:
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO nhan_su (Ma_NV, Ho_Ten, Chuc_Vu, Vai_Tro, Email, Xem, Them_HD, Sua, Xoa_HD, Sua_CDT_BD, Cap_Nhat_CDT)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 0)
                    """, (add_ma, add_ten, add_chuc, add_vai, add_email,
                          1 if add_xem else 0, 1 if add_them else 0, 1 if add_sua else 0, 1 if add_xoa else 0))
                    conn.commit()
                    database.log_action(curr_user.get('Ho_Ten', 'Ẩn danh'), "Thêm mới", "nhan_su", add_ma, f"Thêm nhân sự '{add_ten}' (Mã NV: {add_ma}, Chức vụ: {add_chuc})")
                    conn.close()
                    st.success("Thêm nhân sự mới thành công!")
                    st.rerun()
    # 3. Edit Personnel
    with st.expander("✏️ Chỉnh sửa thông tin & Phân quyền"):
        ns_list = [f"{row['id']} - {row['Ho_Ten']} (Mã NV: {row['Ma_NV']})" for idx, row in df_ns.iterrows()]
        if ns_list:
            sel_ns = st.selectbox("Chọn nhân viên cần chỉnh sửa:", ns_list, key="sel_edit_ns")
            sel_id = int(sel_ns.split(" - ")[0])
            
            # Fetch employee current info
            conn = database.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM nhan_su WHERE id = ?", (sel_id,))
            row_edit = cursor.fetchone()
            conn.close()
            
            if row_edit:
                with st.form("edit_ns_form"):
                    ec1, ec2 = st.columns(2)
                    with ec1:
                        edit_ma = st.text_input("Mã Nhân viên *", value=row_edit['Ma_NV'] or "")
                        edit_ten = st.text_input("Họ & Tên *", value=row_edit['Ho_Ten'] or "")
                        edit_chuc = st.text_input("Chức vụ", value=row_edit['Chuc_Vu'] or "")
                        edit_vai = st.text_input("Vai trò", value=row_edit['Vai_Tro'] or "")
                        edit_email = st.text_input("Email", value=row_edit['Email'] or "")
                    with ec2:
                        st.write("**Chỉnh sửa quyền:**")
                        edit_xem = st.checkbox("Xem", value=(row_edit['Xem'] == 1))
                        edit_them = st.checkbox("Thêm mới", value=(row_edit['Them_HD'] == 1))
                        edit_sua = st.checkbox("Sửa", value=(row_edit['Sua'] == 1))
                        edit_xoa = st.checkbox("Xóa", value=(row_edit['Xoa_HD'] == 1))
                        
                    has_edit_perm = check_permission('Sua')
                    if not has_edit_perm:
                        st.warning("⚠️ Bạn không có quyền chỉnh sửa thông tin nhân sự.")
                    btn_edit_ns = st.form_submit_button("Lưu thay đổi", disabled=not has_edit_perm)
                    if btn_edit_ns:
                        if not has_edit_perm:
                            st.error("⚠️ Bạn không có quyền thực hiện hành động này.")
                        elif not edit_ma or not edit_ten:
                            st.error("Mã NV và Họ & Tên không được bỏ trống.")
                        else:
                            conn = database.get_connection()
                            cursor = conn.cursor()
                            cursor.execute("""
                                UPDATE nhan_su
                                SET Ma_NV = ?, Ho_Ten = ?, Chuc_Vu = ?, Vai_Tro = ?, Email = ?,
                                    Xem = ?, Them_HD = ?, Sua = ?, Xoa_HD = ?, Sua_CDT_BD = 0, Cap_Nhat_CDT = 0
                                WHERE id = ?
                            """, (edit_ma, edit_ten, edit_chuc, edit_vai, edit_email,
                                  1 if edit_xem else 0, 1 if edit_them else 0, 1 if edit_sua else 0, 1 if edit_xoa else 0, sel_id))
                            conn.commit()
                            database.log_action(curr_user.get('Ho_Ten', 'Ẩn danh'), "Cập nhật", "nhan_su", sel_id, f"Cập nhật thông tin & quyền nhân sự '{edit_ten}' (Mã NV: {edit_ma})")
                            conn.close()
                            st.success("Cập nhật thông tin nhân viên thành công!")
                            st.rerun()
                            
    # 4. Delete Personnel
    with st.expander("🗑️ Xóa nhân viên"):
        ns_list_del = [f"{row['id']} - {row['Ho_Ten']} (Mã NV: {row['Ma_NV']})" for idx, row in df_ns.iterrows()]
        if ns_list_del:
            sel_ns_del = st.selectbox("Chọn nhân viên cần xóa:", ns_list_del, key="sel_del_ns")
            sel_id_del = int(sel_ns_del.split(" - ")[0])
            
            has_delete_perm = check_permission('Xoa_HD')
            if not has_delete_perm:
                st.warning("⚠️ Bạn không có quyền xóa nhân sự.")
            if st.button("❌ Xác nhận xóa vĩnh viễn", key="btn_confirm_del_ns", type="primary", disabled=not has_delete_perm):
                if not has_delete_perm:
                    st.error("⚠️ Bạn không có quyền thực hiện hành động này.")
                else:
                    conn = database.get_connection()
                    cursor = conn.cursor()
                    cursor.execute("DELETE FROM nhan_su WHERE id = ?", (sel_id_del,))
                    conn.commit()
                    deleted_name = sel_ns_del.split(" - ")[1].split(" (")[0] if " - " in sel_ns_del else sel_ns_del
                    database.log_action(curr_user.get('Ho_Ten', 'Ẩn danh'), "Xóa", "nhan_su", sel_id_del, f"Xóa nhân sự '{deleted_name}' (ID: {sel_id_del})")
                    conn.close()
                    st.success("Đã xóa nhân viên thành công!")
                    st.rerun()

    # 5. Activity Audit Log
    with st.expander("📜 Nhật ký Hoạt động & Lịch sử thay đổi (Audit Log)"):
        conn = database.get_connection()
        df_logs = pd.read_sql_query("SELECT timestamp AS 'Thời gian', username AS 'Người thực hiện', action_type AS 'Hành động', details AS 'Chi tiết thay đổi' FROM audit_log ORDER BY id DESC LIMIT 200", conn)
        conn.close()
        
        if df_logs.empty:
            st.info("Chưa có nhật ký hoạt động nào được ghi nhận.")
        else:
            st.dataframe(df_logs, use_container_width=True, hide_index=True)
