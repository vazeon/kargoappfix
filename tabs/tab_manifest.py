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

from utils.typography import get_global_font_sizes
from utils import zoom as zoom_helper
from utils.number_formatters import (format_ke_rupiah, format_angka_indonesia)
from utils.table_helper import buat_tabel_item
from utils.widget_helpers import (
    paksa_kapital_lineedit,
    terapkan_popup_combobox_bawah,
)
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

        # 1. ComboBox Jenis Truk dengan Placeholder
        hbox_top.addWidget(QLabel("Truk:"))
        self.cb_jenis_truk = QComboBox()
        self.cb_jenis_truk.addItem("- Pilih jenis -")  # Index 0 sebagai placeholder
        self.cb_jenis_truk.addItems(["TB", "Tronton", "CDD", "Pick-up", "Lainnya..."])
        self.cb_jenis_truk.setFixedWidth(120)

        # --- BIKIN PLACEHOLDER SAJA YANG ITALIC ---
        def ubah_font_placeholder(idx):
            # Ubah font kotak utama (tampilan depan) agar italic HANYA saat index 0 dipilih
            font_utama = self.cb_jenis_truk.font()
            font_utama.setItalic(idx == 0)
            self.cb_jenis_truk.setFont(font_utama)

            font_italic = QFont(font_utama)
            font_italic.setItalic(True)
            self.cb_jenis_truk.setItemData(0, font_italic, Qt.FontRole)

            font_normal = QFont(font_utama)
            font_normal.setItalic(False)
            for i in range(1, self.cb_jenis_truk.count()):
                self.cb_jenis_truk.setItemData(i, font_normal, Qt.FontRole)

        # Hubungkan fungsi dan jalankan sekali di awal
        self.cb_jenis_truk.currentIndexChanged.connect(ubah_font_placeholder)
        self.cb_jenis_truk.currentIndexChanged.connect(self.on_jenis_truk_manifest_changed)
        ubah_font_placeholder(0)
        # --------------------------------

        hbox_top.addWidget(self.cb_jenis_truk)

        self.txt_jenis_truk_lain = QLineEdit()
        self.txt_jenis_truk_lain.setPlaceholderText("Jenis lainnya")
        self.txt_jenis_truk_lain.setFixedWidth(125)
        self.txt_jenis_truk_lain.textChanged.connect(
            lambda: paksa_kapital_lineedit(self.txt_jenis_truk_lain)
        )
        self.txt_jenis_truk_lain.hide()
        hbox_top.addWidget(self.txt_jenis_truk_lain)

        # 2. Input No. Pol (Opsional)
        self.txt_no_pol = QLineEdit()
        self.txt_no_pol.setPlaceholderText("No. Pol")
        self.txt_no_pol.setFixedWidth(100)
        self.txt_no_pol.textChanged.connect(lambda: paksa_kapital_lineedit(self.txt_no_pol))
        hbox_top.addWidget(self.txt_no_pol)

        # 3. Input Nama Sopir (Wajib jika truk dipilih)
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
        hbox_top.addWidget(self.btn_proses)

        self.btn_batal_edit = QPushButton("❌ BATAL")
        self.btn_batal_edit.clicked.connect(self.batal_edit)
        self.btn_batal_edit.hide()
        hbox_top.addWidget(self.btn_batal_edit)
        layout_kiri.addLayout(hbox_top)

        self.tabel_manifest = QTableWidget()
        self.tabel_manifest.setColumnCount(13)
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

        self.btn_proses.clicked.connect(self.update_truk_ke_manifest)
        self.refresh_tahun_filter()
        self.load_data_resi_gudang()
        self.generate_no_manifest()
        self.sesuaikan_tema_lokal()
        self.setup_autocomplete_truk()
        terapkan_popup_combobox_bawah(self)

    def on_jenis_truk_manifest_changed(self, _index=None):
        """Menampilkan kolom jenis lainnya hanya saat diperlukan."""
        pilih_lainnya = self.cb_jenis_truk.currentText().strip() == "Lainnya..."
        self.txt_jenis_truk_lain.setVisible(pilih_lainnya)
        if not pilih_lainnya:
            self.txt_jenis_truk_lain.clear()

    def ambil_jenis_truk_manifest(self):
        """Menghasilkan jenis truk baku untuk payload Manifest."""
        pilihan = self.cb_jenis_truk.currentText().strip()
        if pilihan == "Lainnya...":
            return self.txt_jenis_truk_lain.text().strip().upper()
        if self.cb_jenis_truk.currentIndex() <= 0:
            return ""
        return pilihan

    def set_jenis_truk_manifest(self, jenis):
        """Memilih jenis umum atau mengisi kolom Lainnya untuk jenis khusus."""
        jenis_bersih = str(jenis or "").strip()
        if not jenis_bersih:
            self.cb_jenis_truk.setCurrentIndex(0)
            return

        for index in range(1, self.cb_jenis_truk.count()):
            item_text = self.cb_jenis_truk.itemText(index)
            if item_text == "Lainnya...":
                continue
            if item_text.casefold() == jenis_bersih.casefold():
                self.cb_jenis_truk.setCurrentIndex(index)
                return

        idx_lainnya = self.cb_jenis_truk.findText("Lainnya...", Qt.MatchFixedString)
        self.cb_jenis_truk.setCurrentIndex(idx_lainnya)
        self.txt_jenis_truk_lain.setText(jenis_bersih.upper())

    def setup_autocomplete_truk(self):
        try:
            rows = db_service.ambil_truk_list() or []
            sopirs = sorted({str(row[1]).strip() for row in rows if len(row) > 1 and row[1]})

            completer_lama = getattr(self, 'completer_sopir', None)
            if completer_lama is not None:
                try:
                    completer_lama.activated.disconnect(self.on_sopir_selected)
                except (TypeError, RuntimeError):
                    pass
                completer_lama.deleteLater()

            self.completer_sopir = QCompleter(sopirs, self)
            self.completer_sopir.setCaseSensitivity(Qt.CaseInsensitive)
            self.txt_sopir.setCompleter(self.completer_sopir)
            self.completer_sopir.activated.connect(self.on_sopir_selected)

            self.txt_no_pol.setCompleter(None)
        except Exception as e:
            QMessageBox.warning(self, "Warning Database", f"Gagal memuat autocomplete truk: {e}")

    def on_sopir_selected(self, sopir):
        row = db_service.ambil_detail_truk_by_sopir(sopir)
        if row:
            no_polisi = row[0] if len(row) > 0 else ""
            jenis_truk = row[1] if len(row) > 1 else ""
            ket_truk = row[2] if len(row) > 2 else ""

            if no_polisi:
                self.txt_no_pol.setText(str(no_polisi))

            if jenis_truk:
                self.set_jenis_truk_manifest(jenis_truk)

            if ket_truk and str(ket_truk).strip() not in ('', '-'):
                self.txt_keterangan.setText(str(ket_truk))

    def generate_no_manifest(self):
        if self.is_edit_mode:
            self.txt_no_manifest.setText(self.edit_manifest_id)
            return

        prefix = f"M-{CURRENT_SESSION.get('aturan_prefix', {}).get(self.cb_filter_wilayah.currentText(), 'MF')}"
        seq = 1
        try:
            rows = db_service.ambil_no_manifest_list_by_prefix(prefix, CURRENT_SESSION.get('kode_cabang', 'PUSAT'))
            if rows:
                seq = max(int(r[0].split('-')[-1]) for r in rows if r[0]) + 1
        except:
            pass
        self.txt_no_manifest.setText(f"{prefix}-{seq:04d}")

    def refresh_tahun_filter(self):
        self.cb_tahun_filter.blockSignals(True)
        self.cb_tahun_filter.clear()
        self.cb_tahun_filter.addItem("Semua")
        self.cb_tahun_filter.addItem(str(QDate.currentDate().year()))
        self.cb_tahun_filter.setCurrentIndex(1)
        self.cb_tahun_filter.blockSignals(False)

    def load_data_resi_gudang(self):
        # Amankan zoom_base sebelum merender isi tabel agar kolom tidak melompat
        if not hasattr(self.tabel_manifest, "_zoom_base_column_widths"):
            self.tabel_manifest._zoom_base_column_widths = {i: self.tabel_manifest.columnWidth(i) for i in
                                                            range(self.tabel_manifest.columnCount())}

        self.tabel_manifest.blockSignals(True)
        self.tabel_manifest.setRowCount(0)
        is_dark = self.window().current_theme == "dark" if self.window() and hasattr(self.window(),
                                                                                     'current_theme') else False

        try:
            rows = db_service.ambil_resi_untuk_manifest(CURRENT_SESSION.get('kode_cabang', 'PUSAT'),
                                                        self.cb_filter_wilayah.currentText(), self.is_edit_mode,
                                                        self.edit_manifest_id)
            for row in rows:
                pos = self.tabel_manifest.rowCount()
                self.tabel_manifest.insertRow(pos)
                belong = self.is_edit_mode and row[9] == self.edit_manifest_id
                bg = get_manifest_row_highlight(is_dark, belong)

                # Pembuatan checkbox kolom 0
                chk = buat_tabel_item(text="", editable=False, alignment=Qt.AlignCenter)
                chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                chk.setCheckState(Qt.Checked if belong else Qt.Unchecked)
                if bg:
                    chk.setBackground(QBrush(bg))
                self.tabel_manifest.setItem(pos, self.KOL_CHECK, chk)

                # Pembuatan nomor urut
                item_no = buat_tabel_item(text=str(pos + 1), editable=False, alignment=Qt.AlignCenter)
                if bg:
                    item_no.setBackground(QBrush(bg))
                self.tabel_manifest.setItem(pos, self.KOL_NO, item_no)

                # Pembuatan sel lainnya
                for i, d in enumerate(row[:9]):
                    val = str(d) if d is not None else ""
                    col = i + 2

                    if col == self.KOL_TGL_MASUK and val:
                        val = format_tanggal_ke_ui(val)
                    elif col == self.KOL_TUJUAN and " - " in val:
                        val = val.split(" - ")[-1]
                    elif col in [self.KOL_KOLI, self.KOL_BERAT, self.KOL_CBM]:
                        val = format_angka_indonesia(d, kosong_jika_nol=True, nilai_kosong="-")

                    # Penentuan Alignment Berbasis Tipe Data
                    if col in [self.KOL_KOLI, self.KOL_BERAT, self.KOL_CBM]:
                        align = Qt.AlignRight | Qt.AlignVCenter
                    elif col == self.KOL_TGL_MASUK:
                        align = Qt.AlignCenter | Qt.AlignVCenter
                    else:
                        align = Qt.AlignLeft | Qt.AlignVCenter

                    item = buat_tabel_item(text=val, editable=False, alignment=align)
                    if bg:
                        item.setBackground(QBrush(bg))
                    self.tabel_manifest.setItem(pos, col, item)

                # Kolom Ongkir
                val_ongkir = format_ke_rupiah(row[10]) if row[10] else "-"
                item_ongkir = buat_tabel_item(text=val_ongkir, editable=False,
                                              alignment=Qt.AlignRight | Qt.AlignVCenter)
                if bg:
                    item_ongkir.setBackground(QBrush(bg))
                self.tabel_manifest.setItem(pos, self.KOL_ONGKIR, item_ongkir)

                txt_ket_row = QLineEdit()
                txt_ket_row.setFrame(False)
                txt_ket_row.setPlaceholderText("Ket...")
                if belong and row[11]:
                    txt_ket_row.setText(str(row[11]))
                self.tabel_manifest.setCellWidget(pos, self.KOL_KET, txt_ket_row)

            self.load_histori()
        except Exception as e:
            QMessageBox.critical(self, "Error Load Data", f"Gagal memuat data resi manifes:\n{e}")

        self.tabel_manifest.blockSignals(False)

    def load_histori(self):
        self.list_histori.clear()
        win = self.window()
        is_dark = win.current_theme == "dark" if win and hasattr(win, 'current_theme') else False

        try:
            rows = db_service.ambil_histori_manifest(CURRENT_SESSION.get('kode_cabang', 'PUSAT'),
                                                     self.cb_tahun_filter.currentText())

            NAMA_BULAN = {
                "01": "Januari", "02": "Februari", "03": "Maret", "04": "April",
                "05": "Mei", "06": "Juni", "07": "Juli", "08": "Agustus",
                "09": "September", "10": "Oktober", "11": "November", "12": "Desember"
            }

            parents = {}
            for r in rows:
                tgl_raw, m_id, truk, count = str(r[0]), str(r[1]), str(r[2]), r[3]
                tgl_indo = format_tanggal_ke_ui(tgl_raw)
                mm = tgl_indo[3:5]
                nama_bln = NAMA_BULAN.get(mm, "Unknown")
                title = f"📂 {nama_bln}"

                if title not in parents:
                    parents[title] = QTreeWidgetItem(self.list_histori)
                    parents[title].setText(0, title)

                child = QTreeWidgetItem(parents[title])
                child.setText(0, tgl_indo)

                ukuran_dasar = self.list_histori.font().pointSize()
                font_tanggal, warna_abu = get_manifest_history_date_appearance(
                    is_dark,
                    ukuran_dasar,
                )
                child.setFont(0, font_tanggal)
                child.setForeground(0, QBrush(warna_abu))

                truk_display = f" | {truk}" if truk and truk.strip() != "-" else ""
                child.setText(1, f"{m_id}{truk_display} ({count} Resi)")

            self.list_histori.expandAll()
        except Exception as e:
            QMessageBox.critical(self, "Error Histori", f"Gagal memuat histori manifest:\n{e}")

    def update_truk_ke_manifest(self):
        m_id = self.edit_manifest_id if self.is_edit_mode else self.txt_no_manifest.text().strip()
        resi = []

        for r in range(self.tabel_manifest.rowCount()):
            if self.tabel_manifest.isRowHidden(r):
                continue

            item_check = self.tabel_manifest.item(r, self.KOL_CHECK)
            item_resi = self.tabel_manifest.item(r, self.KOL_RESI)
            if item_check and item_resi and item_check.checkState() == Qt.Checked:
                widget_ket = self.tabel_manifest.cellWidget(r, self.KOL_KET)
                ket_text = widget_ket.text().strip() if widget_ket else ""
                resi.append((item_resi.text().strip(), ket_text))

        if not resi:
            QMessageBox.warning(self, "Warning", "Centang minimal 1 resi!")
            return

        truk_idx = self.cb_jenis_truk.currentIndex()
        truk_text = self.ambil_jenis_truk_manifest()
        nopol = self.txt_no_pol.text().strip().upper()
        sopir = self.txt_sopir.text().strip().upper()
        keterangan = self.txt_keterangan.text().strip().upper()

        if keterangan and truk_idx == 0 and not nopol and not sopir:
            dict_update = {
                'no_polisi': "",
                'nama_sopir': "",
                'jenis_truk': "",
                'nama_truk': keterangan,
                'ket_truk': keterangan
            }
        elif truk_idx > 0:
            if self.cb_jenis_truk.currentText().strip() == "Lainnya..." and not truk_text:
                QMessageBox.warning(self, "Peringatan", "Jenis truk lainnya wajib diisi!")
                self.txt_jenis_truk_lain.setFocus()
                return

            # Saat jenis truk dipilih, minimal No. Polisi ATAU Nama Sopir harus tersedia.
            # Jika hanya Nama Sopir yang tersedia, Manifest tetap disimpan tetapi
            # tidak membuat Master truk karena identitas kendaraan belum diketahui.
            if not nopol and not sopir:
                QMessageBox.warning(
                    self,
                    "Peringatan",
                    "Isi minimal No. Polisi atau Nama Sopir jika jenis truk dipilih!"
                )
                self.txt_no_pol.setFocus()
                return

            nopol_val = nopol if nopol else "BELUM DIKETAHUI"
            sopir_val = sopir if sopir else "BELUM ADA SOPIR"
            truk_full = f"{truk_text} - {nopol_val} - {sopir_val}"
            if keterangan:
                truk_full += f" ({keterangan})"

            dict_update = {
                'no_polisi': nopol,
                'nama_sopir': sopir,
                'jenis_truk': truk_text,
                'nama_truk': truk_full,
                'ket_truk': keterangan
            }
        else:
            QMessageBox.warning(
                self,
                "Peringatan",
                "Isi Keterangan untuk titip ekspedisi, atau pilih Jenis truk lalu isi No. Polisi/Nama Sopir!"
            )
            return

        sukses, err = db_service.simpan_atau_update_manifest_data(
            m_id,
            CURRENT_SESSION.get('kode_cabang', 'PUSAT'),
            dict_update,
            resi,
            self.is_edit_mode,
            QDate.currentDate().toString("yyyy-MM-dd")
        )

        if sukses:
            QMessageBox.information(self, "Sukses", "Manifest berhasil diproses!")
            self.setup_autocomplete_truk()

            if self.is_edit_mode:
                self.batal_edit()
            else:
                self.cb_jenis_truk.setCurrentIndex(0)
                self.txt_jenis_truk_lain.clear()
                self.txt_no_pol.clear()
                self.txt_sopir.clear()
                self.txt_keterangan.clear()
                self.load_data_resi_gudang()
                self.generate_no_manifest()
                self.refresh_tahun_filter()
                self.load_histori()
        else:
            QMessageBox.critical(self, "Error", f"Gagal memproses manifest:\n{err}")

    def preview_histori_manifest(self, item):
        if item.parent():
            teks_info = item.text(1)
            parts = teks_info.split(" | ")
            m_id = parts[0].strip()
            if len(parts) > 1:
                truk = parts[1].split(" (")[0].strip()
            else:
                truk = ""
            self.siapkan_dan_cetak_dari_id(m_id, truk)

    def siapkan_dan_cetak_dari_id(self, m_id, truk):
        try:
            data = db_service.ambil_resi_detail_untuk_cetak(
                CURRENT_SESSION.get('kode_cabang', 'PUSAT'),
                db_service.ambil_resi_list_by_manifest(m_id, CURRENT_SESSION.get('kode_cabang', 'PUSAT'))
            )

            items_cetak = []
            for r in data:
                items_cetak.append((
                    r[0], r[1], r[2],
                    r[3].split(" - ")[-1] if " - " in r[3] else r[3],
                    r[4],
                    format_angka_indonesia(r[5], kosong_jika_nol=True, nilai_kosong="-"),
                    format_angka_indonesia(r[6], kosong_jika_nol=True, nilai_kosong="-"),
                    format_angka_indonesia(r[7], kosong_jika_nol=True, nilai_kosong="-")
                ))

            cetak_manifest_ke_printer(
                {'no_manifest': m_id, 'truk': truk if truk else "-",
                 'tanggal': QDate.currentDate().toString("dd/MM/yyyy"),
                 'items': items_cetak}, self)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal cetak: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        terapkan_popup_combobox_bawah(self)
        self.load_data_resi_gudang()
        self.generate_no_manifest()

    def sesuaikan_tema_lokal(self):
        win = self.window()
        is_dark = win.current_theme == "dark" if win and hasattr(win, 'current_theme') else False

        z = zoom_helper.dapatkan_zoom_level(self.__class__.__name__)
        font_statis = get_global_font_sizes(0)
        font_dinamis = get_global_font_sizes(z)

        styles_statis = get_manifest_styles(is_dark, self.is_edit_mode, 0)
        styles_dinamis = get_manifest_styles(is_dark, self.is_edit_mode, z)

        self.panel_kiri.setStyleSheet(styles_statis['panel_kiri'])
        self.panel_kanan.setStyleSheet(styles_statis['panel_kanan'])
        self.lbl_title.setStyleSheet(styles_statis['lbl_title'])
        self.btn_proses.setStyleSheet(styles_statis['btn_proses'])

        for w in [self.txt_no_manifest, self.txt_jenis_truk_lain, self.txt_no_pol, self.txt_sopir,
                  self.txt_keterangan, self.cb_filter_wilayah, self.cb_jenis_truk,
                  self.cb_tahun_filter, self.txt_cari_histori]:
            w.setStyleSheet(styles_statis['style_input'])

        # Integrasi tabel responsif
        self.tabel_manifest.setStyleSheet(styles_dinamis['style_tabel'])

        font = self.tabel_manifest.font()
        font.setPointSize(font_dinamis["sz_base"])
        self.tabel_manifest.setFont(font)

        header_font = self.tabel_manifest.horizontalHeader().font()
        header_font.setPointSize(font_dinamis["sz_base"])
        self.tabel_manifest.horizontalHeader().setFont(header_font)
        self.tabel_manifest.verticalHeader().setFont(header_font)

        faktor = max(0.68, min(1.0 + (z * 0.08), 1.80))
        tinggi_baris = max(24, int(32 * faktor))
        self.tabel_manifest.verticalHeader().setDefaultSectionSize(tinggi_baris)

        self.tabel_manifest.horizontalHeader().blockSignals(True)
        zoom_helper._skalakan_kolom_tableview(self.tabel_manifest, z)
        self.tabel_manifest.horizontalHeader().blockSignals(False)

        # Histori Manifest responsif ke zoom
        self.list_histori.setStyleSheet(styles_dinamis['list_histori'])
        font_histori = self.list_histori.font()
        font_histori.setPointSize(font_dinamis["sz_base"])
        self.list_histori.setFont(font_histori)

    def simpan_lebar_kolom(self, t):
        z = zoom_helper.dapatkan_zoom_level(self.__class__.__name__)
        faktor = max(0.68, min(1.0 + (z * 0.08), 1.80))

        lebar_dasar = []
        for i in range(t.columnCount()):
            lebar_asli = int(t.columnWidth(i) / faktor)
            lebar_dasar.append(lebar_asli)

            if hasattr(t, "_zoom_base_column_widths"):
                t._zoom_base_column_widths[i] = lebar_asli

        QSettings("EkspedisiApp", "TabManifest").setValue("lebar_kolom", lebar_dasar)

    def load_lebar_kolom(self, t):
        w = QSettings("EkspedisiApp", "TabManifest").value("lebar_kolom")
        if w:
            for i, width in enumerate(w): t.setColumnWidth(i, int(width))

    def on_wilayah_changed(self):
        if self.is_edit_mode:
            self.batal_edit()
        self.generate_no_manifest()
        self.load_data_resi_gudang()

    def filter_histori(self, text):
        for i in range(self.list_histori.topLevelItemCount()):
            p = self.list_histori.topLevelItem(i)
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

        teks_info = item.text(1)
        parts = teks_info.split(" | ")
        m_id = parts[0].strip()
        truk = parts[1].split(" (")[0].strip() if len(parts) > 1 else ""

        if action == act_print:
            self.siapkan_dan_cetak_dari_id(m_id, truk)
        elif action == act_edit:
            self.aktifkan_mode_edit(m_id, truk)

    def aktifkan_mode_edit(self, m_id, truk_str):
        self.is_edit_mode = True
        self.edit_manifest_id = m_id

        self.cb_jenis_truk.setCurrentIndex(0)
        self.txt_jenis_truk_lain.clear()
        self.txt_no_pol.clear()
        self.txt_sopir.clear()
        self.txt_keterangan.clear()

        truk_bersih = str(truk_str or '').strip()
        if truk_bersih and truk_bersih != "-":
            parts = truk_bersih.split(" - ", 2)

            if len(parts) >= 3:
                jenis_text, nopol_text, sopir_ket = parts
                self.set_jenis_truk_manifest(jenis_text.strip())

                nopol_text = nopol_text.strip()
                if nopol_text not in ("-", "BELUM DIKETAHUI"):
                    self.txt_no_pol.setText(nopol_text)

                sopir_text = sopir_ket.strip()
                keterangan_text = ""
                if " (" in sopir_text and sopir_text.endswith(")"):
                    sopir_text, keterangan_text = sopir_text.rsplit(" (", 1)
                    keterangan_text = keterangan_text[:-1]

                if sopir_text.strip() not in ("", "-", "BELUM ADA SOPIR"):
                    self.txt_sopir.setText(sopir_text.strip())
                if keterangan_text:
                    self.txt_keterangan.setText(keterangan_text.strip())
            else:
                self.txt_keterangan.setText(truk_bersih)

        self.lbl_title.setText(f"✏️ Edit Manifest: {m_id}")
        self.txt_no_manifest.setText(m_id)
        self.btn_proses.setText("💾 SIMPAN MANIFES")
        self.btn_batal_edit.show()
        self.sesuaikan_tema_lokal()
        self.load_data_resi_gudang()

    def batal_edit(self):
        self.is_edit_mode = False
        self.edit_manifest_id = ""
        self.lbl_title.setText("📦 Pembuatan Manifes Pengiriman")
        self.btn_proses.setText("⚡ BUAT MANIFES")
        self.btn_batal_edit.hide()

        self.cb_jenis_truk.setCurrentIndex(0)
        self.txt_jenis_truk_lain.clear()
        self.txt_sopir.clear()
        self.txt_no_pol.clear()
        self.txt_keterangan.clear()

        self.sesuaikan_tema_lokal()
        self.generate_no_manifest()
        self.load_data_resi_gudang()