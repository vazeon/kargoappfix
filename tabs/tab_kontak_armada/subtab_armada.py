# tabs/tab_kontak_armada/subtab_armada.py
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



class SubTabArmada(QWidget, ZoomTableMixin):
    def __init__(self, parent=None):
        super().__init__(parent)
        db_service.migrasi_cek_kolom_armada()
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
        self.label_judul = QLabel("🚚 List Data Armada")
        self.label_judul.setFont(QFont(MASTER_FONT, 14, QFont.Bold))
        layout_judul_search.addWidget(self.label_judul)
        layout_judul_search.addStretch()

        self.input_cari = QLineEdit()
        self.input_cari.setPlaceholderText("Cari di Armada...")
        self.input_cari.setProperty("zoom_font_key", "sz_input")
        self.input_cari.setFixedWidth(230)
        self.input_cari.textChanged.connect(lambda _t: helper_paksa_kapital_lineedit(self.input_cari))
        self.input_cari.textChanged.connect(self.filter_tabel_armada)
        layout_judul_search.addWidget(self.input_cari)
        layout_kiri.addLayout(layout_judul_search)

        self.tabel_armada = QTableWidget()
        self.tabel_armada.setColumnCount(7)
        self.tabel_armada.setHorizontalHeaderLabels([
            "NO", "JENIS", "NO. POL", "NAMA SOPIR", "NO. HP", "KETERANGAN", "FOTO"
        ])

        self.tabel_armada.setColumnHidden(6, True)
        self.tabel_armada.setAlternatingRowColors(True)
        self.tabel_armada.verticalHeader().setVisible(False)
        self.tabel_armada.horizontalHeader().setFixedHeight(35)
        self.tabel_armada.verticalHeader().setDefaultSectionSize(32)
        self.tabel_armada.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabel_armada.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabel_armada.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabel_armada.cellClicked.connect(self.pilih_data_dari_tabel)
        layout_kiri.addWidget(self.tabel_armada)

        self.load_lebar_kolom(self.tabel_armada)
        self.tabel_armada.horizontalHeader().sectionResized.connect(
            lambda _logicalIndex, _oldSize, _newSize: self.simpan_lebar_kolom(self.tabel_armada)
        )

        # ========================================================
        # PANEL KANAN: Detail & Editor Area
        # ========================================================
        self.panel_kanan = QFrame()
        self.panel_kanan.setObjectName("panelEditor")
        layout_kanan = QVBoxLayout(self.panel_kanan)
        layout_kanan.setContentsMargins(15, 15, 15, 15)

        self.lbl_judul_kanan = QLabel("📋 Detail / Editor Armada")
        self.lbl_judul_kanan.setFont(QFont(MASTER_FONT, 12, QFont.Bold))
        self.lbl_judul_kanan.setAlignment(Qt.AlignCenter)
        layout_kanan.addWidget(self.lbl_judul_kanan)

        self.lbl_jenis = QLabel("Jenis Truk:")
        self.combo_jenis = QComboBox()
        self.combo_jenis.addItem("- Pilih jenis -")
        self.combo_jenis.addItems(["TB", "Tronton", "CDD", "Pick-up", "Lainnya..."])
        self.combo_jenis.setEditable(False)
        self.combo_jenis.setProperty("zoom_font_key", None)
        self.combo_jenis.currentIndexChanged.connect(self.on_jenis_truk_changed)
        layout_kanan.addWidget(self.lbl_jenis)
        layout_kanan.addWidget(self.combo_jenis)

        self.lbl_jenis_lain = QLabel("Jenis Truk Lainnya:")
        self.input_jenis_lain = QLineEdit()
        self.input_jenis_lain.setPlaceholderText("Contoh: FUSO WINGBOX")
        self.input_jenis_lain.textChanged.connect(
            lambda _t: helper_paksa_kapital_lineedit(self.input_jenis_lain)
        )
        self.lbl_jenis_lain.hide()
        self.input_jenis_lain.hide()
        layout_kanan.addWidget(self.lbl_jenis_lain)
        layout_kanan.addWidget(self.input_jenis_lain)

        self.lbl_nopol = QLabel("No. Polisi:")
        self.input_nopol = QLineEdit()
        self.input_nopol.setPlaceholderText("Contoh: L 1234 AB")
        self.input_nopol.textChanged.connect(lambda _t: helper_paksa_kapital_lineedit(self.input_nopol))
        layout_kanan.addWidget(self.lbl_nopol)
        layout_kanan.addWidget(self.input_nopol)

        self.lbl_sopir = QLabel("Nama Sopir:")
        self.input_sopir = QLineEdit()
        self.input_sopir.setPlaceholderText("Masukkan Nama")
        self.input_sopir.textChanged.connect(lambda _t: helper_paksa_kapital_lineedit(self.input_sopir))
        layout_kanan.addWidget(self.lbl_sopir)
        layout_kanan.addWidget(self.input_sopir)

        self.lbl_hp = QLabel("No. HP / WA:")
        self.input_hp_sopir = QLineEdit()
        self.input_hp_sopir.setPlaceholderText("081xxx")
        layout_kanan.addWidget(self.lbl_hp)
        layout_kanan.addWidget(self.input_hp_sopir)

        self.lbl_ket = QLabel("Keterangan:")
        self.input_keterangan = QLineEdit()
        self.input_keterangan.setPlaceholderText("Milik Perusahaan / Sewa")
        self.input_keterangan.textChanged.connect(lambda _t: helper_paksa_kapital_lineedit(self.input_keterangan))
        layout_kanan.addWidget(self.lbl_ket)
        layout_kanan.addWidget(self.input_keterangan)

        layout_kanan.addSpacing(10)
        self.lbl_foto_title = QLabel("📷 Foto Armada:")
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
        self.btn_pilih_foto.clicked.connect(self.pilih_foto_armada)
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
            self.tabel_armada.clearSelection()
            self.btn_aksi.setText("➕ Tambah Armada")
            self.btn_batal.hide()
            self.btn_pilih_foto.hide()
        elif mode == 'TAMBAH':
            self.bersihkan_form()
            self.aktifkan_input(True)
            self.input_nopol.setReadOnly(False)
            self.btn_aksi.setText("💾 Simpan Armada")
            self.btn_batal.show()
            self.btn_pilih_foto.show()
        elif mode == 'PREVIEW':
            self.aktifkan_input(False)
            self.btn_aksi.setText("✏️ Edit")
            self.btn_batal.hide()
            self.btn_pilih_foto.hide()
        elif mode == 'EDIT':
            self.aktifkan_input(True)
            self.input_nopol.setReadOnly(True)
            self.btn_aksi.setText("💾 Simpan")
            self.btn_batal.show()
            self.btn_pilih_foto.show()
        self.sesuaikan_tema_lokal()

    def aktifkan_input(self, aktif):
        self.combo_jenis.setEnabled(aktif)
        self.input_jenis_lain.setReadOnly(not aktif)
        self.input_nopol.setReadOnly(not aktif)
        self.input_sopir.setReadOnly(not aktif)
        self.input_hp_sopir.setReadOnly(not aktif)
        self.input_keterangan.setReadOnly(not aktif)
        self.on_jenis_truk_changed(self.combo_jenis.currentIndex())

    def on_jenis_truk_changed(self, _index=None):
        """Menampilkan input khusus hanya ketika pilihan Lainnya digunakan."""
        pilih_lainnya = self.combo_jenis.currentText().strip() == "Lainnya..."
        self.lbl_jenis_lain.setVisible(pilih_lainnya)
        self.input_jenis_lain.setVisible(pilih_lainnya)

        if not pilih_lainnya:
            self.input_jenis_lain.clear()

    def ambil_jenis_truk_final(self):
        """Menghasilkan nama jenis truk yang siap disimpan ke database."""
        pilihan = self.combo_jenis.currentText().strip()
        if pilihan == "Lainnya...":
            return self.input_jenis_lain.text().strip().upper()
        if self.combo_jenis.currentIndex() <= 0:
            return ""
        return pilihan

    def set_jenis_truk_form(self, jenis):
        """Memilih jenis baku atau mengalihkan jenis tidak umum ke Lainnya."""
        jenis_bersih = str(jenis or "").strip()
        if not jenis_bersih:
            self.combo_jenis.setCurrentIndex(0)
            return

        for index in range(1, self.combo_jenis.count()):
            item_text = self.combo_jenis.itemText(index)
            if item_text == "Lainnya...":
                continue
            if item_text.casefold() == jenis_bersih.casefold():
                self.combo_jenis.setCurrentIndex(index)
                return

        idx_lainnya = self.combo_jenis.findText("Lainnya...", Qt.MatchFixedString)
        self.combo_jenis.setCurrentIndex(idx_lainnya)
        self.input_jenis_lain.setText(jenis_bersih.upper())

    def bersihkan_form(self):
        self.combo_jenis.setCurrentIndex(0)
        self.input_jenis_lain.clear()
        self.input_nopol.clear()
        self.input_sopir.clear()
        self.input_hp_sopir.clear()
        self.input_keterangan.clear()
        self.current_foto_path = ""
        self.lbl_preview_foto.clear()
        self.lbl_preview_foto.setText("Tidak Ada Foto")

    def handle_tombol_aksi(self):
        if self.mode == 'IDLE':
            self.atur_mode('TAMBAH')
        elif self.mode == 'TAMBAH':
            self.simpan_atau_update_armada()
        elif self.mode == 'PREVIEW':
            self.atur_mode('EDIT')
        elif self.mode == 'EDIT':
            self.simpan_atau_update_armada()

    # ============================================================
    # FOTO ARMADA
    # ============================================================

    def pilih_foto_armada(self):
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Pilih Foto Unit Armada", "",
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
        return QSettings("EkspedisiApp", "SubTabArmada")

    def simpan_lebar_kolom(self, tabel):
        if self._sedang_menerapkan_zoom:
            return
        widths = self._lebar_dasar_tabel(tabel)  # 💡 Dari Mixin
        self._perbarui_cache_lebar_zoom(tabel, widths)  # 💡 Dari Mixin
        self._settings_kolom().setValue("lebar_kolom_armada", widths)

    def load_lebar_kolom(self, tabel):
        try:
            widths = self._settings_kolom().value("lebar_kolom_armada")
            if widths and len(widths) == tabel.columnCount():
                for i, w in enumerate(widths):
                    if i < 5:
                        tabel.setColumnWidth(i, int(w))
            else:
                tabel.setColumnWidth(0, 45)
                tabel.setColumnWidth(1, 80)
                tabel.setColumnWidth(2, 110)
                tabel.setColumnWidth(3, 140)
                tabel.setColumnWidth(4, 120)

            tabel.horizontalHeader().setSectionResizeMode(5, QHeaderView.Stretch)

            base_widths = [tabel.columnWidth(i) for i in range(tabel.columnCount())]
            self._perbarui_cache_lebar_zoom(tabel, base_widths)
        except Exception as e:
            print(f"Error memuat lebar kolom Armada: {e}")

    # ============================================================
    # DATA & TABEL ARMADA
    # ============================================================

    def refresh_tabel(self):
        self.tabel_armada.setRowCount(0)
        try:
            rows = db_service.ambil_semua_armada_full()
            for i, row in enumerate(rows):
                baris = self.tabel_armada.rowCount()
                self.tabel_armada.insertRow(baris)

                # 💡 Mendeklarasikan variabel agar lebih deskriptif dan mudah dibaca
                no_urut = str(i + 1)
                nopol = row[0]
                jenis = row[1]
                sopir = row[2]
                hp = row[3]
                ket = row[4]
                foto = row[5]

                # 💡 Menggunakan fungsi buat_tabel_item()
                self.tabel_armada.setItem(baris, 0, buat_tabel_item(no_urut, editable=False, alignment=Qt.AlignCenter))
                self.tabel_armada.setItem(baris, 1, buat_tabel_item(jenis, editable=False, alignment=Qt.AlignCenter))
                self.tabel_armada.setItem(baris, 2, buat_tabel_item(nopol, editable=False,
                                                                    alignment=Qt.AlignLeft | Qt.AlignVCenter))
                self.tabel_armada.setItem(baris, 3, buat_tabel_item(sopir, editable=False,
                                                                    alignment=Qt.AlignLeft | Qt.AlignVCenter))
                self.tabel_armada.setItem(baris, 4, buat_tabel_item(hp, editable=False, alignment=Qt.AlignCenter))
                self.tabel_armada.setItem(baris, 5, buat_tabel_item(ket, editable=False,
                                                                    alignment=Qt.AlignLeft | Qt.AlignVCenter))
                self.tabel_armada.setItem(baris, 6, buat_tabel_item(foto, editable=False))

            self.filter_tabel_armada(self.input_cari.text())
        except Exception as e:
            print(f"Bypass Error Load Tabel Armada: {e}")

    def filter_tabel_armada(self, text):
        kata_kunci = text.lower().strip()
        nomor_baru = 1

        for row in range(self.tabel_armada.rowCount()):
            harus_muncul = False
            for col in range(1, self.tabel_armada.columnCount() - 1):
                item = self.tabel_armada.item(row, col)
                if item and kata_kunci in item.text().lower():
                    harus_muncul = True
                    break

            if harus_muncul:
                self.tabel_armada.setRowHidden(row, False)
                self.tabel_armada.item(row, 0).setText(str(nomor_baru))
                nomor_baru += 1
            else:
                self.tabel_armada.setRowHidden(row, True)

    def simpan_atau_update_armada(self):
        nopol = self.input_nopol.text().strip().upper()
        sopir = self.input_sopir.text().strip().upper()
        hp = self.input_hp_sopir.text().strip()
        jenis = self.ambil_jenis_truk_final()
        ket = self.input_keterangan.text().strip().upper()
        foto = self.current_foto_path

        if not nopol:
            QMessageBox.warning(self, "Peringatan", "No. Polisi wajib diisi!")
            self.input_nopol.setFocus()
            return

        if not jenis:
            if self.combo_jenis.currentText().strip() == "Lainnya...":
                QMessageBox.warning(self, "Peringatan", "Jenis Truk Lainnya wajib diisi!")
                self.input_jenis_lain.setFocus()
            else:
                QMessageBox.warning(self, "Peringatan", "Jenis Truk wajib dipilih!")
                self.combo_jenis.setFocus()
            return

        try:
            sukses, pesan = db_service.simpan_atau_update_armada_full(
                nopol, jenis, sopir, hp, ket, foto, mode=self.mode
            )

            if not sukses:
                QMessageBox.warning(self, "Data Armada", pesan)
                return

            QMessageBox.information(self, "Sukses", f"Data armada {nopol} berhasil disimpan!")
            self.atur_mode('IDLE')
            self.refresh_tabel()
        except Exception as e:
            QMessageBox.critical(self, "Error Database", f"Gagal menyimpan data:\n{str(e)}")

    def pilih_data_dari_tabel(self, row, column):
        try:
            self.atur_mode('PREVIEW')
            self.input_nopol.setText(self.tabel_armada.item(row, 2).text())
            self.input_sopir.setText(self.tabel_armada.item(row, 3).text())

            hp_val = self.tabel_armada.item(row, 4).text()
            self.input_hp_sopir.setText("" if hp_val == "-" else hp_val)
            self.input_keterangan.setText(self.tabel_armada.item(row, 5).text())

            jenis_text = self.tabel_armada.item(row, 1).text()
            self.set_jenis_truk_form(jenis_text)

            foto_val = self.tabel_armada.item(row, 6).text()
            self.current_foto_path = foto_val if foto_val and foto_val != "None" else ""
            self.tampilkan_foto(self.current_foto_path)

        except Exception as e:
            print(f"Error Select Row: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        terapkan_popup_combobox_bawah(self)

        self.refresh_tabel()
        # Tema dikelola oleh TabKontakArmada.

    # ============================================================
    # TEMA DAN ZOOM
    # ============================================================

    def _kunci_combo_dan_tombol_foto_statis(self):
        """
        Mengunci ComboBox Jenis Truk dan tombol Lampirkan Foto agar tidak
        berubah ukuran ketika helper zoom global dijalankan oleh main window.

        Main window menerapkan zoom global setelah sesuaikan_tema_lokal().
        Karena itu fungsi ini dipanggil langsung dan sekali lagi melalui
        QTimer.singleShot(0, ...) agar menjadi lapisan terakhir.
        """
        if not hasattr(self, "combo_jenis") or not hasattr(self, "btn_pilih_foto"):
            return

        font_statis_base = get_global_font_sizes(0)["sz_base"]
        font_statis_input = get_global_font_sizes(0)["sz_input"]

        style_input_normal = getattr(
            self,
            "_style_input_normal_armada",
            "background-color: #ffffff; color: #0f172a; "
            "border: 1px solid #cbd5e1; border-radius: 4px;"
        )
        style_input_locked = getattr(
            self,
            "_style_input_locked_armada",
            "background-color: #f1f5f9; color: #64748b; "
            "border: 1px dashed #cbd5e1; border-radius: 4px;"
        )
        style_btn_foto = getattr(
            self,
            "_style_btn_foto_armada",
            "QPushButton { background-color: #e2e8f0; color: #0f172a; "
            "border: 1px solid #cbd5e1; border-radius: 4px; } "
            "QPushButton:hover { background-color: #cbd5e1; }"
        )

        # --------------------------------------------------------
        # ComboBox Jenis Truk: teks aktif, editor, dan dropdown
        # --------------------------------------------------------
        font_combo_size = max(8, font_statis_input - 1)
        font_combo = QFont(MASTER_FONT, font_combo_size)
        self.combo_jenis.setProperty("zoom_font_key", None)
        self.combo_jenis.setFont(font_combo)
        self.combo_jenis.setMinimumHeight(30)
        self.combo_jenis.setMaximumHeight(30)

        combo_style = (
            style_input_locked if not self.combo_jenis.isEnabled()
            else style_input_normal
        )
        self.combo_jenis.setStyleSheet(
            f"{combo_style} "
            f"font-family: '{MASTER_FONT}'; "
            f"font-size: {font_combo_size}pt; "
            "padding: 1px 5px;"
        )

        combo_editor = self.combo_jenis.lineEdit()
        if combo_editor is not None:
            combo_editor.setProperty("zoom_font_key", None)
            combo_editor.setFont(font_combo)
            combo_editor.setMinimumHeight(26)
            combo_editor.setMaximumHeight(26)
            combo_editor.setStyleSheet(
                f"font-family: '{MASTER_FONT}'; "
                f"font-size: {font_combo_size}pt; "
                "background: transparent; border: none; padding: 0px 2px;"
            )

        combo_view = self.combo_jenis.view()
        if combo_view is not None:
            combo_view.setFont(font_combo)
            combo_view.setStyleSheet(f"""
                QAbstractItemView {{
                    font-family: '{MASTER_FONT}';
                    font-size: {font_combo_size}pt;
                }}
                QAbstractItemView::item {{
                    min-height: 26px;
                    max-height: 26px;
                    padding: 2px 5px;
                }}
            """)

        # --------------------------------------------------------
        # Tombol Lampirkan Foto: font, tinggi, dan padding statis
        # --------------------------------------------------------
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

        self.combo_jenis.updateGeometry()
        self.btn_pilih_foto.updateGeometry()

    def sesuaikan_tema_lokal(self):
        win = self.window()
        is_dark = win.current_theme == "dark" if win and hasattr(win, 'current_theme') else False
        z = zoom_helper.dapatkan_zoom_level("TabKontakArmada")

        self.label_judul.setProperty("zoom_font_key", "sz_title")

        # 1. Ambil dictionary style dari modul terpusat
        st = get_armada_styles(is_dark, self.mode)

        # Simpan style aktif untuk callback pengunci statis
        self._style_input_normal_armada = st["input_normal"]
        self._style_input_locked_armada = st["input_locked"]
        self._style_btn_foto_armada = st["btn_foto"]

        self.panel_kanan.setStyleSheet(st["panel_kanan"])

        # Style Panel Kiri (Mengikut Zoom)
        self._set_style_dasar_zoom(self.label_judul, st["label_judul"])
        self._set_style_dasar_zoom(self.input_cari, st["input_normal"])

        # --- RESET MARGIN ANTI-OVERFLOW ---
        self.layout().setContentsMargins(10, 10, 10, 10)
        self.panel_kiri.layout().setContentsMargins(0, 0, 10, 0)
        self.panel_kanan.layout().setContentsMargins(15, 15, 15, 15)

        # Blokir signal tabel
        self.tabel_armada.horizontalHeader().blockSignals(True)

        self._sedang_menerapkan_zoom = True
        try:
            zoom_helper.terapkan_zoom_semua_elemen(container_widget=self, z=z, is_dark=is_dark)
        finally:
            self._sedang_menerapkan_zoom = False
            self.tabel_armada.horizontalHeader().blockSignals(False)

        # Paksa skala kolom tabel
        zoom_helper._skalakan_kolom_tableview(self.tabel_armada, z)

        # ========================================================
        # --- KUNCI STATIS TOTAL PANEL KANAN (EDITOR ARMADA) ---
        # ========================================================
        font_statis_base = get_global_font_sizes(0)["sz_base"]
        font_statis_input = get_global_font_sizes(0)["sz_input"]

        # 1. Input Pencarian Kiri (Kebal Zoom)
        font_cari = self.input_cari.font()
        font_cari.setPointSize(font_statis_input)
        self.input_cari.setFont(font_cari)
        self.input_cari.setFixedHeight(30)
        self.input_cari.setFixedWidth(230)

        # 2. Judul & Label Form Editor
        font_judul_kanan = QFont(MASTER_FONT, font_statis_base + 1, QFont.Bold)
        self.lbl_judul_kanan.setFont(font_judul_kanan)

        # 💡 PERBAIKAN DI SINI: Gunakan st["label_judul_kanan"] menggantikan style_label_judul_kanan
        self.lbl_judul_kanan.setStyleSheet(st["label_judul_kanan"])

        font_label = QFont(MASTER_FONT, font_statis_base)
        for lbl in [self.lbl_jenis, self.lbl_jenis_lain, self.lbl_nopol, self.lbl_sopir, self.lbl_hp, self.lbl_ket,
                    self.lbl_foto_title]:
            lbl.setFont(font_label)

        # 3. Widget Input Form Editor
        font_input = QFont(MASTER_FONT, font_statis_input)
        for w_input in [self.input_jenis_lain, self.input_nopol, self.input_sopir, self.input_hp_sopir,
                        self.input_keterangan, self.combo_jenis]:
            w_input.setFont(font_input)
            w_input.setFixedHeight(30)

            style_aktif = st["input_locked"] if (
                    (hasattr(w_input, 'isReadOnly') and w_input.isReadOnly())
                    or not w_input.isEnabled()
            ) else st["input_normal"]

            w_input.setStyleSheet(style_aktif)

        # FIX: teks TB pada editor internal QComboBox
        combo_editor = self.combo_jenis.lineEdit()
        if combo_editor is not None:
            combo_editor.setFont(font_input)
            combo_editor.setProperty("zoom_font_key", None)

        if self.combo_jenis.view():
            self.combo_jenis.view().setFont(font_input)
            self.combo_jenis.view().setStyleSheet(f"""
                        QAbstractItemView {{
                            font-family: '{MASTER_FONT}';
                            font-size: {font_statis_input}pt;
                        }}
                        QAbstractItemView::item {{
                            min-height: 26px;
                            padding: 2px 5px;
                        }}
                    """)

        # 4. Tombol-tombol Editor
        font_btn = QFont(MASTER_FONT, font_statis_base, QFont.Bold)

        self.btn_pilih_foto.setFont(font_label)
        self.btn_pilih_foto.setStyleSheet(st["btn_foto"])

        self.btn_batal.setFont(font_btn)
        self.btn_batal.setFixedHeight(38)
        self.btn_batal.setStyleSheet(st["btn_batal"])

        self.btn_aksi.setFont(font_btn)
        self.btn_aksi.setFixedHeight(38)
        self.btn_aksi.setStyleSheet(st["btn_aksi"])

        self._kunci_combo_dan_tombol_foto_statis()
        QTimer.singleShot(0, self._kunci_combo_dan_tombol_foto_statis)

        # --- KUNCI MATI MARGIN LAYOUT ---
        self.layout().setContentsMargins(10, 10, 10, 10)
        self.panel_kiri.layout().setContentsMargins(0, 0, 10, 0)
        self.panel_kanan.layout().setContentsMargins(15, 15, 15, 15)

