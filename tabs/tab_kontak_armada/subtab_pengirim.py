# tabs/tab_kontak_armada/subtab_pengirim.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QLineEdit, QTableWidget, QHeaderView,
                             QAbstractItemView, QSplitter, QFrame, QSizePolicy)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QFont

from config import CURRENT_SESSION
import services.database_service as db_service

from utils.typography import MASTER_FONT
from utils.widget_helpers import paksa_kapital_lineedit as helper_paksa_kapital_lineedit
import utils.zoom as zoom_helper
from utils.mixins import ZoomTableMixin
from utils.table_helper import buat_tabel_item
from utils.date_ind_format import format_tanggal_ke_ui

class SubTabPengirim(QWidget, ZoomTableMixin):
    KOL_NO = 0
    KOL_ID = 1
    KOL_NAMA_PENGIRIM = 2
    KOL_TELEPON = 3
    KOL_KOTA = 4
    KOL_ALAMAT = 5

    def __init__(self):
        super().__init__()
        self._sedang_menerapkan_zoom = False
        self.init_ui()

    def init_ui(self):
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        layout_utama = QVBoxLayout(self)
        layout_utama.setContentsMargins(10, 10, 10, 10)
        layout_utama.setSpacing(0)

        self.splitter = QSplitter(Qt.Horizontal)
        self.splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        layout_utama.addWidget(self.splitter)

        # --- PANEL KIRI: DATA UTAMA ---
        self.panel_kiri = QWidget()
        layout_kiri = QVBoxLayout(self.panel_kiri)
        layout_kiri.setContentsMargins(0, 0, 5, 0)
        layout_kiri.setSpacing(10)

        hbox_header_kiri = QHBoxLayout()
        self.lbl_judul = QLabel("👤 List Pengirim")
        self.lbl_judul.setFont(QFont(MASTER_FONT, 14, QFont.Bold))
        hbox_header_kiri.addWidget(self.lbl_judul)
        hbox_header_kiri.addStretch()

        self.txt_cari = QLineEdit()
        self.txt_cari.setPlaceholderText("Cari pengirim...")
        self.txt_cari.setProperty("zoom_font_key", "sz_input")
        self.txt_cari.setFixedWidth(230)
        self.txt_cari.textChanged.connect(lambda _t: helper_paksa_kapital_lineedit(self.txt_cari))
        self.txt_cari.textChanged.connect(self.filter_pencarian_tabel)
        hbox_header_kiri.addWidget(self.txt_cari)
        layout_kiri.addLayout(hbox_header_kiri)

        self.tabel_pengirim = QTableWidget()
        self.tabel_pengirim.setColumnCount(6)
        self.tabel_pengirim.setHorizontalHeaderLabels([
            "NO.", "ID SHIPPER", "NAMA PENGIRIM", "NO. HP", "KOTA", "ALAMAT"
        ])
        self.tabel_pengirim.verticalHeader().setVisible(False)
        self.tabel_pengirim.setColumnHidden(self.KOL_ID, True)

        self.tabel_pengirim.setEditTriggers(
            QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed | QAbstractItemView.SelectedClicked
        )
        self.tabel_pengirim.itemChanged.connect(self.simpan_edit_pengirim_dari_tabel)
        self.tabel_pengirim.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabel_pengirim.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabel_pengirim.setAlternatingRowColors(True)
        self.tabel_pengirim.cellClicked.connect(self.pilih_pengirim_tampilkan_histori)

        header_kiri = self.tabel_pengirim.horizontalHeader()
        header_kiri.setSectionResizeMode(QHeaderView.Interactive)
        header_kiri.setSectionsClickable(True)
        header_kiri.setSectionsMovable(True)

        self.load_lebar_kolom(self.tabel_pengirim)

        header_kiri.sectionResized.connect(
            lambda logicalIndex, oldSize, newSize: self.simpan_lebar_kolom(self.tabel_pengirim)
        )
        layout_kiri.addWidget(self.tabel_pengirim)

        # --- PANEL KANAN: HISTORI TRANSAKSI ---
        self.panel_kanan = QFrame()
        self.panel_kanan.setObjectName("panelHistori")
        layout_kanan = QVBoxLayout(self.panel_kanan)
        layout_kanan.setContentsMargins(10, 10, 10, 10)
        layout_kanan.setSpacing(10)

        self.lbl_judul_histori = QLabel("📦 Riwayat Pengiriman")
        self.lbl_judul_histori.setFont(QFont(MASTER_FONT, 11, QFont.Bold))
        self.lbl_judul_histori.setAlignment(Qt.AlignCenter)
        layout_kanan.addWidget(self.lbl_judul_histori)

        self.txt_cari_histori = QLineEdit()
        self.txt_cari_histori.setPlaceholderText("Cari di histori ini...")
        self.txt_cari_histori.setProperty("zoom_font_key", "sz_input")
        self.txt_cari_histori.textChanged.connect(lambda _t: helper_paksa_kapital_lineedit(self.txt_cari_histori))
        self.txt_cari_histori.textChanged.connect(self.filter_pencarian_histori)
        layout_kanan.addWidget(self.txt_cari_histori)

        self.tabel_histori = QTableWidget()
        self.tabel_histori.setColumnCount(7)
        self.tabel_histori.setHorizontalHeaderLabels(
            ["TANGGAL", "NO. RESI", "PENERIMA", "KOLI", "BERAT", "CBM", "ONGKIR"])
        self.tabel_histori.verticalHeader().setVisible(False)
        self.tabel_histori.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabel_histori.setAlternatingRowColors(True)

        header_kanan = self.tabel_histori.horizontalHeader()
        header_kanan.setSectionResizeMode(QHeaderView.Interactive)
        header_kanan.setSectionsClickable(True)
        header_kanan.setSectionsMovable(True)

        self.load_lebar_kolom_histori(self.tabel_histori)

        header_kanan.sectionResized.connect(
            lambda logicalIndex, oldSize, newSize: self.simpan_lebar_kolom_histori(self.tabel_histori)
        )
        layout_kanan.addWidget(self.tabel_histori)

        self.splitter.addWidget(self.panel_kiri)
        self.splitter.addWidget(self.panel_kanan)
        self.splitter.setSizes([650, 450])

        self.load_data_pengirim()
        self.sesuaikan_tema_lokal()

    def filter_pencarian_tabel(self):
        keyword = self.txt_cari.text().lower().strip()
        for row in range(self.tabel_pengirim.rowCount()):
            match = any(
                self.tabel_pengirim.item(row, col) and keyword in self.tabel_pengirim.item(row, col).text().lower()
                for col in [self.KOL_NAMA_PENGIRIM, self.KOL_TELEPON, self.KOL_KOTA, self.KOL_ALAMAT]
            )
            self.tabel_pengirim.setRowHidden(row, not match)

    def filter_pencarian_histori(self):
        keyword = self.txt_cari_histori.text().lower().strip()
        for row in range(self.tabel_histori.rowCount()):
            match = any(
                self.tabel_histori.item(row, col) and keyword in self.tabel_histori.item(row, col).text().lower()
                for col in range(self.tabel_histori.columnCount())
            )
            self.tabel_histori.setRowHidden(row, not match)

    def load_data_pengirim(self):
        self.tabel_pengirim.blockSignals(True)
        self.tabel_pengirim.setRowCount(0)
        self.tabel_histori.setRowCount(0)

        try:
            kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')
            rows = db_service.ambil_semua_master_pengirim(kode_cabang)

            for baris, data in enumerate(rows):
                self.tabel_pengirim.insertRow(baris)

                # 💡 SEKARANG JAUH LEBIH RINGKAS MENGGUNAKAN buat_tabel_item()
                self.tabel_pengirim.setItem(baris, self.KOL_NO,
                                            buat_tabel_item(baris + 1, editable=False, alignment=Qt.AlignCenter))
                self.tabel_pengirim.setItem(baris, self.KOL_ID,
                                            buat_tabel_item(data[0], editable=False, alignment=Qt.AlignCenter))
                self.tabel_pengirim.setItem(baris, self.KOL_NAMA_PENGIRIM,
                                            buat_tabel_item(data[2], alignment=Qt.AlignLeft | Qt.AlignVCenter))
                self.tabel_pengirim.setItem(baris, self.KOL_TELEPON, buat_tabel_item(data[3], alignment=Qt.AlignCenter))
                self.tabel_pengirim.setItem(baris, self.KOL_KOTA, buat_tabel_item(data[5], alignment=Qt.AlignCenter))
                self.tabel_pengirim.setItem(baris, self.KOL_ALAMAT,
                                            buat_tabel_item(data[4], alignment=Qt.AlignLeft | Qt.AlignVCenter))

        except Exception as e:
            print(f"Error Load Pengirim: {e}")
        finally:
            self.tabel_pengirim.blockSignals(False)

    def simpan_edit_pengirim_dari_tabel(self, item):
        if not item or item.column() in [self.KOL_NO, self.KOL_ID]: return
        row = item.row()
        kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')

        try:
            id_pengirim = self.tabel_pengirim.item(row, self.KOL_ID).text().strip()
            nama = self.tabel_pengirim.item(row, self.KOL_NAMA_PENGIRIM).text().strip().upper()
            no_hp = self.tabel_pengirim.item(row, self.KOL_TELEPON).text().strip()
            kota = self.tabel_pengirim.item(row, self.KOL_KOTA).text().strip().upper()
            alamat = self.tabel_pengirim.item(row, self.KOL_ALAMAT).text().strip().upper()

            sukses, pesan = db_service.update_master_pengirim_dari_tabel(id_pengirim, kode_cabang, nama, no_hp, kota,
                                                                         alamat)
            if not sukses:
                self.load_data_pengirim()
                return

            self.tabel_pengirim.blockSignals(True)
            self.tabel_pengirim.item(row, self.KOL_NAMA_PENGIRIM).setText(nama)
            self.tabel_pengirim.item(row, self.KOL_KOTA).setText(kota)
            self.tabel_pengirim.item(row, self.KOL_ALAMAT).setText(alamat)
            self.tabel_pengirim.blockSignals(False)
        except Exception as e:
            print(f"Error simpan edit pengirim: {e}")
            self.load_data_pengirim()

    def pilih_pengirim_tampilkan_histori(self, row, column):
        self.tabel_histori.setRowCount(0)
        item_nama = self.tabel_pengirim.item(row, self.KOL_NAMA_PENGIRIM)
        if not item_nama: return

        nama_pengirim = item_nama.text()
        kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')

        try:
            histori_rows = db_service.ambil_histori_transaksi_by_pengirim(nama_pengirim, kode_cabang)
            self.lbl_judul_histori.setText(f"📦 Riwayat Nota: {nama_pengirim}")

            for baris, h in enumerate(histori_rows):
                self.tabel_histori.insertRow(baris)
                ongkir_formatted = f"{int(h[6]):,}".replace(",", ".") if h[6] else "0"

                # 💡 MENGGUNAKAN buat_tabel_item() PADA TABEL HISTORI
                self.tabel_histori.setItem(baris, 0, buat_tabel_item(format_tanggal_ke_ui(h[0]), editable=False, alignment=Qt.AlignCenter))
                self.tabel_histori.setItem(baris, 1, buat_tabel_item(h[1], editable=False, alignment=Qt.AlignCenter))
                self.tabel_histori.setItem(baris, 2, buat_tabel_item(h[2], editable=False,
                                                                     alignment=Qt.AlignLeft | Qt.AlignVCenter))
                self.tabel_histori.setItem(baris, 3, buat_tabel_item(h[3], editable=False, alignment=Qt.AlignCenter))
                self.tabel_histori.setItem(baris, 4, buat_tabel_item(h[4], editable=False, alignment=Qt.AlignCenter))
                self.tabel_histori.setItem(baris, 5, buat_tabel_item(h[5], editable=False, alignment=Qt.AlignCenter))
                self.tabel_histori.setItem(baris, 6, buat_tabel_item(ongkir_formatted, editable=False,
                                                                     alignment=Qt.AlignRight | Qt.AlignVCenter))

            self.filter_pencarian_histori()
        except Exception as e:
            print(f"Error Load Histori Pengirim: {e}")

    # ============================================================
    # REFAKTOR LOGIKA LEBAR KOLOM MENGGUNAKAN FUNGSI DARI MIXIN
    # ============================================================
    def _settings_kolom(self):
        return QSettings("EkspedisiApp", "SubTabMasterPengirim")

    def simpan_lebar_kolom(self, t):
        if self._sedang_menerapkan_zoom:
            return
        widths = self._lebar_dasar_tabel(t)  # 💡 Dari Mixin
        self._perbarui_cache_lebar_zoom(t, widths)  # 💡 Dari Mixin
        self._settings_kolom().setValue("lebar_kolom_pengirim", widths)

    def load_lebar_kolom(self, t):
        widths = self._settings_kolom().value("lebar_kolom_pengirim")
        if widths:
            for i, width in enumerate(widths):
                if i < t.columnCount(): t.setColumnWidth(i, int(width))
        else:
            t.setColumnWidth(self.KOL_NO, 50)
            t.setColumnWidth(self.KOL_ID, 90)
            t.setColumnWidth(self.KOL_NAMA_PENGIRIM, 180)
            t.setColumnWidth(self.KOL_TELEPON, 130)
            t.setColumnWidth(self.KOL_KOTA, 120)

        t.horizontalHeader().setSectionResizeMode(self.KOL_ALAMAT, QHeaderView.Stretch)
        base_widths = [t.columnWidth(i) for i in range(t.columnCount())]
        self._perbarui_cache_lebar_zoom(t, base_widths)

    def simpan_lebar_kolom_histori(self, t):
        if self._sedang_menerapkan_zoom:
            return
        widths = self._lebar_dasar_tabel(t)  # 💡 Dari Mixin
        self._perbarui_cache_lebar_zoom(t, widths)  # 💡 Dari Mixin
        self._settings_kolom().setValue("lebar_kolom_histori_pengirim", widths)

    def load_lebar_kolom_histori(self, t):
        w = self._settings_kolom().value("lebar_kolom_histori_pengirim")
        if w:
            for i, width in enumerate(w):
                if i < t.columnCount(): t.setColumnWidth(i, int(width))
        else:
            defaults = [95, 100, 140, 50, 60, 60, 90]
            for idx, width in enumerate(defaults):
                if idx < t.columnCount(): t.setColumnWidth(idx, width)

        base_widths = [t.columnWidth(i) for i in range(t.columnCount())]
        self._perbarui_cache_lebar_zoom(t, base_widths)

    def showEvent(self, event):
        super().showEvent(event)

        self.load_data_pengirim()
        # Tema dikelola oleh TabKontakArmada.

    def sesuaikan_tema_lokal(self):
        win = self.window()
        is_dark = win.current_theme == "dark" if win and hasattr(win, 'current_theme') else False
        z = zoom_helper.dapatkan_zoom_level("TabKontakArmada")

        self.lbl_judul.setProperty("zoom_font_key", "sz_title")
        self.lbl_judul_histori.setProperty("zoom_font_key", "sz_title")

        if is_dark:
            style_judul = "color: #ffffff; font-weight: bold;"
            style_judul_histori = "color: #60a5fa; font-weight: bold;"
            style_input = "background-color: #1d2024; color: white; border: 1px solid #4c525e; border-radius: 4px;"
            style_panel = "QFrame#panelHistori { background-color: #1e293b; border-radius: 8px; border: 1px solid #334155; }"
        else:
            style_judul = "color: #1e293b; font-weight: bold;"
            style_judul_histori = "color: #2563eb; font-weight: bold;"
            style_input = "background-color: white; color: #0f172a; border: 1px solid #cbd5e1; border-radius: 4px;"
            style_panel = "QFrame#panelHistori { background-color: #f8fafc; border-radius: 8px; border: 1px solid #e2e8f0; }"

        self.panel_kanan.setStyleSheet(style_panel)
        self._set_style_dasar_zoom(self.lbl_judul, style_judul)  # 💡 Menggunakan metode Mixin
        self._set_style_dasar_zoom(self.lbl_judul_histori, style_judul_histori)
        self._set_style_dasar_zoom(self.txt_cari, style_input)
        self._set_style_dasar_zoom(self.txt_cari_histori, style_input)

        if hasattr(self.tabel_pengirim, "_zoom_base_stylesheet"): delattr(self.tabel_pengirim, "_zoom_base_stylesheet")
        if hasattr(self.tabel_histori, "_zoom_base_stylesheet"): delattr(self.tabel_histori, "_zoom_base_stylesheet")

        self._sedang_menerapkan_zoom = True
        try:
            zoom_helper.terapkan_zoom_semua_elemen(container_widget=self, z=z, is_dark=is_dark)
        finally:
            self._sedang_menerapkan_zoom = False

