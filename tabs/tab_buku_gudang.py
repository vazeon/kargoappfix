# tabs/tab_buku_gudang.py
from datetime import datetime
from PyQt5.QtGui import QColor, QBrush, QFont
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QMenu, QMessageBox, QLineEdit, QComboBox, QDateEdit,
                             QWidgetAction, QVBoxLayout as VBox, QLabel, QApplication,
                             QToolButton, QAction, QPushButton, QDialog, QRadioButton)
from PyQt5.QtCore import Qt, QDate, QSettings, QEvent

from config import CURRENT_SESSION, DATA_CLIENT

import services.database_service as db_service

from utils.typography import (MASTER_FONT, get_global_font_sizes)
from utils.number_formatters import (format_ke_rupiah, rupiah_to_int)
from utils.validators import (get_decimal_validator,get_integer_validator)
from utils.widget_helpers import (paksa_kapital_lineedit)
from themes.modules.buku_gudang import (
    BUKU_GUDANG_INLINE_EDITOR_STYLE,
    get_buku_gudang_action_styles,
    get_buku_gudang_menu_style,
    get_buku_gudang_status_colors,
    get_buku_gudang_styles,
    get_dialog_pilih_penagih_styles,
)


class DialogPilihPenagih(QDialog):
    def __init__(self, nama_pengirim, nama_penerima, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pilih Pihak Tertagih")
        self.setMinimumWidth(350)
        dialog_styles = get_dialog_pilih_penagih_styles()
        self.setStyleSheet(dialog_styles["dialog"])

        layout = QVBoxLayout(self)

        lbl_info = QLabel("<b>Invoice ini akan ditagihkan kepada:</b>")
        layout.addWidget(lbl_info)

        self.rb_pengirim = QRadioButton(f"Pengirim ({nama_pengirim})")
        self.rb_penerima = QRadioButton(f"Penerima ({nama_penerima})")
        self.rb_ketiga = QRadioButton("Pihak Ketiga:")

        self.rb_pengirim.setChecked(True)

        self.txt_ketiga = QLineEdit()
        self.txt_ketiga.setPlaceholderText("Ketik nama pihak ketiga...")
        self.txt_ketiga.setEnabled(False)
        self.txt_ketiga.setStyleSheet(dialog_styles["input"])

        self.rb_ketiga.toggled.connect(lambda: self.txt_ketiga.setEnabled(self.rb_ketiga.isChecked()))

        layout.addWidget(self.rb_pengirim)
        layout.addWidget(self.rb_penerima)
        layout.addWidget(self.rb_ketiga)
        layout.addWidget(self.txt_ketiga)

        layout.addSpacing(10)

        hbox_btn = QHBoxLayout()
        self.btn_lanjut = QPushButton("Lanjutkan ke Invoice")
        self.btn_lanjut.setCursor(Qt.PointingHandCursor)
        self.btn_lanjut.setStyleSheet(dialog_styles["btn_lanjut"])

        self.btn_batal = QPushButton("Batal")
        self.btn_batal.setCursor(Qt.PointingHandCursor)
        self.btn_batal.setStyleSheet(dialog_styles["btn_batal"])

        hbox_btn.addWidget(self.btn_lanjut)
        hbox_btn.addWidget(self.btn_batal)
        layout.addLayout(hbox_btn)

        self.btn_lanjut.clicked.connect(self.validasi_dan_lanjut)
        self.btn_batal.clicked.connect(self.reject)

    def validasi_dan_lanjut(self):
        if self.rb_ketiga.isChecked() and not self.txt_ketiga.text().strip():
            QMessageBox.warning(self, "Peringatan", "Nama Pihak Ketiga tidak boleh kosong!")
            self.txt_ketiga.setFocus()
            return
        self.accept()

    def get_nama_client(self):
        if self.rb_pengirim.isChecked():
            return self.rb_pengirim.text().replace("Pengirim (", "").replace(")", "")
        elif self.rb_penerima.isChecked():
            return self.rb_penerima.text().replace("Penerima (", "").replace(")", "")
        else:
            return self.txt_ketiga.text().strip().upper()


class TabBukuGudang(QWidget):
    KOL_NO = 0
    KOL_RESI = 1
    KOL_MASUK = 2
    KOL_KELUAR = 3
    KOL_STATUS = 4
    KOL_ARMADA = 5
    KOL_PENGIRIM = 6
    KOL_KOTA_ASAL = 7
    KOL_PENERIMA = 8
    KOL_KOTA_TUJUAN = 9
    KOL_NAMA_BARANG = 10
    KOL_KOLI = 11
    KOL_BERAT = 12
    KOL_CBM = 13
    KOL_ONGKIR = 14
    KOL_PAYMENT = 15
    KOL_KETERANGAN = 16

    def __init__(self):
        super().__init__()
        self.tabs_list = []
        self.row_sedang_diedit = -1
        self.init_ui()

    def init_ui(self):
        layout_utama = QVBoxLayout(self)
        layout_utama.setContentsMargins(15, 15, 15, 15)
        layout_utama.setSpacing(10)

        hbox_header = QHBoxLayout()
        self.lbl_judul = QLabel("📑 Buku Gudang")
        hbox_header.addWidget(self.lbl_judul)

        tahun_sekarang = datetime.now().year
        self.btn_tahun = QToolButton()
        self.btn_tahun.setText(str(tahun_sekarang))
        self.btn_tahun.setPopupMode(QToolButton.InstantPopup)
        self.btn_tahun.setFixedWidth(120)
        self.btn_tahun.setCursor(Qt.PointingHandCursor)

        self.menu_tahun = QMenu(self)
        self.setup_menu_tahun(tahun_sekarang)
        self.btn_tahun.setMenu(self.menu_tahun)

        hbox_header.addWidget(self.btn_tahun)
        hbox_header.addStretch()

        self.txt_cari = QLineEdit()
        self.txt_cari.setPlaceholderText("Ketik pencarian (Resi, Truk, Barang, dll)...")
        self.txt_cari.setFixedWidth(280)
        self.txt_cari.textChanged.connect(lambda: paksa_kapital_lineedit(self.txt_cari))
        self.txt_cari.textChanged.connect(self.filter_pencarian_tabel)
        hbox_header.addWidget(self.txt_cari)

        action_styles = get_buku_gudang_action_styles()

        self.btn_buat_invoice = QPushButton("🧾 Buat Invoice")
        self.btn_buat_invoice.setStyleSheet(action_styles["btn_buat_invoice"])
        self.btn_buat_invoice.setCursor(Qt.PointingHandCursor)

        self.btn_simpan_inv = QPushButton("✅ Simpan")
        self.btn_simpan_inv.setStyleSheet(action_styles["btn_simpan_inv"])
        self.btn_simpan_inv.setCursor(Qt.PointingHandCursor)
        self.btn_simpan_inv.setVisible(False)

        self.btn_batal_inv = QPushButton("❌ Batal")
        self.btn_batal_inv.setStyleSheet(action_styles["btn_batal_inv"])
        self.btn_batal_inv.setCursor(Qt.PointingHandCursor)
        self.btn_batal_inv.setVisible(False)

        hbox_header.addWidget(self.btn_buat_invoice)
        hbox_header.addWidget(self.btn_simpan_inv)
        hbox_header.addWidget(self.btn_batal_inv)

        self.btn_buat_invoice.clicked.connect(self.aktifkan_mode_invoice)
        self.btn_batal_inv.clicked.connect(self.batalkan_mode_invoice)
        self.btn_simpan_inv.clicked.connect(self.proses_simpan_ke_invoice)

        layout_utama.addLayout(hbox_header)

        self.tabs_wilayah = QTabWidget()
        provinsi_tujuan = DATA_CLIENT.get('provinsi_tujuan', ["PROVINSI A", "PROVINSI B", "PROVINSI C"])

        for wilayah in provinsi_tujuan:
            widget_tabel = self.create_tabel_tab(wilayah)
            self.tabs_list.append(widget_tabel)
            self.tabs_wilayah.addTab(widget_tabel, f"{wilayah.title()}")

        layout_utama.addWidget(self.tabs_wilayah)
        self.tabs_wilayah.currentChanged.connect(lambda index: self.refresh_session_ui())

        self.refresh_session_ui()
        self.sesuaikan_tema_lokal()

    def aktifkan_mode_invoice(self):
        self.btn_buat_invoice.setVisible(False)
        self.btn_simpan_inv.setVisible(True)
        self.btn_batal_inv.setVisible(True)
        QMessageBox.information(self, "Mode Invoice",
                                "Silakan blok/pilih baris resi yang ingin dijadikan Invoice, lalu klik 'Simpan'.")

    def batalkan_mode_invoice(self):
        self.btn_buat_invoice.setVisible(True)
        self.btn_simpan_inv.setVisible(False)
        self.btn_batal_inv.setVisible(False)
        if self.tabs_wilayah.currentWidget() and hasattr(self.tabs_wilayah.currentWidget(), 'tabel'):
            self.tabs_wilayah.currentWidget().tabel.clearSelection()

    def _ambil_baris_terseleksi_invoice(self, tabel):
        rows = []
        selection_model = tabel.selectionModel()
        if selection_model:
            rows = [idx.row() for idx in selection_model.selectedRows()]

        if not rows:
            rows = [item.row() for item in tabel.selectedItems()]

        return sorted(set(rows))

    def _ambil_text_item(self, tabel, row, col):
        item = tabel.item(row, col)
        return item.text().strip() if item else ""

    def _cari_tab_invoice(self):
        win = self.window()
        if not win:
            return None

        tab_invoice = getattr(win, 'tab_invoice', None)
        if tab_invoice and hasattr(tab_invoice, 'terima_data_baru'):
            return tab_invoice

        for widget in win.findChildren(QWidget):
            if widget.__class__.__name__ == 'TabInvoice' and hasattr(widget, 'terima_data_baru'):
                return widget

        for widget in win.findChildren(QWidget):
            if hasattr(widget, 'terima_data_baru') and hasattr(widget, 'tabel_item_invoice'):
                return widget

        return None

    def _pindah_ke_tab_invoice(self, tab_invoice):
        win = self.window()
        if not win or not tab_invoice:
            return False

        tabs_utama = getattr(win, 'tabs_utama', None)
        if isinstance(tabs_utama, QTabWidget) and tabs_utama.indexOf(tab_invoice) != -1:
            tabs_utama.setCurrentWidget(tab_invoice)
            return True

        for tab_widget in win.findChildren(QTabWidget):
            idx = tab_widget.indexOf(tab_invoice)
            if idx != -1:
                tab_widget.setCurrentIndex(idx)
                return True

        return False

    def proses_simpan_ke_invoice(self):
        current_tab = self.tabs_wilayah.currentWidget()
        if not current_tab or not hasattr(current_tab, 'tabel'):
            QMessageBox.warning(self, "Peringatan", "Tabel Buku Gudang tidak ditemukan.")
            return

        tabel = current_tab.tabel
        baris_terseleksi = self._ambil_baris_terseleksi_invoice(tabel)

        if not baris_terseleksi:
            QMessageBox.warning(self, "Peringatan", "Anda belum memilih resi satupun!")
            return

        list_resi_data = []
        nama_pengirim_pertama = None
        nama_penerima_pertama = None
        peringatan_beda_pengirim_tampil = False

        for row in baris_terseleksi:
            if tabel.isRowHidden(row):
                continue

            no_resi = self._ambil_text_item(tabel, row, self.KOL_RESI)
            pengirim = self._ambil_text_item(tabel, row, self.KOL_PENGIRIM)
            penerima = self._ambil_text_item(tabel, row, self.KOL_PENERIMA)
            ongkir = self._ambil_text_item(tabel, row, self.KOL_ONGKIR)
            koli = self._ambil_text_item(tabel, row, self.KOL_KOLI)

            if not no_resi:
                continue

            if not nama_pengirim_pertama:
                nama_pengirim_pertama = pengirim
                nama_penerima_pertama = penerima

            if pengirim != nama_pengirim_pertama and not peringatan_beda_pengirim_tampil:
                tanya = QMessageBox.question(
                    self, "Konfirmasi",
                    "Resi yang dipilih memiliki nama PENGIRIM yang berbeda-beda.\nYakin ingin menggabungkannya ke dalam 1 Invoice?",
                    QMessageBox.Yes | QMessageBox.No
                )
                if tanya == QMessageBox.No:
                    return
                peringatan_beda_pengirim_tampil = True

            list_resi_data.append({
                'no_resi': no_resi,
                'ket_buku_gudang': f"Tujuan: {penerima} ({koli} KOLI)",
                'ongkir': ongkir if ongkir else "0"
            })

        if not list_resi_data:
            QMessageBox.warning(self, "Peringatan", "Data resi yang dipilih tidak valid atau kosong.")
            return

        dialog = DialogPilihPenagih(nama_pengirim_pertama, nama_penerima_pertama, self)
        if dialog.exec_() != QDialog.Accepted:
            return

        client_terpilih = dialog.get_nama_client()
        tab_invoice = self._cari_tab_invoice()

        if not tab_invoice:
            QMessageBox.critical(
                self,
                "Tab Invoice Tidak Ditemukan",
                "Data berhasil dibaca dari Buku Gudang, tetapi widget TabInvoice tidak ditemukan.\n"
                "Pastikan tab invoice sudah dibuat di MainWindow dan instance-nya tidak dibuat ulang."
            )
            return

        tab_invoice.terima_data_baru(client_terpilih, list_resi_data)

        if not self._pindah_ke_tab_invoice(tab_invoice):
            QMessageBox.information(
                self,
                "Data Invoice Siap",
                "Data sudah dikirim ke draft invoice, tetapi aplikasi tidak menemukan QTabWidget utama untuk berpindah otomatis."
            )

        self.batalkan_mode_invoice()

    def create_tabel_tab(self, wilayah):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 5, 0, 0)

        tabel = QTableWidget()
        tabel.setColumnCount(17)
        headers = ["NO.", "RESI", "MASUK", "KELUAR", "STATUS", "ARMADA", "PENGIRIM",
                   "KOTA ASAL", "PENERIMA", "KOTA TUJUAN", "NAMA BARANG",
                   "KOLI", "BERAT (kg)", "KUBIK (m3)", "ONGKIR (Rp)", "PAYMENT", "KETERANGAN"]
        tabel.setHorizontalHeaderLabels(headers)
        tabel.verticalHeader().setVisible(False)
        self.load_lebar_kolom(tabel)

        tabel.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        tabel.horizontalHeader().customContextMenuRequested.connect(lambda pos, t=tabel: self.show_header_menu(pos, t))

        tabel.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tabel.setSelectionBehavior(QAbstractItemView.SelectRows)
        tabel.setSelectionMode(QAbstractItemView.ExtendedSelection)
        tabel.setAlternatingRowColors(True)

        header = tabel.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setSectionsClickable(True)
        header.setSectionsMovable(True)

        tabel.horizontalHeader().sectionResized.connect(
            lambda logicalIndex, oldSize, newSize, t=tabel: self.simpan_lebar_kolom(t)
        )
        tabel.setContextMenuPolicy(Qt.CustomContextMenu)
        tabel.customContextMenuRequested.connect(lambda pos, t=tabel: self.show_cell_context_menu(pos, t))

        layout.addWidget(tabel)
        widget.tabel = tabel
        widget.wilayah = wilayah
        widget.filter_data = {}
        return widget

    def showEvent(self, event):
        super().showEvent(event)
        self.refresh_session_ui()

    def eventFilter(self, obj, event):
        if isinstance(obj, (QLineEdit, QComboBox)):
            if event.type() == QEvent.KeyPress and event.key() == Qt.Key_Escape:
                if getattr(self, 'row_sedang_diedit', -1) != -1:
                    self.refresh_session_ui()
                    return True
        if isinstance(obj, QLineEdit):
            is_numeric = getattr(obj, 'is_numeric_col', False)
            if event.type() == QEvent.FocusIn:
                if is_numeric and obj.text().strip() == "-": obj.setText("")
            elif event.type() == QEvent.FocusOut:
                if is_numeric and obj.text().strip() == "": obj.setText("-")
        return super().eventFilter(obj, event)

    def sesuaikan_tema_lokal(self):
        win = self.window()
        is_dark = win.current_theme == "dark" if win and hasattr(win, 'current_theme') else (
                "#25282e" in QApplication.instance().styleSheet().lower())
        settings = QSettings("AplikasiEkspedisi", "PengaturanUI")
        z = int(settings.value(f"zoom_{self.__class__.__name__}", 0))

        font_sizes = get_global_font_sizes(z)

        styles = get_buku_gudang_styles(
            is_dark=is_dark,
            sz_base=font_sizes["sz_base"],
            sz_input=font_sizes["sz_input"],
            sz_title=font_sizes["sz_title"],
        )

        self.lbl_judul.setStyleSheet(styles["lbl_judul"])
        self.btn_tahun.setStyleSheet(styles["btn_tahun"])
        self.txt_cari.setStyleSheet(styles["txt_cari"])

        for widget in self.tabs_list:
            if hasattr(widget, 'tabel'):
                widget.tabel.setStyleSheet(styles["tabel"])


    def setup_menu_tahun(self, tahun_sekarang):
        self.menu_tahun.clear()
        self.menu_tahun.setStyleSheet(get_buku_gudang_menu_style(14))

        for i in range(3):
            thn = str(tahun_sekarang - i)
            self.menu_tahun.addAction(thn).triggered.connect(lambda checked, t=thn: self.ubah_tahun(t))

        self.menu_tahun.addSeparator()

        submenu_lainnya = self.menu_tahun.addMenu("Lainnya...")
        submenu_lainnya.setStyleSheet(get_buku_gudang_menu_style(14))

        for i in range(3, 8):
            thn = str(tahun_sekarang - i)
            submenu_lainnya.addAction(thn).triggered.connect(lambda checked, t=thn: self.ubah_tahun(t))

    def ubah_tahun(self, tahun_pilihan):
        self.btn_tahun.setText(tahun_pilihan)
        self.refresh_session_ui()

    def get_editor_type(self, col_index):
        if col_index in [self.KOL_MASUK, self.KOL_KELUAR]: return "date"
        if col_index == self.KOL_STATUS: return "status"
        if col_index == self.KOL_PAYMENT: return "payment"
        return "text"

    def filter_pencarian_tabel(self):
        keyword = self.txt_cari.text().lower()
        current_tab = self.tabs_wilayah.currentWidget()
        if not current_tab or not hasattr(current_tab, 'tabel'): return
        tabel = current_tab.tabel
        for row in range(tabel.rowCount()):
            match = False
            for col in range(tabel.columnCount()):
                widget = tabel.cellWidget(row, col)
                text_val = widget.currentText().lower() if isinstance(widget,
                                                                      QComboBox) else widget.text().lower() if isinstance(
                    widget, QLineEdit) else tabel.item(row, col).text().lower() if tabel.item(row, col) else ""
                if keyword in text_val:
                    match = True
                    break
            tabel.setRowHidden(row, not match)

    def show_header_menu(self, pos, tabel):
        col = tabel.horizontalHeader().logicalIndexAt(pos)
        if col == self.KOL_NO: return
        header_text = tabel.horizontalHeaderItem(col).text()
        editor_type = self.get_editor_type(col)

        menu = QMenu()
        menu.setStyleSheet(get_buku_gudang_menu_style())
        container = QWidget()
        vbox = VBox(container)
        vbox.addWidget(QLabel(f"Filter {header_text}:"))

        if editor_type == "date":
            editor = QDateEdit()
            editor.setCalendarPopup(True)
            editor.setDisplayFormat("yyyy-MM-dd")
            editor.setDate(QDate.currentDate())
        elif editor_type == "status":
            editor = QComboBox()
            editor.addItems(["", "PROSES", "PERJALANAN", "SELESAI"])
        elif editor_type == "payment":
            editor = QComboBox()
            editor.addItems(["TF / INVOICE", "CASH"])
        else:
            editor = QLineEdit()

        vbox.addWidget(editor)
        action = QWidgetAction(menu)
        action.setDefaultWidget(container)
        menu.addAction(action)
        menu.addSeparator()
        menu.addAction("Pasang Filter", lambda: self.apply_filter(tabel, col, editor, menu))
        menu.addAction("Hapus Filter", lambda: self.reset_filter(tabel, col, menu))
        menu.exec_(tabel.viewport().mapToGlobal(pos))

    def apply_filter(self, tabel, col, editor, menu):
        tab_widget = tabel.parent()
        val = editor.date().toString("yyyy-MM-dd") if isinstance(editor,
                                                                 QDateEdit) else editor.currentText() if isinstance(
            editor, QComboBox) else editor.text().strip()
        if val:
            tab_widget.filter_data[col] = val
        else:
            tab_widget.filter_data.pop(col, None)
        self.load_data(tab_widget)
        menu.close()

    def reset_filter(self, tabel, col, menu):
        tabel.parent().filter_data.pop(col, None)
        self.load_data(tabel.parent())
        menu.close()

    def show_cell_context_menu(self, pos, tabel):
        item = tabel.itemAt(pos)
        if not item: return
        menu = QMenu()
        menu.setStyleSheet(get_buku_gudang_menu_style(13))
        row = item.row()

        baris_awal = set(i.row() for i in tabel.selectedItems())
        if row not in baris_awal:
            tabel.selectRow(row)

        baris_terseleksi = set(i.row() for i in tabel.selectedItems())
        jumlah_resi = len(baris_terseleksi)

        if jumlah_resi > 1:
            buat_invoice_action = menu.addAction(
                f"🧾 Buat Invoice Gabungan ({jumlah_resi} Resi)") if self.row_sedang_diedit == -1 else None
            edit_action = None
            save_action = None
            cancel_action = None
            selesai_action = menu.addAction("✅ Tandai 'SELESAI' Massal") if self.row_sedang_diedit == -1 else None
        else:
            buat_invoice_action = menu.addAction(
                "🧾 Buat Invoice dari Resi Ini") if self.row_sedang_diedit == -1 else None
            edit_action = menu.addAction("✏️ Edit Baris Ini") if self.row_sedang_diedit == -1 else None
            save_action = menu.addAction("💾 Simpan Perubahan") if self.row_sedang_diedit == row else None
            cancel_action = menu.addAction("❌ Batalkan Edit") if self.row_sedang_diedit == row else None
            selesai_action = menu.addAction(
                "✅ Tandai 'SELESAI'") if item.column() == self.KOL_STATUS and self.row_sedang_diedit == -1 else None

        action = menu.exec_(tabel.viewport().mapToGlobal(pos))
        if action == edit_action:
            self.aktifkan_mode_edit_baris(tabel, row)
        elif action == save_action:
            self.eksekusi_simpan_baris_ke_db(tabel, row)
        elif action == cancel_action:
            self.refresh_session_ui()
        elif action == selesai_action:
            self.tandai_selesai_massal(tabel)
        elif action == buat_invoice_action:
            self.proses_simpan_ke_invoice()

    def aktifkan_mode_edit_baris(self, tabel, row):
        self.row_sedang_diedit = row

        for col in range(self.KOL_PENGIRIM, self.KOL_KETERANGAN + 1):
            item = tabel.item(row, col)
            teks_asal = item.text() if item else ""
            if col == self.KOL_PAYMENT:
                combo = QComboBox()
                combo.addItems(["", "TF / INVOICE", "CASH"])
                combo.setCurrentText(teks_asal)
                combo.activated.connect(lambda: self.eksekusi_simpan_baris_ke_db(tabel, row))
                combo.installEventFilter(self)
                tabel.setCellWidget(row, col, combo)
            else:
                line_edit = QLineEdit()
                is_numeric = col in [self.KOL_KOLI, self.KOL_BERAT, self.KOL_CBM, self.KOL_ONGKIR]
                line_edit.is_numeric_col = is_numeric
                line_edit.setText("" if is_numeric and teks_asal.strip() == "-" else teks_asal.strip().replace(".",
                                                                                                               "") if is_numeric else teks_asal.strip())
                line_edit.setStyleSheet(BUKU_GUDANG_INLINE_EDITOR_STYLE)

                if col == self.KOL_KOLI:
                    line_edit.setValidator(
                        get_integer_validator(
                            parent=line_edit,
                            minimum=0,
                            maximum=999_999,
                        )
                    )

                elif col == self.KOL_ONGKIR:
                    line_edit.setValidator(
                        get_integer_validator(
                            parent=line_edit,
                            minimum=0,
                            maximum=2_147_483_647,
                        )
                    )

                elif col in [
                    self.KOL_BERAT,
                    self.KOL_CBM,
                ]:
                    line_edit.setValidator(
                        get_decimal_validator(
                            parent=line_edit,
                            decimals=2,
                            minimum=0.0,
                            maximum=999_999_999.99,
                        )
                    )
                else:
                    line_edit.textChanged.connect(lambda _, le=line_edit: paksa_kapital_lineedit(le))

                line_edit.returnPressed.connect(lambda: self.eksekusi_simpan_baris_ke_db(tabel, row))

                line_edit.installEventFilter(self)
                tabel.setCellWidget(row, col, line_edit)
        if tabel.cellWidget(row, self.KOL_PENGIRIM): tabel.cellWidget(row, self.KOL_PENGIRIM).setFocus()

    def load_data(self, tab_widget):
        tabel, wilayah, filters = tab_widget.tabel, tab_widget.wilayah, getattr(tab_widget, 'filter_data', {})
        tabel.blockSignals(True);
        tabel.setRowCount(0)
        is_dark = self.window().current_theme == "dark" if self.window() and hasattr(self.window(),
                                                                                     'current_theme') else False

        try:
            rows = db_service.ambil_data_buku_gudang(CURRENT_SESSION.get('kode_cabang', 'PUSAT'), wilayah,
                                                     self.btn_tahun.text(), filters)
            for row in rows:
                pos = tabel.rowCount();
                tabel.insertRow(pos)
                item_no = QTableWidgetItem(str(pos + 1))
                item_no.setTextAlignment(Qt.AlignCenter);
                item_no.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                tabel.setItem(pos, self.KOL_NO, item_no)

                status = str(row[3]).strip().upper()

                bg, fg = get_buku_gudang_status_colors(
                    is_dark=is_dark,
                    status=status,
                    is_alternate_row=(pos % 2 != 0),
                )

                if bg: item_no.setBackground(QBrush(bg)); item_no.setForeground(QBrush(fg))

                for col_idx, data in enumerate(row):
                    display = str(data).upper() if data is not None else ""
                    col_tabel = col_idx + 1
                    if col_tabel == self.KOL_KOTA_TUJUAN:
                        display = (
                            display
                            .replace(
                                f"{wilayah} - ".upper(),
                                "",
                            )
                            .replace(
                                wilayah.upper(),
                                "",
                            )
                            .strip(" -")
                        )

                    elif (
                            col_tabel
                            in [
                                self.KOL_MASUK,
                                self.KOL_KELUAR,
                            ]
                            and data
                            and "-" in display
                    ):
                        bagian_tanggal = display.split("-")

                        if len(bagian_tanggal) >= 3:
                            display = (
                                f"{bagian_tanggal[2]}/"
                                f"{bagian_tanggal[1]}/"
                                f"{bagian_tanggal[0]}"
                            )

                    elif col_tabel == self.KOL_KOLI:
                        # KOLI adalah teks bebas.
                        # Contoh: 2 DUS, 4 PALET, 3 KARUNG.
                        if (
                                data is not None
                                and str(data).strip()
                                and str(data).strip() != "0"
                        ):
                            display = str(data).strip().upper()
                        else:
                            display = "-"

                    elif col_tabel == self.KOL_ONGKIR:
                        if (
                                data is not None
                                and str(data).strip()
                                not in [
                            "",
                            "0",
                            "0.0",
                            "None",
                        ]
                        ):
                            display = format_ke_rupiah(data)
                        else:
                            display = "-"

                    elif col_tabel in [
                        self.KOL_BERAT,
                        self.KOL_CBM,
                    ]:
                        if (
                                data is not None
                                and str(data).strip()
                                not in [
                            "",
                            "0",
                            "0.0",
                            "None",
                        ]
                        ):
                            try:
                                angka = float(
                                    str(data)
                                    .replace(".", "")
                                    .replace(",", ".")
                                )

                                if angka.is_integer():
                                    display = (
                                        f"{int(angka):,}"
                                        .replace(",", ".")
                                    )
                                else:
                                    display = (
                                        f"{angka:,.2f}"
                                        .replace(",", "X")
                                        .replace(".", ",")
                                        .replace("X", ".")
                                        .replace(",00", "")
                                    )

                            except (
                                    TypeError,
                                    ValueError,
                            ):
                                display = str(data).strip()
                        else:
                            display = "-"

                    item = QTableWidgetItem(display)
                    if col_tabel in [
                        self.KOL_BERAT,
                        self.KOL_CBM,
                        self.KOL_ONGKIR,
                    ]:
                        item.setTextAlignment(
                            Qt.AlignRight
                            | Qt.AlignVCenter
                        )

                    elif col_tabel == self.KOL_KOLI:
                        item.setTextAlignment(
                            Qt.AlignLeft
                            | Qt.AlignVCenter
                        )
                    if bg: item.setBackground(QBrush(bg)); item.setForeground(QBrush(fg))
                    item.setFlags(item.flags() ^ Qt.ItemIsEditable)
                    tabel.setItem(pos, col_tabel, item)
            if tabel.rowCount() > 0: tabel.scrollToBottom()
        except Exception as e:
            print(f"Error load data: {e}")
        tabel.blockSignals(False)

    def eksekusi_simpan_baris_ke_db(self, tabel, row):
        if self.row_sedang_diedit == -1: return
        no_resi = tabel.item(row, self.KOL_RESI).text()

        kolom_db = {
            self.KOL_PENGIRIM: "pengirim", self.KOL_KOTA_ASAL: "kota_asal", self.KOL_PENERIMA: "penerima",
            self.KOL_KOTA_TUJUAN: "kota_tujuan", self.KOL_NAMA_BARANG: "nama_barang", self.KOL_KOLI: "koli",
            self.KOL_BERAT: "berat", self.KOL_CBM: "cbm", self.KOL_ONGKIR: "total_ongkir",
            self.KOL_PAYMENT: "pembayaran", self.KOL_KETERANGAN: "ket_buku_gudang"
        }

        try:
            updates = {}
            for col, field in kolom_db.items():
                w = tabel.cellWidget(row, col)
                val = w.currentText().strip().upper() if isinstance(w,
                                                                    QComboBox) else w.text().strip().upper() if w else ""
                if (
                        col
                        in [
                    self.KOL_BERAT,
                    self.KOL_CBM,
                    self.KOL_ONGKIR,
                ]
                        and val in [
                    "",
                    "-",
                ]
                ):
                    val = "0"

                elif (
                        col == self.KOL_KOLI
                        and val == "-"
                ):
                    val = ""

                if col == self.KOL_ONGKIR:
                    val = str(rupiah_to_int(val))
                elif col in [self.KOL_BERAT, self.KOL_CBM]:
                    val = val.replace(".", "").replace(",", ".")
                elif col == self.KOL_KOTA_TUJUAN:
                    wilayah = tabel.parentWidget().wilayah.upper()
                    if wilayah not in val: val = f"{wilayah} - {val}"
                updates[field] = val

            payload = {'nama_barang': updates['nama_barang'], 'koli': updates['koli'], 'berat': updates['berat'],
                       'cbm': updates['cbm']}
            db_service.update_baris_buku_gudang(no_resi, CURRENT_SESSION.get('kode_cabang', 'PUSAT'), updates, payload)
            self.refresh_session_ui()
            QMessageBox.information(self, "Sukses", f"Data Resi {no_resi} berhasil disimpan!")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal: {e}");
            self.refresh_session_ui()

    def tandai_selesai_massal(self, tabel):
        rows = set(item.row() for item in tabel.selectedItems())
        resi_list = [tabel.item(r, self.KOL_RESI).text() for r in rows]
        if QMessageBox.question(self, "Konfirmasi", f"Tandai {len(resi_list)} resi menjadi SELESAI?",
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                db_service.tandai_resi_selesai_massal(resi_list, CURRENT_SESSION.get('kode_cabang',
                                                                                     'PUSAT'));
                self.refresh_session_ui()
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Gagal: {e}")

    def refresh_session_ui(self):
        self.row_sedang_diedit = -1
        if self.tabs_wilayah.currentWidget(): self.load_data(
            self.tabs_wilayah.currentWidget()); self.filter_pencarian_tabel()


    def simpan_lebar_kolom(self, tabel):
        QSettings("EkspedisiApp", "BukuGudang").setValue("lebar_kolom_gudang_v2",
                                                         [tabel.columnWidth(i) for i in range(tabel.columnCount())])

    def load_lebar_kolom(self, tabel):
        w = QSettings("EkspedisiApp", "BukuGudang").value("lebar_kolom_gudang_v2")
        if w:
            tabel.horizontalHeader().blockSignals(True)
            for i, width in enumerate(w): tabel.setColumnWidth(i, int(width))
            tabel.horizontalHeader().blockSignals(False)
        else:
            tabel.setColumnWidth(self.KOL_NO, 45)