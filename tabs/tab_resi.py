# tabs/tab_resi.py
import json
import logging

from PyQt5.QtCore import QDate, QEasingCurve, QPropertyAnimation, QSettings, Qt, QTimer
from PyQt5.QtWidgets import (QComboBox, QCompleter, QDateEdit, QGraphicsOpacityEffect,
                             QGridLayout, QGroupBox, QHeaderView, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QMessageBox, QPushButton, QScrollArea, QSizePolicy,
                             QSplitter, QTableWidget, QToolButton, QVBoxLayout, QWidget)

from config import CURRENT_SESSION
import services.database_service as db_service
from themes.components import BTN_SIMPAN_CETAK_STYLE, FADE_NOTIFICATION_STYLE
from themes.modules.resi import (
    get_resi_rekening_styles,
    get_resi_static_styles,
    get_resi_styles,
)
from utils.printer.print_resi import cetak_resi_ke_printer

from utils import zoom as zoom_helper
from utils.date_ind_format import format_tanggal_ke_db, format_tanggal_ke_ui
from utils.reset_form_helper import reset_form_input_global
from utils.reset_form_helper import reset_form_input_global
from utils.mixins import ZoomTableMixin
from utils.number_formatters import (
    angka_indonesia_to_decimal,
    format_input_ribuan_gaya_indonesia,
    format_ke_rupiah,
    rupiah_to_int,
)
from utils.placeholder_helper import (
    setup_placeholder_dinamis,
    terap_semua_placeholder_dinamis,
)
from utils.table_helper import buat_tabel_item
from utils.typography import get_global_font_sizes
from utils.validators import UppercaseValidator, get_decimal_validator
from utils.widget_helpers import _blokir_signal_sementara, paksa_kapital_lineedit, terapkan_popup_combobox_bawah

logger = logging.getLogger(__name__)


def _format_ongkir_aman(nilai_mentah):
    """Format nilai ongkir mentah (string) ke format rupiah jika berupa angka valid.

    Mengembalikan nilai apa adanya bila bukan angka murni, supaya data lama
    yang mungkin tidak numerik tetap bisa ditampilkan tanpa membuat aplikasi error.
    """
    nilai_mentah = str(nilai_mentah or "")
    try:
        nilai = int(nilai_mentah) if nilai_mentah.isdigit() else 0
        return format_ke_rupiah(nilai) if nilai > 0 else ""
    except (ValueError, TypeError):
        return nilai_mentah


class FadeNotification(QWidget):
    def __init__(self, message, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.ToolTip | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.label = QLabel(message, self)

        self.label.setStyleSheet(FADE_NOTIFICATION_STYLE)
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        if parent:
            self.center_on_parent(parent)

        QTimer.singleShot(1000, self.start_fade_out)

    def center_on_parent(self, parent):
        self.adjustSize()
        main_window = parent.window().geometry()
        x = main_window.x() + (main_window.width() - self.width()) // 2
        y = main_window.y() + (main_window.height() - self.height()) // 2
        self.move(x, y)

    def start_fade_out(self):
        self.anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.anim.setDuration(400)
        self.anim.setStartValue(1.0)
        self.anim.setEndValue(0.0)
        self.anim.setEasingCurve(QEasingCurve.OutCubic)
        self.anim.finished.connect(self.close)
        self.anim.start()


class TabResi(ZoomTableMixin, QWidget):
    KOL_NO = 0
    KOL_NAMA_BARANG = 1
    KOL_KOLI = 2
    KOL_BERAT = 3
    KOL_CBM = 4

    LEBAR_KOLOM_DASAR = {
        KOL_NO: 42,
        KOL_NAMA_BARANG: 400,
        KOL_KOLI: 100,
        KOL_BERAT: 100,
        KOL_CBM: 100,
    }

    def __init__(self):
        super().__init__()
        self.kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')
        self.settings = QSettings("AplikasiEkspedisi", "PengaturanUI")
        self.current_theme = self.settings.value("theme", "light")
        self.current_resi_data = None
        self.init_ui()

    def init_ui(self):
        layout_utama_asli = QHBoxLayout(self)
        layout_utama_asli.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Qt.Horizontal)
        layout_utama_asli.addWidget(self.splitter)

        initial_theme_styles = get_resi_static_styles(
            self.current_theme == "dark"
        )

        self.scroll_kiri = QScrollArea()
        self.scroll_kiri.setWidgetResizable(True)
        self.scroll_kiri.setFrameShape(QScrollArea.NoFrame)
        self.scroll_kiri.setStyleSheet(
            initial_theme_styles["scroll_kiri"]
        )

        self.widget_kiri = QWidget()
        layout_kiri = QVBoxLayout(self.widget_kiri)
        layout_kiri.setContentsMargins(15, 20, 10, 12)
        layout_kiri.setSpacing(10)

        hbox_top_bar = QHBoxLayout()
        hbox_top_bar.setContentsMargins(0, 0, 0, 5)

        self.lbl_main_title = QLabel("📋 Form Input Surat Jalan")
        hbox_top_bar.addWidget(self.lbl_main_title)
        hbox_top_bar.addStretch(1)

        hbox_date = QHBoxLayout()
        hbox_date.setSpacing(5)
        self.lbl_tgl_tag = QLabel("Tanggal Transaksi:")
        self.date_input = QDateEdit(self)
        self.date_input.setDate(QDate.currentDate())
        self.date_input.setReadOnly(True)
        self.date_input.setFocusPolicy(Qt.NoFocus)
        self.date_input.setButtonSymbols(2)
        self.date_input.setFixedWidth(180)
        self.date_input.setDisplayFormat("dddd, dd/MM/yyyy")
        self.date_input.dateChanged.connect(self.otomatisasi_nomor_resi)
        hbox_date.addWidget(self.lbl_tgl_tag)
        hbox_date.addWidget(self.date_input)
        hbox_top_bar.addLayout(hbox_date)
        hbox_top_bar.addStretch(1)

        hbox_resi_layout = QHBoxLayout()
        hbox_resi_layout.setSpacing(10)
        self.lbl_resi_tag = QLabel("No. Resi:")
        self.lbl_resi_tag.setAlignment(Qt.AlignVCenter)
        self.txt_resi_display = QLabel("GEN-RESI-CODE")
        self.txt_resi_display.setAlignment(Qt.AlignCenter)
        self.txt_resi_display.setFixedWidth(200)
        self.txt_resi_display.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        hbox_resi_layout.addWidget(self.lbl_resi_tag)
        hbox_resi_layout.addWidget(self.txt_resi_display)
        hbox_top_bar.addLayout(hbox_resi_layout)

        layout_kiri.addLayout(hbox_top_bar)

        hbox_cards_data = QHBoxLayout()
        hbox_cards_data.setSpacing(15)

        self.group_pengirim = QGroupBox("")
        grid_pengirim = QGridLayout(self.group_pengirim)
        grid_pengirim.setVerticalSpacing(10)
        grid_pengirim.setHorizontalSpacing(10)
        grid_pengirim.setContentsMargins(15, 15, 30, 15)

        self.btn_clear_pengirim = self._buat_tombol_clear_container(
            self.group_pengirim,
            "Reset pengirim",
            self.bersihkan_data_pengirim,
        )

        self.txt_pengirim = QLineEdit()
        self.txt_pengirim.setPlaceholderText("Nama pengirim/perusahaan/toko ...")

        self.txt_hp_pengirim = QLineEdit()
        self.txt_hp_pengirim.setPlaceholderText("08xx xxxx ...")

        self.txt_alamat_pengirim = QLineEdit()
        self.txt_alamat_pengirim.setPlaceholderText("Masukkan alamat lengkap ...")

        self.txt_kota_pengirim = QLineEdit()
        self.txt_kota_pengirim.setPlaceholderText("Kota asal ...")

        grid_pengirim.addWidget(QLabel("Pengirim:"), 0, 0)
        grid_pengirim.addWidget(self.txt_pengirim, 0, 1)
        grid_pengirim.addWidget(QLabel("No. HP:"), 0, 2)
        grid_pengirim.addWidget(self.txt_hp_pengirim, 0, 3)
        grid_pengirim.addWidget(QLabel("Alamat:"), 1, 0)
        grid_pengirim.addWidget(self.txt_alamat_pengirim, 1, 1, 1, 3)
        grid_pengirim.addWidget(QLabel("Kota Asal:"), 2, 0)
        grid_pengirim.addWidget(self.txt_kota_pengirim, 2, 1, 1, 3)

        grid_pengirim.setRowStretch(0, 1)
        grid_pengirim.setRowStretch(1, 1)
        grid_pengirim.setRowStretch(2, 1)

        grid_pengirim.setColumnStretch(1, 6)
        grid_pengirim.setColumnStretch(3, 4)
        hbox_cards_data.addWidget(self.group_pengirim, stretch=1)

        self.group_penerima = QGroupBox("")
        grid_penerima = QGridLayout(self.group_penerima)
        grid_penerima.setVerticalSpacing(10)
        grid_penerima.setHorizontalSpacing(10)
        grid_penerima.setContentsMargins(15, 15, 30, 15)

        self.btn_clear_penerima = self._buat_tombol_clear_container(
            self.group_penerima,
            "Reset penerima",
            self.bersihkan_data_penerima,
        )

        self.txt_penerima = QLineEdit()
        self.txt_penerima.setPlaceholderText("Nama penerima/perusahaan/toko...")

        self.txt_hp_penerima = QLineEdit()
        self.txt_hp_penerima.setPlaceholderText("08xx xxxx ...")

        self.txt_alamat_penerima = QLineEdit()
        self.txt_alamat_penerima.setPlaceholderText("Masukkan alamat lengkap ...")

        hbox_dest_widgets = QHBoxLayout()
        hbox_dest_widgets.setSpacing(6)
        hbox_dest_widgets.setContentsMargins(0, 0, 0, 0)

        self.txt_kota_penerima = QLineEdit()
        self.txt_kota_penerima.setPlaceholderText("Kota tujuan ...")

        self.cb_provinsi = QComboBox()

        raw_provinsi = db_service.get_setting('provinsi_tujuan')
        provinsi_tujuan = json.loads(raw_provinsi) if isinstance(raw_provinsi, str) else (
                raw_provinsi or ["PROVINSI A", "PROVINSI B", "PROVINSI C"])

        self.cb_provinsi.addItems(provinsi_tujuan)
        self.cb_provinsi.currentTextChanged.connect(self.otomatisasi_nomor_resi)

        hbox_dest_widgets.addWidget(self.txt_kota_penerima, stretch=6)
        hbox_dest_widgets.addWidget(self.cb_provinsi, stretch=4)

        grid_penerima.addWidget(QLabel("Penerima:"), 0, 0)
        grid_penerima.addWidget(self.txt_penerima, 0, 1)
        grid_penerima.addWidget(QLabel("No. HP:"), 0, 2)
        grid_penerima.addWidget(self.txt_hp_penerima, 0, 3)
        grid_penerima.addWidget(QLabel("Alamat:"), 1, 0)
        grid_penerima.addWidget(self.txt_alamat_penerima, 1, 1, 1, 3)
        grid_penerima.addWidget(QLabel("Kota:"), 2, 0)
        grid_penerima.addLayout(hbox_dest_widgets, 2, 1, 1, 3)

        grid_penerima.setRowStretch(0, 1)
        grid_penerima.setRowStretch(1, 1)
        grid_penerima.setRowStretch(2, 1)

        grid_penerima.setColumnStretch(1, 6)
        grid_penerima.setColumnStretch(3, 4)
        hbox_cards_data.addWidget(self.group_penerima, stretch=1)

        layout_kiri.addLayout(hbox_cards_data)

        self.group_tabel_container = QGroupBox("")
        self.group_tabel_container.setMinimumHeight(250)

        vbox_tabel_inner = QVBoxLayout(self.group_tabel_container)
        vbox_tabel_inner.setContentsMargins(10, 12, 30, 12)
        vbox_tabel_inner.setSpacing(8)

        self.btn_clear_barang = self._buat_tombol_clear_container(
            self.group_tabel_container,
            "Reset detail barang",
            self.bersihkan_detail_barang,
        )

        self.table_items = QTableWidget()
        self.table_items.setColumnCount(5)
        self.table_items.setHorizontalHeaderLabels(
            ["NO.", "NAMA BARANG", "KOLI", "BERAT (Kg)", "KUBIK (m³)"]
        )

        mode_resize_kolom = {
            self.KOL_NO: QHeaderView.Fixed,
            self.KOL_NAMA_BARANG: QHeaderView.Interactive,
            self.KOL_KOLI: QHeaderView.Interactive,
            self.KOL_BERAT: QHeaderView.Interactive,
            self.KOL_CBM: QHeaderView.Interactive,
        }
        for kolom, mode in mode_resize_kolom.items():
            self.table_items.horizontalHeader().setSectionResizeMode(kolom, mode)
            self.table_items.setColumnWidth(kolom, self.LEBAR_KOLOM_DASAR[kolom])
        self.table_items.horizontalHeader().setStretchLastSection(True)

        self.table_items.horizontalHeader().sectionResized.connect(self.auto_save_ukuran_kolom)
        self.table_items.setMinimumHeight(150)
        self.table_items.verticalHeader().setVisible(False)
        vbox_tabel_inner.addWidget(self.table_items)

        hbox_tbl_btn = QHBoxLayout()
        hbox_tbl_btn.setSpacing(8)
        self.btn_tambah_baris = QPushButton("➕ Tambah Baris")
        self.btn_tambah_baris.clicked.connect(self.tambah_baris_barang)

        self.btn_hapus_baris = QPushButton("🗑️ Hapus Baris")
        self.btn_hapus_baris.clicked.connect(self.hapus_baris_terpilih)

        hbox_tbl_btn.addWidget(self.btn_tambah_baris)
        hbox_tbl_btn.addWidget(self.btn_hapus_baris)
        hbox_tbl_btn.addStretch()
        vbox_tabel_inner.addLayout(hbox_tbl_btn)

        layout_kiri.addWidget(self.group_tabel_container)

        hbox_bottom_layout = QHBoxLayout()
        hbox_bottom_layout.setSpacing(12)

        self.group_finance = QGroupBox("")
        grid_finansial = QGridLayout(self.group_finance)
        grid_finansial.setSpacing(6)
        grid_finansial.setContentsMargins(12, 15, 30, 12)

        self.btn_clear_finance = self._buat_tombol_clear_container(
            self.group_finance,
            "Reset detail ongkir",
            self.bersihkan_detail_pembayaran,
        )

        self.txt_ongkir_kg = QLineEdit()
        self.txt_ongkir_kg.setPlaceholderText("Ongkir /kg")

        self.txt_ongkir_m3 = QLineEdit()
        self.txt_ongkir_m3.setPlaceholderText("Ongkir /m3")

        self.txt_total_ongkir = QLineEdit()
        self.txt_total_ongkir.setPlaceholderText("Input Bisa Otomatis dan Manual")

        self.cb_pajak = QComboBox()
        self.cb_pajak.addItems(["NONPAJAK", "PAJAK"])
        self.cb_pajak.currentTextChanged.connect(self.otomatisasi_nomor_resi)
        self.cb_payment = QComboBox()
        self.cb_payment.addItems(["TF / INVOICE", "CASH"])

        self.txt_ongkir_kg.textChanged.connect(self.kalkulator_finansial_otomatis)
        self.txt_ongkir_kg.textChanged.connect(lambda: format_input_ribuan_gaya_indonesia(self.txt_ongkir_kg))

        self.txt_ongkir_m3.textChanged.connect(self.kalkulator_finansial_otomatis)
        self.txt_ongkir_m3.textChanged.connect(lambda: format_input_ribuan_gaya_indonesia(self.txt_ongkir_m3))

        self.txt_total_ongkir.textChanged.connect(lambda: format_input_ribuan_gaya_indonesia(self.txt_total_ongkir))

        grid_finansial.addWidget(QLabel("Ongkir per kg (Rp):"), 0, 0)
        grid_finansial.addWidget(self.txt_ongkir_kg, 0, 1)
        grid_finansial.addWidget(QLabel("Ongkir per m3 (Rp):"), 1, 0)
        grid_finansial.addWidget(self.txt_ongkir_m3, 1, 1)
        grid_finansial.addWidget(QLabel("Total Ongkir (Rp):"), 2, 0)
        grid_finansial.addWidget(self.txt_total_ongkir, 2, 1)
        grid_finansial.addWidget(QLabel("Jenis Transaksi:"), 3, 0)
        grid_finansial.addWidget(self.cb_pajak, 3, 1)
        grid_finansial.addWidget(QLabel("Metode Payment:"), 4, 0)
        grid_finansial.addWidget(self.cb_payment, 4, 1)

        grid_finansial.setRowStretch(5, 1)
        hbox_bottom_layout.addWidget(self.group_finance, stretch=45)

        self.layout_pay_method = QHBoxLayout()
        self.layout_pay_method.setContentsMargins(0, 0, 0, 0)
        self.layout_pay_method.setSpacing(10)

        self.rek_cards_labels = []

        self.box_np = QGroupBox("Rekening Nonpajak")
        vbox_np_outer = QVBoxLayout(self.box_np)
        vbox_np_outer.setContentsMargins(4, 10, 4, 4)

        scroll_np = QScrollArea()
        scroll_np.setWidgetResizable(True)
        scroll_np.setFrameShape(QScrollArea.NoFrame)
        scroll_np.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        widget_np_content = QWidget()
        vbox_np = QVBoxLayout(widget_np_content)
        vbox_np.setContentsMargins(6, 6, 6, 6)
        vbox_np.setSpacing(8)

        raw_np = db_service.get_setting('rekening_nonpajak')
        rek_np_list = json.loads(raw_np) if isinstance(raw_np, str) else (raw_np or [])
        self._bangun_kartu_rekening(rek_np_list, vbox_np, initial_theme_styles["rekening_card"])

        vbox_np.addStretch()
        scroll_np.setWidget(widget_np_content)
        vbox_np_outer.addWidget(scroll_np)

        self.box_p = QGroupBox("Rekening Pajak (PT)")
        vbox_p_outer = QVBoxLayout(self.box_p)
        vbox_p_outer.setContentsMargins(4, 10, 4, 4)

        scroll_p = QScrollArea()
        scroll_p.setWidgetResizable(True)
        scroll_p.setFrameShape(QScrollArea.NoFrame)
        scroll_p.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        widget_p_content = QWidget()
        vbox_p = QVBoxLayout(widget_p_content)
        vbox_p.setContentsMargins(6, 6, 6, 6)
        vbox_p.setSpacing(8)

        raw_p = db_service.get_setting('rekening_pajak')
        rek_p_list = json.loads(raw_p) if isinstance(raw_p, str) else (raw_p or [])
        self._bangun_kartu_rekening(rek_p_list, vbox_p, initial_theme_styles["rekening_card"])

        vbox_p.addStretch()
        scroll_p.setWidget(widget_p_content)
        vbox_p_outer.addWidget(scroll_p)

        self.layout_pay_method.addWidget(self.box_np, stretch=1)
        self.layout_pay_method.addWidget(self.box_p, stretch=1)

        hbox_bottom_layout.addLayout(self.layout_pay_method, stretch=55)
        layout_kiri.addLayout(hbox_bottom_layout)

        hbox_main_action = QHBoxLayout()
        hbox_main_action.setContentsMargins(0, 0, 0, 0)
        hbox_main_action.setSpacing(0)

        # Area kiri dan kanan diberi stretch yang sama agar tombol utama
        # tetap tepat di tengah, meskipun teks Reset Form berada di sisi kanan.
        self.widget_action_kiri = QWidget()
        self.widget_action_kiri.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )

        self.btn_generate_simpan = QPushButton("⚡ SIMPAN DAN CETAK")
        self.btn_generate_simpan.setStyleSheet(BTN_SIMPAN_CETAK_STYLE)
        self.btn_generate_simpan.clicked.connect(self.simpan_ke_database)

        self.widget_action_kanan = QWidget()
        self.widget_action_kanan.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Preferred,
        )
        layout_action_kanan = QHBoxLayout(self.widget_action_kanan)
        layout_action_kanan.setContentsMargins(12, 0, 0, 0)
        layout_action_kanan.setSpacing(0)

        self.lbl_reset_form = QPushButton("Reset Form")
        self.lbl_reset_form.setFocusPolicy(Qt.NoFocus)

        self.lbl_reset_form.setStyleSheet("""
                    QPushButton {
                        color: #ef4444;
                        background-color: transparent;
                        border: none;
                        font-weight: 600;
                        text-align: left;
                    }
                    QPushButton:hover {
                        color: #b91c1c; /* Warna berubah jadi merah yang lebih gelap */
                    }
                """)

        self.lbl_reset_form.clicked.connect(self.reset_form_input_manual)

        layout_action_kanan.addWidget(
            self.lbl_reset_form,
            0,
            Qt.AlignLeft | Qt.AlignVCenter,
        )
        layout_action_kanan.addStretch(1)

        hbox_main_action.addWidget(self.widget_action_kiri, stretch=1)
        hbox_main_action.addWidget(
            self.btn_generate_simpan,
            0,
            Qt.AlignCenter,
        )
        hbox_main_action.addWidget(self.widget_action_kanan, stretch=1)

        layout_kiri.addSpacing(15)
        layout_kiri.addLayout(hbox_main_action)
        layout_kiri.addStretch(1)

        self.widget_kanan = QWidget()
        layout_kanan = QVBoxLayout(self.widget_kanan)
        layout_kanan.setContentsMargins(10, 12, 15, 12)
        layout_kanan.setSpacing(10)

        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("Cari resi, pengirim, penerima...")
        self.txt_search.textChanged.connect(self.filter_data_resi)
        layout_kanan.addWidget(self.txt_search)

        hbox_histori_header = QHBoxLayout()
        self.lbl_histori_title = QLabel("🕒 Histori:")
        self.date_histori = QDateEdit(self)
        self.date_histori.setCalendarPopup(True)
        self.date_histori.setDate(QDate.currentDate())
        self.date_histori.setFixedWidth(125)
        self.date_histori.setDisplayFormat("dd/MM/yyyy")
        self.date_histori.dateChanged.connect(self.load_data_resi)

        self.btn_reset_tgl = QPushButton("RESET")
        self.btn_reset_tgl.setFixedWidth(55)
        self.btn_reset_tgl.clicked.connect(self.reset_tanggal)

        hbox_histori_header.addWidget(self.lbl_histori_title)
        hbox_histori_header.addWidget(self.date_histori)
        hbox_histori_header.addWidget(self.btn_reset_tgl)
        hbox_histori_header.addStretch()

        self.list_histori = QListWidget()
        self.list_histori.itemDoubleClicked.connect(self.munculkan_preview)

        layout_kanan.addLayout(hbox_histori_header)
        layout_kanan.addWidget(self.list_histori)

        self.scroll_kiri.setWidget(self.widget_kiri)
        self.splitter.addWidget(self.scroll_kiri)
        self.splitter.addWidget(self.widget_kanan)
        self.splitter.setSizes([850, 250])

        self.setup_uppercase_hooks()
        self.setup_autocomplete()
        self.tambah_baris_barang()

        terap_semua_placeholder_dinamis(
            self,
            is_dark=self.current_theme == "dark",
        )

        self.otomatisasi_nomor_resi()
        self.sesuaikan_tema_lokal()
        self.load_data_resi()
        terapkan_popup_combobox_bawah(self)
        QTimer.singleShot(0, self._posisikan_tombol_clear_container)

    def reset_form_input_manual(self, _link=None):
        """
        Membersihkan seluruh input transaksi setelah konfirmasi.

        Data yang tidak ikut dibersihkan:
        - tanggal transaksi;
        - nomor resi otomatis;
        - kartu rekening;
        - pencarian dan histori resi.
        """
        jawaban = QMessageBox.question(
            self,
            "Reset Form",
            "Bersihkan seluruh data input surat jalan?\n\n"
            "Data yang belum disimpan akan hilang.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )

        if jawaban != QMessageBox.Yes:
            return

        reset_form_input_global(
            self.group_pengirim,
        )
        reset_form_input_global(
            self.group_penerima,
            indeks_combo_default=0,
        )
        reset_form_input_global(
            self.group_tabel_container,
            kosongkan_tabel=True,
        )
        reset_form_input_global(
            self.group_finance,
            indeks_combo_default=0,
        )

        # Detail barang selalu kembali memiliki satu baris kosong.
        self.tambah_baris_barang()

        terap_semua_placeholder_dinamis(
            self.widget_kiri,
            is_dark=self.current_theme == "dark",
        )

        self.kalkulator_finansial_otomatis()
        self.otomatisasi_nomor_resi()

        QTimer.singleShot(0, self.txt_pengirim.setFocus)

    def _buat_tombol_clear_container(self, parent, tooltip, callback):
        tombol = QToolButton(parent)
        tombol.setText("↺")
        tombol.setToolTip(tooltip)

        tombol.setFixedSize(18, 18)
        tombol.setFocusPolicy(Qt.NoFocus)

        tombol.setStyleSheet("""
            QToolButton {
                color: #ef4444;
                background-color: transparent;
                border: none;
                border-radius: 4px;
                font-size: 11pt;
                font-weight: 700;
                padding: 0px;
            }
            QToolButton:hover {
                color: #ffffff;
                background-color: #ef4444;
            }
            QToolButton:pressed {
                background-color: #dc2626;
            }
            QToolTip {
                background-color: #ffffff;
                color: #000000;
                border: 1px solid #d1d5db;
                padding: 2px 5px;
                border-radius: 3px;
                font-size: 9pt;
                font-weight: normal;
            }
        """)
        tombol.clicked.connect(callback)
        tombol.raise_()
        return tombol

    def _posisikan_tombol_clear_container(self):
        """Menjaga seluruh tombol reset tetap di pojok kanan atas container."""
        pasangan = (
            (getattr(self, "group_pengirim", None), getattr(self, "btn_clear_pengirim", None)),
            (getattr(self, "group_penerima", None), getattr(self, "btn_clear_penerima", None)),
            (getattr(self, "group_tabel_container", None), getattr(self, "btn_clear_barang", None)),
            (getattr(self, "group_finance", None), getattr(self, "btn_clear_finance", None)),
        )

        for container, tombol in pasangan:
            if container is None or tombol is None:
                continue

            tombol.move(
                max(2, container.width() - tombol.width() - 4),
                3,
            )
            tombol.raise_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._posisikan_tombol_clear_container()

    def bersihkan_data_pengirim(self):
        """Membersihkan hanya input di container Pengirim."""
        reset_form_input_global(
            self.group_pengirim,
            fokus_ke=self.txt_pengirim,
        )
        terap_semua_placeholder_dinamis(
            self.group_pengirim,
            is_dark=self.current_theme == "dark",
        )

    def bersihkan_data_penerima(self):
        """Membersihkan hanya input di container Penerima."""
        reset_form_input_global(
            self.group_penerima,
            indeks_combo_default=0,
            fokus_ke=self.txt_penerima,
        )
        terap_semua_placeholder_dinamis(
            self.group_penerima,
            is_dark=self.current_theme == "dark",
        )

        self.otomatisasi_nomor_resi()

    def bersihkan_detail_barang(self):
        """Menghapus seluruh detail barang lalu menyiapkan satu baris baru."""
        reset_form_input_global(
            self.group_tabel_container,
            kosongkan_tabel=True,
        )
        self.tambah_baris_barang()
        terap_semua_placeholder_dinamis(
            self.group_tabel_container,
            is_dark=self.current_theme == "dark",
        )
        self.kalkulator_finansial_otomatis()

        widget_nama = self.table_items.cellWidget(
            0,
            self.KOL_NAMA_BARANG,
        )
        if widget_nama is not None:
            QTimer.singleShot(0, widget_nama.setFocus)

    def bersihkan_detail_pembayaran(self):
        """Membersihkan ongkir dan mengembalikan ComboBox ke pilihan awal."""
        reset_form_input_global(
            self.group_finance,
            indeks_combo_default=0,
            fokus_ke=self.txt_ongkir_kg,
        )
        terap_semua_placeholder_dinamis(
            self.group_finance,
            is_dark=self.current_theme == "dark",
        )
        self.kalkulator_finansial_otomatis()
        self.otomatisasi_nomor_resi()

    def showEvent(self, event):
        super().showEvent(event)

        # Autocomplete sudah dibuat saat init_ui().
        # Tema lokal dikelola MainWindow ketika tab diaktifkan.
        self.kode_cabang = CURRENT_SESSION.get(
            "kode_cabang",
            "PUSAT",
        )

        terapkan_popup_combobox_bawah(self)
        QTimer.singleShot(0, self._posisikan_tombol_clear_container)

    def sesuaikan_tema_lokal(self):
        win = self.window()
        is_dark = win.current_theme == "dark" if win and hasattr(win, 'current_theme') else self.settings.value("theme",
                                                                                                                "light") == "dark"

        self.current_theme = "dark" if is_dark else "light"
        z = zoom_helper.dapatkan_zoom_level(
            self.__class__.__name__
        )

        terap_semua_placeholder_dinamis(
            self,
            is_dark=is_dark,
        )
        zoom_berubah = (
            getattr(self, "_zoom_terakhir_tema", None)
            != z
        )
        self._zoom_terakhir_tema = z

        fs = get_global_font_sizes(z)
        sz_title, sz_tag, sz_sm = fs['sz_title'], fs['sz_tag'], fs['sz_sm']
        sz_base, sz_input, sz_total = fs['sz_base'], fs['sz_input'], fs['sz_total']

        styles = get_resi_styles(
            is_dark,
            sz_title,
            sz_tag,
            sz_sm,
            sz_base,
            sz_input,
            sz_total,
            z=z,
        )
        for widget_name, qss in styles.items():
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.setStyleSheet(qss)

        input_utama = [
            self.txt_pengirim, self.txt_hp_pengirim, self.txt_alamat_pengirim, self.txt_kota_pengirim,
            self.txt_penerima, self.txt_hp_penerima, self.txt_alamat_penerima,
            self.txt_kota_penerima, self.cb_provinsi, self.txt_ongkir_kg, self.txt_ongkir_m3,
            self.cb_pajak, self.cb_payment
        ]

        for w in input_utama:
            if w is not None:
                w.setStyleSheet(styles['input_utama'])

        if hasattr(self, 'txt_total_ongkir') and self.txt_total_ongkir:
            self.txt_total_ongkir.setStyleSheet(styles['txt_total_ongkir'])
        if hasattr(self, 'txt_search') and self.txt_search:
            self.txt_search.setStyleSheet(styles['txt_search'])

        self.table_items.setStyleSheet(styles['group_tabel_container'])

        if zoom_berubah:
            self.table_items.verticalHeader().setDefaultSectionSize(42 + z)

            try:
                saved_state = self.settings.value("ukuran_tabel_resi")
                if saved_state:
                    self.table_items.horizontalHeader().restoreState(saved_state)
                else:
                    self.table_items.setColumnWidth(self.KOL_NO, max(30, self.LEBAR_KOLOM_DASAR[self.KOL_NO] + (z * 2)))
                    self.table_items.setColumnWidth(self.KOL_NAMA_BARANG, max(150, self.LEBAR_KOLOM_DASAR[self.KOL_NAMA_BARANG] + (z * 10)))
                    self.table_items.setColumnWidth(self.KOL_KOLI, max(70, self.LEBAR_KOLOM_DASAR[self.KOL_KOLI] + (z * 4)))
                    self.table_items.setColumnWidth(self.KOL_BERAT, max(70, self.LEBAR_KOLOM_DASAR[self.KOL_BERAT] + (z * 4)))
                    self.table_items.setColumnWidth(self.KOL_CBM, max(70, self.LEBAR_KOLOM_DASAR[self.KOL_CBM] + (z * 4)))
            except Exception:
                pass

            self._perbarui_cache_lebar_zoom(
                self.table_items,
                self._lebar_dasar_tabel(self.table_items),
            )

        if hasattr(self, 'date_input') and self.date_input:
            self.date_input.setStyleSheet(styles['date_input'])
        if hasattr(self, 'date_histori') and self.date_histori:
            self.date_histori.setStyleSheet(styles['date_histori'])

        self.handle_rekening_zoom(z, is_dark)

        if hasattr(self, 'date_input') and self.date_input: self.date_input.update()
        if hasattr(self, 'date_histori') and self.date_histori: self.date_histori.update()


    def _bangun_kartu_rekening(self, daftar_rekening, layout_target, style_card):
        """Bangun kartu rekening dari daftar string 'bank, no_rek, a.n' ke layout_target.
        Dipakai untuk panel rekening nonpajak maupun pajak.
        """
        for rek in daftar_rekening:
            if not rek:
                continue
            parts = [p.strip() for p in rek.split(",")]
            card = QWidget()
            card.setStyleSheet(style_card)
            l_card = QVBoxLayout(card)
            l_card.setContentsMargins(10, 8, 10, 8)
            l_card.setSpacing(2)

            if len(parts) >= 3:
                lbl_top = QLabel(f"<b>{parts[0]}</b>")
                lbl_bottom = QLabel(f"{parts[1]}<br>a.n. {parts[2]}")
            elif len(parts) == 2:
                lbl_top = QLabel(f"<b>{parts[0]}</b>")
                lbl_bottom = QLabel(f"a.n. {parts[1]}")
            else:
                lbl_top = QLabel(f"<b>{rek}</b>")
                lbl_bottom = QLabel("")

            lbl_top.setObjectName("rek_lbl_top")
            lbl_bottom.setObjectName("rek_lbl_bottom")
            self.rek_cards_labels.extend([lbl_top, lbl_bottom])
            l_card.addWidget(lbl_top)
            l_card.addWidget(lbl_bottom)
            layout_target.addWidget(card)

    def handle_rekening_zoom(self, z, is_dark):
        rekening_styles = get_resi_rekening_styles(is_dark, z)

        self.setUpdatesEnabled(False)
        try:
            for lbl in self.rek_cards_labels:
                if lbl.objectName() == "rek_lbl_top":
                    lbl.setStyleSheet(rekening_styles["label_top"])
                elif lbl.objectName() == "rek_lbl_bottom":
                    lbl.setStyleSheet(rekening_styles["label_bottom"])

            parent_cards_unik = set(lbl.parentWidget() for lbl in self.rek_cards_labels if lbl.parentWidget())

            for card in parent_cards_unik:
                card.setStyleSheet(rekening_styles["card"])
        finally:
            self.setUpdatesEnabled(True)
            self.update()

    def setup_uppercase_hooks(self):
        self.upper_validator = UppercaseValidator(self)
        self.txt_pengirim.setValidator(self.upper_validator)
        self.txt_alamat_pengirim.setValidator(self.upper_validator)
        self.txt_kota_pengirim.setValidator(self.upper_validator)

        self.txt_penerima.setValidator(self.upper_validator)
        self.txt_alamat_penerima.setValidator(self.upper_validator)
        self.txt_kota_penerima.setValidator(self.upper_validator)

        self.txt_search.setValidator(self.upper_validator)

    def setup_autocomplete(self):
        try:
            self.kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')

            list_pengirim, list_penerima = db_service.ambil_data_autocomplete(self.kode_cabang)

            list_pengirim = sorted(set([str(x).strip().upper() for x in list_pengirim if str(x).strip()]))
            list_penerima = sorted(set([str(x).strip().upper() for x in list_penerima if str(x).strip()]))

            logger.debug(
                "Autocomplete dimuat - Cabang: %s | Pengirim: %d | Penerima: %d",
                self.kode_cabang, len(list_pengirim), len(list_penerima),
            )

            self.txt_pengirim.setCompleter(None)
            self.txt_penerima.setCompleter(None)

            self.comp_pengirim = QCompleter(list_pengirim, self.txt_pengirim)
            self.comp_pengirim.setCaseSensitivity(Qt.CaseInsensitive)
            self.comp_pengirim.setFilterMode(Qt.MatchStartsWith)
            self.comp_pengirim.setCompletionMode(QCompleter.PopupCompletion)
            self.comp_pengirim.setMaxVisibleItems(12)
            self.comp_pengirim.activated[str].connect(self.pilih_autocomplete_pengirim)
            self.txt_pengirim.setCompleter(self.comp_pengirim)

            self.comp_penerima = QCompleter(list_penerima, self.txt_penerima)
            self.comp_penerima.setCaseSensitivity(Qt.CaseInsensitive)
            self.comp_penerima.setFilterMode(Qt.MatchStartsWith)
            self.comp_penerima.setCompletionMode(QCompleter.PopupCompletion)
            self.comp_penerima.setMaxVisibleItems(12)
            self.comp_penerima.activated[str].connect(self.pilih_autocomplete_penerima)
            self.txt_penerima.setCompleter(self.comp_penerima)

            if self.txt_pengirim.property("_autocomplete_connected") != "true":
                self.txt_pengirim.textEdited.connect(
                    lambda text: self.comp_pengirim.complete()
                    if getattr(self, 'comp_pengirim', None) and str(text).strip()
                    else None
                )
                self.txt_pengirim.editingFinished.connect(
                    lambda: self.eksekusi_autofill_pengirim(self.txt_pengirim.text())
                )
                self.txt_pengirim.setProperty("_autocomplete_connected", "true")

            if self.txt_penerima.property("_autocomplete_connected") != "true":
                self.txt_penerima.textEdited.connect(
                    lambda text: self.comp_penerima.complete()
                    if getattr(self, 'comp_penerima', None) and str(text).strip()
                    else None
                )
                self.txt_penerima.editingFinished.connect(
                    lambda: self.eksekusi_autofill_penerima(self.txt_penerima.text())
                )
                self.txt_penerima.setProperty("_autocomplete_connected", "true")

            for w in [
                self.txt_hp_pengirim,
                self.txt_alamat_pengirim,
                self.txt_kota_pengirim,
                self.txt_hp_penerima,
                self.txt_alamat_penerima,
                self.txt_kota_penerima
            ]:
                if w:
                    w.setCompleter(None)

        except Exception:
            logger.exception("Gagal menyiapkan autocomplete resi")

    def pilih_autocomplete_pengirim(self, nama_pengirim):
        nama_pengirim = str(nama_pengirim or "").strip().upper()
        if not nama_pengirim:
            return

        self.txt_pengirim.setText(nama_pengirim)
        QTimer.singleShot(0, lambda: self.eksekusi_autofill_pengirim(nama_pengirim))

    def pilih_autocomplete_penerima(self, nama_penerima):
        nama_penerima = str(nama_penerima or "").strip().upper()
        if not nama_penerima:
            return

        self.txt_penerima.setText(nama_penerima)
        QTimer.singleShot(0, lambda: self.eksekusi_autofill_penerima(nama_penerima))

    def eksekusi_autofill_penerima(self, nama_penerima):
        nama_penerima = str(nama_penerima or "").strip().upper()
        self.kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')

        if not nama_penerima:
            return

        try:
            detail = db_service.ambil_detail_penerima(nama_penerima, self.kode_cabang)
            if detail:
                hp_master, alamat_master, kota_master, provinsi_master = detail

                self.txt_hp_penerima.setText(str(hp_master) if hp_master else "")
                self.txt_kota_penerima.setText(str(kota_master).strip().upper() if kota_master else "")
                self.txt_alamat_penerima.setText(str(alamat_master).strip().upper() if alamat_master else "")

                if provinsi_master and hasattr(self, 'cb_provinsi'):
                    provinsi_clean = str(provinsi_master).strip().upper()
                    index = self.cb_provinsi.findText(provinsi_clean, Qt.MatchFixedString)

                    if index >= 0:
                        self.cb_provinsi.setCurrentIndex(index)
                    else:
                        self.cb_provinsi.addItem(provinsi_clean)
                        self.cb_provinsi.setCurrentIndex(self.cb_provinsi.count() - 1)

        except Exception:
            logger.exception("Gagal menjalankan autofill penerima")

    def reset_tanggal(self):
        self.txt_search.blockSignals(True)
        self.txt_search.clear()
        self.txt_search.blockSignals(False)
        self.date_histori.blockSignals(True)
        self.date_histori.setDate(QDate.currentDate())
        self.date_histori.blockSignals(False)
        self.load_data_resi()

    def filter_data_resi(self):
        keyword = self.txt_search.text().strip().lower()
        if not keyword:
            self.load_data_resi()
            return

        self.list_histori.clear()
        kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')

        try:
            hasil = db_service.cari_histori_resi(keyword, kode_cabang)
            for row in hasil:
                self.list_histori.addItem(f"{row[0]} - {row[1]}")
        except Exception:
            logger.exception("Gagal memuat pencarian histori resi")

    def kalkulator_finansial_otomatis(self):
        try:
            total_berat_kargo = 0.0
            total_volume_kargo = 0.0

            for row in range(self.table_items.rowCount()):
                w_b = self.table_items.cellWidget(row, self.KOL_BERAT)
                w_v = self.table_items.cellWidget(row, self.KOL_CBM)

                if w_b and w_b.text().strip() not in {"", "-"}:
                    total_berat_kargo += float(
                        angka_indonesia_to_decimal(w_b.text())
                    )

                if w_v and w_v.text().strip() not in {"", "-"}:
                    total_volume_kargo += float(
                        angka_indonesia_to_decimal(w_v.text())
                    )

            kg_rate = float(rupiah_to_int(self.txt_ongkir_kg.text()))
            m3_rate = float(rupiah_to_int(self.txt_ongkir_m3.text()))

            with _blokir_signal_sementara(self.txt_total_ongkir):
                if kg_rate > 0 and total_berat_kargo > 0:
                    total_calc = int(total_berat_kargo * kg_rate)
                    self.txt_total_ongkir.setText(
                        format_ke_rupiah(total_calc)
                    )
                elif m3_rate > 0 and total_volume_kargo > 0:
                    total_calc = int(total_volume_kargo * m3_rate)
                    self.txt_total_ongkir.setText(
                        format_ke_rupiah(total_calc)
                    )

        except Exception:
            logger.exception("Gagal menghitung kalkulator finansial otomatis")

    def tambah_baris_barang(self):
        row_count = self.table_items.rowCount()
        self.table_items.insertRow(row_count)

        item_no = buat_tabel_item(
            row_count + 1,
            editable=False,
            alignment=Qt.AlignCenter,
        )
        self.table_items.setItem(row_count, self.KOL_NO, item_no)

        txt_nama = QLineEdit()
        txt_nama.setPlaceholderText("NAMA / JENIS BARANG...")
        txt_nama.textChanged.connect(lambda: paksa_kapital_lineedit(txt_nama))

        txt_koli = QLineEdit()
        txt_koli.setPlaceholderText("-")
        txt_koli.setAlignment(Qt.AlignCenter)
        txt_koli.textChanged.connect(lambda _, w=txt_koli: format_input_ribuan_gaya_indonesia(w))

        txt_berat = QLineEdit()
        txt_berat.setPlaceholderText("-")
        txt_berat.setAlignment(Qt.AlignCenter)
        txt_berat.setValidator(get_decimal_validator(txt_berat))

        txt_volume = QLineEdit()
        txt_volume.setPlaceholderText("-")
        txt_volume.setAlignment(Qt.AlignCenter)
        txt_volume.setValidator(get_decimal_validator(txt_volume))

        txt_berat.textChanged.connect(self.kalkulator_finansial_otomatis)
        txt_volume.textChanged.connect(self.kalkulator_finansial_otomatis)

        for w in [txt_nama, txt_koli, txt_berat, txt_volume]:
            setup_placeholder_dinamis(w, self.current_theme == 'dark')

        self.table_items.setCellWidget(row_count, self.KOL_NAMA_BARANG, txt_nama)
        self.table_items.setCellWidget(row_count, self.KOL_KOLI, txt_koli)
        self.table_items.setCellWidget(row_count, self.KOL_BERAT, txt_berat)
        self.table_items.setCellWidget(row_count, self.KOL_CBM, txt_volume)

    def hapus_baris_terpilih(self):
        current_row = self.table_items.currentRow()
        if current_row >= 0:
            self.table_items.removeRow(current_row)
        else:
            row_count = self.table_items.rowCount()
            if row_count > 0: self.table_items.removeRow(row_count - 1)

        for row in range(self.table_items.rowCount()):
            self.table_items.item(row, self.KOL_NO).setText(str(row + 1))

        self.kalkulator_finansial_otomatis()

    def auto_save_ukuran_kolom(self, logicalIndex, oldSize, newSize):
        state_sekarang = self.table_items.horizontalHeader().saveState()
        self.settings.setValue("ukuran_tabel_resi", state_sekarang)

        self._perbarui_cache_lebar_zoom(
            self.table_items,
            self._lebar_dasar_tabel(self.table_items),
        )

    def eksekusi_autofill_pengirim(self, name_val):
        name_clean = str(name_val or "").strip().upper()
        self.kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')

        if not name_clean:
            return

        try:
            row = db_service.ambil_detail_pengirim(name_clean, self.kode_cabang)
            if row:
                self.txt_hp_pengirim.setText(str(row[0]) if row[0] else "")
                self.txt_alamat_pengirim.setText(str(row[1]).strip().upper() if row[1] else "")
                self.txt_kota_pengirim.setText(str(row[2]).strip().upper() if row[2] else "")
        except Exception:
            logger.exception("Gagal autofill pengirim")

    def otomatisasi_nomor_resi(self):
        cp = self.cb_provinsi.currentText().upper()
        kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')

        kamus_prefix = CURRENT_SESSION.get('aturan_prefix', {})
        pref = kamus_prefix.get(cp, kamus_prefix.get("DEFAULT", "INV"))

        setting_suf = db_service.get_setting('kode_akhiran_pajak') or '-P'
        suf = setting_suf if self.cb_pajak.currentText() == "PAJAK" else ""

        try:
            base_number, max_num = db_service.ambil_sekuens_resi(kode_cabang, pref)
        except Exception:
            base_number, max_num = 0, 0

        template = db_service.get_setting('template_no_resi') or '[PREFIX][COUNTER][SUFFIX]'
        counter_final = str(max(base_number, max_num) + 1)

        hasil_resi = template.replace('[PREFIX]', pref).replace('[COUNTER]', counter_final).replace('[SUFFIX]', suf)
        self.txt_resi_display.setText(hasil_resi)

    def simpan_ke_database(self):
        self.otomatisasi_nomor_resi()
        no_resi = self.txt_resi_display.text()
        kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')
        tgl = format_tanggal_ke_db(QDate.currentDate())
        cp = self.cb_provinsi.currentText()
        ki = self.txt_kota_penerima.text().strip()
        tujuan_full = f"{cp} - {ki}" if ki else cp

        kt_asal = self.txt_kota_pengirim.text().strip().upper()

        items_list, list_barang_html = [], []
        tot_koli, tot_berat, tot_vol = 0, 0.0, 0.0

        for row in range(self.table_items.rowCount()):
            w_nama, w_qty, w_berat, w_vol = [self.table_items.cellWidget(row, i) for i in
                                             [self.KOL_NAMA_BARANG, self.KOL_KOLI, self.KOL_BERAT, self.KOL_CBM]]

            if w_nama and w_qty:
                nama = w_nama.text().strip()
                if nama:
                    qty_int = max(0, rupiah_to_int(w_qty.text()))
                    b_flt = float(
                        angka_indonesia_to_decimal(
                            w_berat.text() if w_berat else "0"
                        )
                    )
                    v_flt = float(
                        angka_indonesia_to_decimal(
                            w_vol.text() if w_vol else "0"
                        )
                    )

                    tot_koli += qty_int
                    tot_berat += b_flt
                    tot_vol += v_flt

                    items_list.append(nama)

                    list_barang_html.append({
                        'nama': nama, 'qty': str(qty_int) if qty_int > 0 else "",
                        'berat': str(b_flt) if b_flt > 0 else "", 'cbm': str(v_flt) if v_flt > 0 else ""
                    })

        total_ongkir_val = rupiah_to_int(self.txt_total_ongkir.text())
        ongkir_kg_clean = str(rupiah_to_int(self.txt_ongkir_kg.text()))
        ongkir_m3_clean = str(rupiah_to_int(self.txt_ongkir_m3.text()))

        payload = {
            'no_resi': no_resi,
            'kode_cabang': kode_cabang,
            'tanggal_masuk': tgl,
            'pengirim': self.txt_pengirim.text().strip(),
            'hp_pengirim': self.txt_hp_pengirim.text().strip(),
            'alamat_pengirim': self.txt_alamat_pengirim.text().strip(),
            'kota_asal': kt_asal,
            'penerima': self.txt_penerima.text().strip(),
            'hp_penerima': self.txt_hp_penerima.text().strip(),
            'alamat_penerima': self.txt_alamat_penerima.text().strip(),
            'kota_tujuan': tujuan_full,
            'provinsi_tujuan': self.cb_provinsi.currentText().strip().upper(),
            'nama_barang': ", ".join(items_list), 'berat': tot_berat, 'koli': tot_koli, 'cbm': tot_vol,
            'ongkir_per_kg': ongkir_kg_clean if int(ongkir_kg_clean) > 0 else "",
            'ongkir_per_cbm': ongkir_m3_clean if int(ongkir_m3_clean) > 0 else "",
            'total_ongkir': total_ongkir_val,
            'pembayaran': self.cb_payment.currentText(),
            'rincian_json': json.dumps(list_barang_html)
        }

        sukses, pesan_error = db_service.simpan_transaksi_resi(payload)

        if sukses:
            formatted_ongkir = f"Rp {format_ke_rupiah(total_ongkir_val)}" if total_ongkir_val > 0 else ""

            fmt_ongkir_kg = _format_ongkir_aman(ongkir_kg_clean)
            fmt_ongkir_m3 = _format_ongkir_aman(ongkir_m3_clean)

            formatted_data = {
                'tanggal': format_tanggal_ke_ui(QDate.currentDate()), 'no_resi': no_resi,
                'pengirim_nama': self.txt_pengirim.text().strip(), 'pengirim_telp': self.txt_hp_pengirim.text().strip(),
                'pengirim_alamat': self.txt_alamat_pengirim.text().strip(),
                'penerima_nama': self.txt_penerima.text().strip(), 'penerima_telp': self.txt_hp_penerima.text().strip(),
                'penerima_alamat': self.txt_alamat_penerima.text().strip(),
                'tipe_pajak': self.cb_pajak.currentText(), 'penerima_kota': ki, 'list_barang': list_barang_html,
                'total_qty': str(tot_koli), 'total_berat': f"{tot_berat:.1f}",
                'total_cbm': f"{tot_vol:.1f}",
                'total_jumlah_ongkir': formatted_ongkir, 'ongkir_kg': fmt_ongkir_kg, 'ongkir_m3': fmt_ongkir_m3,
                'ongkir_per_kg': fmt_ongkir_kg, 'ongkir_per_cbm': fmt_ongkir_m3, 'ongkir_kg_raw': ongkir_kg_clean,
                'ongkir_m3_raw': ongkir_m3_clean
            }

            cetak_resi_ke_printer(formatted_data, self)

            self.notif_tengah = FadeNotification("💾 TERSIMPAN", self)
            self.notif_tengah.show()

            self.date_histori.setDate(QDate.currentDate())
            self.clear_form()
            self.setup_autocomplete()
            self.load_data_resi()
        else:
            kode_error = getattr(pesan_error, "kode", None)

            if kode_error == db_service.KODE_RESI_DUPLIKAT:
                QMessageBox.critical(self, "Gagal", str(pesan_error))
            elif kode_error == db_service.KODE_DB_ERROR:
                QMessageBox.critical(self, "Error Database", str(pesan_error))
            else:
                QMessageBox.critical(self, "Error SQL", f"Gagal simpan: {pesan_error}")

    def load_data_resi(self):
        tgl_pilih = format_tanggal_ke_db(
            self.date_histori.date()
        )
        kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')
        self.list_histori.clear()

        try:
            hasil = db_service.ambil_histori_resi_by_tanggal(tgl_pilih, kode_cabang)
            for row in hasil:
                self.list_histori.addItem(f"{row[0]} - {row[1]}")
        except Exception:
            logger.exception("Gagal memuat histori resi untuk tanggal %s", tgl_pilih)

    def munculkan_preview(self, item):
        teks_item = item.text()
        no_resi = teks_item.split(" - ")[0]
        try:
            row = db_service.ambil_detail_resi(no_resi)
            if not row: return

            tgl_indo = format_tanggal_ke_ui(row[0])

            suffix_pajak = db_service.get_setting('kode_akhiran_pajak') or '-P'
            tipe_pajak = "PAJAK" if suffix_pajak and no_resi.endswith(suffix_pajak) else "NON-PAJAK"

            list_barang_html = json.loads(row[14]) if row[14] else [
                {'nama': str(row[8]), 'qty': str(row[10]), 'berat': str(row[9]), 'cbm': str(row[11])}]

            val_ongkir = int(row[12]) if row[12] else 0
            formatted_ongkir = f"Rp {format_ke_rupiah(val_ongkir)}" if val_ongkir > 0 else ""

            ongkir_kg_db = str(row[15]) if row[15] is not None else ""
            ongkir_m3_db = str(row[16]) if row[16] is not None else ""

            fmt_ongkir_kg = _format_ongkir_aman(ongkir_kg_db)
            fmt_ongkir_m3 = _format_ongkir_aman(ongkir_m3_db)

            formatted_data = {
                'tanggal': tgl_indo, 'no_resi': no_resi,
                'pengirim_nama': str(row[1]), 'pengirim_telp': str(row[2]), 'pengirim_alamat': str(row[3]),
                'penerima_nama': str(row[4]), 'penerima_telp': str(row[5]), 'penerima_alamat': str(row[6]),
                'penerima_kota': str(row[7]), 'tipe_pajak': tipe_pajak,
                'list_barang': list_barang_html, 'total_qty': str(row[10]),
                'total_berat': str(row[9]),
                'total_cbm': str(row[11]),
                'total_jumlah_ongkir': formatted_ongkir, 'ongkir_kg': fmt_ongkir_kg, 'ongkir_m3': fmt_ongkir_m3,
                'ongkir_per_kg': fmt_ongkir_kg, 'ongkir_per_cbm': fmt_ongkir_m3,
                'ongkir_kg_raw': ongkir_kg_db, 'ongkir_m3_raw': ongkir_m3_db
            }
            cetak_resi_ke_printer(formatted_data, self)
        except Exception as e:
            QMessageBox.critical(self, "Error Preview", f"Gagal memuat preview: {e}")

    def refresh_session_ui(self):
        self.kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')
        self.clear_form()
        self.setup_autocomplete()
        self.load_data_resi()

    def auto_refresh_histori(self):
        try:
            self.load_data_resi()
        except Exception:
            logger.exception("Gagal auto-refresh histori dari tab utama")

    def clear_form(self):
        # Pertahankan pilihan yang pada implementasi lama tidak ikut di-reset.
        status_combo = {
            self.cb_provinsi: self.cb_provinsi.currentIndex(),
            self.cb_pajak: self.cb_pajak.currentIndex(),
            self.cb_payment: self.cb_payment.currentIndex(),
        }

        reset_form_input_global(self.group_pengirim)
        reset_form_input_global(self.group_penerima)
        reset_form_input_global(self.group_finance)

        with _blokir_signal_sementara(self.table_items):
            self.table_items.setRowCount(0)

        for combo, index_sebelumnya in status_combo.items():
            with _blokir_signal_sementara(combo):
                if combo.count() > 0:
                    combo.setCurrentIndex(
                        max(0, min(index_sebelumnya, combo.count() - 1))
                    )
                else:
                    combo.setCurrentIndex(-1)

        self.tambah_baris_barang()

        terap_semua_placeholder_dinamis(
            self,
            is_dark=self.current_theme == "dark",
        )

        self.otomatisasi_nomor_resi()