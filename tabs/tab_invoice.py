# tabs/tab_invoice.py
import html
import json
import os
import re

from copy import deepcopy
from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP

from PyQt5.QtCore import QDate, QSettings, Qt, pyqtSignal, QSizeF
from PyQt5.QtGui import QKeySequence, QTextDocument, QPageSize
from PyQt5.QtPrintSupport import QPrinter, QPrintDialog
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from config import CURRENT_SESSION
import services.database_service as db_service
from themes.modules.invoice import get_invoice_styles

from utils import typography
from utils.typography import get_global_font_sizes
from utils.printer.print_invoice import tampilkan_preview_invoice, simpan_invoice_pdf
from utils import zoom as zoom_helper

# ==========================================================
# IMPORT HELPER BARU
# ==========================================================
from utils.number_formatters import (
    rupiah_to_int,
    format_ke_rupiah,
    ambil_angka_dari_teks
)
from utils.table_helper import buat_tabel_item
from utils.reset_form_helper import reset_form_input_global
from utils.placeholder_helper import terap_semua_placeholder_dinamis
from utils.validators import UppercaseValidator
from utils.mixins import ZoomTableMixin
from utils.widget_helpers import blokir_signal_sementara

# ==========================================================
# KONFIGURASI TEMPLATE
# ==========================================================
INVOICE_TEMPLATES = {
    "Standar": {
        "version": 2,
        "layout": "standard",
        "amount_key": "amount",
        "columns": [
            {"key": "resi", "title": "NO RESI", "type": "text", "width": 130},
            {"key": "description", "title": "KETERANGAN", "type": "text", "width": 380, "stretch": True},
            {"key": "amount", "title": "NOMINAL (Rp)", "type": "currency", "width": 150},
        ],
    },
    "Logistik Berat": {
        "version": 2,
        "layout": "logistics",
        "amount_key": "amount",
        "columns": [
            {"key": "no", "title": "NO", "type": "integer", "width": 48},
            {"key": "resi", "title": "RESI", "type": "text", "width": 95},
            {"key": "destination", "title": "TUJUAN", "type": "text", "width": 145},
            {"key": "po_number", "title": "NO. PO", "type": "text", "width": 95},
            {"key": "description", "title": "JENIS BARANG", "type": "text", "width": 210, "stretch": True},
            {"key": "package", "title": "KOLI", "type": "decimal", "width": 70},
            {"key": "weight", "title": "BERAT", "type": "text", "width": 90},
            {"key": "tariff", "title": "TARIF (Rp)", "type": "currency", "width": 105},
            {"key": "amount", "title": "RUPIAH", "type": "currency", "width": 130},
        ],
    },
    "Ritel Samarinda": {
        "version": 2,
        "layout": "bill_ship",
        "amount_key": "amount",
        "formula": {"operation": "multiply", "sources": ["package", "price"], "target": "amount"},
        "columns": [
            {"key": "resi", "title": "RESI", "type": "text", "width": 85},
            {"key": "description", "title": "DESCRIPTION", "type": "text", "width": 310, "stretch": True},
            {"key": "package", "title": "KOLI", "type": "decimal", "width": 72},
            {"key": "ship_date", "title": "TGL KAPAL", "type": "date", "width": 105},
            {"key": "price", "title": "PRICE", "type": "currency", "width": 110},
            {"key": "amount", "title": "AMOUNT", "type": "currency", "width": 135},
        ],
    },
    "Proyek Batangan": {
        "version": 2,
        "layout": "bill_ship",
        "amount_key": "amount",
        "columns": [
            {"key": "resi", "title": "RESI", "type": "text", "width": 105},
            {"key": "description", "title": "DESCRIPTION", "type": "text", "width": 430, "stretch": True},
            {"key": "quantity", "title": "QTY", "type": "text", "width": 85},
            {"key": "destination", "title": "TUJUAN", "type": "text", "width": 170},
            {"key": "amount", "title": "AMOUNT", "type": "currency", "width": 145},
        ],
    },
    "Custom / Bebas": {
        "version": 2,
        "layout": "bill_ship",
        "amount_key": "amount",
        "columns": [
            {"key": "resi", "title": "RESI", "type": "text", "width": 110},
            {"key": "description", "title": "DESCRIPTION", "type": "text", "width": 360, "stretch": True},
            {"key": "quantity", "title": "QTY", "type": "text", "width": 80},
            {"key": "weight", "title": "BERAT", "type": "text", "width": 90},
            {"key": "tariff", "title": "TARIF", "type": "currency", "width": 110},
            {"key": "amount", "title": "AMOUNT", "type": "currency", "width": 140},
        ],
    },
}


# ==========================================================
# SPREADSHEET EDITOR
# ==========================================================
class InvoiceSheet(QTableWidget):
    sheetEdited = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setEditTriggers(
            QAbstractItemView.DoubleClicked
            | QAbstractItemView.EditKeyPressed
            | QAbstractItemView.SelectedClicked
            | QAbstractItemView.AnyKeyPressed
        )
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.verticalHeader().setDefaultSectionSize(28)
        self.verticalHeader().setMinimumSectionSize(24)

    def keyPressEvent(self, event):
        if event.matches(QKeySequence.Copy):
            self.copy_selection()
            return
        if event.matches(QKeySequence.Paste):
            self.paste_selection()
            return
        if event.matches(QKeySequence.Cut):
            self.copy_selection()
            self.clear_selected_cells()
            return
        if event.matches(QKeySequence.Delete):
            self.clear_selected_cells()
            return
        if event.key() == Qt.Key_Insert:
            self.insert_row_below()
            return
        super().keyPressEvent(event)

    def copy_selection(self):
        ranges = self.selectedRanges()
        if not ranges:
            return

        selected_range = ranges[0]
        lines = []
        for row in range(selected_range.topRow(), selected_range.bottomRow() + 1):
            values = []
            for column in range(selected_range.leftColumn(), selected_range.rightColumn() + 1):
                item = self.item(row, column)
                values.append(item.text() if item else "")
            lines.append("\t".join(values))
        QApplication.clipboard().setText("\n".join(lines))

    def paste_selection(self):
        text = QApplication.clipboard().text()
        if not text:
            return

        start_row = max(self.currentRow(), 0)
        start_column = max(self.currentColumn(), 0)
        lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        if lines and lines[-1] == "":
            lines.pop()

        with blokir_signal_sementara(self):
            for row_offset, line in enumerate(lines):
                target_row = start_row + row_offset
                while target_row >= self.rowCount():
                    self.insertRow(self.rowCount())

                values = line.split("\t")
                for column_offset, value in enumerate(values):
                    target_column = start_column + column_offset
                    if target_column >= self.columnCount():
                        break
                    # PENGGUNAAN HELPER
                    self.setItem(target_row, target_column, buat_tabel_item(value.strip()))

        self.sheetEdited.emit()

    def clear_selected_cells(self):
        selected = self.selectedItems()
        if not selected:
            return
        with blokir_signal_sementara(self):
            for item in selected:
                item.setText("")
        self.sheetEdited.emit()

    def insert_blank_row(self, row=None):
        if row is None:
            row = self.rowCount()
        row = max(0, min(row, self.rowCount()))
        self.insertRow(row)
        self.setCurrentCell(row, 0)
        self.sheetEdited.emit()

    def insert_row_above(self):
        row = self.currentRow()
        self.insert_blank_row(0 if row < 0 else row)

    def insert_row_below(self):
        row = self.currentRow()
        self.insert_blank_row(self.rowCount() if row < 0 else row + 1)

    def delete_selected_rows(self):
        rows = sorted({index.row() for index in self.selectedIndexes()}, reverse=True)
        if not rows and self.currentRow() >= 0:
            rows = [self.currentRow()]
        if not rows:
            return

        with blokir_signal_sementara(self):
            for row in rows:
                self.removeRow(row)

        if self.rowCount() == 0:
            self.insertRow(0)
        self.sheetEdited.emit()

    def duplicate_current_row(self):
        source_row = self.currentRow()
        if source_row < 0:
            return
        target_row = source_row + 1

        with blokir_signal_sementara(self):
            self.insertRow(target_row)
            for column in range(self.columnCount()):
                source = self.item(source_row, column)

                # PENGGUNAAN HELPER
                item = buat_tabel_item(
                    text=source.text() if source else "",
                    alignment=source.textAlignment() if source else Qt.AlignLeft
                )
                self.setItem(target_row, column, item)

        self.setCurrentCell(target_row, 0)
        self.sheetEdited.emit()

    def move_current_row(self, offset):
        source_row = self.currentRow()
        if source_row < 0:
            return
        target_row = source_row + offset
        if target_row < 0 or target_row >= self.rowCount():
            return

        with blokir_signal_sementara(self):
            source_values = []
            target_values = []
            for column in range(self.columnCount()):
                source = self.item(source_row, column)
                target = self.item(target_row, column)
                source_values.append((source.text() if source else "", source.textAlignment() if source else 0))
                target_values.append((target.text() if target else "", target.textAlignment() if target else 0))

            # PENGGUNAAN HELPER
            for column, (value, alignment) in enumerate(target_values):
                self.setItem(source_row, column, buat_tabel_item(value, alignment=alignment))

            for column, (value, alignment) in enumerate(source_values):
                self.setItem(target_row, column, buat_tabel_item(value, alignment=alignment))

        self.setCurrentCell(target_row, max(self.currentColumn(), 0))
        self.sheetEdited.emit()

    def clear_all_rows(self):
        with blokir_signal_sementara(self):
            self.setRowCount(1)
            for column in range(self.columnCount()):
                # PENGGUNAAN HELPER
                self.setItem(0, column, buat_tabel_item(""))
        self.setCurrentCell(0, 0)
        self.sheetEdited.emit()

    def _show_context_menu(self, position):
        menu = QMenu(self)
        act_insert_above = menu.addAction("Tambah Baris di Atas")
        act_insert_below = menu.addAction("Tambah Baris di Bawah")
        act_duplicate = menu.addAction("Duplikat Baris")
        menu.addSeparator()
        act_copy = menu.addAction("Salin")
        act_paste = menu.addAction("Tempel")
        act_clear = menu.addAction("Kosongkan Sel")
        menu.addSeparator()
        act_delete = menu.addAction("Hapus Baris")

        selected = menu.exec_(self.viewport().mapToGlobal(position))
        if selected == act_insert_above:
            self.insert_row_above()
        elif selected == act_insert_below:
            self.insert_row_below()
        elif selected == act_duplicate:
            self.duplicate_current_row()
        elif selected == act_copy:
            self.copy_selection()
        elif selected == act_paste:
            self.paste_selection()
        elif selected == act_clear:
            self.clear_selected_cells()
        elif selected == act_delete:
            self.delete_selected_rows()


# ==========================================================
# DIALOG PENGATURAN KOLOM
# ==========================================================
class ColumnDesignerDialog(QDialog):
    TYPES = ["text", "integer", "decimal", "currency", "date"]

    def __init__(self, columns, amount_key, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Atur Kolom Invoice")
        self.resize(760, 430)
        self.result_columns = None
        self.result_amount_key = None

        layout = QVBoxLayout(self)
        info = QLabel(
            "Judul adalah nama kolom yang terlihat. Key dipakai untuk penyimpanan data. "
            "Tandai satu kolom sebagai TOTAL agar subtotal dihitung dari kolom tersebut."
        )
        info.setWordWrap(True)
        layout.addWidget(info)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["JUDUL", "KEY", "TIPE", "LEBAR", "TOTAL?"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.table.verticalHeader().setVisible(False)
        layout.addWidget(self.table)

        for column in columns:
            self._append_row(
                title=column.get("title", ""),
                key=column.get("key", ""),
                data_type=column.get("type", "text"),
                width=column.get("width", 120),
                is_amount=column.get("key") == amount_key,
            )

        toolbar = QHBoxLayout()
        btn_add = QPushButton("+ Tambah Kolom")
        btn_remove = QPushButton("Hapus Kolom")
        btn_up = QPushButton("Naik")
        btn_down = QPushButton("Turun")
        toolbar.addWidget(btn_add)
        toolbar.addWidget(btn_remove)
        toolbar.addWidget(btn_up)
        toolbar.addWidget(btn_down)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        actions = QHBoxLayout()
        actions.addStretch()
        btn_cancel = QPushButton("Batal")
        btn_ok = QPushButton("Terapkan")
        actions.addWidget(btn_cancel)
        actions.addWidget(btn_ok)
        layout.addLayout(actions)

        btn_add.clicked.connect(lambda: self._append_row("KOLOM BARU", "kolom_baru", "text", 120, False))
        btn_remove.clicked.connect(self._remove_current_row)
        btn_up.clicked.connect(lambda: self._move_row(-1))
        btn_down.clicked.connect(lambda: self._move_row(1))
        btn_cancel.clicked.connect(self.reject)
        btn_ok.clicked.connect(self._validate_and_accept)

    @staticmethod
    def _slug_key(value):
        value = str(value or "").strip().lower()
        value = re.sub(r"[^a-z0-9]+", "_", value).strip("_")
        return value or "kolom"

    def _append_row(self, title, key, data_type, width, is_amount):
        row = self.table.rowCount()
        self.table.insertRow(row)

        # PENGGUNAAN HELPER
        self.table.setItem(row, 0, buat_tabel_item(title))
        self.table.setItem(row, 1, buat_tabel_item(key))

        combo = QComboBox()
        combo.addItems(self.TYPES)
        combo.setCurrentText(data_type if data_type in self.TYPES else "text")
        self.table.setCellWidget(row, 2, combo)

        self.table.setItem(row, 3, buat_tabel_item(width))
        self.table.setItem(row, 4, buat_tabel_item("YA" if is_amount else ""))

    def _remove_current_row(self):
        row = self.table.currentRow()
        if row >= 0 and self.table.rowCount() > 1:
            self.table.removeRow(row)

    def _move_row(self, offset):
        source = self.table.currentRow()
        target = source + offset
        if source < 0 or target < 0 or target >= self.table.rowCount():
            return

        row_data = self._read_row(source)
        target_data = self._read_row(target)
        self._write_row(source, target_data)
        self._write_row(target, row_data)
        self.table.setCurrentCell(target, 0)

    def _read_row(self, row):
        combo = self.table.cellWidget(row, 2)
        return {
            "title": self.table.item(row, 0).text() if self.table.item(row, 0) else "",
            "key": self.table.item(row, 1).text() if self.table.item(row, 1) else "",
            "type": combo.currentText() if combo else "text",
            "width": self.table.item(row, 3).text() if self.table.item(row, 3) else "120",
            "amount": self.table.item(row, 4).text() if self.table.item(row, 4) else "",
        }

    def _write_row(self, row, data):
        self.table.setItem(row, 0, buat_tabel_item(data["title"]))
        self.table.setItem(row, 1, buat_tabel_item(data["key"]))
        combo = self.table.cellWidget(row, 2)
        if combo:
            combo.setCurrentText(data["type"])
        self.table.setItem(row, 3, buat_tabel_item(data["width"]))
        self.table.setItem(row, 4, buat_tabel_item(data["amount"]))

    def _validate_and_accept(self):
        columns = []
        used_keys = set()
        amount_key = None

        for row in range(self.table.rowCount()):
            raw = self._read_row(row)
            title = raw["title"].strip()
            key = self._slug_key(raw["key"] or title)
            if not title:
                QMessageBox.warning(self, "Kolom Belum Lengkap", f"Judul pada baris {row + 1} masih kosong.")
                return
            if key in used_keys:
                QMessageBox.warning(self, "Key Ganda", f"Key '{key}' digunakan lebih dari satu kali.")
                return
            used_keys.add(key)

            try:
                width = max(45, min(int(raw["width"]), 800))
            except (TypeError, ValueError):
                width = 120

            column = {
                "key": key,
                "title": title.upper(),
                "type": raw["type"],
                "width": width,
            }
            if raw["type"] == "text" and width >= 220:
                column["stretch"] = True
            columns.append(column)

            if raw["amount"].strip().upper() in {"YA", "Y", "YES", "1", "TOTAL"}:
                if amount_key is not None:
                    QMessageBox.warning(self, "Kolom Total", "Cukup tandai satu kolom sebagai TOTAL.")
                    return
                amount_key = key

        if not columns:
            QMessageBox.warning(self, "Kolom Kosong", "Minimal harus ada satu kolom.")
            return

        if amount_key is None:
            amount_key = columns[-1]["key"]
            columns[-1]["type"] = "currency"

        self.result_columns = columns
        self.result_amount_key = amount_key
        self.accept()


# ==========================================================
# TAB INVOICE
# ==========================================================
class TabInvoice(ZoomTableMixin, QWidget):
    KOL_HISTORI_NO_INV = 0
    KOL_HISTORI_TANGGAL = 1
    KOL_HISTORI_CLIENT = 2
    KOL_HISTORI_STATUS = 3

    def __init__(self):
        super().__init__()
        self.no_invoice_aktif = None
        self.total_invoice_aktif = 0
        self.status_invoice_aktif = "DRAFT"

        self._sedang_memuat_item = False
        self._sedang_menghitung = False
        self._dirty = False
        self._loading_invoice = False

        self.template_configs = deepcopy(INVOICE_TEMPLATES)
        self.current_template_override = None
        self.active_template = deepcopy(self.template_configs["Standar"])
        self.active_columns = deepcopy(self.active_template["columns"])
        self.headers_aktif = [column["title"] for column in self.active_columns]

        self.init_ui()

    # ------------------------------------------------------
    # UI & PENERAPAN HELPER INITIAL
    # ------------------------------------------------------
    def init_ui(self):
        layout_utama = QHBoxLayout(self)
        layout_utama.setContentsMargins(15, 15, 15, 15)

        self.splitter = QSplitter(Qt.Horizontal)
        layout_utama.addWidget(self.splitter)

        # PANEL KIRI
        self.panel_kiri = QWidget()
        layout_kiri = QVBoxLayout(self.panel_kiri)
        layout_kiri.setContentsMargins(0, 0, 10, 0)

        self.lbl_title_histori = QLabel("📜 Histori Invoice")
        layout_kiri.addWidget(self.lbl_title_histori)

        self.txt_cari_invoice = QLineEdit()
        self.txt_cari_invoice.setPlaceholderText("Cari No. Invoice / Pelanggan...")
        layout_kiri.addWidget(self.txt_cari_invoice)

        self.tabel_histori_invoice = QTableWidget()
        self.tabel_histori_invoice.setColumnCount(4)
        self.tabel_histori_invoice.setHorizontalHeaderLabels(["NO. INV", "TANGGAL", "CLIENT", "STATUS"])
        self.tabel_histori_invoice.verticalHeader().setVisible(False)
        self.tabel_histori_invoice.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabel_histori_invoice.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabel_histori_invoice.setAlternatingRowColors(True)

        self.tabel_histori_invoice.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.tabel_histori_invoice.horizontalHeader().setStretchLastSection(True)
        layout_kiri.addWidget(self.tabel_histori_invoice)

        btn_baru_kiri = QPushButton("＋ Invoice Baru")
        btn_baru_kiri.clicked.connect(self.buat_invoice_baru)
        layout_kiri.addWidget(btn_baru_kiri)

        # PANEL KANAN
        self.panel_kanan = QWidget()
        layout_kanan = QVBoxLayout(self.panel_kanan)
        layout_kanan.setContentsMargins(10, 0, 0, 0)

        self.lbl_title_editor = QLabel("DRAFT INVOICE BARU")
        layout_kanan.addWidget(self.lbl_title_editor)

        group_header = QGroupBox("Informasi Invoice")
        grid_header = QGridLayout(group_header)

        # PENGGUNAAN HELPER VALIDATOR
        validator_kapital = UppercaseValidator(self)

        self.txt_client = QLineEdit()
        self.txt_client.setPlaceholderText("Nama client / Bill To")
        self.txt_client.setValidator(validator_kapital)

        self.txt_ship_to = QLineEdit()
        self.txt_ship_to.setPlaceholderText("Ship To / tujuan penerima")
        self.txt_ship_to.setValidator(validator_kapital)

        self.txt_no_invoice = QLineEdit()
        self.txt_no_invoice.setPlaceholderText("Kosongkan untuk nomor otomatis")
        self.txt_no_invoice.setValidator(validator_kapital)

        self.date_invoice = QDateEdit(QDate.currentDate())
        self.date_invoice.setCalendarPopup(True)
        self.date_invoice.setDisplayFormat("dd/MM/yyyy")
        self.date_invoice.setMinimumHeight(34)

        self.cmb_tipe_invoice = QComboBox()
        self.cmb_tipe_invoice.addItems(list(self.template_configs.keys()))

        self.cmb_pajak = QComboBox()
        self.cmb_pajak.addItems(["NONPAJAK", "PPN 1,1%"])

        self.txt_payment_info = QLineEdit()
        self.txt_payment_info.setPlaceholderText("Contoh: BCA 8292572980 a.n PT Ekspedisi kargo")

        self.txt_catatan = QLineEdit()
        self.txt_catatan.setPlaceholderText("Catatan invoice, minimum charge, biaya bongkar, dll.")

        self.txt_penanda_tangan = QLineEdit()
        self.txt_penanda_tangan.setPlaceholderText("Nama penanda tangan")

        grid_header.addWidget(QLabel("Bill To"), 0, 0)
        grid_header.addWidget(self.txt_client, 0, 1)
        grid_header.addWidget(QLabel("Ship To"), 0, 2)
        grid_header.addWidget(self.txt_ship_to, 0, 3)

        grid_header.addWidget(QLabel("No. Invoice"), 1, 0)
        grid_header.addWidget(self.txt_no_invoice, 1, 1)
        grid_header.addWidget(QLabel("Tanggal"), 1, 2)
        grid_header.addWidget(self.date_invoice, 1, 3)

        grid_header.addWidget(QLabel("Template"), 2, 0)
        grid_header.addWidget(self.cmb_tipe_invoice, 2, 1)
        grid_header.addWidget(QLabel("Pajak"), 2, 2)
        grid_header.addWidget(self.cmb_pajak, 2, 3)

        grid_header.addWidget(QLabel("Payment Info"), 3, 0)
        grid_header.addWidget(self.txt_payment_info, 3, 1, 1, 3)
        grid_header.addWidget(QLabel("Catatan"), 4, 0)
        grid_header.addWidget(self.txt_catatan, 4, 1, 1, 3)
        grid_header.addWidget(QLabel("Penanda Tangan"), 5, 0)
        grid_header.addWidget(self.txt_penanda_tangan, 5, 1, 1, 3)

        layout_kanan.addWidget(group_header)

        # Toolbar spreadsheet
        toolbar = QHBoxLayout()
        self.btn_tambah_baris = QPushButton("＋ Baris")
        self.btn_hapus_baris = QPushButton("Hapus Baris")
        self.btn_duplikat_baris = QPushButton("Duplikat")
        self.btn_naik = QPushButton("↑")
        self.btn_turun = QPushButton("↓")
        self.btn_paste = QPushButton("Tempel Excel")
        self.btn_atur_kolom = QPushButton("⚙ Atur Kolom")
        self.btn_bersihkan = QPushButton("Bersihkan")

        for button in [
            self.btn_tambah_baris,
            self.btn_hapus_baris,
            self.btn_duplikat_baris,
            self.btn_naik,
            self.btn_turun,
            self.btn_paste,
            self.btn_atur_kolom,
            self.btn_bersihkan,
        ]:
            toolbar.addWidget(button)
        toolbar.addStretch()
        layout_kanan.addLayout(toolbar)

        # Spreadsheet
        self.tabel_item_invoice = InvoiceSheet(self)
        self.tabel_item_invoice.verticalHeader().setVisible(True)
        self.tabel_item_invoice.setAlternatingRowColors(True)
        layout_kanan.addWidget(self.tabel_item_invoice, 1)

        # Total
        vbox_total = QVBoxLayout()
        self.lbl_subtotal = QLabel("SUB TOTAL: Rp 0")
        self.lbl_subtotal.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_pajak_nominal = QLabel("PAJAK: Rp 0")
        self.lbl_pajak_nominal.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.lbl_total_tagihan = QLabel("TOTAL TAGIHAN: Rp 0")
        self.lbl_total_tagihan.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        vbox_total.addWidget(self.lbl_subtotal)
        vbox_total.addWidget(self.lbl_pajak_nominal)
        vbox_total.addWidget(self.lbl_total_tagihan)
        layout_kanan.addLayout(vbox_total)

        # Tombol aksi
        hbox_aksi = QHBoxLayout()
        self.btn_preview = QPushButton("👁 Preview")
        self.btn_simpan_db = QPushButton("💾 Simpan Invoice")
        self.btn_cetak = QPushButton("🖨️ Cetak Invoice")
        self.menu_cetak = QMenu(self)

        self.action_cetak_pdf = self.menu_cetak.addAction("📄 Ekspor ke PDF (A4)")
        self.action_cetak_a4 = self.menu_cetak.addAction("🖨️ Print Langsung (A4 - Inkjet/Laser)")
        self.action_cetak_dotmatrix = self.menu_cetak.addAction("🖨️ Print Langsung (NCR 9.5 x 5.5 - Dot Matrix)")

        self.btn_cetak.setMenu(self.menu_cetak)
        self.btn_cetak.setEnabled(False)
        self.btn_share = QPushButton("📱 Share WA")
        hbox_aksi.addStretch()
        for button in [self.btn_preview, self.btn_simpan_db, self.btn_cetak, self.btn_share]:
            hbox_aksi.addWidget(button)
        layout_kanan.addLayout(hbox_aksi)

        self.splitter.addWidget(self.panel_kiri)
        self.splitter.addWidget(self.panel_kanan)
        self.splitter.setSizes([340, 1000])

        # Signal utama
        self.txt_cari_invoice.textChanged.connect(self.filter_histori_invoice)
        self.tabel_histori_invoice.itemDoubleClicked.connect(self.buka_invoice_dari_histori)
        self.tabel_item_invoice.itemChanged.connect(self._on_table_item_changed)
        self.tabel_item_invoice.sheetEdited.connect(self._on_sheet_bulk_edited)
        self.cmb_tipe_invoice.currentIndexChanged.connect(self._on_template_changed)
        self.cmb_pajak.currentIndexChanged.connect(self.ubah_rekening_otomatis)

        for field in [
            self.txt_client,
            self.txt_ship_to,
            self.txt_no_invoice,
            self.txt_payment_info,
            self.txt_catatan,
            self.txt_penanda_tangan,
        ]:
            field.textChanged.connect(self._on_metadata_changed)
        self.date_invoice.dateChanged.connect(self._on_metadata_changed)

        # Signal toolbar
        self.btn_tambah_baris.clicked.connect(self.tabel_item_invoice.insert_row_below)
        self.btn_hapus_baris.clicked.connect(self.tabel_item_invoice.delete_selected_rows)
        self.btn_duplikat_baris.clicked.connect(self.tabel_item_invoice.duplicate_current_row)
        self.btn_naik.clicked.connect(lambda: self.tabel_item_invoice.move_current_row(-1))
        self.btn_turun.clicked.connect(lambda: self.tabel_item_invoice.move_current_row(1))
        self.btn_paste.clicked.connect(self.tabel_item_invoice.paste_selection)
        self.btn_atur_kolom.clicked.connect(self.atur_kolom_invoice)
        self.btn_bersihkan.clicked.connect(self._confirm_clear_table)

        self.btn_preview.clicked.connect(self.tampilkan_preview)
        self.btn_simpan_db.clicked.connect(self.simpan_invoice_ke_db)
        self.action_cetak_pdf.triggered.connect(self.cetak_pdf)
        self.action_cetak_a4.triggered.connect(lambda: self.cetak_langsung("A4"))
        self.action_cetak_dotmatrix.triggered.connect(lambda: self.cetak_langsung("NCR"))
        self.btn_share.clicked.connect(self.info_fitur_share)

        # TERAPKAN HELPER PLACEHOLDER
        terap_semua_placeholder_dinamis(self)

        # MEMUAT LEBAR KOLOM HISTORI
        self.load_lebar_kolom_histori(self.tabel_histori_invoice)
        self.tabel_histori_invoice.horizontalHeader().sectionResized.connect(
            lambda: self.simpan_lebar_kolom_histori(self.tabel_histori_invoice)
        )

        self.apply_template(preserve_rows=False)
        self.sesuaikan_tema_lokal()
        self.load_histori_invoice()

    # ------------------------------------------------------
    # FUNGSI PENDUKUNG HISTORI KOLOM
    # ------------------------------------------------------
    def simpan_lebar_kolom_histori(self, tabel):
        lebar_kolom = [tabel.columnWidth(i) for i in range(tabel.columnCount())]
        QSettings("AplikasiEkspedisi", "TabInvoiceHistori").setValue("lebar_kolom", lebar_kolom)

    def load_lebar_kolom_histori(self, tabel):
        lebar_tersimpan = QSettings("AplikasiEkspedisi", "TabInvoiceHistori").value("lebar_kolom")
        if lebar_tersimpan:
            try:
                for i, width in enumerate(lebar_tersimpan):
                    if i < tabel.columnCount():
                        tabel.setColumnWidth(i, int(width))
            except Exception as e:
                print(f"Gagal memuat lebar kolom histori: {e}")

    # ------------------------------------------------------
    # TEMPLATE DAN KOLOM
    # ------------------------------------------------------
    @staticmethod
    def _buat_item_tabel(value, column):
        """Membuat item tabel dengan style rata teks menggunakan table_helper."""
        data_type = column.get("type", "text")
        if data_type in {"currency", "integer", "decimal"}:
            align = Qt.AlignRight | Qt.AlignVCenter
        elif data_type == "date":
            align = Qt.AlignCenter
        else:
            align = Qt.AlignLeft | Qt.AlignVCenter

        return buat_tabel_item(text=value, alignment=align)

    def _current_template_config(self):
        if self.current_template_override:
            return deepcopy(self.current_template_override)
        name = self.cmb_tipe_invoice.currentText() or "Standar"
        return deepcopy(self.template_configs.get(name, self.template_configs["Standar"]))

    def _capture_rows_by_key(self):
        rows = []
        if not self.active_columns:
            return rows
        for row in range(self.tabel_item_invoice.rowCount()):
            row_data = {}
            for column_index, column in enumerate(self.active_columns):
                item = self.tabel_item_invoice.item(row, column_index)
                row_data[column["key"]] = item.text() if item else ""
            if any(str(value).strip() for value in row_data.values()):
                rows.append(row_data)
        return rows

    def apply_template(self, preserve_rows=True, rows_override=None):
        old_rows = rows_override if rows_override is not None else (
            self._capture_rows_by_key() if preserve_rows else [])
        template = self._current_template_config()

        self.active_template = template
        self.active_columns = deepcopy(template.get("columns", []))
        self.headers_aktif = [column.get("title", column.get("key", "")) for column in self.active_columns]

        self._sedang_memuat_item = True
        try:
            with blokir_signal_sementara(self.tabel_item_invoice):
                self.tabel_item_invoice.clear()
                self.tabel_item_invoice.setColumnCount(len(self.active_columns))
                self.tabel_item_invoice.setHorizontalHeaderLabels(self.headers_aktif)
                self.tabel_item_invoice.setRowCount(0)

                header = self.tabel_item_invoice.horizontalHeader()
                has_stretch = False
                for index, column in enumerate(self.active_columns):
                    if column.get("stretch") and not has_stretch:
                        header.setSectionResizeMode(index, QHeaderView.Stretch)
                        has_stretch = True
                    else:
                        header.setSectionResizeMode(index, QHeaderView.Interactive)
                        self.tabel_item_invoice.setColumnWidth(index, int(column.get("width", 110)))

                lebar_dasar = [
                    int(column.get("width", 110))
                    for column in self.active_columns
                ]
                self._perbarui_cache_lebar_zoom(
                    self.tabel_item_invoice,
                    lebar_dasar,
                )
                zoom_aktif = zoom_helper.dapatkan_zoom_level(
                    self.__class__.__name__
                )
                zoom_helper._skalakan_kolom_tableview(
                    self.tabel_item_invoice,
                    zoom_aktif,
                )

                for row_data in old_rows:
                    row = self.tabel_item_invoice.rowCount()
                    self.tabel_item_invoice.insertRow(row)
                    for column_index, column in enumerate(self.active_columns):
                        value = row_data.get(column["key"], "")

                        # PENGGUNAAN HELPER
                        item = self._buat_item_tabel(value, column)
                        self.tabel_item_invoice.setItem(row, column_index, item)

                if self.tabel_item_invoice.rowCount() == 0:
                    self.tabel_item_invoice.insertRow(0)
        finally:
            self._sedang_memuat_item = False

        self.hitung_ulang_total_tagihan()

    def _on_template_changed(self, *_):
        if self._loading_invoice:
            return
        old_rows = self._capture_rows_by_key()
        self.current_template_override = None
        self.apply_template(preserve_rows=False, rows_override=old_rows)
        self._mark_dirty()

    def atur_kolom_invoice(self):
        dialog = ColumnDesignerDialog(
            self.active_columns,
            self.active_template.get("amount_key", "amount"),
            self,
        )
        if dialog.exec_() != QDialog.Accepted:
            return

        old_rows = self._capture_rows_by_key()
        override = deepcopy(self.active_template)
        override["columns"] = dialog.result_columns
        override["amount_key"] = dialog.result_amount_key
        override.pop("formula", None)
        override["customized"] = True
        self.current_template_override = override
        self.apply_template(preserve_rows=False, rows_override=old_rows)
        self._mark_dirty()

    def _column_index_by_key(self, key):
        for index, column in enumerate(self.active_columns):
            if column.get("key") == key:
                return index
        return -1

    # ------------------------------------------------------
    # EVENT EDITOR DAN TOTAL
    # ------------------------------------------------------
    def _on_table_item_changed(self, item):
        if self._sedang_memuat_item or self._sedang_menghitung:
            return

        # PENGGUNAAN HELPER MENGATUR ALIGNMENT KEMBALI
        if 0 <= item.column() < len(self.active_columns):
            column = self.active_columns[item.column()]
            data_type = column.get("type", "text")
            if data_type in {"currency", "integer", "decimal"}:
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            elif data_type == "date":
                item.setTextAlignment(Qt.AlignCenter)
            else:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._apply_formula_for_row(item.row(), edited_column=item.column())
        self.hitung_ulang_total_tagihan()
        self._mark_dirty()

    def _normalisasi_format_item_tabel(self):
        for row in range(self.tabel_item_invoice.rowCount()):
            for column_index, column in enumerate(self.active_columns):
                item = self.tabel_item_invoice.item(row, column_index)
                if item is None:
                    continue

                data_type = column.get("type", "text")
                if data_type in {"currency", "integer", "decimal"}:
                    alignment = Qt.AlignRight | Qt.AlignVCenter
                elif data_type == "date":
                    alignment = Qt.AlignCenter
                else:
                    alignment = Qt.AlignLeft | Qt.AlignVCenter

                item.setTextAlignment(alignment)

                if data_type == "currency":
                    teks = item.text().strip()
                    if teks and any(karakter.isdigit() for karakter in teks):
                        item.setText(format_ke_rupiah(rupiah_to_int(teks)))

    def _on_sheet_bulk_edited(self):
        if self._sedang_memuat_item:
            return

        with blokir_signal_sementara(self.tabel_item_invoice):
            self._normalisasi_format_item_tabel()
            self._recalculate_all_formulas()

        self.hitung_ulang_total_tagihan()
        self._mark_dirty()

    def _on_metadata_changed(self, *_):
        if self._loading_invoice:
            return
        self.hitung_ulang_total_tagihan()
        self._mark_dirty()

    def _mark_dirty(self):
        if self._loading_invoice:
            return
        self._dirty = True
        self.btn_simpan_db.setEnabled(True)
        if self.no_invoice_aktif:
            self.lbl_title_editor.setText(f"EDIT INVOICE: {self.no_invoice_aktif} *")
        else:
            self.lbl_title_editor.setText("DRAFT INVOICE BARU *")

    def _apply_formula_for_row(self, row, edited_column=None):
        formula = self.active_template.get("formula")
        if not formula or formula.get("operation") != "multiply":
            return

        source_keys = formula.get("sources", [])
        target_key = formula.get("target")
        source_indexes = [self._column_index_by_key(key) for key in source_keys]
        target_index = self._column_index_by_key(target_key)
        if target_index < 0 or any(index < 0 for index in source_indexes):
            return
        if edited_column is not None and edited_column not in source_indexes:
            return

        values = []
        for index in source_indexes:
            item = self.tabel_item_invoice.item(row, index)

            # PENGGUNAAN HELPER
            value = ambil_angka_dari_teks(item.text() if item else "")
            values.append(value)

        result = Decimal("1")
        for value in values:
            result *= value

        self._sedang_menghitung = True
        try:
            item = self.tabel_item_invoice.item(row, target_index)
            nilai_akhir = int(result.quantize(Decimal("1"), rounding=ROUND_HALF_UP))

            # PENGGUNAAN HELPER FORMAT KE RUPIAH (Ribuan)
            teks_akhir = format_ke_rupiah(nilai_akhir)

            if item is None:
                item = self._buat_item_tabel(teks_akhir, self.active_columns[target_index])
                self.tabel_item_invoice.setItem(row, target_index, item)
            else:
                item.setText(teks_akhir)
        finally:
            self._sedang_menghitung = False

    def _recalculate_all_formulas(self):
        for row in range(self.tabel_item_invoice.rowCount()):
            self._apply_formula_for_row(row)

    def hitung_ulang_total_tagihan(self, *_):
        if self._sedang_memuat_item:
            return

        amount_key = self.active_template.get("amount_key", "amount")
        amount_column = self._column_index_by_key(amount_key)
        subtotal = 0

        if amount_column >= 0:
            for row in range(self.tabel_item_invoice.rowCount()):
                item = self.tabel_item_invoice.item(row, amount_column)

                # PENGGUNAAN HELPER
                subtotal += rupiah_to_int(item.text() if item else "0")

        tax_name = self.cmb_pajak.currentText()
        tax_rate = {"NONPAJAK": Decimal("0"), "PPN 1,1%": Decimal("0.011")}.get(tax_name, Decimal("0"))
        tax_value = int((Decimal(subtotal) * tax_rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        self.total_invoice_aktif = subtotal + tax_value

        # PENGGUNAAN HELPER
        self.lbl_subtotal.setText(f"SUB TOTAL: Rp {format_ke_rupiah(subtotal)}")
        self.lbl_pajak_nominal.setText(f"{tax_name}: Rp {format_ke_rupiah(tax_value)}")
        self.lbl_total_tagihan.setText(f"TOTAL TAGIHAN: Rp {format_ke_rupiah(self.total_invoice_aktif)}")

    def ubah_rekening_otomatis(self, *_):
        if self._loading_invoice:
            return

        try:
            from config import DEFAULT_CLIENT_DATA, muat_pengaturan_sistem

            pengaturan = DEFAULT_CLIENT_DATA.copy()
            pengaturan.update(muat_pengaturan_sistem())

            pajak_dipilih = self.cmb_pajak.currentText()

            if pajak_dipilih == "NONPAJAK":
                list_rekening = pengaturan.get("rekening_nonpajak", [])
            else:
                list_rekening = pengaturan.get("rekening_pajak", [])

            if isinstance(list_rekening, list) and list_rekening:
                teks_rekening = " | ".join(list_rekening)
            elif isinstance(list_rekening, str):
                teks_rekening = list_rekening
            else:
                teks_rekening = ""

            self.txt_payment_info.setText(teks_rekening)

        except ImportError:
            pass

    def terima_data_baru(self, nama_client, list_resi_data):
        self.buat_invoice_baru()
        self._loading_invoice = True
        try:
            self.txt_client.setText(str(nama_client).strip().upper())
            self.cmb_tipe_invoice.setCurrentText("Standar")
            self.current_template_override = None
            self.apply_template(preserve_rows=False)

            self._sedang_memuat_item = True
            with blokir_signal_sementara(self.tabel_item_invoice):
                self.tabel_item_invoice.setRowCount(0)

                for data in list_resi_data:
                    row = self.tabel_item_invoice.rowCount()
                    self.tabel_item_invoice.insertRow(row)
                    values = {
                        "resi": str(data.get("no_resi", "")).strip().upper(),
                        "description": str(data.get("ket_buku_gudang", "")).strip(),
                        "amount": str(data.get("ongkir", "0")).strip(),
                    }
                    for column_index, column in enumerate(self.active_columns):
                        # PENGGUNAAN HELPER
                        item = self._buat_item_tabel(values.get(column["key"], ""), column)
                        self.tabel_item_invoice.setItem(row, column_index, item)

                if self.tabel_item_invoice.rowCount() == 0:
                    self.tabel_item_invoice.insertRow(0)
        finally:
            self._sedang_memuat_item = False
            self._loading_invoice = False

        self.hitung_ulang_total_tagihan()
        self._mark_dirty()

    def _generate_no_invoice(self):
        try:
            from config import CURRENT_SESSION, muat_pengaturan_sistem
            pengaturan = muat_pengaturan_sistem()
            prefix_inv = pengaturan.get("prefix_invoice", "INV")
            branch_code = CURRENT_SESSION.get("kode_cabang", "PUSAT").strip().upper()
        except ImportError:
            prefix_inv = "INV"
            branch_code = "PUSAT"

        prefix = f"{prefix_inv}-{branch_code}-{datetime.now().strftime('%Y%m%d')}"
        sequence = db_service.dapatkan_sequence_invoice_baru(prefix)
        return f"{prefix}-{sequence:04d}"

    def _metadata_dict(self):
        metadata = {
            "ship_to": self.txt_ship_to.text().strip(),
            "payment_info": self.txt_payment_info.text().strip(),
            "notes": self.txt_catatan.text().strip(),
            "signer": self.txt_penanda_tangan.text().strip(),
        }
        if self.current_template_override:
            metadata["template_config"] = self.current_template_override
        return metadata

    def ambil_data_item_invoice(self):
        items = []
        amount_key = self.active_template.get("amount_key", "amount")
        amount_column = self._column_index_by_key(amount_key)

        for row in range(self.tabel_item_invoice.rowCount()):
            row_data = {}
            for column_index, column in enumerate(self.active_columns):
                item = self.tabel_item_invoice.item(row, column_index)
                row_data[column["key"]] = item.text().strip() if item else ""

            if not any(row_data.values()):
                continue

            amount_item = self.tabel_item_invoice.item(row, amount_column) if amount_column >= 0 else None

            # PENGGUNAAN HELPER
            nominal = rupiah_to_int(amount_item.text() if amount_item else "0")
            items.append(
                {
                    "nomor_urut": row,
                    "data_kolom": json.dumps(row_data, ensure_ascii=False),
                    "nominal": nominal,
                }
            )
        return items

    def simpan_invoice_ke_db(self):
        client = self.txt_client.text().strip().upper()
        items = self.ambil_data_item_invoice()

        if not client:
            QMessageBox.warning(self, "Peringatan", "Nama client / Bill To tidak boleh kosong.")
            return
        if not items:
            QMessageBox.warning(self, "Peringatan", "Belum ada item tagihan yang akan disimpan.")
            return

        self.hitung_ulang_total_tagihan()
        manual_number = self.txt_no_invoice.text().strip().upper()
        no_invoice = self.no_invoice_aktif or manual_number or self._generate_no_invoice()

        header_data = {
            "no_invoice": no_invoice,
            "tanggal": self.date_invoice.date().toString("yyyy-MM-dd"),
            "client": client,
            "tipe_invoice": self.cmb_tipe_invoice.currentText(),
            "jenis_pajak": self.cmb_pajak.currentText(),
            "subtotal": sum(item["nominal"] for item in items),
            "total_akhir": self.total_invoice_aktif,
            "status": self.status_invoice_aktif,
            "metadata_json": json.dumps(self._metadata_dict(), ensure_ascii=False),
            "template_version": int(self.active_template.get("version", 1))
        }

        try:
            is_update = self.no_invoice_aktif is not None
            sukses, pesan = db_service.simpan_atau_update_invoice(header_data, items, is_update)

            if not sukses:
                if "sudah digunakan" in pesan.lower():
                    QMessageBox.warning(self, "Nomor Invoice Sudah Ada",
                                        "Nomor invoice tersebut sudah tersimpan. Buka dari histori untuk mengeditnya.")
                else:
                    QMessageBox.warning(self, "Peringatan", pesan)
                return

            self.no_invoice_aktif = no_invoice
            self.txt_no_invoice.setText(no_invoice)
            self._dirty = False
            self.btn_simpan_db.setEnabled(False)
            self.lbl_title_editor.setText(f"{self.status_invoice_aktif} INVOICE: {no_invoice}")
            self.load_histori_invoice()
            QMessageBox.information(self, "Sukses", f"Invoice {no_invoice} berhasil disimpan.")

        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Gagal menyimpan invoice:\n{exc}")

    def load_histori_invoice(self):
        self.tabel_histori_invoice.setRowCount(0)
        try:
            rows = db_service.ambil_histori_invoice(limit=300)
            for data in rows:
                row = self.tabel_histori_invoice.rowCount()
                self.tabel_histori_invoice.insertRow(row)
                for column, value in enumerate(data):
                    # PENGGUNAAN HELPER
                    item = buat_tabel_item(text=value, editable=False)
                    item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                    self.tabel_histori_invoice.setItem(row, column, item)
        except Exception as e:
            print(f"Error load histori invoice: {e}")

    def filter_histori_invoice(self, *_):
        keyword = self.txt_cari_invoice.text().strip().lower()
        for row in range(self.tabel_histori_invoice.rowCount()):
            match = any(
                self.tabel_histori_invoice.item(row, column)
                and keyword in self.tabel_histori_invoice.item(row, column).text().lower()
                for column in range(self.tabel_histori_invoice.columnCount())
            )
            self.tabel_histori_invoice.setRowHidden(row, not match)

    def buka_invoice_dari_histori(self, *_):
        selected = self.tabel_histori_invoice.selectionModel().selectedRows()
        if selected:
            no_invoice = self.tabel_histori_invoice.item(selected[0].row(), self.KOL_HISTORI_NO_INV).text()
            self.load_invoice_by_no(no_invoice)

    def load_invoice_by_no(self, no_invoice):
        try:
            header, details = db_service.ambil_invoice_by_no(no_invoice)
            if not header:
                return

            self._loading_invoice = True
            self._sedang_memuat_item = True
            try:
                client, template_name, tax_name, status, date_text, metadata_text = header
                metadata = json.loads(metadata_text or "{}") if metadata_text else {}

                self.no_invoice_aktif = no_invoice
                self.status_invoice_aktif = status or "DRAFT"
                self.txt_no_invoice.setText(no_invoice)
                self.txt_client.setText(client or "")
                self.txt_ship_to.setText(metadata.get("ship_to", ""))
                self.txt_payment_info.setText(metadata.get("payment_info", ""))
                self.txt_catatan.setText(metadata.get("notes", ""))
                self.txt_penanda_tangan.setText(metadata.get("signer", ""))

                parsed_date = QDate.fromString(date_text or "", "yyyy-MM-dd")
                self.date_invoice.setDate(parsed_date if parsed_date.isValid() else QDate.currentDate())

                if template_name not in self.template_configs:
                    self.cmb_tipe_invoice.addItem(template_name)
                    self.template_configs[template_name] = deepcopy(self.template_configs["Custom / Bebas"])
                self.cmb_tipe_invoice.setCurrentText(template_name)
                self.cmb_pajak.setCurrentText(tax_name or "NONPAJAK")

                override = metadata.get("template_config")
                self.current_template_override = override if isinstance(override, dict) else None
                self.apply_template(preserve_rows=False)

                with blokir_signal_sementara(self.tabel_item_invoice):
                    self.tabel_item_invoice.setRowCount(0)
                    for detail in details:
                        try:
                            data = json.loads(detail[0] or "{}")
                        except Exception:
                            data = {}
                        row = self.tabel_item_invoice.rowCount()
                        self.tabel_item_invoice.insertRow(row)
                        for column_index, column in enumerate(self.active_columns):
                            value = data.get(column["key"], data.get(column["title"], ""))

                            # PENGGUNAAN HELPER
                            item = self._buat_item_tabel(value, column)
                            self.tabel_item_invoice.setItem(row, column_index, item)

                    if self.tabel_item_invoice.rowCount() == 0:
                        self.tabel_item_invoice.insertRow(0)

                self.lbl_title_editor.setText(f"{self.status_invoice_aktif} INVOICE: {no_invoice}")
                self._dirty = False
                self.btn_simpan_db.setEnabled(False)
            finally:
                self._sedang_memuat_item = False
                self._loading_invoice = False

            self.hitung_ulang_total_tagihan()

        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Gagal membuka invoice:\n{exc}")

    def buat_invoice_baru(self):
        if self._dirty:
            answer = QMessageBox.question(
                self,
                "Invoice Belum Disimpan",
                "Perubahan belum disimpan. Tetap buat invoice baru?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

        self._loading_invoice = True
        try:
            self.no_invoice_aktif = None
            self.status_invoice_aktif = "DRAFT"
            self.current_template_override = None

            # PENGGUNAAN HELPER MEMBERSIHKAN FORM
            # Membersihkan seluruh field di panel kanan dengan bersih total
            reset_form_input_global(
                self.panel_kanan,
                reset_tanggal=True,
                fokus_ke=self.txt_client,
            )

            window = self.window()
            is_dark = bool(
                window
                and hasattr(window, "current_theme")
                and window.current_theme == "dark"
            )
            terap_semua_placeholder_dinamis(
                self.panel_kanan,
                is_dark=is_dark,
            )

            # Kembalikan ke pilihan default
            self.cmb_tipe_invoice.setCurrentText("Standar")
            self.cmb_pajak.setCurrentText("NONPAJAK")

            self.apply_template(preserve_rows=False)
            self.lbl_title_editor.setText("DRAFT INVOICE BARU")
            self._dirty = False
            self.btn_simpan_db.setEnabled(True)
        finally:
            self._loading_invoice = False

        self.ubah_rekening_otomatis()
        self.hitung_ulang_total_tagihan()

    def _confirm_clear_table(self):
        answer = QMessageBox.question(
            self,
            "Bersihkan Tabel",
            "Kosongkan seluruh item pada invoice?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.tabel_item_invoice.clear_all_rows()

    # ------------------------------------------------------
    # PREVIEW DAN PDF
    # ------------------------------------------------------
    @staticmethod
    def _esc(value):
        return html.escape(str(value if value is not None else ""))

    def _visible_rows(self):
        rows = []
        for row in range(self.tabel_item_invoice.rowCount()):
            data = {}
            for column_index, column in enumerate(self.active_columns):
                item = self.tabel_item_invoice.item(row, column_index)
                data[column["key"]] = item.text().strip() if item else ""
            if any(data.values()):
                rows.append(data)
        return rows

    def build_invoice_html(self):
        self.hitung_ulang_total_tagihan()
        invoice_number = self.no_invoice_aktif or self.txt_no_invoice.text().strip() or "DRAFT"
        client = self.txt_client.text().strip().upper() or "-"
        ship_to = self.txt_ship_to.text().strip().upper() or "-"
        date_text = self.date_invoice.date().toString("dd MMMM yyyy")
        payment = self.txt_payment_info.text().strip()
        notes = self.txt_catatan.text().strip()
        layout_type = self.active_template.get("layout", "standard")
        rows = self._visible_rows()

        nama_perusahaan = "PT NAMA PERUSAHAAN"
        alamat_lengkap = "Alamat Perusahaan<br>Telp: 08xx"
        logo_html = "LOGO"
        default_signer = "Admin"

        try:
            from config import CURRENT_SESSION, DEFAULT_CLIENT_DATA, muat_pengaturan_sistem
            data_perusahaan = DEFAULT_CLIENT_DATA.copy()
            data_perusahaan.update(muat_pengaturan_sistem())

            nama_perusahaan = data_perusahaan.get("nama_perusahaan", "")
            alamat = data_perusahaan.get("alamat", "")
            telp = data_perusahaan.get("telp", "")
            logo_html = data_perusahaan.get("logo_text_html", nama_perusahaan)

            alamat_lengkap = f"{alamat}<br>Telp. {telp}"
            default_signer = CURRENT_SESSION.get("username", "Admin")
        except Exception:
            pass

        signer = self.txt_penanda_tangan.text().strip() or default_signer

        headers_html = "".join(
            f'<th style="width:{int(column.get("width", 100))}px">{self._esc(column.get("title", ""))}</th>'
            for column in self.active_columns
        )

        body_lines = []
        for row_data in rows:
            cells = []
            for column in self.active_columns:
                value = row_data.get(column["key"], "")
                data_type = column.get("type", "text")
                cls = "num" if data_type in {"currency", "integer", "decimal"} else ""

                # PENGGUNAAN HELPER
                if data_type == "currency" and value:
                    parsed = rupiah_to_int(value)
                    value = format_ke_rupiah(parsed) if parsed else value

                cells.append(f'<td class="{cls}">{self._esc(value)}</td>')
            body_lines.append("<tr>" + "".join(cells) + "</tr>")

        if not body_lines:
            body_lines.append(
                f'<tr><td colspan="{max(len(self.active_columns), 1)}" class="empty">Belum ada item</td></tr>')

        subtotal = sum(item["nominal"] for item in self.ambil_data_item_invoice())
        tax_name = self.cmb_pajak.currentText()
        tax_value = self.total_invoice_aktif - subtotal

        if layout_type == "logistics":
            party_header = f"""
                <table class="party single">
                    <tr><th>TO :</th><td>{self._esc(client)}</td></tr>
                </table>
            """
        else:
            party_header = f"""
                <table class="party">
                    <tr>
                        <th>BILL TO</th>
                        <th>SHIP TO</th>
                    </tr>
                    <tr>
                        <td>{self._esc(client)}</td>
                        <td>{self._esc(ship_to)}</td>
                    </tr>
                </table>
            """

        notes_html = f'<div class="notes"><b>Catatan:</b> {self._esc(notes)}</div>' if notes else ""
        payment_html = self._esc(payment).replace("\n", "<br>") if payment else "-"

        # PENGGUNAAN HELPER DALAM F-STRING TABEL HTML BAWAH (Rp {format_ke_rupiah(subtotal)})
        return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
    @page {{ size: A4; margin: 8mm; }}
    * {{ box-sizing: border-box; }}
    body {{ font-family: "{typography.MASTER_FONT}"; color: #111; font-size: 10pt; margin: 0; }}
    .page {{ width: 100%; }}
    .company {{ width: 100%; border: 1px solid #111; border-bottom: none; border-collapse: collapse; }}
    .company td {{ padding: 7px 10px; vertical-align: middle; }}
    .brand {{ font-size: 18pt; font-weight: bold; color: #1747a6; }}
    .logo-kargo {{ color: #e00000; }}
    .address {{ text-align:right; font-size:9pt; }}
    .invoice-title {{ border: 1px solid #111; text-align:center; padding:5px; }}
    .invoice-title .title {{ font-size:13pt; font-weight:bold; }}
    .invoice-title .number {{ font-size:10pt; margin-top:2px; }}
    .party {{ width:100%; border-collapse:collapse; margin-top:0; table-layout:fixed; }}
    .party th, .party td {{ border:1px solid #111; padding:5px 8px; text-align:center; }}
    .party th {{ background:#e5e5e5; font-weight:bold; }}
    .party.single th {{ width:70px; text-align:left; }}
    .party.single td {{ text-align:left; font-size:13pt; font-weight:bold; }}
    .items {{ width:100%; border-collapse:collapse; table-layout:fixed; margin-top:0; }}
    .items th, .items td {{ border:1px solid #111; padding:4px 5px; word-wrap:break-word; vertical-align:top; }}
    .items th {{ background:#d9d9d9; text-align:center; font-size:8.5pt; }}
    .items td {{ font-size:8.5pt; }}
    .items .num {{ text-align:right; white-space:nowrap; }}
    .items .empty {{ text-align:center; color:#777; padding:20px; }}
    .bottom {{ width:100%; border-collapse:collapse; margin-top:0; }}
    .bottom td {{ vertical-align:top; }}
    .payment {{ width:65%; padding:8px 4px; line-height:1.45; }}
    .totals {{ width:35%; border-collapse:collapse; }}
    .totals td {{ border:1px solid #111; padding:5px 7px; }}
    .totals .label {{ text-align:right; font-weight:bold; }}
    .totals .value {{ text-align:right; white-space:nowrap; }}
    .totals .grand {{ font-size:13pt; font-weight:bold; }}
    .notes {{ margin-top:8px; padding:6px; border:1px solid #999; }}
    .signature {{ margin-top:12px; text-align:right; padding-right:18px; }}
    .signature .space {{ height:55px; }}
    .signature .name {{ font-weight:bold; text-decoration:underline; }}
</style>
</head>
<body>
<div class="page">
    <table class="company">
        <tr>
            <td>
                <span class="brand">{logo_html}</span><br>
                <span style="font-weight:bold;">{self._esc(nama_perusahaan)}</span>
            </td>
            <td class="address">{alamat_lengkap}</td>
        </tr>
    </table>

    <div class="invoice-title">
        <div class="title">INVOICE</div>
        <div class="number">No. {self._esc(invoice_number)}</div>
    </div>

    {party_header}

    <table class="items">
        <thead><tr>{headers_html}</tr></thead>
        <tbody>{''.join(body_lines)}</tbody>
    </table>

    <table class="bottom">
        <tr>
            <td class="payment">
                <b>PAYMENT INFO</b><br>{payment_html}
                {notes_html}
            </td>
            <td>
                <table class="totals">
                    <tr><td class="label">SUB TOTAL</td><td class="value">Rp {format_ke_rupiah(subtotal)}</td></tr>
                    <tr><td class="label">{self._esc(tax_name)}</td><td class="value">Rp {format_ke_rupiah(tax_value)}</td></tr>
                    <tr><td class="label grand">TOTAL</td><td class="value grand">Rp {format_ke_rupiah(self.total_invoice_aktif)}</td></tr>
                </table>
            </td>
        </tr>
    </table>

    <div class="signature">
        Surabaya, {self._esc(date_text)}
        <div class="space"></div>
        <div class="name">{self._esc(signer)}</div>
    </div>
</div>
</body>
</html>
        """

    def tampilkan_preview(self):
        html_content = self.build_invoice_html()
        default_name = self.no_invoice_aktif or self.txt_no_invoice.text().strip() or "invoice_draft"

        tampilkan_preview_invoice(
            html_content=html_content,
            suggested_name=default_name,
            parent=self,
        )

    def cetak_pdf(self):
        html_content = self.build_invoice_html()
        default_name = self.no_invoice_aktif or self.txt_no_invoice.text().strip() or "invoice_draft"

        simpan_invoice_pdf(
            html_content=html_content,
            suggested_name=default_name,
            parent=self,
        )

    def cetak_langsung(self, tipe_kertas):
        printer = QPrinter(QPrinter.HighResolution)

        if tipe_kertas == "A4":
            printer.setPageSize(QPrinter.A4)
            printer.setPageMargins(8, 8, 8, 8, QPrinter.Millimeter)

        elif tipe_kertas == "NCR":
            custom_size = QPageSize(QSizeF(9.5, 5.5), QPageSize.Inch)
            printer.setPageSize(custom_size)
            printer.setPageMargins(4, 4, 4, 4, QPrinter.Millimeter)

        dialog = QPrintDialog(printer, self)
        dialog.setWindowTitle("Pilih Printer")

        if dialog.exec_() == QPrintDialog.Accepted:
            html_content = self.build_invoice_html()

            if tipe_kertas == "NCR":
                html_content = html_content.replace(
                    f'body {{ font-family: "{typography.MASTER_FONT}"; color: #111; font-size: 10pt; margin: 0; }}',
                    'body { font-family: "Courier New", monospace; color: #000; font-size: 9pt; font-weight: bold; margin: 0; }'
                )

            document = QTextDocument()
            document.setHtml(html_content)

            try:
                document.print_(printer)
                QMessageBox.information(
                    self,
                    "Sukses",
                    f"Invoice sedang dikirim ke printer:\n{printer.printerName()}"
                )
            except Exception as exc:
                QMessageBox.critical(self, "Gagal Mencetak", str(exc))

    def info_fitur_cetak(self):
        self.cetak_pdf()

    def info_fitur_share(self):
        QMessageBox.information(
            self,
            "Share WhatsApp",
            "PDF invoice sudah dapat dibuat. Pengiriman WhatsApp dapat disambungkan setelah metode API/WhatsApp Desktop ditentukan.",
        )

    # ------------------------------------------------------
    # TEMA
    # ------------------------------------------------------
    def showEvent(self, event):
        super().showEvent(event)
        self.load_histori_invoice()

    def sesuaikan_tema_lokal(self):
        window = self.window()
        is_dark = bool(window and hasattr(window, "current_theme") and window.current_theme == "dark")

        terap_semua_placeholder_dinamis(
            self,
            is_dark=is_dark,
        )

        z = zoom_helper.dapatkan_zoom_level(self.__class__.__name__)

        font_sizes_fixed = get_global_font_sizes(0)
        font_sizes_zoomed = get_global_font_sizes(z)

        st_fixed = get_invoice_styles(
            is_dark, font_sizes_fixed["sz_title"], font_sizes_fixed["sz_base"],
            font_sizes_fixed["sz_input"], font_sizes_fixed["sz_total"]
        )
        st_zoomed = get_invoice_styles(
            is_dark, font_sizes_zoomed["sz_title"], font_sizes_zoomed["sz_base"],
            font_sizes_zoomed["sz_input"], font_sizes_zoomed["sz_total"]
        )

        # BAGIAN LUAR KOTAK MERAH
        self.lbl_title_histori.setStyleSheet(st_fixed["lbl_title_histori"])
        self.lbl_title_editor.setStyleSheet(st_fixed["lbl_title_editor"])
        self.lbl_subtotal.setStyleSheet(st_fixed["lbl_subtotal"])
        self.lbl_pajak_nominal.setStyleSheet(st_fixed["lbl_subtotal"])
        self.lbl_total_tagihan.setStyleSheet(st_fixed["lbl_total_tagihan"])

        self.txt_cari_invoice.setStyleSheet(st_fixed["input"])
        self.tabel_histori_invoice.setStyleSheet(st_fixed["tabel_histori"])

        font_histori = self.tabel_histori_invoice.font()
        font_histori.setPointSize(font_sizes_fixed["sz_base"])
        self.tabel_histori_invoice.setFont(font_histori)
        self.tabel_histori_invoice.horizontalHeader().setFont(font_histori)
        self.tabel_histori_invoice.verticalHeader().setFont(font_histori)
        self.tabel_histori_invoice.verticalHeader().setDefaultSectionSize(28)

        for button in self.findChildren(QPushButton):
            button.setStyleSheet(st_fixed["button_default"])

        self.btn_simpan_db.setStyleSheet(st_fixed["button_simpan"])
        self.btn_preview.setStyleSheet(st_fixed["button_preview"])
        self.btn_cetak.setStyleSheet(st_fixed["button_cetak"])
        self.btn_share.setStyleSheet(st_fixed["button_share"])

        if hasattr(self, "menu_cetak"):
            self.menu_cetak.setStyleSheet(st_fixed["menu_cetak"])

        # BAGIAN DALAM KOTAK MERAH
        fields_zoomed = [
            self.txt_client, self.txt_ship_to, self.txt_no_invoice,
            self.txt_payment_info, self.txt_catatan, self.txt_penanda_tangan
        ]
        for widget in fields_zoomed:
            widget.setStyleSheet(st_zoomed["input"])

        self.cmb_tipe_invoice.setStyleSheet(st_zoomed["input"])
        self.cmb_pajak.setStyleSheet(st_zoomed["input"])
        self.date_invoice.setStyleSheet(st_zoomed["input"])

        toolbar_buttons = [
            self.btn_tambah_baris, self.btn_hapus_baris, self.btn_duplikat_baris,
            self.btn_naik, self.btn_turun, self.btn_paste, self.btn_atur_kolom,
            self.btn_bersihkan
        ]
        for button in toolbar_buttons:
            button.setStyleSheet(st_zoomed["button_default"])

        self.tabel_item_invoice.setStyleSheet(st_zoomed["tabel_editor"])

        font_editor = self.tabel_item_invoice.font()
        font_editor.setPointSize(font_sizes_zoomed["sz_base"])
        self.tabel_item_invoice.setFont(font_editor)

        header_font_editor = self.tabel_item_invoice.horizontalHeader().font()
        header_font_editor.setPointSize(font_sizes_zoomed["sz_base"])
        self.tabel_item_invoice.horizontalHeader().setFont(header_font_editor)
        self.tabel_item_invoice.verticalHeader().setFont(header_font_editor)

        faktor = max(0.68, min(1.0 + (z * 0.08), 1.80))
        tinggi_baris = max(24, int(32 * faktor))
        self.tabel_item_invoice.verticalHeader().setDefaultSectionSize(tinggi_baris)

        with blokir_signal_sementara(
            self.tabel_item_invoice.horizontalHeader()
        ):
            zoom_helper._skalakan_kolom_tableview(
                self.tabel_item_invoice,
                z,
            )