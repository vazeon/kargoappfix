# tabs/tab_setting.py
import json
import os
import re
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit,
    QPushButton, QMessageBox, QGroupBox, QTextEdit, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout, QLabel,
    QListWidget, QListWidgetItem, QStackedWidget, QApplication, QSizePolicy, QSpacerItem
)
from PyQt5.QtCore import Qt, QSettings, QEvent
from PyQt5.QtGui import QFontDatabase
from config import CURRENT_SESSION, DATA_CLIENT

import services.database_service as db_service

from themes.modules.setting import get_setting_styles

from utils.typography import (
    get_master_font,
    perbarui_font_master,
)

class TabSettingSistem(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.load_current_settings()

    def init_ui(self):
        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # ── 1. SIDEBAR KIRI (Navigasi) ──
        self.sidebar_container = QWidget()
        self.sidebar_container.setFixedWidth(240)
        sidebar_layout = QVBoxLayout(self.sidebar_container)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(8)

        self.lbl_menu = QLabel("Preferences")
        sidebar_layout.addWidget(self.lbl_menu)

        self.sidebar_list = QListWidget()
        self.sidebar_list.setFocusPolicy(Qt.NoFocus)

        menus = [
            "🏢  Identitas & Sistem",
            "📦  Format & Resi",
            "🏦  Rekening Bank",
            "📍  Kantor Cabang",
            "🎨  Tampilan & Font"
        ]
        self.sidebar_list.addItems(menus)
        self.sidebar_list.setCurrentRow(0)

        sidebar_layout.addWidget(self.sidebar_list)
        root_layout.addWidget(self.sidebar_container)

        # ── 2. KONTEN KANAN (Tumpukan Halaman) ──
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(32, 24, 40, 24)
        right_layout.setSpacing(20)

        self.stacked_widget = QStackedWidget()

        self.page_general = QWidget()
        self.page_resi = QWidget()
        self.page_bank = QWidget()
        self.page_cabang = QWidget()
        self.page_font = QWidget()

        self._build_page_general()
        self._build_page_resi()
        self._build_page_bank()
        self._build_page_cabang()
        self._build_page_font()

        self.stacked_widget.addWidget(self.page_general)
        self.stacked_widget.addWidget(self.page_resi)
        self.stacked_widget.addWidget(self.page_bank)
        self.stacked_widget.addWidget(self.page_cabang)
        self.stacked_widget.addWidget(self.page_font)

        self.sidebar_list.currentRowChanged.connect(self.stacked_widget.setCurrentIndex)

        right_layout.addWidget(self.stacked_widget)

        # ── 3. TOMBOL SIMPAN GLOBAL (Selalu Terlihat di Bawah) ──
        self.btn_simpan_all = QPushButton("💾 SIMPAN PENGATURAN")
        self.btn_simpan_all.setFixedHeight(48)
        self.btn_simpan_all.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.btn_simpan_all.clicked.connect(self.simpan_pengaturan)
        right_layout.addWidget(self.btn_simpan_all)

        root_layout.addWidget(right_container)

        self.sesuaikan_tema_lokal()

        # 🌟 VALIDASI HAK AKSES USER SETELAH UI TERBENTUK
        self.validasi_hak_akses_setting()

    def _build_page_general(self):
        layout = QVBoxLayout(self.page_general)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel("Identitas & Sistem")
        lbl_title.setProperty("is_page_title", True)
        layout.addWidget(lbl_title)

        # --- GROUP 1: IDENTITAS PERUSAHAAN ---
        self.group_pt = QGroupBox("Identitas Perusahaan (White-Label)")
        form_pt = QFormLayout(self.group_pt)
        self._init_form(form_pt)
        self.txt_nama_pt = QLineEdit()
        self.txt_nama_pt.setPlaceholderText("Contoh: PT MAHKOTA KARGO LOGISTIK")
        form_pt.addRow("Nama Perusahaan:", self.txt_nama_pt)
        layout.addWidget(self.group_pt)

        # --- 🌟 GROUP 2: BRANDING TEKS LOGO (SATU WARNA FLAT) 🌟 ---
        self.group_logo_html = QGroupBox("Branding Teks Logo Aplikasi")
        form_logo = QFormLayout(self.group_logo_html)
        self._init_form(form_logo)

        self.txt_logo_aplikasi = QLineEdit()
        self.txt_logo_aplikasi.setPlaceholderText("Contoh: MAHKOTA KARGO")
        self.txt_logo_aplikasi.textChanged.connect(lambda: self.paksa_kapital_lineedit(self.txt_logo_aplikasi))

        lbl_hint_logo = QLabel("💡 Teks logo akan tampil dengan satu warna solid yang serasi di seluruh aplikasi.")
        lbl_hint_logo.setStyleSheet("color: #94a3b8; font-style: italic;")

        form_logo.addRow("Teks Logo Utama:", self.txt_logo_aplikasi)
        form_logo.addRow("", lbl_hint_logo)
        layout.addWidget(self.group_logo_html)

        # --- GROUP 3: NAMA DATABASE ---
        self.group_db = QGroupBox("Nama Database")
        form_db = QFormLayout(self.group_db)
        self._init_form(form_db)
        self.txt_db_path = QLineEdit()
        self.txt_db_path.setPlaceholderText("Contoh: database_cargo.db")

        form_db.addRow("Path Database (.db):", self.txt_db_path)
        layout.addWidget(self.group_db)
        layout.addStretch()

    def _build_page_resi(self):
        layout = QVBoxLayout(self.page_resi)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel("Format & Resi")
        lbl_title.setProperty("is_page_title", True)
        layout.addWidget(lbl_title)

        self.group_resi = QGroupBox("Format Nomor Resi & Wilayah Dropdown")
        form_resi = QFormLayout(self.group_resi)
        self._init_form(form_resi)

        self.txt_template_resi = QLineEdit()
        self.txt_template_resi.setPlaceholderText("Contoh: [PREFIX][COUNTER][SUFFIX]")
        self.txt_suffix_pajak = QLineEdit()
        self.txt_suffix_pajak.setMaximumWidth(160)
        self.txt_suffix_pajak.setPlaceholderText("Contoh: -P")
        self.txt_provinsi_tujuan = QTextEdit()
        self.txt_provinsi_tujuan.setPlaceholderText("Pisahkan dengan koma. Contoh: KALIMANTAN TIMUR, BALI")
        self.txt_provinsi_tujuan.setFixedHeight(70)

        form_resi.addRow("Template Nomor Resi:", self.txt_template_resi)
        form_resi.addRow("Akhiran Pajak (Suffix):", self.txt_suffix_pajak)
        form_resi.addRow("List Wilayah Dropdown:", self.txt_provinsi_tujuan)
        layout.addWidget(self.group_resi)
        layout.addStretch()

    def _build_page_bank(self):
        layout = QVBoxLayout(self.page_bank)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel("Rekening Bank")
        lbl_title.setProperty("is_page_title", True)
        layout.addWidget(lbl_title)

        # --- 1. TABEL NON-PAJAK ---
        self.group_np = QGroupBox("Daftar Rekening Non-Pajak")
        vbox_np = QVBoxLayout(self.group_np)
        vbox_np.setContentsMargins(16, 22, 16, 16)
        vbox_np.setSpacing(8)

        self.table_np = QTableWidget(0, 4)
        self.setup_tabel_rekening(self.table_np)
        vbox_np.addWidget(self.table_np)

        hbox_in_np = QHBoxLayout()
        hbox_in_np.setSpacing(4)

        self.txt_in_bank_np = QLineEdit()
        self.txt_in_bank_np.setPlaceholderText("BANK...")
        self.txt_in_bank_np.setFixedWidth(100)
        self.txt_in_bank_np.textChanged.connect(lambda: self.paksa_kapital_lineedit(self.txt_in_bank_np))

        self.txt_in_norek_np = QLineEdit()
        self.txt_in_norek_np.setPlaceholderText("NO. REK...")
        self.txt_in_norek_np.setFixedWidth(160)
        self.txt_in_norek_np.textChanged.connect(lambda: self.paksa_kapital_lineedit(self.txt_in_norek_np))

        self.txt_in_nama_np = QLineEdit()
        self.txt_in_nama_np.setPlaceholderText("NAMA...")
        self.txt_in_nama_np.textChanged.connect(lambda: self.paksa_kapital_lineedit(self.txt_in_nama_np))

        self.btn_add_np = QPushButton("+")
        self.btn_add_np.setFixedWidth(40)
        self.btn_add_np.clicked.connect(self.tambah_rek_np)

        hbox_in_np.addWidget(self.txt_in_bank_np)
        hbox_in_np.addWidget(self.txt_in_norek_np)
        hbox_in_np.addWidget(self.txt_in_nama_np, stretch=1)
        hbox_in_np.addWidget(self.btn_add_np)

        vbox_np.addLayout(hbox_in_np)
        layout.addWidget(self.group_np)

        # --- 2. TABEL PAJAK ---
        self.group_p = QGroupBox("Daftar Rekening Pajak (PT)")
        vbox_p = QVBoxLayout(self.group_p)
        vbox_p.setContentsMargins(16, 22, 16, 16)
        vbox_p.setSpacing(8)

        self.table_p = QTableWidget(0, 4)
        self.setup_tabel_rekening(self.table_p)
        vbox_p.addWidget(self.table_p)

        hbox_in_p = QHBoxLayout()
        hbox_in_p.setSpacing(4)

        self.txt_in_bank_p = QLineEdit()
        self.txt_in_bank_p.setPlaceholderText("BANK...")
        self.txt_in_bank_p.setFixedWidth(100)
        self.txt_in_bank_p.textChanged.connect(lambda: self.paksa_kapital_lineedit(self.txt_in_bank_p))

        self.txt_in_norek_p = QLineEdit()
        self.txt_in_norek_p.setPlaceholderText("NO. REK...")
        self.txt_in_norek_p.setFixedWidth(160)
        self.txt_in_norek_p.textChanged.connect(lambda: self.paksa_kapital_lineedit(self.txt_in_norek_p))

        self.txt_in_nama_p = QLineEdit()
        self.txt_in_nama_p.setPlaceholderText("NAMA...")
        self.txt_in_nama_p.textChanged.connect(lambda: self.paksa_kapital_lineedit(self.txt_in_nama_p))

        self.btn_add_p = QPushButton("+")
        self.btn_add_p.setFixedWidth(40)
        self.btn_add_p.clicked.connect(self.tambah_rek_p)

        hbox_in_p.addWidget(self.txt_in_bank_p)
        hbox_in_p.addWidget(self.txt_in_norek_p)
        hbox_in_p.addWidget(self.txt_in_nama_p, stretch=1)
        hbox_in_p.addWidget(self.btn_add_p)

        vbox_p.addLayout(hbox_in_p)
        layout.addWidget(self.group_p)

    def _build_page_cabang(self):
        layout = QVBoxLayout(self.page_cabang)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel("Jaringan Kantor Cabang")
        lbl_title.setProperty("is_page_title", True)
        layout.addWidget(lbl_title)

        self.group_branches = QGroupBox("Manajemen Data Cabang")
        vbox_branch = QVBoxLayout(self.group_branches)
        vbox_branch.setContentsMargins(16, 22, 16, 16)
        vbox_branch.setSpacing(8)

        self.table_cabang = QTableWidget()
        self.table_cabang.setColumnCount(5)
        self.table_cabang.setHorizontalHeaderLabels([
            "KODE", "NAMA KANTOR CABANG", "PREFIX NOTA", "START COUNTER (JSON)", "KAMUS ROUTE (JSON)",
        ])
        self.table_cabang.setRowCount(10)
        self.table_cabang.setAlternatingRowColors(True)
        self.table_cabang.verticalHeader().setVisible(True)
        self.table_cabang.setFixedHeight(280)
        self.table_cabang.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_cabang.setEditTriggers(QTableWidget.DoubleClicked | QTableWidget.SelectedClicked)

        hdr = self.table_cabang.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Fixed)
        self.table_cabang.setColumnWidth(0, 64)
        hdr.setSectionResizeMode(1, QHeaderView.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.Fixed)
        self.table_cabang.setColumnWidth(2, 96)
        hdr.setSectionResizeMode(3, QHeaderView.Interactive)
        self.table_cabang.setColumnWidth(3, 185)
        hdr.setSectionResizeMode(4, QHeaderView.Interactive)
        self.table_cabang.setColumnWidth(4, 185)

        self._tbl_hint_label = QLabel("💡 Double-click sel untuk mengedit. Kolom JSON harus berformat valid.")

        vbox_branch.addWidget(self.table_cabang)
        vbox_branch.addWidget(self._tbl_hint_label)
        layout.addWidget(self.group_branches)
        layout.addStretch()

    def _build_page_font(self):
        layout = QVBoxLayout(self.page_font)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl_title = QLabel("Tampilan & Font")
        lbl_title.setProperty("is_page_title", True)
        layout.addWidget(lbl_title)

        self.group_font = QGroupBox(
            "Pengaturan Font Global"
        )

        form_font = QFormLayout(self.group_font)
        self._init_form(form_font)

        self.combo_font = QComboBox()
        self.combo_font.setFixedHeight(36)

        font_kandidat = [
            "Inter",
            "Roboto",
            "JetBrains Mono",
            "Segoe UI",
            "Arial",
        ]

        font_tersedia = set(
            QFontDatabase().families()
        )

        font_valid = [
            nama_font
            for nama_font in font_kandidat
            if nama_font in font_tersedia
        ]

        # Inter menjadi fallback apabila daftar tidak terdeteksi.
        if not font_valid:
            font_valid = ["Inter"]

        self.combo_font.addItems(font_valid)

        font_sekarang = get_master_font()

        idx_sekarang = self.combo_font.findText(
            font_sekarang,
            Qt.MatchFixedString,
        )

        if idx_sekarang >= 0:
            self.combo_font.setCurrentIndex(
                idx_sekarang
            )

        # activated hanya berjalan ketika pengguna benar-benar memilih.
        self.combo_font.activated[str].connect(
            self.aksi_simpan_font_baru
        )

        lbl_info = QLabel(
            "Pilih keluarga font yang digunakan di seluruh aplikasi.\n"
            "Tutup dan buka kembali aplikasi agar font diterapkan sepenuhnya."
        )
        lbl_info.setStyleSheet(
            "color: #94a3b8; font-style: italic;"
        )

        form_font.addRow(
            "Pilih Font Aplikasi:",
            self.combo_font,
        )
        form_font.addRow("", lbl_info)

        layout.addWidget(self.group_font)
        layout.addStretch()

    @staticmethod
    def _init_form(form: QFormLayout):
        form.setContentsMargins(16, 22, 16, 16)
        form.setVerticalSpacing(16)
        form.setHorizontalSpacing(16)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    # ─────────────────────────────────────────────────────────────────
    # HAK AKSES ROLE VALIDATION
    # ─────────────────────────────────────────────────────────────────
    def validasi_hak_akses_setting(self):
        role_sekarang = CURRENT_SESSION.get('role', 'ADMIN')

        if role_sekarang != "SUPER_ADMIN":
            self.btn_simpan_all.setEnabled(False)
            self.btn_simpan_all.setText("🔒 PENGATURAN TERKUNCI (VIEW-ONLY MODE)")
            self.btn_simpan_all.setStyleSheet("""
                QPushButton {
                    background-color: #64748b; 
                    color: #cbd5e1; 
                    font-weight: bold;
                    border: none;
                }
            """)
            self.btn_simpan_all.setToolTip("Hanya SUPER_ADMIN yang dapat memodifikasi konfigurasi sistem.")

            if hasattr(self, 'btn_add_np') and self.btn_add_np:
                self.btn_add_np.setEnabled(False)
                self.btn_add_np.setStyleSheet("color: #94a3b8; font-size: 26px; background: transparent; border: none;")
            if hasattr(self, 'btn_add_p') and self.btn_add_p:
                self.btn_add_p.setEnabled(False)
                self.btn_add_p.setStyleSheet("color: #94a3b8; font-size: 26px; background: transparent; border: none;")

            for widget in self.findChildren(
                    (QLineEdit, QTextEdit, QComboBox, QTableWidget)
            ):
                if isinstance(
                        widget,
                        (QLineEdit, QTextEdit),
                ):
                    widget.setReadOnly(True)

                elif isinstance(
                        widget,
                        (QComboBox, QTableWidget),
                ):
                    widget.setEnabled(False)

                widget.setStyleSheet(
                    widget.styleSheet()
                    + "\nbackground-color: transparent;"
                    + " color: #94a3b8;"
                )

    # ─────────────────────────────────────────────────────────────────
    # AKSI TAMBAHAN KHUSUS (REKENING & FONT)
    # ─────────────────────────────────────────────────────────────────
    def paksa_kapital_lineedit(self, edit_widget):
        edit_widget.blockSignals(True)
        pos = edit_widget.cursorPosition()
        edit_widget.setText(edit_widget.text().upper())
        edit_widget.setCursorPosition(pos)
        edit_widget.blockSignals(False)

    def setup_tabel_rekening(self, table: QTableWidget):
        table.setHorizontalHeaderLabels(["BANK", "NO. REK", "ATAS NAMA", ""])
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.setMinimumHeight(120)

        hdr = table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Interactive)
        table.setColumnWidth(0, 100)
        hdr.setSectionResizeMode(1, QHeaderView.Interactive)
        table.setColumnWidth(1, 160)
        hdr.setSectionResizeMode(2, QHeaderView.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.Fixed)
        table.setColumnWidth(3, 40)

    def tambah_rek_np(self):
        self._tambah_ke_tabel(self.table_np, self.txt_in_bank_np, self.txt_in_norek_np, self.txt_in_nama_np)

    def tambah_rek_p(self):
        self._tambah_ke_tabel(self.table_p, self.txt_in_bank_p, self.txt_in_norek_p, self.txt_in_nama_p)

    def _tambah_ke_tabel(self, table, w_bank, w_norek, w_nama):
        bank = w_bank.text().strip()
        norek = w_norek.text().strip()
        nama = w_nama.text().strip()

        if not bank or not norek or not nama:
            QMessageBox.warning(self, "Peringalan", "Data Bank, No. Rekening, dan Atas Nama wajib diisi!")
            return

        self._insert_row_with_button(table, bank, norek, nama)

        w_bank.clear()
        w_norek.clear()
        w_nama.clear()

    def _insert_row_with_button(self, table, bank, norek, nama):
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(bank))
        table.setItem(row, 1, QTableWidgetItem(norek))
        table.setItem(row, 2, QTableWidgetItem(nama))

        btn_del = QPushButton("-")

        if CURRENT_SESSION.get('role', 'ADMIN') != "SUPER_ADMIN":
            btn_del.setEnabled(False)
            btn_del.setStyleSheet(
                "color: #94a3b8; font-size: 26px; font-weight: bold; background: transparent; border: none;")
        else:
            font_aktif = get_master_font()

            btn_del.setStyleSheet(
                f"""
                QPushButton {{
                    color: #ef4444;
                    font-size: 26px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                    font-family: "{font_aktif}";
                }}
                """
            )
            btn_del.clicked.connect(lambda _, t=table, b=btn_del: self.hapus_baris_via_tombol(t, b))

        table.setCellWidget(row, 3, btn_del)

    def hapus_baris_via_tombol(self, table, btn):
        for row in range(table.rowCount()):
            if table.cellWidget(row, 3) == btn:
                bank = table.item(row, 0).text() if table.item(row, 0) else "-"
                norek = table.item(row, 1).text() if table.item(row, 1) else "-"
                nama = table.item(row, 2).text() if table.item(row, 2) else "-"

                pesan_konfirmasi = (
                    "Hapus rekening berikut?\n\n"
                    f"Bank\t\t: {bank}\n"
                    f"No. Rek\t: {norek}\n"
                    f"Atas Nama\t: {nama}"
                )

                konfirmasi = QMessageBox.question(
                    self,
                    "Konfirmasi Hapus",
                    pesan_konfirmasi,
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.No
                )

                if konfirmasi == QMessageBox.Yes:
                    table.removeRow(row)
                break

    def aksi_simpan_font_baru(
            self,
            font_terpilih: str,
    ):
        if (
                CURRENT_SESSION.get("role", "ADMIN")
                != "SUPER_ADMIN"
        ):
            return

        font_terpilih = str(
            font_terpilih or ""
        ).strip()

        if not font_terpilih:
            return

        perbarui_font_master(
            font_terpilih
        )

        QMessageBox.information(
            self,
            "Font Diperbarui",
            (
                f"Font utama berhasil diubah menjadi "
                f"{font_terpilih}.\n\n"
                "Tutup dan buka kembali aplikasi agar "
                "perubahan font diterapkan sepenuhnya."
            ),
        )

    # ─────────────────────────────────────────────────────────────────
    # TEMA (STYLING KHUSUS FDM LAYOUT)
    # ─────────────────────────────────────────────────────────────────
    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() in (QEvent.PaletteChange, QEvent.StyleChange):
            self.sesuaikan_tema_lokal()

    def showEvent(self, event):
        super().showEvent(event)
        self.sesuaikan_tema_lokal()

    def sesuaikan_tema_lokal(self):
        win = self.window()
        if win and hasattr(win, 'current_theme'):
            is_dark = win.current_theme == "dark"
        else:
            app = QApplication.instance()
            qss = app.styleSheet().lower() if app else ""
            is_dark = "#25282e" in qss or "#1d2024" in qss

        settings = QSettings("AplikasiEkspedisi", "PengaturanUI")
        z = int(settings.value(f"zoom_{self.__class__.__name__}", 0))
        sz_base, sz_input, sz_title = 13 + z, 14 + z, 15 + z

        s = get_setting_styles(is_dark, sz_base, sz_input, sz_title)

        self.sidebar_container.setStyleSheet(s['sidebar_container'])
        self.sidebar_list.setStyleSheet(s['sidebar_list'])

        self._tbl_hint_label.setStyleSheet(s['lbl_hint'])
        if hasattr(self, 'lbl_menu'):
            self.lbl_menu.setStyleSheet(s['lbl_menu'])

        # 🎯 FIX PETIK GANTUNG: Diperbaiki total dari versi sebelumnya
        groups = [self.group_pt, self.group_logo_html, self.group_resi, self.group_branches, self.group_db, self.group_font]
        if hasattr(self, 'group_np'):
            groups.extend([self.group_np, self.group_p])

        for grp in groups:
            grp.setStyleSheet(s['custom_groupbox'])

        for lbl in self.findChildren(QLabel):
            if lbl.property("is_page_title"):
                lbl.setStyleSheet(s['lbl_page_title'])
            elif not lbl.property("is_page_title") and lbl not in (self._tbl_hint_label,):
                if hasattr(self, 'lbl_menu') and lbl == self.lbl_menu:
                    continue
                lbl.setStyleSheet(s['form_label'])

        # 🎯 FIX INDENTASI: Diikat masuk ke dalam method class
        for w in self.findChildren((QLineEdit, QTextEdit, QComboBox)):
            w.setStyleSheet(s['input'])

        if CURRENT_SESSION.get('role', 'ADMIN') != "SUPER_ADMIN":
            self.txt_db_path.setStyleSheet(s['input_readonly'])
        else:
            self.txt_db_path.setStyleSheet(s['input'])

        self.table_cabang.setStyleSheet(s['input'])
        self.btn_simpan_all.setStyleSheet(s['btn_simpan'])

        if hasattr(self, 'table_np'):
            self.table_np.setStyleSheet(s.get('input', ''))
            self.table_p.setStyleSheet(s.get('input', ''))

            font_aktif = get_master_font()

            qss_plus = f"""
                QPushButton {{
                    color: #3b82f6;
                    font-size: 26px;
                    font-weight: bold;
                    background: transparent;
                    border: none;
                    font-family: "{font_aktif}";
                }}
            """
            self.btn_add_np.setStyleSheet(qss_plus)
            self.btn_add_p.setStyleSheet(qss_plus)

        self.validasi_hak_akses_setting()

    # ─────────────────────────────────────────────────────────────────
    # LOAD & SIMPAN DATA (🎯 SEKARANG AMAN DI DALAM CLASS)
    # ─────────────────────────────────────────────────────────────────
    def load_current_settings(self):
        # 🌟 SINKRON VARIABEL: Menggunakan keyword baru 'nama_perusahaan'
        self.txt_nama_pt.setText(DATA_CLIENT.get('nama_perusahaan', DATA_CLIENT.get('pt_nama', '')))
        self.txt_template_resi.setText(DATA_CLIENT.get('template_no_resi', '[PREFIX][COUNTER][SUFFIX]'))
        self.txt_suffix_pajak.setText(DATA_CLIENT.get('kode_akhiran_pajak', '-P'))
        self.txt_db_path.setText(CURRENT_SESSION.get('db_name', 'database_cargo.db'))

        # 🌟 LOAD LOGO: Hapus tag HTML jika ada data kotor sisa versi lama
        raw_logo = DATA_CLIENT.get('logo_text_html', 'EXPEDISI LOGISTIK')
        clean_logo = re.sub(r'<[^>]*>', '', raw_logo).strip()
        self.txt_logo_aplikasi.setText(clean_logo)

        sub_tabs = DATA_CLIENT.get('provinsi_tujuan', [])
        if isinstance(sub_tabs, str):
            try:
                sub_tabs = json.loads(sub_tabs)
            except:
                sub_tabs = []
        self.txt_provinsi_tujuan.setText(", ".join(sub_tabs))

        raw_np = DATA_CLIENT.get('rekening_nonpajak', DATA_CLIENT.get('rekening', {}).get('rekening_nonpajak', []))
        rek_np = json.loads(raw_np) if isinstance(raw_np, str) else raw_np

        raw_p = DATA_CLIENT.get('rekening_pajak', DATA_CLIENT.get('rekening', {}).get('rekening_pajak', []))
        rek_p = json.loads(raw_p) if isinstance(raw_p, str) else raw_p

        def parse_dan_tambah_ke_tabel(rek_str, table):
            if not rek_str: return
            bank, norek, nama = "", "", ""
            parts = [p.strip() for p in rek_str.split(",")]

            if len(parts) >= 3:
                bank, norek, nama = parts[0], parts[1], parts[2]
            elif len(parts) == 2:
                bank, nama = parts[0], parts[1]
            else:
                nama = rek_str

            self._insert_row_with_button(table, bank, norek, nama)

        self.table_np.setRowCount(0)
        self.table_p.setRowCount(0)

        for rek in rek_np:
            parse_dan_tambah_ke_tabel(rek, self.table_np)

        for rek in rek_p:
            parse_dan_tambah_ke_tabel(rek, self.table_p)

        # 💡 DIBERSIHKAN: Menggunakan db_service untuk membaca data cabang
        try:
            rows = db_service.ambil_semua_data_cabang(limit=10)
            for idx, r in enumerate(rows):
                for col, val in enumerate(r):
                    self.table_cabang.setItem(idx, col, QTableWidgetItem(str(val)))
        except Exception as e:
            print(f"[TabSetting] Gagal memuat data cabang: {e}")

    def simpan_pengaturan(self):
        if CURRENT_SESSION.get('role', 'ADMIN') != "SUPER_ADMIN":
            return

        nama_pt = self.txt_nama_pt.text().strip().upper()
        template = self.txt_template_resi.text().strip()
        suffix = self.txt_suffix_pajak.text().strip().upper()
        db_path_input = self.txt_db_path.text().strip()

        # 🌟 AMBIL DATA LOGO SATU WARNA POLOS
        logo_input = self.txt_logo_aplikasi.text().strip().upper()

        if not db_path_input or not nama_pt or not logo_input:
            QMessageBox.warning(self, "Peringatan", "Nama Perusahaan, Teks Logo, and Path database wajib diisi!")
            return

        raw_subs = self.txt_provinsi_tujuan.toPlainText().split(',')
        sub_tabs = [s.strip().upper() for s in raw_subs if s.strip()]
        sub_tabs_json = json.dumps(sub_tabs)

        list_np_raw = []
        for r in range(self.table_np.rowCount()):
            b = self.table_np.item(r, 0).text() if self.table_np.item(r, 0) else ""
            n = self.table_np.item(r, 1).text() if self.table_np.item(r, 1) else ""
            nm = self.table_np.item(r, 2).text() if self.table_np.item(r, 2) else ""
            if b or n or nm:
                list_np_raw.append(f"{b}, {n}, {nm}")

        list_p_raw = []
        for r in range(self.table_p.rowCount()):
            b = self.table_p.item(r, 0).text() if self.table_p.item(r, 0) else ""
            n = self.table_p.item(r, 1).text() if self.table_p.item(r, 1) else ""
            nm = self.table_p.item(r, 2).text() if self.table_p.item(r, 2) else ""
            if b or n or nm:
                list_p_raw.append(f"{b}, {n}, {nm}")

        list_np = [x for x in list_np_raw if x]
        list_p = [x for x in list_p_raw if x]

        # 💡 SUSUN DATA SETTING
        settings_to_save = [
            ('nama_perusahaan', nama_pt),
            ('pt_nama', nama_pt),
            ('logo_text_html', logo_input),
            ('template_no_resi', template),
            ('kode_akhiran_pajak', suffix),
            ('provinsi_tujuan', sub_tabs_json),
            ('rekening_nonpajak', json.dumps(list_np)),
            ('rekening_pajak', json.dumps(list_p)),
        ]

        # 💡 SUSUN DATA CABANG
        branches_to_save = []
        for row in range(self.table_cabang.rowCount()):
            item_kode = self.table_cabang.item(row, 0)
            if not (item_kode and item_kode.text().strip()):
                continue

            item_nama = self.table_cabang.item(row, 1)
            item_prefix = self.table_cabang.item(row, 2)
            item_seq = self.table_cabang.item(row, 3)
            item_route = self.table_cabang.item(row, 4)

            kode_c = item_kode.text().strip().upper()
            nama_c = item_nama.text().strip().upper() if item_nama else f"CABANG {kode_c}"
            pref_c = item_prefix.text().strip().upper() if item_prefix else "INV"

            seq_json_str = (item_seq.text().strip() if item_seq and item_seq.text().strip() else '{"DEFAULT": 0}')
            route_json_str = (item_route.text().strip() if item_route and item_route.text().strip() else '{"DEFAULT": "INV"}')

            try:
                json.loads(seq_json_str)
                json.loads(route_json_str)
            except json.JSONDecodeError:
                QMessageBox.critical(self, "Error Format JSON",
                                     f"Baris ke-{row + 1} ({kode_c}) gagal disimpan!\nFormat JSON tidak valid.")
                return

            branches_to_save.append({
                'kode_cabang': kode_c,
                'nama_cabang': nama_c,
                'resi_prefix': pref_c,
                'start_seq_json': seq_json_str,
                'aturan_prefix': route_json_str
            })

        # 💡 EKSEKUSI SIMPAN VIA SERVICE
        try:
            sukses, pesan = db_service.simpan_semua_pengaturan_dan_cabang(settings_to_save, branches_to_save)
            if not sukses:
                QMessageBox.critical(self, "Error", f"Gagal menyimpan data:\n{pesan}")
                return

            db_lama = CURRENT_SESSION['db_name']

            if db_lama != db_path_input:
                import shutil
                if os.path.exists(db_lama):
                    try:
                        shutil.copy2(db_lama, db_path_input)
                    except Exception as e:
                        print(f"Gagal menyalin database fisik: {e}")

                try:
                    with open("app_env.json", "w") as f:
                        json.dump({"active_db": db_path_input}, f)
                except Exception as e:
                    print(f"Gagal menulis env: {e}")

            CURRENT_SESSION['db_name'] = db_path_input

            QMessageBox.information(
                self, "Sukses",
                "⚙️ PENGATURAN BERHASIL DISIMPAN!\n\n"
                "Silakan restart aplikasi."
            )
            if self.parent() and hasattr(self.parent(), 'close'):
                self.parent().close()

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal menyimpan data ke database:\n{e}")