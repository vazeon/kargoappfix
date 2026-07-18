# init_db_mahkota.py
import sqlite3
import os

DB_NAME = "database_cargo.db"

def generate_mahkota_environment():
    """Menghapus DB lama dan membuat ulang khusus ekosistem Mahkota Kargo (100% Supabase-Ready)"""
    if os.path.exists(DB_NAME):
        try:
            os.remove(DB_NAME)
            print(f"🗑️ Database lama '{DB_NAME}' berhasil dihapus.")
        except Exception as e:
            print(f"⚠️ Gagal menghapus database: {e}")
            return

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    print(f"📁 Database baru '{DB_NAME}' berhasil dibuat.")

    try:
        # 1. TABEL PENGATURAN
        cursor.execute('CREATE TABLE IF NOT EXISTS pengaturan_sistem (kunci TEXT PRIMARY KEY, nilai TEXT)')

        data_pengaturan = [
            ('pt_name', 'PT MAHKOTA KARGO LOGISTIK'),
            ('rekening_pajak', '["BCA, 829 257 2980, PT MAHKOTA KARGO LOGISTIK"]'),
            ('rekening_nonpajak',
             '["MANDIRI, 141 001 991 2963, REGGY ANITA RIANDA", "BCA, 187 064 1628, REGGY ANITA RIANDA"]'),
            ('format_resi_manual', '0'),
            ('template_no_resi', '[PREFIX][COUNTER][SUFFIX]'),
            ('kode_akhiran_pajak', '-P'),
            ('prefix_invoice', 'INV-MKT'),
            ('provinsi_tujuan', '["KALIMANTAN TIMUR", "KALIMANTAN SELATAN", "PROVINSI LAINNYA"]')
        ]

        cursor.executemany("INSERT INTO pengaturan_sistem VALUES (?, ?)", data_pengaturan)

        # 2. TABEL CABANG
        cursor.execute('''CREATE TABLE IF NOT EXISTS data_cabang (
            kode_cabang TEXT PRIMARY KEY,
            nama_cabang TEXT NOT NULL,
            resi_prefix TEXT NOT NULL,
            start_seq_json TEXT DEFAULT '{}',
            aturan_prefix TEXT DEFAULT '{"DEFAULT": "INV"}'
        )''')

        aturan_sby = '{"KALIMANTAN TIMUR": "KT", "KALIMANTAN SELATAN": "KS", "DEFAULT": "IND"}'
        aturan_jkt = '{"KALIMANTAN TIMUR": "J-KT", "KALIMANTAN SELATAN": "J-KS", "DEFAULT": "J-IND"}'
        seq_sby = '{"KT": 18000, "KS": 5000, "DEFAULT": 1000}'
        seq_jkt = '{"J-KT": 8000, "J-KS": 4000, "DEFAULT": 1000}'

        cabang_mahkota = [
            ('SBY', 'SURABAYA (PUSAT)', 'MKT', seq_sby, aturan_sby),
            ('JKT', 'JAKARTA (CABANG)', 'MKTJ', seq_jkt, aturan_jkt)
        ]
        cursor.executemany("INSERT INTO data_cabang VALUES (?, ?, ?, ?, ?)", cabang_mahkota)

        # 3. TABEL USER
        cursor.execute('''CREATE TABLE IF NOT EXISTS manajemen_user (
            id_user INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            role TEXT DEFAULT 'ADMIN',
            nama_lengkap TEXT,
            kode_cabang TEXT NOT NULL,
            FOREIGN KEY (kode_cabang) REFERENCES data_cabang (kode_cabang)
        )''')

        akun_mahkota = [
            ('SUPER', '123', 'SUPER_ADMIN', 'OWNER MAHKOTA', 'SBY'),
            ('ADMINSBY', '123', 'ADMIN', 'STAFF SBY', 'SBY'),
            ('ADMINJKT', '123', 'ADMIN', 'STAFF JKT', 'JKT')
        ]
        cursor.executemany("INSERT INTO manajemen_user (username, password, role, nama_lengkap, kode_cabang) VALUES (?, ?, ?, ?, ?)", akun_mahkota)

        # 4. TABEL RESI
        cursor.execute('''CREATE TABLE IF NOT EXISTS data_resi (
            no_resi TEXT PRIMARY KEY,
            kode_cabang TEXT NOT NULL,
            tanggal_masuk DATE,
            tanggal_keluar DATE,
            pengirim TEXT,
            hp_pengirim TEXT,
            alamat_pengirim TEXT,
            kota_asal TEXT,
            penerima TEXT,
            hp_penerima TEXT,
            alamat_penerima TEXT,
            kota_tujuan TEXT,
            nama_barang TEXT,
            koli TEXT,
            berat REAL,
            cbm REAL,
            ongkir_per_kg INTEGER,
            ongkir_per_cbm INTEGER,
            total_ongkir INTEGER,
            pembayaran TEXT,
            status_resi TEXT,
            foto_bukti TEXT,
            armada TEXT,
            ket_buku_gudang TEXT,
            no_manifest TEXT,
            ket_manifest TEXT,
            rincian_json TEXT,
            is_synced INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kode_cabang) REFERENCES data_cabang (kode_cabang)
        )''')

        # 5. TABEL BUKU GUDANG
        cursor.execute('''CREATE TABLE IF NOT EXISTS buku_gudang (
            id_gudang TEXT PRIMARY KEY,
            kode_cabang TEXT NOT NULL,
            tanggal DATE,
            no_resi TEXT,
            jenis TEXT,
            status_resi TEXT,
            is_synced INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kode_cabang) REFERENCES data_cabang (kode_cabang)
        )''')

        # 6. TABEL MANIFEST
        cursor.execute('''CREATE TABLE IF NOT EXISTS manifest (
            id_manifest TEXT PRIMARY KEY,
            kode_cabang TEXT NOT NULL,
            tanggal DATE,
            no_armada TEXT,
            supir TEXT,
            status_kirim TEXT,
            is_synced INTEGER DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kode_cabang) REFERENCES data_cabang (kode_cabang)
        )''')

        # 7. Tabel Invoice (Diperbarui untuk mendukung template Dinamis / JSON)
        cursor.execute('''CREATE TABLE IF NOT EXISTS invoice_header (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            no_invoice TEXT UNIQUE NOT NULL,
            tanggal TEXT NOT NULL,
            client TEXT NOT NULL,
            tipe_invoice TEXT NOT NULL,
            jenis_pajak TEXT NOT NULL,
            subtotal INTEGER NOT NULL DEFAULT 0,
            total_akhir INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'DRAFT',
            created_at TEXT NOT NULL,
            metadata_json TEXT NOT NULL DEFAULT '{}',
            template_version INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT
        )''')

        cursor.execute('''CREATE TABLE IF NOT EXISTS invoice_detail (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            no_invoice TEXT NOT NULL,
            nomor_urut INTEGER NOT NULL,
            data_kolom TEXT NOT NULL,
            nominal_subtotal INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY(no_invoice) REFERENCES invoice_header(no_invoice) ON DELETE CASCADE
        )''')

        # 8. TABEL MASTER PENGIRIM
        cursor.execute('''CREATE TABLE IF NOT EXISTS master_pengirim (
            id_pengirim TEXT PRIMARY KEY, 
            kode_cabang TEXT NOT NULL,
            nama TEXT,
            no_hp TEXT,
            kota TEXT,
            alamat TEXT,
            is_synced INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        # 9. TABEL MASTER PENERIMA
        cursor.execute('''CREATE TABLE IF NOT EXISTS master_penerima (
            id_penerima TEXT PRIMARY KEY, 
            kode_cabang TEXT NOT NULL,
            nama TEXT,
            no_hp TEXT,
            alamat TEXT,
            kota TEXT,
            provinsi TEXT,
            total_transaksi INTEGER DEFAULT 0,
            pembayaran TEXT DEFAULT 'TF / INVOICE',
            status_tagihan TEXT DEFAULT 'NORMAL',
            is_synced INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (kode_cabang) REFERENCES data_cabang (kode_cabang)
        )''')

        # 10. TABEL ARMADA
        cursor.execute('''CREATE TABLE IF NOT EXISTS armada (
            jenis_truk TEXT NOT NULL,
            no_polisi TEXT PRIMARY KEY,
            nama_sopir TEXT NOT NULL,                        
            hp_sopir TEXT,
            ket_armada TEXT,
            foto_armada TEXT,                        
            is_synced INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')

        conn.commit()
        print("✨ EKOSISTEM MAHKOTA KARGO 100% SUPABASE-READY BERHASIL DI-GENERATE!")

    except Exception as e:
        print(f"❌ Terjadi kesalahan: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    generate_mahkota_environment()