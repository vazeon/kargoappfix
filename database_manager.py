# database_manager.py
import sqlite3
import json

def init_db(db_name="database_cargo.db"):
    """Hanya membangun struktur database (Tabel). Tidak ada data default yang dipaksa masuk."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()

    # 1. Tabel Pengaturan
    cursor.execute('''CREATE TABLE IF NOT EXISTS pengaturan_sistem (
                        kunci TEXT PRIMARY KEY,
                        nilai TEXT)''')

    # 2. Tabel Cabang
    cursor.execute('''CREATE TABLE IF NOT EXISTS data_cabang (
                        kode_cabang TEXT PRIMARY KEY,
                        nama_cabang TEXT NOT NULL,
                        resi_prefix TEXT NOT NULL,
                        start_seq_json TEXT DEFAULT '{"DEFAULT": 1000}',
                        aturan_prefix TEXT DEFAULT '{"DEFAULT": "INV"}',
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 3. Tabel User
    cursor.execute('''CREATE TABLE IF NOT EXISTS manajemen_user (
                        id_user TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT DEFAULT 'ADMIN',
                        nama_lengkap TEXT,
                        kode_cabang TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (kode_cabang) REFERENCES data_cabang (kode_cabang))''')

    # 4. Tabel Data Resi
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
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, 
                        FOREIGN KEY (kode_cabang) REFERENCES data_cabang(kode_cabang))''')

    # 5. Tabel Buku Gudang
    cursor.execute('''CREATE TABLE IF NOT EXISTS buku_gudang (
                        id_gudang TEXT PRIMARY KEY, 
                        kode_cabang TEXT NOT NULL,
                        tanggal DATE, 
                        no_resi TEXT,
                        jenis TEXT,
                        status_resi TEXT,
                        is_synced INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 6. Tabel Manifest
    cursor.execute('''CREATE TABLE IF NOT EXISTS manifest (
                        id_manifest TEXT PRIMARY KEY,
                        kode_cabang TEXT NOT NULL,
                        tanggal DATE, 
                        no_polisi TEXT,
                        nama_sopir TEXT,
                        status_manifest TEXT,
                        is_synced INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

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
                        updated_at TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS invoice_detail (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        no_invoice TEXT NOT NULL,
                        nomor_urut INTEGER NOT NULL,
                        data_kolom TEXT NOT NULL,
                        nominal_subtotal INTEGER NOT NULL DEFAULT 0,
                        FOREIGN KEY(no_invoice) REFERENCES invoice_header(no_invoice) ON DELETE CASCADE)''')
    # 8. Tabel Pengirim
    cursor.execute('''CREATE TABLE IF NOT EXISTS master_pengirim (
                        id_pengirim TEXT PRIMARY KEY, 
                        kode_cabang TEXT NOT NULL,
                        nama TEXT,
                        no_hp TEXT,
                        alamat TEXT,
                        kota TEXT,
                        is_synced INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 9. Tabel Penerima
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
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    # 10. Tabel Unit Armada
    cursor.execute('''CREATE TABLE IF NOT EXISTS armada (
                        jenis_truk TEXT NOT NULL,
                        no_polisi TEXT PRIMARY KEY,
                        nama_sopir TEXT,
                        hp_sopir TEXT,
                        ket_armada TEXT,
                        foto_armada TEXT,                        
                        is_synced INTEGER DEFAULT 0,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')

    conn.commit()
    conn.close()
    print("✅ Database (Tabel) berhasil di-load.")

def set_config(db_name, key, value):
    """Fungsi pembantu untuk menyuntikkan data klien dari luar."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    val_to_save = json.dumps(value) if isinstance(value, list) else str(value)
    cursor.execute("INSERT OR REPLACE INTO pengaturan_sistem (kunci, nilai) VALUES (?, ?)", (key, val_to_save))
    conn.commit()
    conn.close()