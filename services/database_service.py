# services/database_service.py
import sqlite3
import json
import logging
import re
import uuid
from config import CURRENT_SESSION, DATA_CLIENT

logger = logging.getLogger(__name__)

# 🌟 SAKLAR UTAMA: Set ke True jika nanti sudah siap online ke Supabase
USE_CLOUD = False


# ==============================================================================
# 🧯 ERROR TERSTRUKTUR
# Dipakai supaya caller (mis. tab_resi.py) tidak perlu cocokkan string pesan
# mentah dari SQLite untuk menentukan jenis kegagalan — cukup cek `.kode`.
# ==============================================================================

class KesalahanTransaksiResi(Exception):
    """Error terstruktur untuk operasi simpan_transaksi_resi.

    `kode` adalah penanda stabil yang aman dipakai UI untuk percabangan logic,
    terpisah dari `pesan` (teks untuk ditampilkan ke user, boleh berubah
    redaksinya kapan saja tanpa mematahkan logic caller).
    """

    def __init__(self, kode, pesan):
        self.kode = kode
        self.pesan = pesan
        super().__init__(pesan)

    def __str__(self):
        return self.pesan


KODE_RESI_DUPLIKAT = "RESI_DUPLIKAT"
KODE_DB_ERROR = "DB_ERROR"


# ==============================================================================
# ⚙️ KONEKSI INTI & UTILITY SISTEM (GLOBAL)
# ==============================================================================

def get_db_connection():
    db_name = CURRENT_SESSION.get('db_name', 'database_cargo.db')
    # Tambahkan timeout 20 detik agar antrean query bisa menunggu
    return sqlite3.connect(db_name, timeout=20.0)

def get_setting(key):
    """
    Mengambil settingan dengan prioritas:
    1. Cek di Database (Data custom user)
    2. Jika TIDAK ada/error, ambil dari DATA_CLIENT (Config.py)
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT nilai FROM pengaturan_sistem WHERE kunci = ?", (key,))
        row = cursor.fetchone()

        # Prioritas 1: Jika ada di DB, kembalikan datanya
        if row:
            return row[0]

    except Exception as e:
        print(f"[Service] Gagal ambil setting {key}: {e}")
        # Jika ada error database (tabel belum ada/locked), lanjut ke fallback
    finally:
        if conn:
            conn.close()

    # Prioritas 2: Fallback ke config.py
    return DATA_CLIENT.get(key, "Data Tidak Ditemukan")


def migrasi_hapus_unique_no_hp_master():
    """
    Menghapus constraint UNIQUE pada no_hp di master_pengirim dan master_penerima.
    Ini penting agar no_hp boleh kosong, boleh sama, dan tidak mengganggu sinkronisasi Tab Resi <-> Master.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA foreign_keys = OFF")

        # ==========================================================
        # MIGRASI master_pengirim
        # ==========================================================
        cursor.execute("""
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'master_pengirim'
        """)
        row_pengirim = cursor.fetchone()

        if row_pengirim and row_pengirim[0]:
            sql_pengirim = " ".join(row_pengirim[0].lower().split())
            perlu_migrasi_pengirim = (
                "no_hp text unique" in sql_pengirim
                or "unique(no_hp" in sql_pengirim
                or "unique (no_hp" in sql_pengirim
            )

            if perlu_migrasi_pengirim:
                print("[Migrasi] Menghapus UNIQUE no_hp dari master_pengirim...")

                cursor.execute("DROP TABLE IF EXISTS master_pengirim_backup_fix")
                cursor.execute("""
                    CREATE TABLE master_pengirim_backup_fix AS
                    SELECT *
                    FROM master_pengirim
                """)

                cursor.execute("DROP TABLE IF EXISTS master_pengirim")

                cursor.execute("""
                    CREATE TABLE master_pengirim (
                        id_pengirim TEXT PRIMARY KEY,
                        kode_cabang TEXT NOT NULL,
                        nama TEXT,
                        no_hp TEXT,
                        kota TEXT,
                        alamat TEXT,
                        is_synced INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    INSERT OR IGNORE INTO master_pengirim (
                        id_pengirim, kode_cabang, nama, no_hp, kota, alamat,
                        is_synced, created_at, updated_at
                    )
                    SELECT
                        id_pengirim,
                        kode_cabang,
                        nama,
                        NULLIF(no_hp, ''),
                        kota,
                        alamat,
                        COALESCE(is_synced, 0),
                        COALESCE(created_at, CURRENT_TIMESTAMP),
                        COALESCE(updated_at, CURRENT_TIMESTAMP)
                    FROM master_pengirim_backup_fix
                """)

                cursor.execute("DROP TABLE IF EXISTS master_pengirim_backup_fix")

        # ==========================================================
        # MIGRASI master_penerima
        # ==========================================================
        cursor.execute("""
            SELECT sql
            FROM sqlite_master
            WHERE type = 'table'
              AND name = 'master_penerima'
        """)
        row_penerima = cursor.fetchone()

        if row_penerima and row_penerima[0]:
            sql_penerima = " ".join(row_penerima[0].lower().split())
            perlu_migrasi_penerima = (
                "no_hp text unique" in sql_penerima
                or "unique(no_hp" in sql_penerima
                or "unique (no_hp" in sql_penerima
            )

            if perlu_migrasi_penerima:
                print("[Migrasi] Menghapus UNIQUE no_hp dari master_penerima...")

                cursor.execute("DROP TABLE IF EXISTS master_penerima_backup_fix")
                cursor.execute("""
                    CREATE TABLE master_penerima_backup_fix AS
                    SELECT *
                    FROM master_penerima
                """)

                cursor.execute("DROP TABLE IF EXISTS master_penerima")

                cursor.execute("""
                    CREATE TABLE master_penerima (
                        id_penerima TEXT PRIMARY KEY,
                        kode_cabang TEXT NOT NULL,
                        nama TEXT,
                        no_hp TEXT,
                        kota TEXT,
                        alamat TEXT,
                        total_transaksi INTEGER DEFAULT 0,
                        pembayaran TEXT DEFAULT 'TF / INVOICE',
                        status_tagihan TEXT DEFAULT 'NORMAL',
                        is_synced INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                cursor.execute("""
                    INSERT OR IGNORE INTO master_penerima (
                        id_penerima, kode_cabang, nama, no_hp, kota, alamat,
                        total_transaksi, pembayaran, status_tagihan,
                        is_synced, created_at, updated_at
                    )
                    SELECT
                        id_penerima,
                        kode_cabang,
                        nama,
                        NULLIF(no_hp, ''),
                        kota,
                        alamat,
                        COALESCE(total_transaksi, 0),
                        COALESCE(pembayaran, 'TF / INVOICE'),
                        COALESCE(status_tagihan, 'NORMAL'),
                        COALESCE(is_synced, 0),
                        COALESCE(created_at, CURRENT_TIMESTAMP),
                        COALESCE(updated_at, CURRENT_TIMESTAMP)
                    FROM master_penerima_backup_fix
                """)

                cursor.execute("DROP TABLE IF EXISTS master_penerima_backup_fix")

        cursor.execute("PRAGMA foreign_keys = ON")
        conn.commit()
        return True

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[Migrasi UNIQUE no_hp Master] Error: {e}")
        return False

    finally:
        if conn:
            conn.close()


def inisialisasi_database():
    """
    Dijalankan HANYA SEKALI saat aplikasi pertama kali dibuka.
    Memastikan constraint master data diperbaiki.
    """
    try:
        migrasi_hapus_unique_no_hp_master()
        pastikan_kolom_provinsi_master_penerima()
        print("[Init DB] Inisialisasi master data berhasil dilewati dengan aman.")
    except Exception as e:
        print(f"[Init DB] Error saat inisialisasi: {e}")


# ==============================================================================
# 📋 TAB RESI (FORM INPUT SURAT JALAN & HISTORI HARIAN)
# ==============================================================================

def cari_histori_resi(keyword, kode_cabang):
    """Digunakan untuk pencarian live di sidebar histori kanan Tab Resi"""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            search_pattern = f"%{keyword}%"
            cursor.execute("""
                           SELECT no_resi, penerima
                           FROM data_resi
                           WHERE kode_cabang = ?
                             AND (LOWER(no_resi) LIKE ? OR LOWER(pengirim) LIKE ? OR LOWER(penerima) LIKE ?)
                           ORDER BY rowid DESC LIMIT 50
                           """, (kode_cabang, search_pattern, search_pattern, search_pattern))
            hasil = cursor.fetchall()
            return hasil
        finally:
            if conn:
                conn.close()


def ambil_histori_resi_by_tanggal(tgl_pilih, kode_cabang):
    """Memuat daftar resi di sidebar kanan berdasarkan kalender yang dipilih"""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT no_resi, penerima FROM data_resi WHERE tanggal_masuk = ? AND kode_cabang = ? ORDER BY rowid ASC",
                (tgl_pilih, kode_cabang))
            hasil = cursor.fetchall()
            return hasil
        finally:
            if conn:
                conn.close()


def ambil_detail_resi(no_resi):
    """Mengambil data lengkap satu resi untuk keperluan Cetak / Preview Nota"""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                           SELECT tanggal_masuk,
                                  pengirim,
                                  hp_pengirim,
                                  alamat_pengirim,
                                  penerima,
                                  hp_penerima,
                                  alamat_penerima,
                                  kota_tujuan,
                                  nama_barang,
                                  berat,
                                  koli,
                                  cbm,
                                  total_ongkir,
                                  pembayaran,
                                  rincian_json,
                                  ongkir_per_kg,
                                  ongkir_per_cbm
                           FROM data_resi
                           WHERE no_resi = ?
                           """, (no_resi,))
            row = cursor.fetchone()
            return row
        finally:
            if conn:
                conn.close()


def ambil_data_autocomplete(kode_cabang):
    """Menyediakan daftar nama Pengirim dan Penerima untuk QCompleter di form input Resi"""
    if USE_CLOUD:
        return [], []

    pengirim, penerima = [], []
    conn = None

    kode_cabang = str(kode_cabang or CURRENT_SESSION.get('kode_cabang', 'PUSAT')).strip()

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("""
                SELECT DISTINCT TRIM(nama)
                FROM master_pengirim
                WHERE TRIM(COALESCE(nama, '')) != ''
                  AND kode_cabang = ?
                ORDER BY TRIM(nama) COLLATE NOCASE ASC
            """, (kode_cabang,))
            pengirim = [str(r[0]).strip().upper() for r in cursor.fetchall() if r[0]]
        except sqlite3.OperationalError as e:
            print(f"[Autocomplete Service] Gagal memuat pengirim: {e}")

        try:
            cursor.execute("""
                SELECT DISTINCT TRIM(nama)
                FROM master_penerima
                WHERE TRIM(COALESCE(nama, '')) != ''
                  AND kode_cabang = ?
                ORDER BY TRIM(nama) COLLATE NOCASE ASC
            """, (kode_cabang,))
            penerima = [str(r[0]).strip().upper() for r in cursor.fetchall() if r[0]]
        except sqlite3.OperationalError as e:
            print(f"[Autocomplete Service] Gagal memuat penerima: {e}")

    except Exception as e:
        print(f"[Autocomplete Service] Critical Error: {e}")

    finally:
        if conn:
            conn.close()

    return pengirim, penerima


def ambil_detail_pengirim(name_clean, kode_cabang):
    """Autofill detail profil pengirim saat nama dipilih di form resi"""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT no_hp, alamat, kota
                FROM master_pengirim
                WHERE TRIM(UPPER(nama)) = TRIM(UPPER(?))
                  AND kode_cabang = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (name_clean, kode_cabang))
            row = cursor.fetchone()
            return row
        finally:
            if conn:
                conn.close()


def ambil_detail_penerima(nama_penerima, kode_cabang):
    """Autofill detail profil penerima saat nama dipilih di form resi"""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT no_hp, alamat, kota, provinsi
                FROM master_penerima
                WHERE TRIM(UPPER(nama)) = TRIM(UPPER(?))
                  AND kode_cabang = ?
                ORDER BY updated_at DESC
                LIMIT 1
            """, (nama_penerima, kode_cabang))
            row = cursor.fetchone()
            return row
        finally:
            if conn:
                conn.close()


def ambil_sekuens_resi(kode_cabang, pref):
    """Menghitung nomor urut/counter resi otomatis berdasarkan cabang dan tipe transaksi"""
    if USE_CLOUD:
        pass
    else:
        base_number = 0
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT start_seq_json FROM data_cabang WHERE kode_cabang = ?", (kode_cabang,))
            row = cursor.fetchone()
            if row and row[0]:
                try:
                    seq_dict = json.loads(row[0])
                    base_number = seq_dict.get(pref, seq_dict.get("DEFAULT", 0))
                except Exception:
                    pass

            cursor.execute("SELECT no_resi FROM data_resi WHERE no_resi LIKE ? AND kode_cabang = ?",
                           (f"{pref}%", kode_cabang))
            rows = cursor.fetchall()

            max_num = 0
            for r in rows:
                no_resi_db = str(r[0] or "").strip()

                if no_resi_db.upper().startswith(str(pref).upper()):
                    bagian_counter = no_resi_db[len(str(pref)):]
                else:
                    bagian_counter = no_resi_db

                m = re.findall(r'\d+', bagian_counter)
                if m:
                    try:
                        max_num = max(max_num, int(m[-1]))
                    except ValueError:
                        pass

            return base_number, max_num
        finally:
            if conn:
                conn.close()


def simpan_transaksi_resi(data):
    """Menyimpan data resi baru & otomatis sinkron ke master_pengirim dan master_penerima"""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            # 0. Cegah No Resi duplikat SEBELUM insert dijalankan.
            #    Sengaja dicek eksplisit, bukan mengandalkan IntegrityError dari SQLite,
            #    karena statement di bawah sebelumnya pakai INSERT OR REPLACE — yang mana
            #    SQLite tidak pernah melempar error untuk itu, ia diam-diam menimpa baris
            #    lama. Makanya duplikat dicek manual dulu di sini.
            cursor.execute(
                "SELECT 1 FROM data_resi WHERE no_resi = ? AND kode_cabang = ? LIMIT 1",
                (data['no_resi'], data['kode_cabang']),
            )
            if cursor.fetchone():
                return False, KesalahanTransaksiResi(
                    KODE_RESI_DUPLIKAT,
                    "No Resi sudah ada di database cabang ini!",
                )

            # 1. Simpan data utama resi
            cursor.execute("""
                           INSERT INTO data_resi (no_resi, kode_cabang, tanggal_masuk, pengirim, hp_pengirim,
                                                  alamat_pengirim, kota_asal, penerima, hp_penerima, alamat_penerima,
                                                  kota_tujuan, nama_barang, berat, koli, cbm,
                                                  ongkir_per_kg, ongkir_per_cbm, total_ongkir,
                                                  pembayaran, status_resi, foto_bukti, rincian_json)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PROSES', 'BELUM', ?)
                           """, (
                               data['no_resi'], data['kode_cabang'], data['tanggal_masuk'], data['pengirim'],
                               data['hp_pengirim'], data['alamat_pengirim'], data['kota_asal'], data['penerima'],
                               data['hp_penerima'], data['alamat_penerima'], data['kota_tujuan'], data['nama_barang'],
                               data['berat'], data['koli'], data['cbm'], data['ongkir_per_kg'], data['ongkir_per_cbm'],
                               data['total_ongkir'], data['pembayaran'], data['rincian_json']
                           ))

            # 2. Simpan / update buku gudang
            cursor.execute(
                "INSERT OR REPLACE INTO buku_gudang (id_gudang, kode_cabang, tanggal, no_resi, jenis, status_resi) VALUES (?, ?, ?, ?, 'BARANG MASUK', 'PROSES')",
                (f"GDG-{data['no_resi']}", data['kode_cabang'], data['tanggal_masuk'], data['no_resi'])
            )

            kode_cabang = data.get('kode_cabang', CURRENT_SESSION.get('kode_cabang', 'PUSAT'))

            # ==========================================================
            # 3. SINKRONISASI KE master_pengirim
            # Syarat simpan/update master hanya NAMA.
            # no_hp, alamat, kota boleh kosong.
            # ==========================================================
            nama_pengirim = data.get('pengirim', '').strip().upper()
            hp_pengirim = data.get('hp_pengirim', '').strip()
            alamat_pengirim = data.get('alamat_pengirim', '').strip().upper()
            kota_pengirim = data.get('kota_asal', '').strip().upper()

            hp_pengirim_db = hp_pengirim if hp_pengirim else None

            if nama_pengirim:
                cursor.execute("""
                    SELECT id_pengirim
                    FROM master_pengirim
                    WHERE TRIM(UPPER(nama)) = TRIM(UPPER(?))
                      AND kode_cabang = ?
                    ORDER BY updated_at DESC
                    LIMIT 1
                """, (nama_pengirim, kode_cabang))
                exist_pengirim = cursor.fetchone()

                if exist_pengirim:
                    cursor.execute("""
                        UPDATE master_pengirim
                        SET nama = ?,
                            no_hp = ?,
                            alamat = ?,
                            kota = ?,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id_pengirim = ?
                          AND kode_cabang = ?
                    """, (
                        nama_pengirim,
                        hp_pengirim_db,
                        alamat_pengirim,
                        kota_pengirim,
                        exist_pengirim[0],
                        kode_cabang
                    ))
                else:
                    id_baru_shp = f"SHP-{uuid.uuid4().hex[:6].upper()}"
                    cursor.execute("""
                        INSERT INTO master_pengirim (
                            id_pengirim, kode_cabang, nama, no_hp, alamat, kota
                        )
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        id_baru_shp,
                        kode_cabang,
                        nama_pengirim,
                        hp_pengirim_db,
                        alamat_pengirim,
                        kota_pengirim
                    ))

            # ==========================================================
            # 4. SINKRONISASI KE master_penerima
            # Syarat simpan/update master hanya NAMA.
            # no_hp, alamat, kota boleh kosong.
            # ==========================================================
            nama_penerima = data.get('penerima', '').strip().upper()
            hp_penerima = data.get('hp_penerima', '').strip()
            alamat_penerima = data.get('alamat_penerima', '').strip().upper()

            kota_tujuan = data.get('kota_tujuan', '')
            kota_clean = kota_tujuan.split(" - ")[
                -1].strip().upper() if " - " in kota_tujuan else kota_tujuan.strip().upper()

            provinsi_clean = data.get('provinsi_tujuan', '').strip().upper()
            if not provinsi_clean and " - " in kota_tujuan:
                provinsi_clean = kota_tujuan.split(" - ")[0].strip().upper()

            hp_penerima_db = hp_penerima if hp_penerima else None
            provinsi_db = provinsi_clean if provinsi_clean else None

            if nama_penerima:
                cursor.execute("""
                                SELECT id_penerima
                                FROM master_penerima
                                WHERE TRIM(UPPER(nama)) = TRIM(UPPER(?))
                                  AND kode_cabang = ?
                                ORDER BY updated_at DESC
                                LIMIT 1
                            """, (nama_penerima, data['kode_cabang']))
                exist_penerima = cursor.fetchone()

                # 🚀 HITUNG AKTUAL JUMLAH RESI YANG SUDAH TERINSERSI UNTUK USER INI
                cursor.execute("""
                                SELECT COUNT(*) FROM data_resi 
                                WHERE TRIM(UPPER(penerima)) = TRIM(UPPER(?)) AND kode_cabang = ?
                            """, (nama_penerima, data['kode_cabang']))
                total_resi = cursor.fetchone()[0]

                if not exist_penerima:
                    id_baru_cne = f"CNE-{uuid.uuid4().hex[:6].upper()}"
                    cursor.execute('''
                                    INSERT INTO master_penerima (
                                        id_penerima, kode_cabang, nama, no_hp, kota, provinsi, alamat,
                                        total_transaksi, pembayaran
                                    )
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                                ''', (
                        id_baru_cne,
                        data['kode_cabang'],
                        nama_penerima,
                        hp_penerima_db,
                        kota_clean,
                        provinsi_db,
                        alamat_penerima,
                        total_resi,  # Simpan jumlah resi aktual
                        data.get('pembayaran', 'TF / INVOICE')
                    ))
                else:
                    # 🚀 UPDATE JUMLAH TRANSAKSI SAAT ADA RESI BARU MASUK
                    cursor.execute('''
                                    UPDATE master_penerima
                                    SET nama       = ?,
                                        no_hp      = ?,
                                        kota       = ?,
                                        provinsi   = ?,
                                        alamat     = ?,
                                        pembayaran = ?,
                                        total_transaksi = ?,
                                        updated_at = CURRENT_TIMESTAMP
                                    WHERE id_penerima = ?
                                      AND kode_cabang = ?
                                ''', (
                        nama_penerima,
                        hp_penerima_db,
                        kota_clean,
                        provinsi_db,
                        alamat_penerima,
                        data.get('pembayaran', 'TF / INVOICE'),
                        total_resi,  # Update dengan jumlah total transaksi terbaru
                        exist_penerima[0],
                        data['kode_cabang']
                    ))

            conn.commit()
            return True, ""

        except sqlite3.IntegrityError as e:
            if conn:
                conn.rollback()
            pesan_asli = str(e)

            # Jaring pengaman untuk race condition langka: dua penyimpanan
            # bersamaan lolos pre-check di atas sebelum salah satunya commit.
            if "no_resi" in pesan_asli.lower() and "data_resi" in pesan_asli.lower():
                return False, KesalahanTransaksiResi(
                    KODE_RESI_DUPLIKAT,
                    "No Resi sudah ada di database cabang ini!",
                )

            logger.exception("IntegrityError saat menyimpan transaksi resi")
            return False, KesalahanTransaksiResi(
                KODE_DB_ERROR,
                f"Gagal simpan karena aturan database.\n\nDetail error:\n{pesan_asli}",
            )

        except Exception as e:
            if conn:
                conn.rollback()
            logger.exception("Gagal menyimpan transaksi resi")
            return False, KesalahanTransaksiResi(KODE_DB_ERROR, f"Gagal simpan: {e}")

        finally:
            if conn:
                conn.close()


# ==============================================================================
# 🏭 TAB BUKU GUDANG (MONITORING DATA RESI MASUK & KELUAR)
# ==============================================================================

def ambil_data_buku_gudang(kode_cabang, wilayah, tahun_terpilih, filters=None):
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            mapping = {
                2: "tanggal_masuk", 3: "tanggal_keluar", 4: "status_resi", 5: "armada",
                6: "pengirim", 7: "kota_asal", 8: "penerima",
                9: "kota_tujuan", 10: "nama_barang", 14: "total_ongkir",
                15: "pembayaran", 16: "ket_buku_gudang"
            }

            query = """
                    SELECT no_resi, \
                           tanggal_masuk, \
                           tanggal_keluar, \
                           status_resi, \
                           armada, \
                           pengirim, \
                           kota_asal, \
                           penerima, \
                           kota_tujuan, \
                           nama_barang, \
                           koli, \
                           berat, \
                           cbm, \
                           total_ongkir, \
                           pembayaran, \
                           ket_buku_gudang
                    FROM data_resi
                    WHERE kode_cabang = ? \
                      AND kota_tujuan LIKE ? \
                      AND tanggal_masuk LIKE ? \
                    """
            params = [kode_cabang, f"%{wilayah}%", f"{tahun_terpilih}%"]

            if filters:
                for col_idx, val in filters.items():
                    if col_idx in mapping:
                        if col_idx == 14:
                            val = val.replace(".", "")
                        query += f" AND {mapping[col_idx]} LIKE ?"
                        params.append(f"%{val}%")

            query += " ORDER BY tanggal_masuk ASC, rowid ASC"
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return rows
        finally:
            if conn:
                conn.close()


def update_baris_buku_gudang(no_resi, kode_cabang, updates_dict, barang_payload=None):
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            if updates_dict:
                fields = [f"{k} = ?" for k in updates_dict.keys()]
                values = list(updates_dict.values())
                values.extend([no_resi, kode_cabang])

                query = f"UPDATE data_resi SET {', '.join(fields)} WHERE no_resi = ? AND kode_cabang = ?"
                cursor.execute(query, values)

            if barang_payload:
                tabel_target = ["data_barang", "rincian_barang_resi", "data_barang_resi"]
                for t_name in tabel_target:
                    try:
                        cursor.execute(f"SELECT 1 FROM {t_name} LIMIT 1")
                        cursor.execute(f"""
                            INSERT OR REPLACE INTO {t_name} (no_resi, nama_barang, koli, berat, cbm)
                            VALUES (?, ?, ?, ?, ?)
                        """, (no_resi, barang_payload['nama_barang'], barang_payload['koli'],
                              barang_payload['berat'], barang_payload['cbm']))
                        break
                    except sqlite3.OperationalError:
                        continue

            conn.commit()
            return True
        except Exception as e:
            if conn: conn.rollback()
            print(f"[Update Buku Gudang] Error: {e}")
            return False
        finally:
            if conn:
                conn.close()


def tandai_resi_selesai_massal(resi_terpilih, kode_cabang):
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            for no_resi in resi_terpilih:
                cursor.execute(
                    "UPDATE data_resi SET status_resi = 'SELESAI' WHERE no_resi = ? AND kode_cabang = ?",
                    (no_resi, kode_cabang)
                )
            conn.commit()
            return True
        except Exception as e:
            if conn: conn.rollback()
            print(f"[Selesai Massal] Error: {e}")
            return False
        finally:
            if conn:
                conn.close()


# ==============================================================================
# 🚚 TAB MANIFEST (PROSES PEMBERANGKATAN & TRACKING ARMADA)
# ==============================================================================

def ambil_armada_list():
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT no_polisi, nama_sopir FROM armada")
            rows = cursor.fetchall()
            return rows
        finally:
            if conn:
                conn.close()


def ambil_detail_armada_by_nopol(nopol):
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT nama_sopir, jenis_truk FROM armada WHERE no_polisi = ?", (nopol,))
            row = cursor.fetchone()
            return row
        finally:
            if conn:
                conn.close()


def ambil_detail_armada_by_sopir(sopir):
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT no_polisi, jenis_truk, ket_armada FROM armada WHERE nama_sopir = ? ORDER BY updated_at DESC",
                           (sopir,))
            row = cursor.fetchone()
            return row
        finally:
            if conn:
                conn.close()


def ambil_no_manifest_list_by_prefix(prefix, kode_cabang):
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT no_manifest FROM data_resi WHERE no_manifest LIKE ? AND kode_cabang = ?",
                           (f"{prefix}-%", kode_cabang))
            rows = cursor.fetchall()
            return rows
        finally:
            if conn:
                conn.close()


def ambil_daftar_tahun_manifest(kode_cabang):
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT substr(tanggal_keluar, 1, 4) FROM data_resi WHERE no_manifest IS NOT NULL AND tanggal_keluar IS NOT NULL AND kode_cabang = ?",
                (kode_cabang,))
            rows = cursor.fetchall()
            return rows
        finally:
            if conn:
                conn.close()


def ambil_resi_untuk_manifest(kode_cabang, wilayah, is_edit_mode, edit_manifest_id):
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            if is_edit_mode:
                cursor.execute(
                    """SELECT no_resi, tanggal_masuk, pengirim, penerima, kota_tujuan,
                              nama_barang, koli, berat, cbm, no_manifest,
                              total_ongkir, ket_manifest
                       FROM data_resi
                       WHERE kode_cabang = ?
                         AND (no_manifest = ? OR (kota_tujuan LIKE ? AND (armada IS NULL OR armada = '')))
                       ORDER BY CASE WHEN no_manifest = ? THEN 0 ELSE 1 END, tanggal_masuk ASC""",
                    (kode_cabang, edit_manifest_id, f"%{wilayah}%", edit_manifest_id)
                )
            else:
                cursor.execute(
                    """SELECT no_resi, tanggal_masuk, pengirim, penerima, kota_tujuan,
                              nama_barang, koli, berat, cbm, NULL as no_manifest,
                              total_ongkir, NULL as ket_manifest
                       FROM data_resi
                       WHERE kode_cabang = ?
                         AND kota_tujuan LIKE ?
                         AND (armada IS NULL OR armada = '')
                       ORDER BY tanggal_masuk ASC""",
                    (kode_cabang, f"%{wilayah}%")
                )
            rows = cursor.fetchall()
            return rows
        finally:
            if conn:
                conn.close()


def ambil_histori_manifest(kode_cabang, tahun_terpilih):
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            query = """
                    SELECT DISTINCT r1.tanggal_keluar, \
                                    r1.no_manifest, \
                                    r1.armada,
                                    (SELECT COUNT(*) \
                                     FROM data_resi r2 \
                                     WHERE r2.no_manifest = r1.no_manifest \
                                       AND r2.kode_cabang = r1.kode_cabang)
                    FROM data_resi r1 \
                    WHERE r1.no_manifest IS NOT NULL \
                      AND r1.kode_cabang = ? \
                    """
            params = [kode_cabang]
            if tahun_terpilih and tahun_terpilih != "Semua":
                query += " AND r1.tanggal_keluar LIKE ?"
                params.append(f"{tahun_terpilih}-%")
            query += " ORDER BY r1.tanggal_keluar ASC, r1.no_manifest ASC"

            rows = cursor.execute(query, params).fetchall()
            return rows
        finally:
            if conn:
                conn.close()


def simpan_atau_update_manifest_data(manifest_id, kode_cabang, armada_payload, resi_list, is_edit_mode, tgl_k):

    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")

            nopol = str(armada_payload.get('no_polisi', '') or '').strip().upper()
            sopir = str(armada_payload.get('nama_sopir', '') or '').strip().upper()
            jenis = str(armada_payload.get('jenis_truk', '') or '').strip()
            ket_armada = str(armada_payload.get('ket_armada', '') or '').strip().upper()

            if nopol:
                cursor.execute(
                    "SELECT nama_sopir, jenis_truk, ket_armada FROM armada WHERE no_polisi = ?",
                    (nopol,)
                )
                data_lama = cursor.fetchone()

                if data_lama:
                    cursor.execute('''
                        UPDATE armada
                        SET nama_sopir = CASE
                                WHEN TRIM(?) <> '' THEN ?
                                ELSE nama_sopir
                            END,
                            jenis_truk = CASE
                                WHEN TRIM(?) <> '' THEN ?
                                ELSE jenis_truk
                            END,
                            ket_armada = CASE
                                WHEN TRIM(?) <> '' THEN ?
                                ELSE ket_armada
                            END,
                            is_synced = 0,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE no_polisi = ?
                    ''', (
                        sopir, sopir,
                        jenis, jenis,
                        ket_armada, ket_armada,
                        nopol
                    ))
                else:
                    jenis_db = jenis if jenis else "BELUM DIKETAHUI"
                    cursor.execute('''
                        INSERT INTO armada (
                            no_polisi, nama_sopir, jenis_truk,
                            hp_sopir, ket_armada, foto_armada,
                            is_synced, updated_at
                        )
                        VALUES (?, ?, ?, '', ?, '', 0, CURRENT_TIMESTAMP)
                    ''', (nopol, sopir, jenis_db, ket_armada))

            if is_edit_mode:
                cursor.execute(
                    "UPDATE data_resi "
                    "SET armada = NULL, status_resi = 'GUDANG', tanggal_keluar = NULL, "
                    "no_manifest = NULL, ket_manifest = NULL "
                    "WHERE no_manifest = ? AND kode_cabang = ?",
                    (manifest_id, kode_cabang)
                )

            nama_armada = str(armada_payload.get('nama_armada', '') or '').strip()
            if not nama_armada:
                raise ValueError("Detail armada/keterangan Manifest tidak boleh kosong.")

            for r_data in resi_list:
                no_resi_item = r_data[0]
                ket_manifest = r_data[1] if len(r_data) > 1 else ""
                cursor.execute(
                    "UPDATE data_resi "
                    "SET armada = ?, status_resi = 'PERJALANAN', tanggal_keluar = ?, "
                    "no_manifest = ?, ket_manifest = ?, updated_at = CURRENT_TIMESTAMP "
                    "WHERE no_resi = ? AND kode_cabang = ?",
                    (nama_armada, tgl_k, manifest_id, ket_manifest, no_resi_item, kode_cabang)
                )

                if cursor.rowcount == 0:
                    raise ValueError(f"Resi {no_resi_item} tidak ditemukan pada cabang {kode_cabang}.")

            conn.commit()
            return True, ""
        except Exception as e:
            if conn:
                conn.rollback()
            return False, str(e)
        finally:
            if conn:
                conn.close()

def ambil_resi_detail_untuk_cetak(kode_cabang, resi_list):
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            placeholders = ','.join(['?'] * len(resi_list))
            params = [kode_cabang] + resi_list
            rows = cursor.execute(
                f"SELECT no_resi, pengirim, penerima, kota_tujuan, nama_barang, koli, berat, cbm FROM data_resi WHERE kode_cabang = ? AND no_resi IN ({placeholders})",
                params).fetchall()
            return rows
        finally:
            if conn:
                conn.close()


def ambil_resi_list_by_manifest(manifest_id, kode_cabang):
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            rows = cursor.execute("SELECT no_resi FROM data_resi WHERE no_manifest = ? AND kode_cabang = ?",
                                  (manifest_id, kode_cabang)).fetchall()
            return [r[0] for r in rows]
        finally:
            if conn:
                conn.close()


# ==============================================================================
# 🧾 TAB INVOICE (TAGIHAN & TEMPLATE JSON)
# ==============================================================================

def dapatkan_sequence_invoice_baru(prefix):
    """Mendapatkan nomor urut invoice berikutnya berdasarkan prefix."""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            count = cursor.execute(
                "SELECT COUNT(*) FROM invoice_header WHERE no_invoice LIKE ?",
                (f"{prefix}%",)
            ).fetchone()[0]
            return int(count) + 1
        except Exception as e:
            logger.error(f"[Invoice] Gagal generate sequence: {e}")
            return 1
        finally:
            if conn:
                conn.close()


def simpan_atau_update_invoice(header, items, is_update=False):
    """Menyimpan invoice baru atau memperbarui invoice lama."""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")

            from datetime import datetime
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            no_invoice = header["no_invoice"]

            if is_update:
                cursor.execute("""
                    UPDATE invoice_header
                    SET tanggal = ?, client = ?, tipe_invoice = ?, jenis_pajak = ?, subtotal = ?, 
                        total_akhir = ?, status = ?, metadata_json = ?, template_version = ?, updated_at = ?
                    WHERE no_invoice = ?
                """, (
                    header["tanggal"], header["client"], header["tipe_invoice"], header["jenis_pajak"],
                    header["subtotal"], header["total_akhir"], header["status"], header["metadata_json"],
                    header["template_version"], now, no_invoice
                ))
                # Hapus detail lama untuk diganti yang baru
                cursor.execute("DELETE FROM invoice_detail WHERE no_invoice = ?", (no_invoice,))
            else:
                # Cek duplikasi
                existing = cursor.execute("SELECT 1 FROM invoice_header WHERE no_invoice = ?", (no_invoice,)).fetchone()
                if existing:
                    return False, "Nomor invoice sudah digunakan."

                cursor.execute("""
                    INSERT INTO invoice_header
                    (no_invoice, tanggal, client, tipe_invoice, jenis_pajak, subtotal, total_akhir, 
                     status, created_at, metadata_json, template_version, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    no_invoice, header["tanggal"], header["client"], header["tipe_invoice"], header["jenis_pajak"],
                    header["subtotal"], header["total_akhir"], header["status"], now, header["metadata_json"],
                    header["template_version"], now
                ))

            # Insert detail item
            for item in items:
                cursor.execute("""
                    INSERT INTO invoice_detail (no_invoice, nomor_urut, data_kolom, nominal_subtotal)
                    VALUES (?, ?, ?, ?)
                """, (no_invoice, item["nomor_urut"], item["data_kolom"], item["nominal"]))

            conn.commit()
            return True, "Sukses"

        except Exception as e:
            if conn: conn.rollback()
            logger.error(f"[Invoice] Gagal simpan/update: {e}")
            return False, str(e)
        finally:
            if conn:
                conn.close()


def ambil_histori_invoice(limit=300):
    """Mengambil daftar histori invoice untuk tabel sebelah kiri."""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            return conn.execute(
                "SELECT no_invoice, tanggal, client, status FROM invoice_header ORDER BY id DESC LIMIT ?",
                (limit,)
            ).fetchall()
        except Exception as e:
            logger.error(f"[Invoice] Gagal ambil histori: {e}")
            return []
        finally:
            if conn:
                conn.close()


def ambil_invoice_by_no(no_invoice):
    """Membaca data lengkap invoice (header & detail) untuk ditampilkan ke editor."""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            header = conn.execute(
                "SELECT client, tipe_invoice, jenis_pajak, status, tanggal, metadata_json FROM invoice_header WHERE no_invoice = ?",
                (no_invoice,)
            ).fetchone()

            if not header:
                return None, None

            details = conn.execute(
                "SELECT data_kolom FROM invoice_detail WHERE no_invoice = ? ORDER BY nomor_urut ASC",
                (no_invoice,)
            ).fetchall()

            return header, details
        except Exception as e:
            logger.error(f"[Invoice] Gagal baca detail invoice: {e}")
            return None, None
        finally:
            if conn:
                conn.close()


# ==============================================================================
# 👥 TAB INDUK: KONTAK & ARMADA (MENU MASTER DATA BARU)
# ==============================================================================

# --- 📁 SUB-TAB: MASTER PENGIRIM (SHIPPER) ---

def ambil_semua_master_pengirim(kode_cabang):
    """Menarik semua data pelanggan tetap pengirim di cabang saat ini"""
    conn = None
    try:
        kode_cabang = str(kode_cabang or CURRENT_SESSION.get('kode_cabang', 'PUSAT')).strip()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id_pengirim,
                kode_cabang,
                COALESCE(nama, '') AS nama,
                COALESCE(no_hp, '') AS no_hp,
                COALESCE(alamat, '') AS alamat,
                COALESCE(kota, '') AS kota
            FROM master_pengirim
            WHERE kode_cabang = ?
            ORDER BY TRIM(COALESCE(nama, '')) COLLATE NOCASE ASC
        """, (kode_cabang,))

        rows = cursor.fetchall()
        return rows

    except Exception as e:
        print(f"[Master Pengirim] Gagal mengambil data: {e}")
        return []

    finally:
        if conn:
            conn.close()


def ambil_histori_transaksi_by_pengirim(nama_pengirim, kode_cabang):
    """Melacak histori resi berdasarkan nama pengirim.
    Return dibuat 7 kolom agar sesuai dengan tabel histori SubTabPengirim:
    tanggal_masuk, no_resi, penerima, koli, berat, cbm, total_ongkir.
    """
    conn = None
    try:
        nama_pengirim = str(nama_pengirim or "").strip()
        kode_cabang = str(kode_cabang or CURRENT_SESSION.get('kode_cabang', 'PUSAT')).strip()

        if not nama_pengirim:
            return []

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT
                COALESCE(tanggal_masuk, '') AS tanggal_masuk,
                COALESCE(no_resi, '') AS no_resi,
                COALESCE(penerima, '') AS penerima,
                COALESCE(koli, 0) AS koli,
                COALESCE(berat, 0) AS berat,
                COALESCE(cbm, 0) AS cbm,
                COALESCE(total_ongkir, 0) AS total_ongkir
            FROM data_resi
            WHERE TRIM(UPPER(COALESCE(pengirim, ''))) = TRIM(UPPER(?))
              AND TRIM(UPPER(COALESCE(kode_cabang, ''))) = TRIM(UPPER(?))
            ORDER BY tanggal_masuk DESC, rowid DESC
        """, (nama_pengirim, kode_cabang))

        return cursor.fetchall()

    except Exception as e:
        print(f"[Histori Pengirim] Gagal mengambil data: {e}")
        return []

    finally:
        if conn:
            conn.close()


def update_master_pengirim_dari_tabel(id_pengirim, kode_cabang, nama, no_hp, kota, alamat):
    conn = None
    try:
        nama = str(nama or "").strip().upper()
        no_hp = str(no_hp or "").strip()
        kota = str(kota or "").strip().upper()
        alamat = str(alamat or "").strip().upper()

        if not nama:
            return False, "Nama pengirim tidak boleh kosong."

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE master_pengirim
            SET nama = ?,
                no_hp = ?,
                kota = ?,
                alamat = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_pengirim = ?
              AND kode_cabang = ?
        """, (nama, no_hp if no_hp else None, kota, alamat, id_pengirim, kode_cabang))

        conn.commit()
        return True, ""

    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e)

    finally:
        if conn:
            conn.close()


# --- 📁 SUB-TAB: MASTER PENERIMA (CONSIGNEE) ---

def ambil_semua_master_penerima(kode_cabang):
    """Menarik semua data pelanggan tetap penerima di cabang saat ini untuk ditampilkan di tabel"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        # Menembak ke tabel master_penerima sesuai struktur database_manager.py
        cursor.execute("""
            SELECT id_penerima, kode_cabang, nama, no_hp, alamat, kota 
            FROM master_penerima 
            WHERE kode_cabang = ?
            ORDER BY nama ASC
        """, (kode_cabang,))
        rows = cursor.fetchall()
        return rows
    finally:
        if conn:
            conn.close()


def ambil_histori_transaksi_by_penerima(nama_penerima, kode_cabang):
    """(Opsional) Melacak seluruh histori resi kargo yang pernah diterima oleh penerima ini"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT tanggal_masuk, no_resi, pengirim, koli, berat, cbm, kota_asal, total_ongkir 
            FROM data_resi 
            WHERE penerima = ? AND kode_cabang = ?
            ORDER BY tanggal_masuk DESC, rowid DESC
        """, (nama_penerima, kode_cabang))
        rows = cursor.fetchall()
        return rows
    finally:
        if conn:
            conn.close()


def ambil_semua_master_penerima_full(kode_cabang):
    """Menarik data lengkap penerima untuk keperluan render tabel UI"""
    conn = None
    try:
        kode_cabang = str(kode_cabang or CURRENT_SESSION.get('kode_cabang', 'PUSAT')).strip()

        pastikan_kolom_provinsi_master_penerima()

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                id_penerima,
                COALESCE(nama, '') AS nama,
                COALESCE(no_hp, '') AS no_hp,
                COALESCE(alamat, '') AS alamat,
                COALESCE(kota, '') AS kota,                
                COALESCE(provinsi, '') AS provinsi,                
                (SELECT COUNT(*) FROM data_resi WHERE TRIM(UPPER(penerima)) = TRIM(UPPER(master_penerima.nama)) AND kode_cabang = master_penerima.kode_cabang) AS total_transaksi,
                COALESCE(pembayaran, 'TF / INVOICE') AS pembayaran,
                COALESCE(status_tagihan, 'NORMAL') AS status_tagihan
            FROM master_penerima
            WHERE kode_cabang = ?
            ORDER BY TRIM(COALESCE(nama, '')) COLLATE NOCASE ASC
        """, (kode_cabang,))

        rows = cursor.fetchall()
        return rows

    except Exception as e:
        print(f"[Master Penerima] Gagal mengambil data: {e}")
        return []

    finally:
        if conn:
            conn.close()


def ubah_status_tagihan_penerima(id_penerima, status_baru, kode_cabang):
    """Mengubah status blacklist/normal penerima langsung dari data master"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE master_penerima 
            SET status_tagihan = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE id_penerima = ? AND kode_cabang = ?
        """, (status_baru, id_penerima, kode_cabang))
        conn.commit()
    except Exception as e:
        if conn: conn.rollback()
        print(f"[Ubah Status Pembayaran] Error: {e}")
    finally:
        if conn:
            conn.close()


def update_master_penerima_dari_tabel(id_penerima, kode_cabang, nama, no_hp, alamat, kota, provinsi, pembayaran):
    conn = None
    try:
        id_penerima = str(id_penerima or "").strip()
        kode_cabang = str(kode_cabang or CURRENT_SESSION.get('kode_cabang', 'PUSAT')).strip()
        nama = str(nama or "").strip().upper()
        no_hp = str(no_hp or "").strip()
        alamat = str(alamat or "").strip().upper()
        kota = str(kota or "").strip().upper()
        provinsi = str(provinsi or "").strip().upper()
        pembayaran = str(pembayaran or "TF / INVOICE").strip().upper()

        if not nama:
            return False, "Nama penerima tidak boleh kosong."

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE master_penerima
            SET nama = ?,
                no_hp = ?,
                alamat = ?,
                kota = ?,
                provinsi = ?,
                pembayaran = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id_penerima = ?
              AND kode_cabang = ?
        """, (
            nama,
            no_hp if no_hp else None,
            alamat,
            kota,
            provinsi if provinsi else None,
            pembayaran,
            id_penerima,
            kode_cabang
        ))

        conn.commit()
        return True, ""

    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e)

    finally:
        if conn:
            conn.close()


def pastikan_kolom_provinsi_master_penerima():
    """
    Menambahkan kolom provinsi pada master_penerima jika belum ada.
    Kolom ini dipakai untuk autofill propinsi di Tab Resi.
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        try:
            cursor.execute("SELECT provinsi FROM master_penerima LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute("ALTER TABLE master_penerima ADD COLUMN provinsi TEXT;")
            conn.commit()
            print("[Init DB] Kolom provinsi berhasil ditambahkan ke master_penerima.")

        return True

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[Init DB] Gagal cek/tambah kolom provinsi master_penerima: {e}")
        return False

    finally:
        if conn:
            conn.close()


# --- 📁 SUB-TAB: DATA ARMADA TRUK & SOPIR ---

def simpan_atau_update_armada(db_name, no_polisi, nama_sopir, jenis_truk, hp_sopir, ket_armada, foto_armada=""):
    '''Menambah atau memperbarui Armada berdasarkan nomor polisi tanpa menimpa data lama dengan nilai kosong.'''
    if not db_name:
        db_name = CURRENT_SESSION.get('db_name', 'database_cargo.db')

    nopol = str(no_polisi or '').strip().upper()
    sopir = str(nama_sopir or '').strip().upper()
    jenis = str(jenis_truk or '').strip()
    hp = str(hp_sopir or '').strip()
    ket = str(ket_armada or '').strip().upper()
    foto = str(foto_armada or '').strip()

    if not nopol:
        return False, "No. Polisi wajib diisi."
    if not jenis:
        return False, "Jenis truk wajib diisi."

    conn = None
    try:
        conn = sqlite3.connect(db_name, timeout=20.0)
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT 1 FROM armada WHERE no_polisi = ?", (nopol,))
        ada = cursor.fetchone()

        if ada:
            cursor.execute('''
                UPDATE armada
                SET nama_sopir = CASE WHEN TRIM(?) <> '' THEN ? ELSE nama_sopir END,
                    jenis_truk = CASE WHEN TRIM(?) <> '' THEN ? ELSE jenis_truk END,
                    hp_sopir = CASE WHEN TRIM(?) <> '' THEN ? ELSE hp_sopir END,
                    ket_armada = CASE WHEN TRIM(?) <> '' THEN ? ELSE ket_armada END,
                    foto_armada = CASE WHEN TRIM(?) <> '' THEN ? ELSE foto_armada END,
                    is_synced = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE no_polisi = ?
            ''', (sopir, sopir, jenis, jenis, hp, hp, ket, ket, foto, foto, nopol))
        else:
            cursor.execute('''
                INSERT INTO armada (
                    no_polisi, nama_sopir, jenis_truk, hp_sopir,
                    ket_armada, foto_armada, is_synced, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
            ''', (nopol, sopir, jenis, hp, ket, foto))

        conn.commit()
        return True, ""
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e)
    finally:
        if conn:
            conn.close()

def ambil_semua_armada(db_name=None):
    """Menampilkan list semua unit truk terdaftar di menu manajemen armada"""
    if not db_name:
        db_name = CURRENT_SESSION.get('db_name', 'database_cargo.db')

    conn = None
    try:
        conn = sqlite3.connect(db_name, timeout=20.0)
        cursor = conn.cursor()

        cursor.execute(
            "SELECT no_polisi, nama_sopir, jenis_truk, hp_sopir, ket_armada FROM armada ORDER BY no_polisi ASC")
        data = cursor.fetchall()
        return data
    finally:
        if conn:
            conn.close()


def migrasi_cek_kolom_armada():
    '''
    Memastikan kolom pendukung Master Armada tersedia.

    Database masih tahap trial, sehingga perubahan NOT NULL nama_sopir diterapkan melalui
    database_manager.py saat database dibuat ulang. Fungsi ini tetap menjaga kompatibilitas
    bila file database uji lama masih sempat dibuka.
    '''
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(armada)")
        info_kolom = cursor.fetchall()
        columns = [info[1] for info in info_kolom]

        if not columns:
            return False

        if 'ket_armada' not in columns:
            cursor.execute("ALTER TABLE armada ADD COLUMN ket_armada TEXT")
            if 'keterangan' in columns:
                cursor.execute('''
                    UPDATE armada
                    SET ket_armada = keterangan
                    WHERE TRIM(COALESCE(ket_armada, '')) = ''
                      AND TRIM(COALESCE(keterangan, '')) <> ''
                ''')

        if 'foto_armada' not in columns:
            cursor.execute("ALTER TABLE armada ADD COLUMN foto_armada TEXT")

        conn.commit()
        return True
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"[Migration Fallback] Info armada: {e}")
        return False
    finally:
        if conn:
            conn.close()

def ambil_semua_armada_full():
    """Menarik semua kolom data armada kargo terdaftar untuk di-render ke UI"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT no_polisi, jenis_truk, nama_sopir, hp_sopir, ket_armada, foto_armada 
            FROM armada 
            ORDER BY no_polisi ASC
        """)
        data = cursor.fetchall()
        return data
    finally:
        if conn:
            conn.close()


def simpan_atau_update_armada_full(nopol, jenis, sopir, hp, ket, foto, mode="TAMBAH"):
    '''
    Menyimpan Master Armada dari tab Armada.

    - TAMBAH: menolak nomor polisi yang sudah ada agar tidak overwrite diam-diam.
    - EDIT: memperbarui baris terpilih; nama sopir boleh kosong.
    '''
    nopol = str(nopol or '').strip().upper()
    jenis = str(jenis or '').strip()
    sopir = str(sopir or '').strip().upper()
    hp = str(hp or '').strip()
    ket = str(ket or '').strip().upper()
    foto = str(foto or '').strip()
    mode = str(mode or 'TAMBAH').strip().upper()

    if not nopol:
        return False, "No. Polisi wajib diisi."
    if not jenis:
        return False, "Jenis truk wajib diisi."

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("BEGIN IMMEDIATE")
        cursor.execute("SELECT 1 FROM armada WHERE no_polisi = ?", (nopol,))
        ada = cursor.fetchone() is not None

        if mode == 'TAMBAH':
            if ada:
                conn.rollback()
                return False, f"No. Polisi {nopol} sudah terdaftar. Gunakan menu Edit untuk memperbarui data."

            cursor.execute('''
                INSERT INTO armada (
                    no_polisi, jenis_truk, nama_sopir, hp_sopir,
                    ket_armada, foto_armada, is_synced, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, 0, CURRENT_TIMESTAMP)
            ''', (nopol, jenis, sopir, hp, ket, foto))

        elif mode == 'EDIT':
            if not ada:
                conn.rollback()
                return False, f"Data Armada {nopol} tidak ditemukan."

            cursor.execute('''
                UPDATE armada
                SET jenis_truk = ?,
                    nama_sopir = ?,
                    hp_sopir = ?,
                    ket_armada = ?,
                    foto_armada = ?,
                    is_synced = 0,
                    updated_at = CURRENT_TIMESTAMP
                WHERE no_polisi = ?
            ''', (jenis, sopir, hp, ket, foto, nopol))
        else:
            conn.rollback()
            return False, f"Mode penyimpanan Armada tidak dikenal: {mode}"

        conn.commit()
        return True, ""
    except Exception as e:
        if conn:
            conn.rollback()
        return False, str(e)
    finally:
        if conn:
            conn.close()


# ==============================================================================
# ⚙️ TAB SETTING SISTEM
# ==============================================================================

def ambil_semua_data_cabang(limit=10):
    """Mengambil daftar kantor cabang dari database."""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT kode_cabang, nama_cabang, resi_prefix, start_seq_json, aturan_prefix FROM data_cabang LIMIT ?",
                (limit,)
            )
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"[Setting] Gagal ambil data cabang: {e}")
            return []
        finally:
            if conn:
                conn.close()


def simpan_semua_pengaturan_dan_cabang(settings_to_save, branches_to_save):
    """Menyimpan seluruh konfigurasi sistem dan data cabang secara atomic."""
    if USE_CLOUD:
        pass
    else:
        conn = None
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("BEGIN IMMEDIATE")

            # 1. Simpan Pengaturan Sistem
            for kunci, nilai in settings_to_save:
                cursor.execute(
                    "INSERT OR REPLACE INTO pengaturan_sistem (kunci, nilai) VALUES (?, ?)",
                    (kunci, nilai)
                )

            # 2. Simpan Data Cabang
            for b in branches_to_save:
                cursor.execute("""
                    INSERT OR REPLACE INTO data_cabang 
                    (kode_cabang, nama_cabang, resi_prefix, start_seq_json, aturan_prefix)
                    VALUES (?, ?, ?, ?, ?)
                """, (b['kode_cabang'], b['nama_cabang'], b['resi_prefix'], b['start_seq_json'], b['aturan_prefix']))

            conn.commit()
            return True, "Sukses"
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"[Setting] Gagal simpan pengaturan: {e}")
            return False, str(e)
        finally:
            if conn:
                conn.close()