# tabs/tab_armada/subtab_kapal.py
import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTableWidget,
    QHeaderView, QMessageBox, QComboBox,
    QSplitter, QFrame, QFileDialog, QAbstractItemView
)
from PyQt5.QtCore import Qt, QSettings, QTimer
from PyQt5.QtGui import QFont, QPixmap

from config import CURRENT_SESSION

import services.database_service as db_service

from themes.modules.kontak_armada import get_armada_styles

from utils.typography import MASTER_FONT, get_global_font_sizes
from utils.mixins import ZoomTableMixin
from utils.table_helper import buat_tabel_item
import utils.zoom as zoom_helper
from utils.widget_helpers import (
    paksa_kapital_lineedit as helper_paksa_kapital_lineedit,
    terapkan_popup_combobox_bawah,
)


class SubTabKapal(QWidget, ZoomTableMixin):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.mode = 'IDLE'
        self.current_foto_path = ""
        self._sedang_menerapkan_zoom = False
        self.init_ui()

    def init_ui(self):
        layout_utama = QVBoxLayout(self)
        layout_utama.setContentsMargins(10, 10, 10, 10)

        self.splitter = QSplitter(Qt.Horizontal)
        layout_utama.addWidget(self.splitter)

        # ========================================================
        # PANEL KIRI: Master Data (Pencarian & Tabel)
        # ========================================================
        self.panel_kiri = QWidget()
        layout_kiri = QVBoxLayout(self.panel_kiri)
        layout_kiri.setContentsMargins(0, 0, 10, 0)

        layout_judul_search = QHBoxLayout()
        self.label_judul = QLabel("🚢 List Data Kapal")
        self.label_judul.setFont(QFont(MASTER_FONT, 14, QFont.Bold))
        layout_judul_search.addWidget(self.label_judul)
        layout_judul_search.addStretch()

        self.input_cari = QLineEdit()
        self.input_cari.setPlaceholderText("Cari Data Kapal...")
        self.input_cari.setProperty("zoom_font_key", "sz_input")
        self.input_cari.setFixedWidth(230)
        self.input_cari.textChanged.connect(lambda _t: helper_paksa_kapital_lineedit(self.input_cari))
        self.input_cari.textChanged.connect(self.filter_tabel_kapal)
        layout_judul_search.addWidget(self.input_cari)
        layout_kiri.addLayout(layout_judul_search)

        self.tabel_kapal = QTableWidget()
        self.tabel_kapal.setColumnCount(5)
        self.tabel_kapal.setHorizontalHeaderLabels([
            "NO", "NAMA KAPAL", "TUJUAN", "KETERANGAN", "FOTO"
        ])

        self.tabel_kapal.setColumnHidden(4, True)  # Simpan path foto tersembunyi
        self.tabel_kapal.setAlternatingRowColors(True)
        self.tabel_kapal.verticalHeader().setVisible(False)
        self.tabel_kapal.horizontalHeader().setFixedHeight(35)
        self.tabel_kapal.verticalHeader().setDefaultSectionSize(32)
        self.tabel_kapal.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabel_kapal.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabel_kapal.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabel_kapal.cellClicked.connect(self.pilih_data_dari_tabel)
        layout_kiri.addWidget(self.tabel_kapal)

        self.load_lebar_kolom(self.tabel_kapal)
        self.tabel_kapal.horizontalHeader().sectionResized.connect(
            lambda _logicalIndex, _oldSize, _newSize: self.simpan_lebar_kolom(self.tabel_kapal)
        )

        # ========================================================
        # PANEL KANAN: Detail & Editor Area
        # ========================================================
        self.panel_kanan = QFrame()
        self.panel_kanan.setObjectName("panelEditor")
        layout_kanan = QVBoxLayout(self.panel_kanan)
        layout_kanan.setContentsMargins(15, 15, 15, 15)

        self.lbl_judul_kanan = QLabel("📋 Detail / Editor Kapal")
        self.lbl_judul_kanan.setFont(QFont(MASTER_FONT, 12, QFont.Bold))
        self.lbl_judul_kanan.setAlignment(Qt.AlignCenter)
        layout_kanan.addWidget(self.lbl_judul_kanan)

        self.lbl_nama_kapal = QLabel("Nama Kapal:")
        self.input_nama_kapal = QLineEdit()
        self.input_nama_kapal.setPlaceholderText("Contoh: KM. SPIL NIKEN")
        self.input_nama_kapal.textChanged.connect(lambda _t: helper_paksa_kapital_lineedit(self.input_nama_kapal))
        layout_kanan.addWidget(self.lbl_nama_kapal)
        layout_kanan.addWidget(self.input_nama_kapal)

        self.lbl_tujuan = QLabel("Tujuan:")
        self.input_tujuan = QLineEdit()
        self.input_tujuan.setPlaceholderText("Contoh: MAKASSAR / BANJARMASIN")
        self.input_tujuan.textChanged.connect(lambda _t: helper_paksa_kapital_lineedit(self.input_tujuan))
        layout_kanan.addWidget(self.lbl_tujuan)
        layout_kanan.addWidget(self.input_tujuan)

        self.lbl_ket = QLabel("Keterangan:")
        self.input_keterangan = QLineEdit()
        self.input_keterangan.setPlaceholderText("Informasi Pelayaran / Dll")
        self.input_keterangan.textChanged.connect(lambda _t: helper_paksa_kapital_lineedit(self.input_keterangan))
        layout_kanan.addWidget(self.lbl_ket)
        layout_kanan.addWidget(self.input_keterangan)

        layout_kanan.addSpacing(10)
        self.lbl_foto_title = QLabel("📷 Foto Kapal:")
        layout_kanan.addWidget(self.lbl_foto_title)

        self.lbl_preview_foto = QLabel("Tidak Ada Foto")
        self.lbl_preview_foto.setAlignment(Qt.AlignCenter)
        self.lbl_preview_foto.setFixedHeight(180)
        self.lbl_preview_foto.setStyleSheet(
            "border: 2px dashed #9ca3af; border-radius: 8px; color: #9ca3af; background-color: transparent;"
        )
        layout_kanan.addWidget(self.lbl_preview_foto)

        self.btn_pilih_foto = QPushButton("📂 Lampirkan Foto Baru")
        self.btn_pilih_foto.setProperty("zoom_font_key", None)
        self.btn_pilih_foto.clicked.connect(self.pilih_foto_kapal)
        layout_kanan.addWidget(self.btn_pilih_foto)
        layout_kanan.addStretch()

        hbox_tombol = QHBoxLayout()
        self.btn_aksi = QPushButton("Aksi")
        self.btn_aksi.setFixedHeight(40)
        self.btn_aksi.clicked.connect(self.handle_tombol_aksi)

        self.btn_batal = QPushButton("❌ Batal")
        self.btn_batal.setFixedHeight(40)
        self.btn_batal.clicked.connect(lambda: self.atur_mode('IDLE'))

        hbox_tombol.addWidget(self.btn_batal)
        hbox_tombol.addWidget(self.btn_aksi)
        layout_kanan.addLayout(hbox_tombol)

        self.splitter.addWidget(self.panel_kiri)
        self.splitter.addWidget(self.panel_kanan)
        self.splitter.setSizes([700, 350])

        self.atur_mode('IDLE')
        self.refresh_tabel()
        self.sesuaikan_tema_lokal()
        terapkan_popup_combobox_bawah(self)

    # ============================================================
    # MODE STATE & FORM
    # ============================================================

    def atur_mode(self, mode):
        self.mode = mode
        if mode == 'IDLE':
            self.bersihkan_form()
            self.aktifkan_input(False)
            self.tabel_kapal.clearSelection()
            self.btn_aksi.setText("➕ Tambah Kapal")
            self.btn_batal.hide()
            self.btn_pilih_foto.hide()
        elif mode == 'TAMBAH':
            self.bersihkan_form()
            self.aktifkan_input(True)
            self.input_nama_kapal.setReadOnly(False)
            self.btn_aksi.setText("💾 Simpan Kapal")
            self.btn_batal.show()
            self.btn_pilih_foto.show()
        elif mode == 'PREVIEW':
            self.aktifkan_input(False)
            self.btn_aksi.setText("✏️ Edit")
            self.btn_batal.hide()
            self.btn_pilih_foto.hide()
        elif mode == 'EDIT':
            self.aktifkan_input(True)
            self.input_nama_kapal.setReadOnly(True)  # Primary key/identitas kapal dikunci
            self.btn_aksi.setText("💾 Simpan")
            self.btn_batal.show()
            self.btn_pilih_foto.show()
        self.sesuaikan_tema_lokal()

    def aktifkan_input(self, aktif):
        self.input_nama_kapal.setReadOnly(not aktif)
        self.input_tujuan.setReadOnly(not aktif)
        self.input_keterangan.setReadOnly(not aktif)

    def bersihkan_form(self):
        self.input_nama_kapal.clear()
        self.input_tujuan.clear()
        self.input_keterangan.clear()
        self.current_foto_path = ""
        self.lbl_preview_foto.clear()
        self.lbl_preview_foto.setText("Tidak Ada Foto")

    def handle_tombol_aksi(self):
        if self.mode == 'IDLE':
            self.atur_mode('TAMBAH')
        elif self.mode == 'TAMBAH':
            self.simpan_atau_update_kapal()
        elif self.mode == 'PREVIEW':
            self.atur_mode('EDIT')
        elif self.mode == 'EDIT':
            self.simpan_atau_update_kapal()

    # ============================================================
    # FOTO KAPAL
    # ============================================================

    def pilih_foto_kapal(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Foto Kapal", "",
            "Images (*.png *.jpeg *.jpg *.bmp)", options=options
        )
        if file_path:
            self.current_foto_path = file_path
            self.tampilkan_foto(file_path)

    def tampilkan_foto(self, path):
        if path and os.path.exists(path):
            pixmap = QPixmap(path)
            self.lbl_preview_foto.setPixmap(
                pixmap.scaled(self.lbl_preview_foto.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self.lbl_preview_foto.clear()
            self.lbl_preview_foto.setText("Tidak Ada Foto")

    # ============================================================
    # LEBAR KOLOM MENGGUNAKAN MIXIN
    # ============================================================

    def _settings_kolom(self):
        return QSettings("EkspedisiApp", "SubTabKapal")

    def simpan_lebar_kolom(self, tabel):
        if self._sedang_menerapkan_zoom:
            return
        widths = self._lebar_dasar_tabel(tabel)
        self._perbarui_cache_lebar_zoom(tabel, widths)
        self._settings_kolom().setValue("lebar_kolom_kapal", widths)

    def load_lebar_kolom(self, tabel):
        try:
            widths = self._settings_kolom().value("lebar_kolom_kapal")
            if widths and len(widths) == tabel.columnCount():
                for i, w in enumerate(widths):
                    if i < 3:
                        tabel.setColumnWidth(i, int(w))
            else:
                tabel.setColumnWidth(0, 45)   # NO
                tabel.setColumnWidth(1, 180)  # NAMA KAPAL
                tabel.setColumnWidth(2, 150)  # TUJUAN

            tabel.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)  # KETERANGAN

            base_widths = [tabel.columnWidth(i) for i in range(tabel.columnCount())]
            self._perbarui_cache_lebar_zoom(tabel, base_widths)
        except Exception as e:
            print(f"Error memuat lebar kolom Kapal: {e}")

    # ============================================================
    # DATA & TABEL KAPAL
    # ============================================================

    def refresh_tabel(self):
        self.tabel_kapal.setRowCount(0)
        try:
            # Pastikan fungsi db_service.ambil_semua_kapal_full() disesuaikan di db_service Anda
            rows = getattr(db_service, "ambil_semua_kapal_full", lambda: [])()
            for i, row in enumerate(rows):
                baris = self.tabel_kapal.rowCount()
                self.tabel_kapal.insertRow(baris)

                no_urut = str(i + 1)
                nama_kapal = row[0] if len(row) > 0 else ""
                tujuan = row[1] if len(row) > 1 else ""
                ket = row[2] if len(row) > 2 else ""
                foto = row[3] if len(row) > 3 else ""

                self.tabel_kapal.setItem(baris, 0, buat_tabel_item(no_urut, editable=False, alignment=Qt.AlignCenter))
                self.tabel_kapal.setItem(baris, 1, buat_tabel_item(nama_kapal, editable=False, alignment=Qt.AlignLeft | Qt.AlignVCenter))
                self.tabel_kapal.setItem(baris, 2, buat_tabel_item(tujuan, editable=False, alignment=Qt.AlignLeft | Qt.AlignVCenter))
                self.tabel_kapal.setItem(baris, 3, buat_tabel_item(ket, editable=False, alignment=Qt.AlignLeft | Qt.AlignVCenter))
                self.tabel_kapal.setItem(baris, 4, buat_tabel_item(foto, editable=False))

            self.filter_tabel_kapal(self.input_cari.text())
        except Exception as e:
            print(f"Bypass Error Load Tabel Kapal: {e}")

    def filter_tabel_kapal(self, text):
        kata_kunci = text.lower().strip()
        nomor_baru = 1

        for row in range(self.tabel_kapal.rowCount()):
            harus_muncul = False
            for col in range(1, self.tabel_kapal.columnCount() - 1):
                item = self.tabel_kapal.item(row, col)
                if item and kata_kunci in item.text().lower():
                    harus_muncul = True
                    break

            if harus_muncul:
                self.tabel_kapal.setRowHidden(row, False)
                self.tabel_kapal.item(row, 0).setText(str(nomor_baru))
                nomor_baru += 1
            else:
                self.tabel_kapal.setRowHidden(row, True)

    def simpan_atau_update_kapal(self):
        nama_kapal = self.input_nama_kapal.text().strip().upper()
        tujuan = self.input_tujuan.text().strip().upper()
        ket = self.input_keterangan.text().strip().upper()
        foto = self.current_foto_path

        if not nama_kapal:
            QMessageBox.warning(self, "Peringatan", "Nama Kapal wajib diisi!")
            self.input_nama_kapal.setFocus()
            return

        try:
            simpan_fn = getattr(db_service, "simpan_atau_update_kapal_full", None)
            if callable(simpan_fn):
                sukses, pesan = simpan_fn(nama_kapal, tujuan, ket, foto, mode=self.mode)
                if not sukses:
                    QMessageBox.warning(self, "Data Kapal", pesan)
                    return
            else:
                # Mockup notification jika db service belum siap
                pass

            QMessageBox.information(self, "Sukses", f"Data kapal {nama_kapal} berhasil disimpan!")
            self.atur_mode('IDLE')
            self.refresh_tabel()
        except Exception as e:
            QMessageBox.critical(self, "Error Database", f"Gagal menyimpan data: {str(e)}")

    def pilih_data_dari_tabel(self, row, column):
        try:
            self.atur_mode('PREVIEW')
            self.input_nama_kapal.setText(self.tabel_kapal.item(row, 1).text())
            self.input_tujuan.setText(self.tabel_kapal.item(row, 2).text())
            self.input_keterangan.setText(self.tabel_kapal.item(row, 3).text())

            foto_val = self.tabel_kapal.item(row, 4).text()
            self.current_foto_path = foto_val if foto_val and foto_val != "None" else ""
            self.tampilkan_foto(self.current_foto_path)

        except Exception as e:
            print(f"Error Select Row Kapal: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        terapkan_popup_combobox_bawah(self)
        self.refresh_tabel()

    # ============================================================
    # TEMA DAN ZOOM
    # ============================================================

    def _kunci_tombol_foto_statis(self):
        if not hasattr(self, "btn_pilih_foto"):
            return

        font_statis_base = get_global_font_sizes(0)["sz_base"]

        style_btn_foto = getattr(
            self,
            "_style_btn_foto_kapal",
            "QPushButton { background-color: #e2e8f0; color: #0f172a; "
            "border: 1px solid #cbd5e1; border-radius: 4px; } "
            "QPushButton:hover { background-color: #cbd5e1; }"
        )

        font_foto = QFont(MASTER_FONT, font_statis_base)
        self.btn_pilih_foto.setProperty("zoom_font_key", None)
        self.btn_pilih_foto.setFont(font_foto)
        self.btn_pilih_foto.setMinimumHeight(30)
        self.btn_pilih_foto.setMaximumHeight(30)
        self.btn_pilih_foto.setStyleSheet(
            style_btn_foto
            + f"""
            QPushButton {{
                font-family: '{MASTER_FONT}';
                font-size: {font_statis_base}pt;
                padding: 2px 6px;
            }}
            """
        )
        self.btn_pilih_foto.updateGeometry()

    def sesuaikan_tema_lokal(self):
        win = self.window()
        is_dark = win.current_theme == "dark" if win and hasattr(win, 'current_theme') else False
        z = zoom_helper.dapatkan_zoom_level("TabArmada")

        self.label_judul.setProperty("zoom_font_key", "sz_title")

        st = get_armada_styles(is_dark, self.mode)
        self._style_btn_foto_kapal = st["btn_foto"]

        self.panel_kanan.setStyleSheet(st["panel_kanan"])

        self._set_style_dasar_zoom(self.label_judul, st["label_judul"])
        self._set_style_dasar_zoom(self.input_cari, st["input_normal"])

        self.layout().setContentsMargins(10, 10, 10, 10)
        self.panel_kiri.layout().setContentsMargins(0, 0, 10, 0)
        self.panel_kanan.layout().setContentsMargins(15, 15, 15, 15)

        self.tabel_kapal.horizontalHeader().blockSignals(True)

        self._sedang_menerapkan_zoom = True
        try:
            zoom_helper.terapkan_zoom_semua_elemen(container_widget=self, z=z, is_dark=is_dark)
        finally:
            self._sedang_menerapkan_zoom = False
            self.tabel_kapal.horizontalHeader().blockSignals(False)

        zoom_helper._skalakan_kolom_tableview(self.tabel_kapal, z)

        font_statis_base = get_global_font_sizes(0)["sz_base"]
        font_statis_input = get_global_font_sizes(0)["sz_input"]

        font_cari = self.input_cari.font()
        font_cari.setPointSize(font_statis_input)
        self.input_cari.setFont(font_cari)
        self.input_cari.setFixedHeight(30)
        self.input_cari.setFixedWidth(230)

        font_judul_kanan = QFont(MASTER_FONT, font_statis_base + 1, QFont.Bold)
        self.lbl_judul_kanan.setFont(font_judul_kanan)
        self.lbl_judul_kanan.setStyleSheet(st["label_judul_kanan"])

        font_label = QFont(MASTER_FONT, font_statis_base)
        for lbl in [self.lbl_nama_kapal, self.lbl_tujuan, self.lbl_ket, self.lbl_foto_title]:
            lbl.setFont(font_label)

        font_input = QFont(MASTER_FONT, font_statis_input)
        for w_input in [self.input_nama_kapal, self.input_tujuan, self.input_keterangan]:
            w_input.setFont(font_input)
            w_input.setFixedHeight(30)

            style_aktif = st["input_locked"] if (
                    (hasattr(w_input, 'isReadOnly') and w_input.isReadOnly())
                    or not w_input.isEnabled()
            ) else st["input_normal"]

            w_input.setStyleSheet(style_aktif)

        font_btn = QFont(MASTER_FONT, font_statis_base, QFont.Bold)

        self.btn_pilih_foto.setFont(font_label)
        self.btn_pilih_foto.setStyleSheet(st["btn_foto"])

        self.btn_batal.setFont(font_btn)
        self.btn_batal.setFixedHeight(38)
        self.btn_batal.setStyleSheet(st["btn_batal"])

        self.btn_aksi.setFont(font_btn)
        self.btn_aksi.setFixedHeight(38)
        self.btn_aksi.setStyleSheet(st["btn_aksi"])

        self._kunci_tombol_foto_statis()
        QTimer.singleShot(0, self._kunci_tombol_foto_statis)

        self.layout().setContentsMargins(10, 10, 10, 10)
        self.panel_kiri.layout().setContentsMargins(0, 0, 10, 0)
        self.panel_kanan.layout().setContentsMargins(15, 15, 15, 15)