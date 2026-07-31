# tabs/tab_manifest.py
import re
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame, QSizePolicy,
                             QLineEdit, QComboBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QMessageBox, QApplication, QSplitter, QTreeWidget, QTreeWidgetItem,
                             QCompleter, QMenu)
from PyQt5.QtGui import QFont, QBrush
from PyQt5.QtCore import Qt, QEvent, QSettings, QDate, QStringListModel

from config import CURRENT_SESSION, DATA_CLIENT

import services.database_service as db_service
from themes.modules.manifest import (
    get_manifest_history_date_appearance,
    get_manifest_row_highlight,
    get_manifest_styles,
)

from utils.printer.print_manifest import cetak_manifest_ke_printer
from utils.frozen_table_helper import FrozenTableWidget
from utils.typography import get_global_font_sizes
from utils import zoom as zoom_helper
from utils.number_formatters import (format_ke_rupiah, format_angka_indonesia)
from utils.table_helper import buat_tabel_item
from utils.widget_helpers import (
    paksa_kapital_lineedit,
    terapkan_popup_combobox_bawah,
)
from utils.date_ind_format import format_tanggal_ke_ui
from utils.placeholder_helper import terap_semua_placeholder_dinamis

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

        # Cache master Kapal untuk autocomplete, autofill, dan pencegahan duplikat.
        self._kapal_master_by_key = {}

        self.init_ui()

    def init_ui(self):
        layout_utama = QHBoxLayout(self)
        layout_utama.setContentsMargins(0, 0, 0, 0)
        self.splitter = QSplitter(Qt.Horizontal)
        layout_utama.addWidget(self.splitter)

        self.panel_kiri = QWidget()
        # Batas lebar panel kiri agar tidak dapat digeser sampai hilang.
        self.panel_kiri.setMinimumWidth(700)
        self.panel_kiri.setMaximumWidth(1800)
        layout_kiri = QVBoxLayout(self.panel_kiri)
        layout_kiri.setContentsMargins(8, 6, 8, 6)
        layout_kiri.setSpacing(6)

        # Header dibungkus QWidget dengan tinggi tetap. Tanpa pembungkus ini,
        # QGridLayout dapat ikut menerima sisa tinggi panel dan mendorong kartu
        # input serta tabel menjauh.
        self.wadah_header_manifest = QWidget()
        self.wadah_header_manifest.setObjectName("wadahHeaderManifest")
        self.wadah_header_manifest.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.wadah_header_manifest.setFixedHeight(48)

        layout_header = QGridLayout(self.wadah_header_manifest)
        layout_header.setContentsMargins(0, 0, 0, 2)
        layout_header.setHorizontalSpacing(12)
        layout_header.setColumnStretch(0, 1)
        layout_header.setColumnStretch(1, 1)
        layout_header.setColumnStretch(2, 1)

        self.lbl_title = QLabel("📦 Pembuatan Manifest Pengiriman")
        layout_header.addWidget(
            self.lbl_title,
            0,
            0,
            Qt.AlignLeft | Qt.AlignVCenter,
        )

        wadah_tanggal = QWidget()
        layout_tanggal = QHBoxLayout(wadah_tanggal)
        layout_tanggal.setContentsMargins(0, 0, 0, 0)
        layout_tanggal.setSpacing(6)
        self.lbl_tanggal_manifest = QLabel("Tanggal Transaksi:")
        self.txt_tanggal_manifest = QLineEdit()
        self.txt_tanggal_manifest.setReadOnly(True)
        self.txt_tanggal_manifest.setAlignment(Qt.AlignCenter)
        self.txt_tanggal_manifest.setFixedSize(180, 30)
        self.txt_tanggal_manifest.setFocusPolicy(Qt.NoFocus)
        layout_tanggal.addWidget(self.lbl_tanggal_manifest)
        layout_tanggal.addWidget(self.txt_tanggal_manifest)
        layout_header.addWidget(
            wadah_tanggal,
            0,
            1,
            Qt.AlignCenter | Qt.AlignVCenter,
        )

        wadah_nomor = QWidget()
        layout_nomor = QHBoxLayout(wadah_nomor)
        layout_nomor.setContentsMargins(0, 0, 0, 0)
        layout_nomor.setSpacing(8)
        self.lbl_no_manifest = QLabel("No. Manifest:")
        self.txt_no_manifest = QLineEdit()
        self.txt_no_manifest.setReadOnly(True)
        self.txt_no_manifest.setAlignment(Qt.AlignCenter)
        self.txt_no_manifest.setFixedSize(200, 36)
        self.txt_no_manifest.setFocusPolicy(Qt.NoFocus)
        layout_nomor.addWidget(self.lbl_no_manifest)
        layout_nomor.addWidget(self.txt_no_manifest)
        layout_header.addWidget(
            wadah_nomor,
            0,
            2,
            Qt.AlignRight | Qt.AlignVCenter,
        )

        layout_kiri.addWidget(self.wadah_header_manifest, 0)
        self.perbarui_tanggal_header()

        # Area input detail dibuat seperti kartu input pada Tab Resi.
        # Panel kiri berisi informasi rute, panel kanan berisi armada,
        # sedangkan tombol aksi tetap berdiri sendiri di sisi kanan.
        # Bungkus area detail dalam QWidget dengan tinggi tetap agar QVBoxLayout
        # tidak membagikan ruang kosong vertikal ke area kartu.
        self.wadah_detail_manifest = QWidget()
        self.wadah_detail_manifest.setObjectName("wadahDetailManifest")
        self.wadah_detail_manifest.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.wadah_detail_manifest.setFixedHeight(172)

        layout_detail = QHBoxLayout(self.wadah_detail_manifest)
        layout_detail.setContentsMargins(0, 0, 0, 0)
        layout_detail.setSpacing(14)

        self.card_rute_manifest = QFrame()
        self.card_rute_manifest.setObjectName("cardRuteManifest")
        self.card_rute_manifest.setFixedHeight(164)
        self.card_rute_manifest.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        grid_rute = QGridLayout(self.card_rute_manifest)
        grid_rute.setContentsMargins(26, 18, 26, 18)
        grid_rute.setHorizontalSpacing(14)
        grid_rute.setVerticalSpacing(12)
        grid_rute.setColumnStretch(0, 0)
        grid_rute.setColumnStretch(1, 1)

        self.lbl_input_tujuan = QLabel("Tujuan:")
        self.lbl_input_kapal = QLabel("Kapal:")
        self.lbl_input_note = QLabel("Note:")
        self.lbl_input_tujuan.setMinimumWidth(70)
        self.lbl_input_kapal.setMinimumWidth(70)
        self.lbl_input_note.setMinimumWidth(70)

        self.cb_filter_wilayah = QComboBox()
        self.cb_filter_wilayah.addItems(
            DATA_CLIENT.get(
                'provinsi_tujuan',
                ["PROVINSI A", "PROVINSI B", "PROVINSI C"],
            )
        )
        self.cb_filter_wilayah.setMinimumWidth(230)
        self.cb_filter_wilayah.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.cb_filter_wilayah.currentTextChanged.connect(
            self.on_wilayah_changed
        )

        # Nama Kapal bersifat opsional. Hanya nama yang disimpan ke Manifest.
        self.txt_nama_kapal = QLineEdit()
        self.txt_nama_kapal.setPlaceholderText("Nama Kapal (Opsional)")
        self.txt_nama_kapal.setMinimumWidth(230)
        self.txt_nama_kapal.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.txt_nama_kapal.textChanged.connect(
            lambda: paksa_kapital_lineedit(self.txt_nama_kapal)
        )
        self.txt_nama_kapal.editingFinished.connect(
            self.autofill_kapal_dari_input
        )

        self.txt_note_manifest = QLineEdit()
        self.txt_note_manifest.setPlaceholderText("Note (Wajib jika tanpa detail truk)")
        self.txt_note_manifest.setMinimumWidth(230)
        self.txt_note_manifest.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.txt_note_manifest.textChanged.connect(
            lambda: paksa_kapital_lineedit(self.txt_note_manifest)
        )

        grid_rute.addWidget(
            self.lbl_input_tujuan,
            0,
            0,
            Qt.AlignLeft | Qt.AlignVCenter,
        )
        grid_rute.addWidget(self.cb_filter_wilayah, 0, 1)
        grid_rute.addWidget(
            self.lbl_input_kapal,
            1,
            0,
            Qt.AlignLeft | Qt.AlignVCenter,
        )
        grid_rute.addWidget(self.txt_nama_kapal, 1, 1)
        grid_rute.addWidget(
            self.lbl_input_note,
            2,
            0,
            Qt.AlignLeft | Qt.AlignVCenter,
        )
        grid_rute.addWidget(self.txt_note_manifest, 2, 1)

        self.card_armada_manifest = QFrame()
        self.card_armada_manifest.setObjectName("cardArmadaManifest")
        self.card_armada_manifest.setFixedHeight(164)
        self.card_armada_manifest.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        grid_armada = QGridLayout(self.card_armada_manifest)
        grid_armada.setContentsMargins(26, 18, 26, 18)
        grid_armada.setHorizontalSpacing(14)
        grid_armada.setVerticalSpacing(10)
        grid_armada.setColumnStretch(0, 0)
        grid_armada.setColumnStretch(1, 1)

        self.lbl_input_truk = QLabel("Truk:")
        self.lbl_input_sopir = QLabel("Sopir:")
        self.lbl_input_keterangan = QLabel("Ket:")
        for label_input in (
                self.lbl_input_truk,
                self.lbl_input_sopir,
                self.lbl_input_keterangan,
        ):
            label_input.setMinimumWidth(70)

        # ComboBox Jenis Truk dengan placeholder.
        self.cb_jenis_truk = QComboBox()
        self.cb_jenis_truk.addItem("- Pilih jenis -")
        self.cb_jenis_truk.addItems(
            ["TB", "Tronton", "CDD", "Pick-up", "Lainnya..."]
        )
        self.cb_jenis_truk.setMinimumWidth(150)
        self.cb_jenis_truk.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )

        def ubah_font_placeholder(idx):
            font_utama = self.cb_jenis_truk.font()
            font_utama.setItalic(idx == 0)
            self.cb_jenis_truk.setFont(font_utama)

            font_italic = QFont(font_utama)
            font_italic.setItalic(True)
            self.cb_jenis_truk.setItemData(
                0,
                font_italic,
                Qt.FontRole,
            )

            font_normal = QFont(font_utama)
            font_normal.setItalic(False)
            for i in range(1, self.cb_jenis_truk.count()):
                self.cb_jenis_truk.setItemData(
                    i,
                    font_normal,
                    Qt.FontRole,
                )

        self.cb_jenis_truk.currentIndexChanged.connect(
            ubah_font_placeholder
        )
        self.cb_jenis_truk.currentIndexChanged.connect(
            self.on_jenis_truk_manifest_changed
        )
        ubah_font_placeholder(0)

        self.txt_jenis_truk_lain = QLineEdit()
        self.txt_jenis_truk_lain.setPlaceholderText("Jenis lainnya")
        self.txt_jenis_truk_lain.setMinimumWidth(130)
        self.txt_jenis_truk_lain.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.txt_jenis_truk_lain.textChanged.connect(
            lambda: paksa_kapital_lineedit(self.txt_jenis_truk_lain)
        )
        self.txt_jenis_truk_lain.hide()

        self.txt_no_pol = QLineEdit()
        self.txt_no_pol.setPlaceholderText("No. Pol")
        self.txt_no_pol.setMinimumWidth(130)
        self.txt_no_pol.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.txt_no_pol.textChanged.connect(
            lambda: paksa_kapital_lineedit(self.txt_no_pol)
        )

        wadah_truk = QWidget()
        layout_truk = QHBoxLayout(wadah_truk)
        layout_truk.setContentsMargins(0, 0, 0, 0)
        layout_truk.setSpacing(8)
        layout_truk.addWidget(self.cb_jenis_truk, 5)
        layout_truk.addWidget(self.txt_jenis_truk_lain, 4)
        layout_truk.addWidget(self.txt_no_pol, 4)

        self.txt_sopir = QLineEdit()
        self.txt_sopir.setPlaceholderText("Nama Sopir")
        self.txt_sopir.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.txt_sopir.textChanged.connect(
            lambda: paksa_kapital_lineedit(self.txt_sopir)
        )

        self.txt_keterangan = QLineEdit()
        self.txt_keterangan.setPlaceholderText("Keterangan")
        self.txt_keterangan.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Fixed,
        )
        self.txt_keterangan.textChanged.connect(
            lambda: paksa_kapital_lineedit(self.txt_keterangan)
        )

        grid_armada.addWidget(
            self.lbl_input_truk,
            0,
            0,
            Qt.AlignLeft | Qt.AlignVCenter,
        )
        grid_armada.addWidget(wadah_truk, 0, 1)
        grid_armada.addWidget(
            self.lbl_input_sopir,
            1,
            0,
            Qt.AlignLeft | Qt.AlignVCenter,
        )
        grid_armada.addWidget(self.txt_sopir, 1, 1)
        grid_armada.addWidget(
            self.lbl_input_keterangan,
            2,
            0,
            Qt.AlignLeft | Qt.AlignVCenter,
        )
        grid_armada.addWidget(self.txt_keterangan, 2, 1)

        wadah_tombol_manifest = QWidget()
        wadah_tombol_manifest.setFixedSize(210, 132)
        wadah_tombol_manifest.setSizePolicy(
            QSizePolicy.Fixed,
            QSizePolicy.Fixed,
        )
        layout_tombol_manifest = QVBoxLayout(wadah_tombol_manifest)
        layout_tombol_manifest.setContentsMargins(4, 0, 0, 0)
        layout_tombol_manifest.setSpacing(8)
        layout_tombol_manifest.setAlignment(Qt.AlignVCenter)

        self.btn_proses = QPushButton("⚡ BUAT MANIFEST")
        self.btn_proses.setMinimumWidth(190)
        self.btn_proses.setMinimumHeight(38)
        layout_tombol_manifest.addWidget(
            self.btn_proses,
            0,
            Qt.AlignHCenter,
        )

        self.btn_batal_edit = QPushButton("❌ BATAL")
        self.btn_batal_edit.setMinimumWidth(190)
        self.btn_batal_edit.clicked.connect(self.batal_edit)
        self.btn_batal_edit.hide()
        layout_tombol_manifest.addWidget(
            self.btn_batal_edit,
            0,
            Qt.AlignHCenter,
        )

        layout_detail.addWidget(self.card_rute_manifest, 5)
        layout_detail.addWidget(self.card_armada_manifest, 6)
        layout_detail.addWidget(
            wadah_tombol_manifest,
            0,
            Qt.AlignVCenter,
        )
        layout_kiri.addWidget(
            self.wadah_detail_manifest,
            0,
            Qt.AlignTop,
        )

        self.tabel_manifest = FrozenTableWidget(
            frozen_cols=3,
            fixed_cols=[0],
            fixed_widths={0: 22}
        )

        self.tabel_manifest.setColumnCount(13)
        self.tabel_manifest.setHorizontalHeaderLabels(
            ["✔", "NO.", "RESI", "TGL MASUK", "PENGIRIM", "PENERIMA", "TUJUAN", "NAMA BARANG", "KOLI", "BERAT (kg)",
             "KUBIK (m3)", "ONGKIR (Rp)", "KETERANGAN"])
        self.tabel_manifest.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabel_manifest.verticalHeader().setVisible(False)
        self.tabel_manifest.setAlternatingRowColors(True)

        self.load_lebar_kolom(self.tabel_manifest)
        self.tabel_manifest.horizontalHeader().sectionResized.connect(
            lambda: self.simpan_lebar_kolom(self.tabel_manifest))
        # Hanya tabel yang boleh mengambil sisa tinggi panel. Header dan kartu
        # selalu menempel di atas tanpa ruang kosong tambahan.
        self.tabel_manifest.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding,
        )
        layout_kiri.addWidget(self.tabel_manifest, 1)
        layout_kiri.setStretch(0, 0)
        layout_kiri.setStretch(1, 0)
        layout_kiri.setStretch(2, 1)

        self.panel_kanan = QWidget()
        # Batas lebar panel kanan agar tidak dapat digeser sampai hilang.
        self.panel_kanan.setMinimumWidth(260)
        self.panel_kanan.setMaximumWidth(520)
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
        # Cegah kedua panel diciutkan menjadi 0 piksel.
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setCollapsible(0, False)
        self.splitter.setCollapsible(1, False)
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
        finally:
            # Saat Tab Manifest dibuka, refresh Truk sekaligus menyegarkan
            # daftar nama Kapal dari Subtab Kapal.
            self.setup_autocomplete_kapal()

    @staticmethod
    def _normalisasi_kunci_kapal(nama):
        """Menyamakan huruf, spasi, titik, dan tanda baca untuk cek duplikat."""
        return re.sub(
            r"[^A-Z0-9]+",
            "",
            str(nama or "").strip().upper(),
        )

    def setup_autocomplete_kapal(self):
        """Memuat master Kapal untuk autocomplete dan autofill Manifest."""
        try:
            rows = db_service.ambil_semua_kapal_full() or []
            master_by_key = {}

            for row in rows:
                if not row:
                    continue

                nama = str(row[0] or "").strip().upper()
                if not nama:
                    continue

                tujuan = str(row[1] or "").strip().upper() if len(row) > 1 else ""
                keterangan = str(row[2] or "").strip().upper() if len(row) > 2 else ""
                foto = str(row[3] or "").strip() if len(row) > 3 else ""

                key = self._normalisasi_kunci_kapal(nama)
                if key and key not in master_by_key:
                    master_by_key[key] = {
                        "nama": nama,
                        "tujuan": tujuan,
                        "keterangan": keterangan,
                        "foto": foto,
                    }

            self._kapal_master_by_key = master_by_key
            daftar_nama = sorted(
                item["nama"]
                for item in master_by_key.values()
            )

            if not hasattr(self, "model_autocomplete_kapal"):
                self.model_autocomplete_kapal = QStringListModel(self)
                self.completer_kapal = QCompleter(
                    self.model_autocomplete_kapal,
                    self,
                )
                self.completer_kapal.setCaseSensitivity(
                    Qt.CaseInsensitive
                )
                self.completer_kapal.setFilterMode(
                    Qt.MatchContains
                )
                self.completer_kapal.setCompletionMode(
                    QCompleter.PopupCompletion
                )
                self.completer_kapal.activated[str].connect(
                    self.on_kapal_selected
                )
                self.txt_nama_kapal.setCompleter(
                    self.completer_kapal
                )

            self.model_autocomplete_kapal.setStringList(
                daftar_nama
            )

        except Exception as exc:
            QMessageBox.warning(
                self,
                "Warning Database",
                f"Gagal memuat autocomplete kapal: {exc}",
            )

    def _cari_master_kapal(self, nama):
        key = self._normalisasi_kunci_kapal(nama)
        if not key:
            return None
        return self._kapal_master_by_key.get(key)

    def on_kapal_selected(self, nama):
        """Mengisi nama resmi dan tujuan Manifest dari master Kapal."""
        data = self._cari_master_kapal(nama)
        if not data:
            return

        nama_resmi = data["nama"]
        if self.txt_nama_kapal.text().strip().upper() != nama_resmi:
            self.txt_nama_kapal.setText(nama_resmi)

        tujuan = data.get("tujuan", "")
        if tujuan:
            index_tujuan = self.cb_filter_wilayah.findText(
                tujuan,
                Qt.MatchFixedString,
            )
            if index_tujuan >= 0:
                self.cb_filter_wilayah.setCurrentIndex(
                    index_tujuan
                )

        detail_tooltip = []
        if tujuan:
            detail_tooltip.append(f"Tujuan: {tujuan}")
        if data.get("keterangan"):
            detail_tooltip.append(
                f"Keterangan: {data['keterangan']}"
            )
        self.txt_nama_kapal.setToolTip(
            "\n".join(detail_tooltip)
        )

    def autofill_kapal_dari_input(self):
        """Menangkap nama yang diketik manual tetapi sebenarnya sudah terdaftar."""
        nama = self.txt_nama_kapal.text().strip()
        if not nama:
            self.txt_nama_kapal.setToolTip("")
            return

        data = self._cari_master_kapal(nama)
        if data:
            self.on_kapal_selected(data["nama"])

    def _refresh_subtab_kapal(self):
        """Menyegarkan Subtab Kapal bila widget-nya sudah dibuat."""
        window = self.window()
        if not window:
            return

        for widget in window.findChildren(QWidget):
            if widget.__class__.__name__ != "SubTabKapal":
                continue

            refresh = getattr(widget, "refresh_tabel", None)
            if callable(refresh):
                try:
                    refresh()
                except RuntimeError:
                    pass
            break

    def pastikan_kapal_terdaftar(self, nama_kapal):
        """
        Memastikan Nama Kapal Manifest tersedia di master Kapal.

        Kapal lama dipakai ulang berdasarkan nama yang dinormalisasi.
        Kapal baru dibuat satu kali dengan tujuan Manifest aktif.
        """
        nama_kapal = str(nama_kapal or "").strip().upper()
        if not nama_kapal:
            return True, ""

        # Baca ulang agar cache selalu mencerminkan perubahan dari Subtab Kapal.
        self.setup_autocomplete_kapal()

        data_lama = self._cari_master_kapal(nama_kapal)
        if data_lama:
            self.on_kapal_selected(data_lama["nama"])
            return True, data_lama["nama"]

        simpan = getattr(
            db_service,
            "simpan_atau_update_kapal_full",
            None,
        )
        if not callable(simpan):
            return False, (
                "Fungsi penyimpanan master Kapal tidak tersedia "
                "pada database_service.py."
            )

        tujuan = self.cb_filter_wilayah.currentText().strip().upper()
        sukses, pesan = simpan(
            nama_kapal,
            tujuan,
            "",
            "",
            mode="TAMBAH",
        )

        if not sukses:
            # Antisipasi data dibuat oleh proses lain setelah cache dibaca.
            self.setup_autocomplete_kapal()
            data_lama = self._cari_master_kapal(nama_kapal)
            if data_lama:
                self.on_kapal_selected(data_lama["nama"])
                return True, data_lama["nama"]

            return False, str(pesan or "Gagal menyimpan master Kapal.")

        self.setup_autocomplete_kapal()
        data_baru = self._cari_master_kapal(nama_kapal)
        nama_resmi = (
            data_baru["nama"]
            if data_baru
            else nama_kapal
        )

        self.txt_nama_kapal.setText(nama_resmi)
        self._refresh_subtab_kapal()
        return True, nama_resmi

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

    @staticmethod
    def _format_tanggal_header(tanggal):
        """Format tanggal header dalam bahasa Indonesia."""
        nama_hari = {
            1: "Senin",
            2: "Selasa",
            3: "Rabu",
            4: "Kamis",
            5: "Jumat",
            6: "Sabtu",
            7: "Minggu",
        }
        return (
            f"{nama_hari.get(tanggal.dayOfWeek(), '')}, "
            f"{tanggal.toString('dd/MM/yyyy')}"
        )

    def perbarui_tanggal_header(self):
        """Menampilkan tanggal transaksi hari ini pada header Manifest."""
        if hasattr(self, "txt_tanggal_manifest"):
            self.txt_tanggal_manifest.setText(
                self._format_tanggal_header(QDate.currentDate())
            )

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

                chk = QTableWidgetItem()
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

        terap_semua_placeholder_dinamis(
            self.tabel_manifest,
            is_dark=is_dark,
        )

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
                tgl_raw = str(r[0])
                m_id = str(r[1])
                truk = str(r[2] or "")
                nama_kapal = str(r[3] or "")
                count = r[4]
                note_manifest = (
                    str(r[5] or "")
                    if len(r) > 5
                    else ""
                )
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

                # Pada manifest tanpa armada, data_resi.truk masih dapat berisi
                # salinan Note untuk kompatibilitas. Tampilkan sebagai Note.
                is_note_only = bool(
                    note_manifest
                    and truk.strip().upper() == note_manifest.strip().upper()
                )
                if is_note_only:
                    truk_display = f" | NOTE: {note_manifest}"
                else:
                    truk_display = (
                        f" | {truk}"
                        if truk and truk.strip() != "-"
                        else ""
                    )
                kapal_display = (
                    f" | 🚢 {nama_kapal}"
                    if nama_kapal
                    else ""
                )
                child.setText(
                    1,
                    f"{m_id}{truk_display}{kapal_display} ({count} Resi)",
                )

                # Simpan data asli supaya edit/cetak tidak bergantung pada
                # pemisahan teks tampilan histori.
                child.setData(0, Qt.UserRole, m_id)
                child.setData(0, Qt.UserRole + 1, truk)
                child.setData(0, Qt.UserRole + 2, nama_kapal)
                child.setData(0, Qt.UserRole + 3, note_manifest)

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
        nama_kapal = self.txt_nama_kapal.text().strip().upper()
        note_manifest = self.txt_note_manifest.text().strip().upper()

        if truk_idx == 0:
            # Tanpa armada: seluruh input detail truk harus kosong dan Note wajib.
            if nopol or sopir or keterangan:
                QMessageBox.warning(
                    self,
                    "Peringatan",
                    "No. Polisi, Sopir, dan Keterangan hanya untuk detail truk. "
                    "Pilih Jenis Truk, atau kosongkan detail truk lalu isi Note!"
                )
                self.cb_jenis_truk.setFocus()
                return

            if not note_manifest:
                QMessageBox.warning(
                    self,
                    "Peringatan",
                    "Isi Note jika manifest tidak menggunakan detail truk!"
                )
                self.txt_note_manifest.setFocus()
                return

            dict_update = {
                'no_polisi': "",
                'nama_sopir': "",
                'jenis_truk': "",
                # Salinan ini mempertahankan kompatibilitas modul lama.
                # Saat cetak, nilai ini dipisahkan kembali sebagai NOTE.
                'nama_truk': note_manifest,
                'ket_truk': "",
                'nama_kapal': nama_kapal,
                'note_manifest': note_manifest,
            }
        else:
            if self.cb_jenis_truk.currentText().strip() == "Lainnya..." and not truk_text:
                QMessageBox.warning(self, "Peringatan", "Jenis truk lainnya wajib diisi!")
                self.txt_jenis_truk_lain.setFocus()
                return

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
                'ket_truk': keterangan,
                'nama_kapal': nama_kapal,
                'note_manifest': note_manifest,
            }

        kapal_ok, nama_kapal_resmi = self.pastikan_kapal_terdaftar(nama_kapal)
        if not kapal_ok:
            QMessageBox.warning(self, "Data Kapal", nama_kapal_resmi)
            self.txt_nama_kapal.setFocus()
            return

        dict_update["nama_kapal"] = nama_kapal_resmi

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
                self.txt_nama_kapal.clear()
                self.txt_note_manifest.clear()
                self.load_data_resi_gudang()
                self.generate_no_manifest()
                self.refresh_tahun_filter()
                self.load_histori()
        else:
            QMessageBox.critical(self, "Error", f"Gagal memproses manifest:\n{err}")

    def preview_histori_manifest(self, item):
        if item.parent():
            m_id = str(item.data(0, Qt.UserRole) or "").strip()
            truk = str(item.data(0, Qt.UserRole + 1) or "").strip()
            nama_kapal = str(item.data(0, Qt.UserRole + 2) or "").strip()
            note_manifest = str(item.data(0, Qt.UserRole + 3) or "").strip()

            if not m_id:
                m_id = item.text(1).split(" | ")[0].strip()

            self.siapkan_dan_cetak_dari_id(
                m_id,
                truk,
                nama_kapal,
                note_manifest,
            )

    def siapkan_dan_cetak_dari_id(
            self,
            m_id,
            truk,
            nama_kapal="",
            note_manifest="",
    ):
        try:
            kode_cabang = CURRENT_SESSION.get('kode_cabang', 'PUSAT')
            data = db_service.ambil_resi_detail_untuk_cetak(
                kode_cabang,
                db_service.ambil_resi_list_by_manifest(m_id, kode_cabang)
            )

            items_cetak = []
            for r in data:
                # r[8] = total_ongkir, r[9] = ket_manifest
                ongkir_val = format_ke_rupiah(r[8]) if len(r) > 8 and r[8] else "-"
                ket_val = str(r[9] or "-").strip() if len(r) > 9 else "-"

                items_cetak.append((
                    r[0],  # no_resi
                    r[1],  # pengirim
                    r[2],  # penerima
                    r[3].split(" - ")[-1] if " - " in r[3] else r[3],  # kota
                    r[4],  # nama_barang
                    format_angka_indonesia(r[5], kosong_jika_nol=True, nilai_kosong="-"),  # koli
                    format_angka_indonesia(r[6], kosong_jika_nol=True, nilai_kosong="-"),  # berat
                    format_angka_indonesia(r[7], kosong_jika_nol=True, nilai_kosong="-"),  # cbm
                    ongkir_val,  # total_ongkir
                    ket_val  # ket_manifest
                ))

            if not nama_kapal:
                nama_kapal = db_service.ambil_nama_kapal_manifest(m_id, kode_cabang)

            if not note_manifest:
                ambil_note = getattr(db_service, "ambil_note_manifest", None)
                if callable(ambil_note):
                    note_manifest = ambil_note(m_id, kode_cabang)

            truk_cetak = str(truk or "").strip()
            note_manifest = str(note_manifest or "").strip()

            if (
                    note_manifest
                    and truk_cetak.upper() == note_manifest.upper()
            ):
                truk_cetak = ""

            cetak_manifest_ke_printer(
                {
                    "no_manifest": m_id,
                    "armada": truk_cetak,
                    "note_manifest": note_manifest,
                    "nama_kapal": nama_kapal,
                    "tanggal": QDate.currentDate().toString("dd/MM/yyyy"),
                    "items": items_cetak,
                },
                self,
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Gagal cetak: {e}")

    def showEvent(self, event):
        super().showEvent(event)
        terapkan_popup_combobox_bawah(self)
        self.perbarui_tanggal_header()
        self.load_data_resi_gudang()
        self.generate_no_manifest()

    def sesuaikan_tema_lokal(self):
        win = self.window()
        is_dark = win.current_theme == "dark" if win and hasattr(win, 'current_theme') else False

        terap_semua_placeholder_dinamis(
            self,
            is_dark=is_dark,
        )

        z = zoom_helper.dapatkan_zoom_level(self.__class__.__name__)
        font_statis = get_global_font_sizes(0)
        font_dinamis = get_global_font_sizes(z)

        styles_statis = get_manifest_styles(is_dark, self.is_edit_mode, 0)
        styles_dinamis = get_manifest_styles(is_dark, self.is_edit_mode, z)

        self.panel_kiri.setStyleSheet(styles_statis['panel_kiri'])
        self.panel_kanan.setStyleSheet(styles_statis['panel_kanan'])
        self.lbl_title.setStyleSheet(styles_statis['lbl_title'])
        self.btn_proses.setStyleSheet(styles_statis['btn_proses'])

        for w in [self.txt_jenis_truk_lain, self.txt_no_pol, self.txt_sopir,
                  self.txt_keterangan, self.txt_nama_kapal,
                  self.txt_note_manifest,
                  self.cb_filter_wilayah, self.cb_jenis_truk,
                  self.cb_tahun_filter, self.txt_cari_histori]:
            w.setStyleSheet(styles_statis['style_input'])

        # Kartu input mengikuti karakter visual panel Pengirim/Penerima
        # pada Tab Resi, termasuk warna adaptif untuk mode terang/gelap.
        if is_dark:
            warna_bg_kartu = "#171B23"
            warna_border_kartu = "#3A4556"
            warna_label_kartu = "#F2F4F7"
        else:
            warna_bg_kartu = "#FFFFFF"
            warna_border_kartu = "#C8D4E3"
            warna_label_kartu = "#172033"

        style_kartu_manifest = f"""
            QFrame#cardRuteManifest,
            QFrame#cardArmadaManifest {{
                background-color: {warna_bg_kartu};
                border: 1px solid {warna_border_kartu};
                border-radius: 11px;
            }}
        """
        self.card_rute_manifest.setStyleSheet(style_kartu_manifest)
        self.card_armada_manifest.setStyleSheet(style_kartu_manifest)

        style_label_input = f"""
            QLabel {{
                color: {warna_label_kartu};
                background: transparent;
                border: none;
                font-size: {font_statis['sz_base']}px;
                font-weight: 600;
            }}
        """
        for label_input in (
                self.lbl_input_tujuan,
                self.lbl_input_kapal,
                self.lbl_input_note,
                self.lbl_input_truk,
                self.lbl_input_sopir,
                self.lbl_input_keterangan,
        ):
            label_input.setStyleSheet(style_label_input)

        # Style khusus header agar konsisten dengan tampilan header Tab Resi.
        ukuran_header = font_statis["sz_base"]
        if is_dark:
            warna_label = "#C8D1E0"
            warna_teks_tanggal = "#F8FAFC"
            bg_tanggal = "#181C24"
            border_tanggal = "#4B5563"
            warna_nomor = "#FFC400"
            bg_nomor = "#171B23"
            border_nomor = "#3B82F6"
        else:
            warna_label = "#4B5C73"
            warna_teks_tanggal = "#10233F"
            bg_tanggal = "#FFFFFF"
            border_tanggal = "#C8D4E3"
            warna_nomor = "#C90000"
            bg_nomor = "#FFF2F2"
            border_nomor = "#FF4D5E"

        style_label_header = f"""
            QLabel {{
                color: {warna_label};
                background: transparent;
                font-size: {ukuran_header}px;
                font-weight: 600;
            }}
        """
        self.lbl_tanggal_manifest.setStyleSheet(style_label_header)
        self.lbl_no_manifest.setStyleSheet(style_label_header)

        self.txt_tanggal_manifest.setStyleSheet(f"""
            QLineEdit {{
                color: {warna_teks_tanggal};
                background: {bg_tanggal};
                border: 1px solid {border_tanggal};
                border-radius: 5px;
                padding: 2px 8px;
                font-size: {ukuran_header}px;
            }}
        """)
        self.txt_no_manifest.setStyleSheet(f"""
            QLineEdit {{
                color: {warna_nomor};
                background: {bg_nomor};
                border: 2px solid {border_nomor};
                border-radius: 6px;
                padding: 2px 10px;
                font-size: {ukuran_header + 3}px;
                font-weight: 800;
                letter-spacing: 1px;
            }}
        """)

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

        if hasattr(self.tabel_manifest, "frozen_table"):
            self.tabel_manifest.frozen_table.horizontalHeader().setFont(header_font)
            self.tabel_manifest.frozen_table.verticalHeader().setDefaultSectionSize(tinggi_baris)

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
        t.setColumnWidth(self.KOL_CHECK, 22)

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

        m_id = str(
            item.data(0, Qt.UserRole)
            or ""
        ).strip()
        truk = str(
            item.data(0, Qt.UserRole + 1)
            or ""
        ).strip()
        nama_kapal = str(
            item.data(0, Qt.UserRole + 2)
            or ""
        ).strip()
        note_manifest = str(
            item.data(0, Qt.UserRole + 3)
            or ""
        ).strip()

        if not m_id:
            m_id = item.text(1).split(" | ")[0].strip()

        if action == act_print:
            self.siapkan_dan_cetak_dari_id(
                m_id,
                truk,
                nama_kapal,
                note_manifest,
            )
        elif action == act_edit:
            self.aktifkan_mode_edit(
                m_id,
                truk,
                nama_kapal,
                note_manifest,
            )

    def aktifkan_mode_edit(
            self,
            m_id,
            truk_str,
            nama_kapal="",
            note_manifest="",
    ):
        self.is_edit_mode = True
        self.edit_manifest_id = m_id

        self.cb_jenis_truk.setCurrentIndex(0)
        self.txt_jenis_truk_lain.clear()
        self.txt_no_pol.clear()
        self.txt_sopir.clear()
        self.txt_keterangan.clear()
        self.txt_nama_kapal.clear()
        self.txt_note_manifest.clear()

        kode_cabang = CURRENT_SESSION.get("kode_cabang", "PUSAT")

        nama_kapal = str(nama_kapal or "").strip().upper()
        if not nama_kapal:
            nama_kapal = db_service.ambil_nama_kapal_manifest(m_id, kode_cabang)
        self.txt_nama_kapal.setText(nama_kapal)

        if not note_manifest:
            ambil_note = getattr(db_service, "ambil_note_manifest", None)
            if callable(ambil_note):
                note_manifest = ambil_note(m_id, kode_cabang)
        note_manifest = str(note_manifest or "").strip().upper()
        self.txt_note_manifest.setText(note_manifest)

        truk_bersih = str(truk_str or '').strip()
        is_note_only = bool(
            note_manifest
            and truk_bersih.upper() == note_manifest.upper()
        )

        if truk_bersih and truk_bersih != "-" and not is_note_only:
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
            elif not note_manifest:
                # Kompatibilitas manifest lama sebelum kolom Note tersedia.
                self.txt_note_manifest.setText(truk_bersih.upper())

        self.lbl_title.setText(f"✏️ Edit Manifest: {m_id}")
        self.txt_no_manifest.setText(m_id)
        self.btn_proses.setText("💾 SIMPAN MANIFES")
        self.btn_batal_edit.show()
        self.sesuaikan_tema_lokal()
        self.load_data_resi_gudang()

    def batal_edit(self):
        self.is_edit_mode = False
        self.edit_manifest_id = ""
        self.lbl_title.setText("📦 Pembuatan Manifest Pengiriman")
        self.btn_proses.setText("⚡ BUAT MANIFES")
        self.btn_batal_edit.hide()

        self.cb_jenis_truk.setCurrentIndex(0)
        self.txt_jenis_truk_lain.clear()
        self.txt_sopir.clear()
        self.txt_no_pol.clear()
        self.txt_keterangan.clear()
        self.txt_nama_kapal.clear()
        self.txt_note_manifest.clear()

        self.sesuaikan_tema_lokal()
        self.generate_no_manifest()
        self.load_data_resi_gudang()