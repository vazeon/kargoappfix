# tabs/tab_manifest.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QComboBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QMessageBox, QApplication, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QCompleter, QMenu)
from PyQt5.QtGui import QFont, QBrush
from PyQt5.QtCore import Qt, QEvent, QSettings, QDate

from config import CURRENT_SESSION, DATA_CLIENT
from utils.printer.print_manifest import cetak_manifest_ke_printer
import services.database_service as db_service
from themes.modules.manifest import (
    get_manifest_history_date_appearance,
    get_manifest_row_highlight,
    get_manifest_styles,
)
from utils.typography import MASTER_FONT
from utils.widget_helpers import paksa_kapital_lineedit
from utils.date_ind_format import format_tanggal_ke_ui


class TabManifest(QWidget):
    KOL_CHECK = 0
    KOL_NO = 1
    KOL_RESI = 2
    KOL_TGL_MASUK = 3
    KOL_PENGIRIM = 4
    KOL_PENERIMA = 5
    KOL_TUJUAN = 6
    KOL_NAMA_BARANG = 7
    KOL_KOLI = 8
    KOL_BERAT = 9
    KOL_CBM = 10
    KOL_ONGKIR = 11
    KOL_KET = 12

    def __init__(self):
        super().__init__()
        self.is_edit_mode = False
        self.edit_manifest_id = ""
        self.init_ui()

    def init_ui(self):
        layout_utama = QHBoxLayout(self)
        layout_utama.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Qt.Horizontal)
        layout_utama.addWidget(self.splitter)

        self.panel_kiri = QWidget()
        layout_kiri = QVBoxLayout(self.panel_kiri)

        self.lbl_title = QLabel("📦 Pembuatan Manifest Pengiriman")
        layout_kiri.addWidget(self.lbl_title)

        hbox_top = QHBoxLayout()
        hbox_top.addWidget(QLabel("Nomor:"))
        self.txt_no_manifest = QLineEdit()
        self.txt_no_manifest.setReadOnly(True)
        self.txt_no_manifest.setFixedWidth(100)
        hbox_top.addWidget(self.txt_no_manifest)

        hbox_top.addWidget(QLabel("Tujuan:"))
        self.cb_filter_wilayah = QComboBox()
        self.cb_filter_wilayah.addItems(DATA_CLIENT.get('provinsi_tujuan', ["PROVINSI A", "PROVINSI B", "PROVINSI C"]))
        self.cb_filter_wilayah.setFixedWidth(180)
        self.cb_filter_wilayah.currentTextChanged.connect(self.on_wilayah_changed)
        hbox_top.addWidget(self.cb_filter_wilayah)

        # 1. ComboBox Jenis Truk (Armada) dengan Placeholder
        hbox_top.addWidget(QLabel("Armada:"))
        self.cb_jenis_truk = QComboBox()
        self.cb_jenis_truk.addItem("- Pilih jenis -")  # Index 0 sebagai placeholder
        self.cb_jenis_truk.addItems(["TB", "Tronton", "CDD", "Pick-up"])
        self.cb_jenis_truk.setFixedWidth(120)

        # --- BIKIN PLACEHOLDER SAJA YANG ITALIC ---
        def ubah_font_placeholder(idx):
            # Ubah font kotak utama (tampilan depan) agar italic HANYA saat index 0 dipilih
            font_utama = self.cb_jenis_truk.font()
            font_utama.setItalic(idx == 0)
            self.cb_jenis_truk.setFont(font_utama)

            # Pastikan item ke-0 ("Armada...") di dalam list dropdown selalu italic
            font_italic = QFont(font_utama)
            font_italic.setItalic(True)
            self.cb_jenis_truk.setItemData(0, font_italic, Qt.FontRole)

            # Pastikan item lainnya (TB, Tronton, dll) di dalam list TETAP NORMAL
            font_normal = QFont(font_utama)
            font_normal.setItalic(False)
            for i in range(1, self.cb_jenis_truk.count()):
                self.cb_jenis_truk.setItemData(i, font_normal, Qt.FontRole)

        # Hubungkan fungsi dan jalankan sekali di awal
        self.cb_jenis_truk.currentIndexChanged.connect(ubah_font_placeholder)
        ubah_font_placeholder(0)
        # --------------------------------

        hbox_top.addWidget(self.cb_jenis_truk)

        # 2. Input No. Pol (Opsional)
        self.txt_no_pol = QLineEdit()
        self.txt_no_pol.setPlaceholderText("No. Pol")
        self.txt_no_pol.setFixedWidth(100)
        self.txt_no_pol.textChanged.connect(lambda: paksa_kapital_lineedit(self.txt_no_pol))
        hbox_top.addWidget(self.txt_no_pol)

        # 3. Input Nama Sopir (Wajib jika armada dipilih)
        self.txt_sopir = QLineEdit()
        self.txt_sopir.setPlaceholderText("Nama Sopir")
        self.txt_sopir.setFixedWidth(130)
        self.txt_sopir.textChanged.connect(lambda: paksa_kapital_lineedit(self.txt_sopir))
        hbox_top.addWidget(self.txt_sopir)

        self.txt_keterangan = QLineEdit()
        self.txt_keterangan.setPlaceholderText("Keterangan")
        self.txt_keterangan.setFixedWidth(150)
        self.txt_keterangan.textChanged.connect(lambda: paksa_kapital_lineedit(self.txt_keterangan))
        hbox_top.addWidget(self.txt_keterangan)

        hbox_top.addStretch()
        self.btn_proses = QPushButton("⚡ BUAT MANIFEST")
        self.btn_proses.setCursor(Qt.PointingHandCursor)
        hbox_top.addWidget(self.btn_proses)

        self.btn_batal_edit = QPushButton("❌ BATAL")
        self.btn_batal_edit.setCursor(Qt.PointingHandCursor)
        self.btn_batal_edit.clicked.connect(self.batal_edit)
        self.btn_batal_edit.hide()
        hbox_top.addWidget(self.btn_batal_edit)
        layout_kiri.addLayout(hbox_top)

        self.tabel_manifest = QTableWidget()
        self.tabel_manifest.setColumnCount(13)  # Ubah dari 11 ke 13
        self.tabel_manifest.setHorizontalHeaderLabels(
            ["✔", "NO.", "RESI", "TGL MASUK", "PENGIRIM", "PENERIMA", "TUJUAN", "NAMA BARANG", "KOLI", "BERAT (kg)",
             "KUBIK (m3)", "TOTAL ONGKIR", "KETERANGAN"])
        self.tabel_manifest.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabel_manifest.verticalHeader().setVisible(False)
        self.tabel_manifest.setAlternatingRowColors(True)

        self.load_lebar_kolom(self.tabel_manifest)
        self.tabel_manifest.horizontalHeader().sectionResized.connect(
            lambda: self.simpan_lebar_kolom(self.tabel_manifest))
        layout_kiri.addWidget(self.tabel_manifest)

        self.panel_kanan = QWidget()
        layout_kanan = QVBoxLayout(self.panel_kanan)
        layout_kanan.addWidget(QLabel("🕒 Histori Manifest:"))

        hbox_filter = QHBoxLayout()
        hbox_filter.addWidget(QLabel("Tahun:"))
        self.cb_tahun_filter = QComboBox()
        self.cb_tahun_filter.setFixedWidth(80)
        self.cb_tahun_filter.currentTextChanged.connect(self.load_histori)
        hbox_filter.addWidget(self.cb_tahun_filter)

        self.txt_cari_histori = QLineEdit()
        self.txt_cari_histori.setPlaceholderText("Cari manifest...")
        self.txt_cari_histori.textChanged.connect(lambda: paksa_kapital_lineedit(self.txt_cari_histori))
        self.txt_cari_histori.textChanged.connect(self.filter_histori)
        hbox_filter.addWidget(self.txt_cari_histori)
        layout_kanan.addLayout(hbox_filter)

        self.list_histori = QTreeWidget()
        self.list_histori.setColumnCount(2)
        self.list_histori.setHeaderHidden(True)
        self.list_histori.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.list_histori.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.list_histori.itemDoubleClicked.connect(self.preview_histori_manifest)
        self.list_histori.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_histori.customContextMenuRequested.connect(self.buka_menu_klik_kanan_histori)
        layout_kanan.addWidget(self.list_histori)

        self.splitter.addWidget(self.panel_kiri)
        self.splitter.addWidget(self.panel_kanan)
        self.splitter.setSizes([800, 200])

        self.btn_proses.clicked.connect(self.update_armada_ke_manifest)
        self.refresh_tahun_filter()
        self.load_data_resi_gudang()
        self.generate_no_manifest()
        self.sesuaikan_tema_lokal()
        self.setup_autocomplete_armada()

    def setup_autocomplete_armada(self):
        try:
            # Ambil data dari database
            rows = db_service.ambil_armada_list()
            # Ambil hanya nama sopir dan hilangkan duplikat
            sopirs = list(set([row[1] for row in rows if row[1]]))

            # Setup khusus untuk input Nama Sopir
            self.completer_sopir = QCompleter(sopirs, self)
            self.completer_sopir.setCaseSensitivity(Qt.CaseInsensitive)
            self.txt_sopir.setCompleter(self.completer_sopir)

            # Trigger saat nama sopir dipilih/di-enter
            self.completer_sopir.activated.connect(self.on_sopir_selected)

            # Pastikan Nopol TIDAK memiliki autocomplete (sesuai rule)
            self.txt_no_pol.setCompleter(None)
        except Exception as e:
            print(f"Gagal memuat autocomplete armada: {e}")

    def on_sopir_selected(self, sopir):
        row = db_service.ambil_detail_armada_by_sopir(sopir)
        if row:
            no_polisi = row[0]
            jenis_truk = row[1]

            # Autofill Nomor Polisi
            if no_polisi:
                self.txt_no_pol.setText(no_polisi)

            # Autofill Jenis Truk di ComboBox
            if jenis_truk:
                idx = self.cb_jenis_truk.findText(jenis_truk, Qt.MatchFixedString)
                if idx >= 0:
                    self.cb_jenis_truk.setCurrentIndex(idx)
                else:
                    self.cb_jenis_truk.setCurrentText(jenis_truk)

    def generate_no_manifest(self):
        if self.is_edit_mode: self.txt_no_manifest.setText(self.edit_manifest_id); return
        prefix = f"M-{CURRENT_SESSION.get('aturan_prefix', {}).get(self.cb_filter_wilayah.currentText(), 'MF')}"
        seq = 1
        try:
            rows = db_service.ambil_no_manifest_list_by_prefix(prefix, CURRENT_SESSION.get('kode_cabang', 'PUSAT'))
            if rows: seq = max(int(r[0].split('-')[-1]) for r in rows if r[0]) + 1
        except:
            pass
        self.txt_no_manifest.setText(f"{prefix}-{seq:04d}")

    def refresh_tahun_filter(self):
        self.cb_tahun_filter.blockSignals(True);
        self.cb_tahun_filter.clear()
        self.cb_tahun_filter.addItem("Semua")
        self.cb_tahun_filter.addItem(str(QDate.currentDate().year()))
        self.cb_tahun_filter.setCurrentIndex(1);
        self.cb_tahun_filter.blockSignals(False)

    def load_data_resi_gudang(self):
        self.tabel_manifest.setRowCount(0)
        is_dark = self.window().current_theme == "dark" if self.window() and hasattr(self.window(),
                                                                                     'current_theme') else False
        try:
            rows = db_service.ambil_resi_untuk_manifest(CURRENT_SESSION.get('kode_cabang', 'PUSAT'),
                                                        self.cb_filter_wilayah.currentText(), self.is_edit_mode,
                                                        self.edit_manifest_id)
            for row in rows:
                pos = self.tabel_manifest.rowCount();
                self.tabel_manifest.insertRow(pos)
                belong = self.is_edit_mode and row[9] == self.edit_manifest_id
                bg = get_manifest_row_highlight(is_dark, belong)

                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                chk.setCheckState(Qt.Checked if belong else Qt.Unchecked)
                if bg: chk.setBackground(QBrush(bg))
                self.tabel_manifest.setItem(pos, self.KOL_CHECK, chk)

                item_no = QTableWidgetItem(str(pos + 1))
                if bg: item_no.setBackground(QBrush(bg))
                self.tabel_manifest.setItem(pos, self.KOL_NO, item_no)

                for i, d in enumerate(row[:9]):
                    val = str(d) if d is not None else ""
                    col = i + 2
                    if col == self.KOL_TGL_MASUK and val:
                        val = format_tanggal_ke_ui(val)
                    elif col == self.KOL_TUJUAN and " - " in val:
                        val = val.split(" - ")[-1]
                    elif col in [self.KOL_KOLI, self.KOL_BERAT, self.KOL_CBM]:
                        val = self.format_angka(d, "cbm" if col == self.KOL_CBM else "bulat")

                    item = QTableWidgetItem(val)
                    if col in [self.KOL_KOLI, self.KOL_BERAT, self.KOL_CBM]: item.setTextAlignment(
                        Qt.AlignRight | Qt.AlignVCenter)
                    if bg: item.setBackground(QBrush(bg))
                    self.tabel_manifest.setItem(pos, col, item)

                val_ongkir = self.format_angka(row[10], "bulat")
                item_ongkir = QTableWidgetItem(val_ongkir)
                item_ongkir.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if bg: item_ongkir.setBackground(QBrush(bg))
                self.tabel_manifest.setItem(pos, self.KOL_ONGKIR, item_ongkir)

                txt_ket_row = QLineEdit()
                txt_ket_row.setFrame(False)  # Agar menyatu dengan tabel
                txt_ket_row.setPlaceholderText("Ket...")
                if belong and row[11]:
                    txt_ket_row.setText(str(row[11]))
                self.tabel_manifest.setCellWidget(pos, self.KOL_KET, txt_ket_row)

            self.load_histori()
        except Exception as e:
            print(f"Error Load: {e}")

    def load_histori(self):
        self.list_histori.clear()

        # Deteksi tema aktif untuk menyesuaikan warna teks
        win = self.window()
        is_dark = win.current_theme == "dark" if win and hasattr(win, 'current_theme') else False

        try:
            rows = db_service.ambil_histori_manifest(CURRENT_SESSION.get('kode_cabang', 'PUSAT'),
                                                     self.cb_tahun_filter.currentText())

            # Kamus nama bulan Indonesia
            NAMA_BULAN = {
                "01": "Januari", "02": "Februari", "03": "Maret", "04": "April",
                "05": "Mei", "06": "Juni", "07": "Juli", "08": "Agustus",
                "09": "September", "10": "Oktober", "11": "November", "12": "Desember"
            }

            parents = {}
            for r in rows:
                # Ambil data mentah
                tgl_raw, m_id, armada, count = str(r[0]), str(r[1]), str(r[2]), r[3]

                # Format ke gaya Indonesia
                tgl_indo = format_tanggal_ke_ui(tgl_raw)

                # Ambil bulan untuk judul folder
                mm = tgl_indo[3:5]
                nama_bln = NAMA_BULAN.get(mm, "Unknown")

                title = f"📂 {nama_bln}"

                if title not in parents:
                    parents[title] = QTreeWidgetItem(self.list_histori)
                    parents[title].setText(0, title)

                child = QTreeWidgetItem(parents[title])

                # --- SETTING KOLOM 0 (TANGGAL) ---
                child.setText(0, tgl_indo)

                # 1. Atur font dan warna tanggal melalui modul theme.
                ukuran_dasar = self.list_histori.font().pointSize()
                font_tanggal, warna_abu = get_manifest_history_date_appearance(
                    is_dark,
                    ukuran_dasar,
                )
                child.setFont(0, font_tanggal)
                child.setForeground(0, QBrush(warna_abu))

                # --- SETTING KOLOM 1 (ID & ARMADA) ---
                # Jika armada kosong (karena opsional), sembunyikan tanda "-" agar rapi
                armada_display = f" | {armada}" if armada and armada.strip() != "-" else ""
                child.setText(1, f"{m_id}{armada_display} ({count} Resi)")

            self.list_histori.expandAll()
        except Exception as e:
            print(f"Gagal memuat histori manifest: {e}")

    def update_armada_ke_manifest(self):
        m_id = self.edit_manifest_id if self.is_edit_mode else self.txt_no_manifest.text()
        resi = []
        for r in range(self.tabel_manifest.rowCount()):
            if self.tabel_manifest.item(r, self.KOL_CHECK).checkState() == Qt.Checked:
                no_resi = self.tabel_manifest.item(r, self.KOL_RESI).text()
                widget_ket = self.tabel_manifest.cellWidget(r, self.KOL_KET)
                ket_text = widget_ket.text().strip() if widget_ket else ""
                resi.append((no_resi, ket_text))

        if not resi:
            return QMessageBox.warning(self, "Warning", "Centang minimal 1 resi!")

        # --- BACA INPUT DETAIL ARMADA ---
        armada_idx = self.cb_jenis_truk.currentIndex()
        armada_text = self.cb_jenis_truk.currentText()
        nopol = self.txt_no_pol.text().strip().upper()
        sopir = self.txt_sopir.text().strip().upper()
        keterangan = self.txt_keterangan.text().strip()

        # --- KONDISI 1: MODE TITIP MUATAN (Hanya isi keterangan saja) ---
        if keterangan and armada_idx == 0 and not sopir and not nopol:
            # Tetap sah disimpan ke manifes jalan, data armada dirangkai dari keterangan saja
            armada_full = f"{keterangan}"
            dict_update = {
                'no_polisi': "",
                'nama_sopir': "",
                'jenis_truk': "",
                'nama_armada': armada_full,
                'ket_armada': keterangan
            }

        # --- KONDISI 2: MODE ARMADA RESMI (Pilih jenis truk & isi sopir) ---
        elif armada_idx > 0:
            # Rule: Sopir Wajib jika jenis truk dipilih
            if not sopir:
                QMessageBox.warning(self, "Peringatan", "Nama Sopir wajib diisi jika jenis armada dipilih!")
                self.txt_sopir.setFocus()
                return

            nopol_val = nopol if nopol else "-"
            armada_full = f"{armada_text} - {nopol_val} - {sopir}"
            if keterangan:
                armada_full += f" ({keterangan})"

            dict_update = {
                'no_polisi': nopol,  # Nopol bisa kosong/menyusul sesuai skenario baru
                'nama_sopir': sopir,
                'jenis_truk': armada_text,
                'nama_armada': armada_full,
                'ket_armada': keterangan
            }

        # --- KONDISI 3: BELUM MENGISI APA-APA / SALAH INPUT ---
        else:
            QMessageBox.warning(self, "Peringatan",
                                "Mohon isi Keterangan (untuk titip muatan) ATAU pilih Jenis Armada & Nama Sopir!")
            return

        # Kirim payload ke database service
        sukses, err = db_service.simpan_atau_update_manifest_data(m_id, CURRENT_SESSION.get('kode_cabang', 'PUSAT'),
                                                                  dict_update, resi, self.is_edit_mode,
                                                                  QDate.currentDate().toString("yyyy-MM-dd"))
        if sukses:
            QMessageBox.information(self, "Sukses", "Manifest Berhasil diproses!")
            if self.is_edit_mode:
                self.batal_edit()
            else:
                self.cb_jenis_truk.setCurrentIndex(0)
                self.txt_no_pol.clear()
                self.txt_sopir.clear()
                self.txt_keterangan.clear()
                self.load_data_resi_gudang()
        else:
            QMessageBox.critical(self, "Error", f"Gagal: {err}")

    def preview_histori_manifest(self, item):
        if item.parent():
            teks_info = item.text(1)
            parts = teks_info.split(" | ")
            m_id = parts[0].strip()
            # Handle saat armada tidak ada
            if len(parts) > 1:
                armada = parts[1].split(" (")[0].strip()
            else:
                armada = ""
            self.siapkan_dan_cetak_dari_id(m_id, armada)

    def siapkan_dan_cetak_dari_id(self, m_id, armada):
        try:
            data = db_service.ambil_resi_detail_untuk_cetak(CURRENT_SESSION.get('kode_cabang', 'PUSAT'),
                                                            db_service.ambil_resi_list_by_manifest(m_id,
                                                                                                   CURRENT_SESSION.get(
                                                                                                       'kode_cabang',
                                                                                                       'PUSAT')))
            # Jika armada string kosong, ubah jadi "-" agar rapi di kertas struk cetak
            cetak_manifest_ke_printer(
                {'no_manifest': m_id, 'armada': armada if armada else "-",
                 'tanggal': QDate.currentDate().toString("dd/MM/yyyy"),
                 'items': [
                     (r[0], r[1], r[2], r[3].split(" - ")[-1] if " - " in r[3] else r[3], r[4], self.format_angka(r[5]),
                      self.format_angka(r[6]), self.format_angka(r[7], "cbm")) for r in data]}, self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal cetak: {e}")

    def showEvent(self, event):
        super().showEvent(event)

        self.load_data_resi_gudang()
        self.generate_no_manifest()

        # Autocomplete sudah dibuat satu kali saat init_ui().

    def sesuaikan_tema_lokal(self):
        win = self.window()
        is_dark = win.current_theme == "dark" if win and hasattr(win, 'current_theme') else False
        styles = get_manifest_styles(is_dark, self.is_edit_mode,
                                     int(QSettings("AplikasiEkspedisi", "PengaturanUI").value("zoom_TabManifest", 0)))
        self.panel_kiri.setStyleSheet(styles['panel_kiri']);
        self.panel_kanan.setStyleSheet(styles['panel_kanan'])
        self.lbl_title.setStyleSheet(styles['lbl_title']);
        self.btn_proses.setStyleSheet(styles['btn_proses'])
        self.list_histori.setStyleSheet(styles['list_histori']);
        self.tabel_manifest.setStyleSheet(styles['style_tabel'])

        # Tambahkan txt_keterangan ke daftar yang disesuaikan temanya
        for w in [self.txt_no_manifest, self.txt_no_pol, self.txt_sopir, self.txt_keterangan, self.cb_filter_wilayah,
                  self.cb_jenis_truk, self.cb_tahun_filter, self.txt_cari_histori]:
            w.setStyleSheet(styles['style_input'])


    def simpan_lebar_kolom(self, t):
        QSettings("EkspedisiApp", "TabManifest").setValue("lebar_kolom",
                                                          [t.columnWidth(i) for i in range(t.columnCount())])

    def load_lebar_kolom(self, t):
        w = QSettings("EkspedisiApp", "TabManifest").value("lebar_kolom")
        if w:
            for i, width in enumerate(w): t.setColumnWidth(i, int(width))

    def on_wilayah_changed(self):
        self.batal_edit() if self.is_edit_mode else None;
        self.generate_no_manifest();
        self.load_data_resi_gudang()

    def format_angka(self, value, jenis="bulat"):
        try:
            if value is None or str(value).strip() == "" or float(value) == 0: return "-"
            return f"{float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X",
                                                                                      ".") if jenis == "cbm" else f"{int(float(value)):,}".replace(
                ",", ".")
        except:
            return "-"

    def filter_histori(self, text):
        for i in range(self.list_histori.topLevelItemCount()):
            p = self.list_histori.topLevelItem(i);
            visible = False
            for j in range(p.childCount()):
                match = text.lower() in p.child(j).text(1).lower()
                p.child(j).setHidden(not match)
                if match: visible = True
            p.setHidden(not visible)

    def buka_menu_klik_kanan_histori(self, pos):
        item = self.list_histori.itemAt(pos)
        if not item or not item.parent(): return
        menu = QMenu()
        act_print = menu.addAction("🖨 Preview Cetak")
        act_edit = menu.addAction("✏️ Edit Workspace")
        action = menu.exec_(self.list_histori.mapToGlobal(pos))

        # Handler data kosong
        teks_info = item.text(1)
        parts = teks_info.split(" | ")
        m_id = parts[0].strip()
        armada = parts[1].split(" (")[0].strip() if len(parts) > 1 else ""

        if action == act_print:
            self.siapkan_dan_cetak_dari_id(m_id, armada)
        elif action == act_edit:
            self.aktifkan_mode_edit(m_id, armada)

    def aktifkan_mode_edit(self, m_id, armada_str):
        self.is_edit_mode = True;
        self.edit_manifest_id = m_id

        # Kembalikan data dari string ke input
        if armada_str and armada_str.strip() and armada_str != "-":
            parts = armada_str.split(" - ")
            if len(parts) >= 3:
                self.cb_jenis_truk.setCurrentText(parts[0])
                self.txt_no_pol.setText(parts[1] if parts[1] != "-" else "")

                sopir_ket = parts[2]
                if " (" in sopir_ket and sopir_ket.endswith(")"):
                    s_parts = sopir_ket.split(" (")
                    self.txt_sopir.setText(s_parts[0])
                    self.txt_keterangan.setText(s_parts[1][:-1])  # Hapus tanda tutup kurung ')'
                else:
                    self.txt_sopir.setText(sopir_ket)
                    self.txt_keterangan.clear()
            else:
                self.cb_jenis_truk.setCurrentIndex(0)
        else:
            self.cb_jenis_truk.setCurrentIndex(0)
            self.txt_no_pol.clear()
            self.txt_sopir.clear()
            self.txt_keterangan.clear()

        self.lbl_title.setText(f"✏️ Edit Manifest: {m_id}");
        self.txt_no_manifest.setText(m_id)
        self.btn_proses.setText("💾 SIMPAN MANIFES");
        self.btn_batal_edit.show();
        self.sesuaikan_tema_lokal();
        self.load_data_resi_gudang()

    def batal_edit(self):
        self.is_edit_mode = False;
        self.edit_manifest_id = ""
        self.lbl_title.setText("📦 Pembuatan Manifes Pengiriman");
        self.btn_proses.setText("⚡ BUAT MANIFES");
        self.btn_batal_edit.hide()

        # Kosongkan semua form input
        self.cb_jenis_truk.setCurrentIndex(0)
        self.txt_sopir.clear();
        self.txt_no_pol.clear();
        self.txt_keterangan.clear();

        self.sesuaikan_tema_lokal();
        self.generate_no_manifest();
        self.load_data_resi_gudang()