import sqlite3
import pandas as pd
import datetime
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, 'project_control.db'))
EXCEL_PATH = os.path.normpath(os.path.join(BASE_DIR, 'TDG_Masterfile BQLDA_v1_20260623.xlsx'))

def clean_date(val):
    if pd.isna(val) or val is None:
        return None
    if isinstance(val, (pd.Timestamp, datetime.datetime)):
        return val.strftime('%Y-%m-%d')
    val_str = str(val).strip()
    if not val_str or val_str.lower() in ('none', 'nat', 'null'):
        return None
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y-%m-%d %H:%M:%S'):
        try:
            return datetime.datetime.strptime(val_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return val_str

def clean_float(val):
    if pd.isna(val) or val is None:
        return None
    try:
        return float(val)
    except ValueError:
        return None

def clean_str(val):
    if pd.isna(val) or val is None:
        return None
    val_str = str(val).strip()
    if not val_str or val_str.lower() == 'nan':
        return None
    return val_str

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")  # Kích hoạt khóa ngoại SQLite cứng
    conn.row_factory = sqlite3.Row
    return conn

def check_and_add_columns(cursor):
    # Đảm bảo bảng nhan_su và audit_log có đầy đủ các cột (Self-Healing)
    expected_schemas = {
        "nhan_su": {
            "Ma_NV": "TEXT",
            "Ho_Ten": "TEXT",
            "Chuc_Vu": "TEXT",
            "Vai_Tro": "TEXT",
            "Email": "TEXT",
            "Xem": "INTEGER DEFAULT 1",
            "Them_HD": "INTEGER",
            "Sua": "INTEGER",
            "Xoa_HD": "INTEGER",
            "Sua_CDT_BD": "INTEGER",
            "Cap_Nhat_CDT": "INTEGER"
        },
        "audit_log": {
            "timestamp": "TEXT",
            "username": "TEXT",
            "action_type": "TEXT",
            "table_name": "TEXT",
            "record_id": "TEXT",
            "details": "TEXT"
        }
    }
    for table_name, cols in expected_schemas.items():
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        if not cursor.fetchone():
            continue
        cursor.execute(f"PRAGMA table_info({table_name})")
        existing_cols = [row[1] for row in cursor.fetchall()]
        for col_name, col_type in cols.items():
            if col_name not in existing_cols:
                try:
                    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}")
                    print(f"Auto-migration: Added column '{col_name}' to table '{table_name}'")
                except Exception as e:
                    print(f"Error migrating column {col_name} in {table_name}: {e}")

def init_db(force_reseed=False):
    try:
        import gdrive_sync
        if gdrive_sync.download_from_gdrive(DB_PATH, "project_control.db"):
            print("Successfully downloaded latest database from Google Drive!")
            gdrive_sync.download_from_gdrive(EXCEL_PATH, "TDG_Masterfile BQLDA_v1_20260623.xlsx")
    except Exception as e:
        print(f"Google Drive startup download skipped/failed: {e}")

    conn = get_connection()
    cursor = conn.cursor()

    if force_reseed:
        # Tạm tắt khóa ngoại để drop các bảng cũ an toàn
        conn.execute("PRAGMA foreign_keys = OFF;")
        cursor.execute("DROP TABLE IF EXISTS progress_tracking")
        cursor.execute("DROP TABLE IF EXISTS pre_construction_docs")
        cursor.execute("DROP TABLE IF EXISTS monthly_weekly_plans")
        cursor.execute("DROP TABLE IF EXISTS cost_variations")
        cursor.execute("DROP TABLE IF EXISTS special_procurements")
        cursor.execute("DROP TABLE IF EXISTS delay_mitigations")
        cursor.execute("DROP TABLE IF EXISTS packages")
        cursor.execute("DROP TABLE IF EXISTS master_bang_tonghop")
        cursor.execute("DROP TABLE IF EXISTS hso_tienkc")
        cursor.execute("DROP TABLE IF EXISTS kh_thang_tuan")
        cursor.execute("DROP TABLE IF EXISTS phat_sinh")
        cursor.execute("DROP TABLE IF EXISTS cu_dac_thu")
        cursor.execute("DROP TABLE IF EXISTS bu_tien_do")
        conn.execute("PRAGMA foreign_keys = ON;")

    # 1. Bảng danh mục gói thầu packages (Master)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS packages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        package_code TEXT UNIQUE NOT NULL,      -- TT (e.g. '1', '2', '2.2', '2.2.1')
        parent_code TEXT,                       -- parent TT (phục vụ WBS Tree)
        bsc_code TEXT,                          -- Ma_BSC
        goi_thau_pl TEXT,                       -- Gói thầu (PL) (e.g. 'PL10', 'PL17')
        package_name TEXT NOT NULL,             -- Hang_muc
        project_group TEXT,                     -- Nhom_CT
        person_in_charge TEXT,                  -- Phu_trach
        plan_start_date TEXT,                   -- Ngay_BD_YC
        plan_end_date TEXT,                     -- Ngay_KT_YC
        cdt_budget REAL DEFAULT 0.00,           -- Ngan_sach
        contract_value REAL DEFAULT 0.00,       -- Gia_tri_HDCU
        status TEXT DEFAULT 'Chờ khởi công',
        actual_start_date TEXT,                 -- Ngay_BD_Khoi_Cong
        kh_hstktc TEXT,
        tt_hstktc TEXT,
        tt_specs TEXT,
        tt_boq TEXT,
        kh_lcnt TEXT,
        tt_lcnt TEXT,
        kh_hdcu TEXT,
        tt_hdcu TEXT,
        kh_khcu TEXT,
        tt_khcu TEXT,
        kh_plhd TEXT,
        tt_plhd TEXT,
        kh_khtk TEXT,
        tt_khtk TEXT,
        qa_kh_thang REAL,
        qa_kq_thang REAL,
        qa_dg_thang TEXT,
        kh_thang REAL,
        kq_thang REAL,
        dg_thang TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (parent_code) REFERENCES packages(package_code) ON DELETE SET NULL
    )
    """)

    # 2. Bảng Hồ sơ Tiền khởi công pre_construction_docs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS pre_construction_docs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        package_id INTEGER NOT NULL,
        doc_type TEXT NOT NULL,                 -- Loai_ho_so
        doc_name TEXT,                          -- Ten_san_pham
        file_url TEXT,                          -- Link_luu_tru
        status TEXT DEFAULT 'Chưa duyệt',       -- TT_duyet
        uploaded_at TEXT,                       -- Ngay_HT
        approved_at TEXT,
        created_by TEXT,                        -- Nguoi_lap
        approved_by TEXT,                       -- Nguoi_duyet
        FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE
    )
    """)

    # 3. Bảng Kế hoạch tháng/tuần monthly_weekly_plans
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS monthly_weekly_plans (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        package_id INTEGER NOT NULL,
        plan_period TEXT NOT NULL,              -- Thang
        bptc_status TEXT DEFAULT 'Chưa lập',     -- Biện pháp thi công
        manpower_chart_status TEXT DEFAULT 'Chưa lập',
        machinery_chart_status TEXT DEFAULT 'Chưa lập',
        cashflow_plan_status TEXT DEFAULT 'Chưa lập',
        material_plan_status TEXT DEFAULT 'Chưa lập',
        approval_rate REAL DEFAULT 0.00,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE
    )
    """)

    # 4. Bảng Theo dõi tiến độ tuần progress_tracking
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS progress_tracking (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        package_id INTEGER NOT NULL,
        report_week INTEGER NOT NULL,           -- Tuần báo cáo (1, 2, 3, 4)
        planned_progress REAL NOT NULL,         -- % Kế hoạch
        actual_progress REAL NOT NULL,          -- % Thực tế đạt được
        variance REAL,                          -- actual - planned
        report_date TEXT DEFAULT CURRENT_DATE,
        FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE,
        UNIQUE (package_id, report_week)
    )
    """)

    # 5. Bảng Nhật ký Phát sinh chi phí cost_variations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS cost_variations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        package_id INTEGER NOT NULL,
        variation_code TEXT UNIQUE NOT NULL,    -- Ma_PS
        variation_date TEXT,                    -- Ngay_PS
        variation_type TEXT NOT NULL,           -- Loai
        description TEXT NOT NULL,              -- Mo_ta
        reason TEXT,                            -- Nguyen_nhan
        proposal TEXT,                          -- De_xuat_xu_ly
        variation_value REAL DEFAULT 0.00,      -- Gia_tri_phat_sinh
        delay_days_impact REAL DEFAULT 0.0,     -- Anh_huong_TD (ngày)
        status TEXT DEFAULT 'Chờ duyệt',         -- TT_Phe_duyet
        created_by TEXT,                        
        approved_by TEXT,                       -- Nguoi_duyet
        approved_at TEXT,                       -- Ngay_duyet
        adjusted_content TEXT,                  -- Noi_dung_dieu_chinh
        note TEXT,                              -- Ghi_chu
        FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE
    )
    """)

    # 6. Bảng Yêu cầu Cung ứng Vật tư đặc thù special_procurements
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS special_procurements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        package_id INTEGER NOT NULL,
        req_code TEXT UNIQUE NOT NULL,          -- Ma_YC
        request_date TEXT,                      -- Ngay_YC
        req_type TEXT NOT NULL,                 -- Loai_YC
        material_name TEXT NOT NULL,            -- Vat_tu_thiet_bi
        quantity REAL DEFAULT 1.00,             -- KL
        unit TEXT,                              -- DVT
        estimated_value REAL DEFAULT 0.00,      -- Gia_tri_phat_sinh (dự toán)
        contract_scope TEXT DEFAULT 'Trong HĐ',  -- Trong_Ngoai_HDCU
        supply_status TEXT DEFAULT 'Chưa cung ứng', -- TT_cung_ung
        file_url TEXT,                          -- Link_ho_so
        status TEXT DEFAULT 'Chờ duyệt',         -- TT_Phe_duyet
        created_by TEXT,                        
        approved_by TEXT,                       -- Nguoi_duyet
        needed_date TEXT,                       -- Ngay_can
        note TEXT,                              -- Ghi_chu
        FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE
    )
    """)

    # 7. Bảng Nhật ký Phương án bù tiến độ delay_mitigations
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS delay_mitigations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        package_id INTEGER NOT NULL,
        delay_days REAL DEFAULT 0.0,            -- Muc_cham_ngay
        delay_reason TEXT NOT NULL,             -- Nguyen_nhan
        mitigation_plan TEXT NOT NULL,          -- Phuong_an
        plan_detail TEXT,                       -- Chi_tiet_giai_phap
        commit_date TEXT NOT NULL,              -- Moc_cam_ket_HT
        status TEXT DEFAULT 'Chờ duyệt',         -- TT_duyet
        approved_by TEXT,                       -- Nguoi_duyet
        evaluation TEXT,                        -- KQ_thuc_hien_bu
        mitigation_status TEXT DEFAULT 'Đang thực hiện', -- TT_Trien_khai
        file_url TEXT,                          -- Link_phuong_an
        note TEXT,                              -- Ghi_chu
        FOREIGN KEY (package_id) REFERENCES packages(id) ON DELETE CASCADE
    )
    """)

    # Bảng cấu hình hệ thống
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sys_config (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # Bảng nhật ký kiểm toán
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT,
        username TEXT,
        action_type TEXT,
        table_name TEXT,
        record_id TEXT,
        details TEXT
    )
    """)

    # Bảng phân quyền nhân sự
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS nhan_su (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        Ma_NV TEXT,
        Ho_Ten TEXT,
        Chuc_Vu TEXT,
        Vai_Tro TEXT,
        Email TEXT,
        Xem INTEGER DEFAULT 1,
        Them_HD INTEGER,
        Sua INTEGER,
        Xoa_HD INTEGER,
        Sua_CDT_BD INTEGER,
        Cap_Nhat_CDT INTEGER
    )
    """)

    check_and_add_columns(cursor)

    cursor.execute("SELECT value FROM sys_config WHERE key='is_seeded'")
    seeded_row = cursor.fetchone()
    already_seeded = seeded_row is not None and seeded_row[0] == '1'

    if force_reseed or not already_seeded:
        cursor.execute("SELECT COUNT(*) FROM nhan_su")
        count_ns = cursor.fetchone()[0]
        if count_ns == 0:
            personnel_data = [
                ("80", "Cao Thị An", "Phó phòng", "Trống", "caothian11@gmail.com", 1, 0, 1, 0, 0, 0),
                ("58", "Hoàng Văn Vượng", "CV QLCL", "User2", "hoangvuongdhv@gmail.com", 1, 0, 1, 0, 0, 0),
                ("38", "Hồ Nghĩa Chất", "Admin", "admin2", "Hochat.tayan@gmail.com", 1, 1, 1, 1, 1, 1),
                ("467", "Lê Thị Ngọc Hoa", "NV hỗ trợ", "Trống", "lengochoa289@gmail.com", 1, 0, 0, 0, 0, 0),
                ("364", "Lê Xuân Văn", "CV QLCL", "User2", "lexuanvankt@gmail.com", 1, 0, 1, 0, 0, 0),
                ("76", "Nguyễn Hoàng Kiên", "CV Vật tư", "Trống", "kienprotl4@gmail.com", 1, 0, 0, 0, 0, 0),
                ("312", "Nguyễn Thành Chung", "CV QLCL", "User2", "thanhchunglcc@gmail.com", 1, 0, 1, 0, 0, 0)
            ]
            cursor.executemany("""
                INSERT INTO nhan_su (Ma_NV, Ho_Ten, Chuc_Vu, Vai_Tro, Email, Xem, Them_HD, Sua, Xoa_HD, Sua_CDT_BD, Cap_Nhat_CDT)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, personnel_data)
        
        cursor.execute("INSERT OR REPLACE INTO sys_config (key, value) VALUES ('is_seeded', '1')")

    conn.commit()

    cursor.execute("SELECT COUNT(*) FROM packages")
    count_master = cursor.fetchone()[0]
    if force_reseed or count_master == 0:
        if os.path.exists(EXCEL_PATH):
            print("Seeding database from Excel file...")
            seed_from_excel(conn)
        else:
            print("Excel file not found. Seeding skipped.")

    conn.close()

def seed_from_excel(conn, excel_file=None):
    if excel_file is None:
        excel_file = EXCEL_PATH
    cursor = conn.cursor()

    conn.execute("PRAGMA foreign_keys = OFF;")
    cursor.execute("DELETE FROM progress_tracking")
    cursor.execute("DELETE FROM pre_construction_docs")
    cursor.execute("DELETE FROM monthly_weekly_plans")
    cursor.execute("DELETE FROM cost_variations")
    cursor.execute("DELETE FROM special_procurements")
    cursor.execute("DELETE FROM delay_mitigations")
    cursor.execute("DELETE FROM packages")
    conn.execute("PRAGMA foreign_keys = ON;")

    # 1. Seed packages
    df_master = pd.read_excel(excel_file, sheet_name='BANG TONG HOP', header=None)
    current_pl = None
    raw_packages = []
    
    for idx in range(5, len(df_master)):
        row = df_master.iloc[idx].values
        if len(row) < 5 or (pd.isna(row[0]) and pd.isna(row[4])):
            continue

        tt = clean_str(row[0])
        ma_bsc = clean_str(row[1])
        goi_thau = clean_str(row[2])
        
        if goi_thau and goi_thau.upper().startswith('PL'):
            current_pl = goi_thau
            
        if not goi_thau or not goi_thau.upper().startswith('PL'):
            if current_pl:
                goi_thau = current_pl
            else:
                continue
                
        nhom_ct = clean_str(row[3])
        hang_muc = clean_str(row[4])
        phu_trach = clean_str(row[5])
        ngay_bd_yc = clean_date(row[6])
        ngay_kt_yc = clean_date(row[7])
        ngan_sach = clean_float(row[8])
        kh_hstktc = clean_date(row[9])
        tt_hstktc = clean_str(row[10])
        tt_specs = clean_str(row[11])
        tt_boq = clean_str(row[12])
        kh_lcnt = clean_date(row[13])
        tt_lcnt = clean_str(row[14])
        kh_hdcu = clean_date(row[15])
        tt_hdcu = clean_str(row[16])
        kh_khcu = clean_date(row[17])
        tt_khcu = clean_str(row[18])
        gia_tri_hdcu = clean_float(row[19])
        kh_plhd = clean_date(row[21])
        tt_plhd = clean_str(row[22])
        kh_khtk = clean_date(row[23])
        tt_khtk = clean_str(row[24])
        ngay_bd_khoi_cong = clean_date(row[29])
        
        qa_kh_thang = clean_float(row[38])
        qa_kq_thang = clean_float(row[39])
        qa_dg_thang = clean_str(row[40])
        kh_thang = clean_float(row[41])
        kq_thang = clean_float(row[42])
        dg_thang = clean_str(row[43])
        
        parent_code = None
        if tt and '.' in tt:
            parent_code = tt[:tt.rfind('.')]
            
        raw_packages.append((
            tt, parent_code, ma_bsc, goi_thau, hang_muc, nhom_ct, phu_trach, ngay_bd_yc, ngay_kt_yc, ngan_sach,
            kh_hstktc, tt_hstktc, tt_specs, tt_boq, kh_lcnt, tt_lcnt, kh_hdcu, tt_hdcu,
            kh_khcu, tt_khcu, gia_tri_hdcu, kh_plhd, tt_plhd, kh_khtk, tt_khtk, ngay_bd_khoi_cong,
            qa_kh_thang, qa_kq_thang, qa_dg_thang, kh_thang, kq_thang, dg_thang
        ))

    conn.execute("PRAGMA foreign_keys = OFF;")
    cursor.executemany("""
    INSERT INTO packages (
        package_code, parent_code, bsc_code, goi_thau_pl, package_name, project_group, person_in_charge, plan_start_date, plan_end_date, cdt_budget,
        kh_hstktc, tt_hstktc, tt_specs, tt_boq, kh_lcnt, tt_lcnt, kh_hdcu, tt_hdcu,
        kh_khcu, tt_khcu, contract_value, kh_plhd, tt_plhd, kh_khtk, tt_khtk, actual_start_date,
        qa_kh_thang, qa_kq_thang, qa_dg_thang, kh_thang, kq_thang, dg_thang
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, raw_packages)
    conn.execute("PRAGMA foreign_keys = ON;")

    cursor.execute("SELECT id, bsc_code, package_code FROM packages")
    pkg_rows = cursor.fetchall()
    bsc_to_id = {}
    code_to_id = {}
    for r in pkg_rows:
        pkg_id = r['id']
        bsc = r['bsc_code']
        code = r['package_code']
        if bsc:
            bsc_to_id[bsc.strip()] = pkg_id
        if code:
            code_to_id[code.strip()] = pkg_id

    # Seed progress_tracking
    raw_progress = []
    for idx in range(5, len(df_master)):
        row = df_master.iloc[idx].values
        if len(row) < 5 or (pd.isna(row[0]) and pd.isna(row[4])):
            continue
        tt = clean_str(row[0])
        if not tt or tt not in code_to_id:
            continue
        pkg_id = code_to_id[tt]
        
        t1_kh = clean_float(row[44])
        t1_kq = clean_float(row[45])
        if t1_kh is not None or t1_kq is not None:
            v = (t1_kq or 0.0) - (t1_kh or 0.0)
            raw_progress.append((pkg_id, 1, t1_kh or 0.0, t1_kq or 0.0, v))
            
        t2_kh = clean_float(row[47])
        t2_kq = clean_float(row[48])
        if t2_kh is not None or t2_kq is not None:
            v = (t2_kq or 0.0) - (t2_kh or 0.0)
            raw_progress.append((pkg_id, 2, t2_kh or 0.0, t2_kq or 0.0, v))
            
        t3_kh = clean_float(row[50])
        t3_kq = clean_float(row[51])
        if t3_kh is not None or t3_kq is not None:
            v = (t3_kq or 0.0) - (t3_kh or 0.0)
            raw_progress.append((pkg_id, 3, t3_kh or 0.0, t3_kq or 0.0, v))
            
        t4_kh = clean_float(row[53])
        t4_kq = clean_float(row[54])
        if t4_kh is not None or t4_kq is not None:
            v = (t4_kq or 0.0) - (t4_kh or 0.0)
            raw_progress.append((pkg_id, 4, t4_kh or 0.0, t4_kq or 0.0, v))

    cursor.executemany("""
    INSERT INTO progress_tracking (package_id, report_week, planned_progress, actual_progress, variance)
    VALUES (?, ?, ?, ?, ?)
    """, raw_progress)

    # 2. Seed pre_construction_docs
    df_01 = pd.read_excel(excel_file, sheet_name='01_HSo TienKC', header=None)
    raw_docs = []
    for idx in range(2, len(df_01)):
        row = df_01.iloc[idx].values
        if len(row) < 10 or pd.isna(row[1]):
            continue
        bsc = clean_str(row[1])
        if bsc not in bsc_to_id:
            continue
        pkg_id = bsc_to_id[bsc]
        raw_docs.append((
            pkg_id, clean_str(row[3]), clean_str(row[4]), clean_str(row[5]),
            clean_str(row[9]), clean_date(row[6]), clean_str(row[7]), clean_str(row[8])
        ))
    cursor.executemany("""
    INSERT INTO pre_construction_docs (package_id, doc_type, doc_name, file_url, status, uploaded_at, created_by, approved_by)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, raw_docs)

    # 3. Seed monthly_weekly_plans
    df_02 = pd.read_excel(excel_file, sheet_name='02_KH Thang_Tuan', header=None)
    plans_map = {}
    for idx in range(2, len(df_02)):
        row = df_02.iloc[idx].values
        if len(row) < 13 or pd.isna(row[1]):
            continue
        bsc = clean_str(row[1])
        if bsc not in bsc_to_id:
            continue
        pkg_id = bsc_to_id[bsc]
        period = clean_str(row[3]) or "Tháng 06/2026"
        doc_type = clean_str(row[4])
        status = clean_str(row[9])
        
        key = (pkg_id, period)
        if key not in plans_map:
            plans_map[key] = {
                'bptc': 'Chưa lập', 'manpower': 'Chưa lập', 'machinery': 'Chưa lập',
                'cashflow': 'Chưa lập', 'material': 'Chưa lập'
            }
        if doc_type == 'Biện pháp thi công':
            plans_map[key]['bptc'] = status
        elif doc_type == 'Biểu đồ nhân lực':
            plans_map[key]['manpower'] = status
        elif doc_type == 'Biểu đồ máy móc thiết bị':
            plans_map[key]['machinery'] = status
        elif doc_type == 'Biểu đồ cung ứng' or doc_type == 'Kế hoạch dòng tiền':
            plans_map[key]['cashflow'] = status
        elif doc_type == 'Kế hoạch cung ứng' or doc_type == 'Kế hoạch vật tư':
            plans_map[key]['material'] = status

    raw_plans = []
    for (pkg_id, period), vals in plans_map.items():
        statuses = [vals['bptc'], vals['manpower'], vals['machinery'], vals['cashflow'], vals['material']]
        approved_count = sum(1 for s in statuses if s == 'Đã duyệt')
        rate = (approved_count / 5.0) * 100.0
        raw_plans.append((
            pkg_id, period, vals['bptc'], vals['manpower'], vals['machinery'], vals['cashflow'], vals['material'], rate
        ))
    cursor.executemany("""
    INSERT INTO monthly_weekly_plans (package_id, plan_period, bptc_status, manpower_chart_status, machinery_chart_status, cashflow_plan_status, material_plan_status, approval_rate)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, raw_plans)

    # 4. Seed cost_variations
    df_03 = pd.read_excel(excel_file, sheet_name='03_Phat sinh', header=None)
    raw_vars = []
    for idx in range(2, len(df_03)):
        row = df_03.iloc[idx].values
        if len(row) < 15 or pd.isna(row[2]):
            continue
        bsc = clean_str(row[2])
        if bsc not in bsc_to_id:
            continue
        pkg_id = bsc_to_id[bsc]
        raw_vars.append((
            pkg_id, clean_str(row[1]), clean_date(row[4]), clean_str(row[5]), clean_str(row[6]), clean_str(row[7]), clean_str(row[8]),
            clean_float(row[9]) or 0.0, clean_float(row[10]) or 0.0, clean_str(row[12]), clean_str(row[13]),
            clean_date(row[14]), clean_str(row[15]) if len(row)>15 else None, clean_str(row[16]) if len(row)>16 else None
        ))
    cursor.executemany("""
    INSERT INTO cost_variations (
        package_id, variation_code, variation_date, variation_type, description, reason, proposal, variation_value, delay_days_impact,
        status, approved_by, approved_at, adjusted_content, note
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, raw_vars)

    # 5. Seed special_procurements
    df_04 = pd.read_excel(excel_file, sheet_name='04_CU dac thu', header=None)
    raw_procs = []
    for idx in range(2, len(df_04)):
        row = df_04.iloc[idx].values
        if len(row) < 15 or pd.isna(row[2]):
            continue
        bsc = clean_str(row[2])
        if bsc not in bsc_to_id:
            continue
        pkg_id = bsc_to_id[bsc]
        raw_procs.append((
            pkg_id, clean_str(row[1]), clean_date(row[4]), clean_str(row[5]), clean_str(row[6]), clean_float(row[8]) or 1.0,
            clean_str(row[9]), clean_float(row[10]) or 0.0, clean_str(row[11]), clean_str(row[16]) if len(row)>16 else 'Chưa cung ứng',
            clean_str(row[12]), clean_str(row[13]), clean_str(row[14]), clean_date(row[15]) if len(row)>15 else None,
            clean_str(row[17]) if len(row)>17 else None
        ))
    cursor.executemany("""
    INSERT INTO special_procurements (
        package_id, req_code, request_date, req_type, material_name, quantity, unit, estimated_value, contract_scope, supply_status,
        file_url, status, approved_by, needed_date, note
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, raw_procs)

    # 6. Seed delay_mitigations
    df_05 = pd.read_excel(excel_file, sheet_name='05_Bu tien do', header=None)
    raw_mitigations = []
    for idx in range(2, len(df_05)):
        row = df_05.iloc[idx].values
        if len(row) < 14 or pd.isna(row[1]):
            continue
        bsc = clean_str(row[1])
        if bsc not in bsc_to_id:
            continue
        pkg_id = bsc_to_id[bsc]
        raw_mitigations.append((
            pkg_id, clean_float(row[4]) or 0.0, clean_str(row[5]), clean_str(row[6]), clean_str(row[7]),
            clean_date(row[8]), clean_str(row[10]), clean_str(row[11]), clean_str(row[12]),
            clean_str(row[13]) if len(row)>13 else 'Đang thực hiện', clean_str(row[9]), clean_str(row[14]) if len(row)>14 else None
        ))
    cursor.executemany("""
    INSERT INTO delay_mitigations (
        package_id, delay_days, delay_reason, mitigation_plan, plan_detail, commit_date, status, approved_by, evaluation,
        mitigation_status, file_url, note
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, raw_mitigations)

    conn.commit()
    print("Database seeding completed successfully.")

def log_action(username, action_type, table_name, record_id, details):
    try:
        conn = get_connection()
        cursor = conn.cursor()
        now_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            INSERT INTO audit_log (timestamp, username, action_type, table_name, record_id, details)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (now_str, username, action_type, table_name, str(record_id), details))
        conn.commit()
        conn.close()
        try:
            import gdrive_sync
            import threading
            threading.Thread(target=gdrive_sync.upload_to_gdrive, args=(DB_PATH, "project_control.db"), daemon=True).start()
        except Exception:
            pass
    except Exception as e:
        print(f"Error writing audit log: {e}")

if __name__ == '__main__':
    init_db(force_reseed=True)
