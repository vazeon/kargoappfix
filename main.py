# main.py
import sys
import os
import ctypes
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QTabWidget, QTabBar,
                             QStylePainter, QStyleOptionTab, QStyle, QDialog, QMessageBox,
                             QLineEdit, QTextEdit)
from PyQt5.QtCore import Qt, QSettings, QObject, QEvent, QTimer
from PyQt5.QtGui import QColor, QFontDatabase, QFont

from utils.typography import get_master_font
from utils.placeholder_helpers import setup_placeholder_dinamis

from config import DATA_CLIENT, CURRENT_SESSION

from themes.base import BASE_STYLE
from themes.shell import get_main_shell_styles
from themes.top_right import get_top_right_styles
from themes.palette import get_theme_palette
from themes.scrollbar import GlobalScrollbarManager

from login import LoginWindow
from database_manager import init_db
import services.database_service as db_service

from tabs.tab_resi import TabResi
from tabs.tab_buku_gudang import TabBukuGudang
from tabs.tab_manifest import TabManifest
from tabs.tab_invoice import TabInvoice
from tabs.tab_kontak_armada import TabKontakArmada
from tab_setting import TabSettingSistem

class GlobalPlaceholderManager(QObject):
    """
    Memasang pengelola placeholder satu kali ketika widget dipoles Qt.

    Seluruh logika signal dan dynamic property dipusatkan di
    utils.placeholder_helpers agar tidak ada koneksi ganda.
    """

    def eventFilter(self, obj, event):
        if (
            event.type() == QEvent.Polish
            and isinstance(obj, (QLineEdit, QTextEdit))
            and obj.placeholderText()
        ):
            setup_placeholder_dinamis(
                obj,
                is_dark=False,
            )

        return False


class FloatingIndicatorTabBar(QTabBar):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.is_dark = False

    def set_dark_theme(self, is_dark):
        self.is_dark = is_dark
        self.update()

    def paintEvent(self, event):
        painter = QStylePainter(self)
        option = QStyleOptionTab()
        for i in range(self.count()):
            self.initStyleOption(option, i)
            painter.drawControl(QStyle.CE_TabBarTab, option)
            if i == self.currentIndex():
                rect = self.tabRect(i)
                line_width = 40
                line_height = 3
                x = rect.x() + (rect.width() - line_width) // 2
                y = rect.y() + 10
                color = QColor("#3b82f6") if self.is_dark else QColor("#2563eb")
                painter.fillRect(x, y, line_width, line_height, color)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.settings = QSettings(
            "AplikasiEkspedisi",
            "PengaturanUI",
        )
        self.current_theme = self.settings.value(
            "theme",
            "light",
        )

        # Mencegah klik tema berulang ketika proses sebelumnya
        # belum selesai dan menyimpan tema lokal per tab.
        self._sedang_ganti_tema = False
        self._cache_tema_tab = {}

        app = QApplication.instance()
        if app is not None:
            # Stylesheet global dipasang hanya sekali. Pergantian tema
            # berikutnya cukup mengganti QPalette yang jauh lebih ringan.
            if not bool(app.property("_base_style_terpasang")):
                app.setStyleSheet(BASE_STYLE)
                app.setProperty("_base_style_terpasang", True)

            app.setPalette(
                get_theme_palette(
                    self.current_theme == "dark"
                )
            )

        self.scrollbar_manager = GlobalScrollbarManager(
            root_widget=self,
            is_dark_getter=lambda: (
                self.current_theme == "dark"
            ),
        )
        self.scrollbar_manager.install(app)

        self.init_ui()

    def init_ui(self):
        self.central_widget = QWidget(self)
        self.central_widget.setObjectName("CentralWidget")
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        self.tabs = QTabWidget(self)
        self.tabs.setObjectName("MainTabs")
        self.custom_tab_bar = FloatingIndicatorTabBar(self)
        self.custom_tab_bar.setObjectName("MainTabBar")
        self.tabs.setTabBar(self.custom_tab_bar)
        self.tabs.setElideMode(Qt.ElideNone)
        self.tabs.setUsesScrollButtons(True)
        self.main_layout.addWidget(self.tabs)

        self.container_top_right = QWidget(self)
        hbox_top_right = QHBoxLayout(self.container_top_right)
        hbox_top_right.setContentsMargins(0, 4, 15, 0)
        hbox_top_right.setSpacing(6)

        self.lbl_info_cabang = QLabel("🏢 PUSAT")

        self.btn_zoom_out = QPushButton("🔍-")
        self.btn_zoom_out.setFixedSize(40, 32)
        self.btn_zoom_out.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_out.clicked.connect(lambda: self.ubah_zoom(-1))

        self.btn_zoom_in = QPushButton("🔍+")
        self.btn_zoom_in.setFixedSize(40, 32)
        self.btn_zoom_in.setCursor(Qt.PointingHandCursor)
        self.btn_zoom_in.clicked.connect(lambda: self.ubah_zoom(1))

        self.btn_theme = QPushButton(self)
        self.btn_theme.setFixedWidth(120)
        self.btn_theme.setFixedHeight(32)
        self.btn_theme.setCursor(Qt.PointingHandCursor)
        self.btn_theme.clicked.connect(self.toggle_theme)

        self.btn_setting = QPushButton("⚙️")
        self.btn_setting.setFixedSize(40, 32)
        self.btn_setting.setCursor(Qt.PointingHandCursor)
        self.btn_setting.setToolTip("Pengaturan Sistem (Super Admin)")
        self.btn_setting.clicked.connect(self.buka_dasbor_pengaturan)

        hbox_top_right.addWidget(self.lbl_info_cabang)
        hbox_top_right.addWidget(self.btn_zoom_out)
        hbox_top_right.addWidget(self.btn_zoom_in)
        hbox_top_right.addWidget(self.btn_theme)
        hbox_top_right.addWidget(self.btn_setting)
        self.tabs.setCornerWidget(self.container_top_right, Qt.TopRightCorner)

        self.tab_resi_widget = TabResi()
        self.tabs.addTab(self.tab_resi_widget, "📦 Data Resi")

        self.tab_buku_gudang = TabBukuGudang()
        self.tabs.addTab(self.tab_buku_gudang, "🏭 Buku Gudang")

        self.tab_manifest = TabManifest()
        self.tabs.addTab(self.tab_manifest, "📋 Manifest")

        self.tab_invoice = TabInvoice()
        self.tabs.addTab(self.tab_invoice, "🧾 Invoice")

        self.tab_kontak_armada = TabKontakArmada()
        self.tabs.addTab(self.tab_kontak_armada, "👥 Kontak dan Armada")

        from PyQt5.QtWidgets import QScroller, QScrollArea, QTableWidget

        for widget in self.findChildren(QScrollArea):
            QScroller.grabGesture(widget.viewport(), QScroller.LeftMouseButtonGesture)

        for table in self.findChildren(QTableWidget):
            table.setVerticalScrollMode(QTableWidget.ScrollPerPixel)
            table.setHorizontalScrollMode(QTableWidget.ScrollPerPixel)
            QScroller.grabGesture(table.viewport(), QScroller.LeftMouseButtonGesture)

        self.tabs.currentChanged.connect(self.refresh_tab_utama_diklik)
        self.apply_theme()

    def _signature_tema_tab(self, tab_widget):
        if tab_widget is None:
            return None

        nama_kelas = tab_widget.__class__.__name__

        try:
            zoom = int(
                self.settings.value(
                    f"zoom_{nama_kelas}",
                    0,
                )
            )
        except (TypeError, ValueError):
            zoom = 0

        return (
            self.current_theme,
            zoom,
        )


    def _terapkan_tema_lokal(
        self,
        tab_widget,
        force=False,
    ):
        """
        Menerapkan tema lokal hanya pada tab yang dibutuhkan.

        Tab tersembunyi tidak diproses saat tombol tema ditekan.
        Tema tab tersebut diterapkan ketika pengguna membukanya.
        """
        if tab_widget is None:
            return

        fungsi_tema = getattr(
            tab_widget,
            "sesuaikan_tema_lokal",
            None,
        )

        if not callable(fungsi_tema):
            return

        signature = self._signature_tema_tab(
            tab_widget
        )
        cache_key = id(tab_widget)

        if (
            not force
            and self._cache_tema_tab.get(cache_key)
            == signature
        ):
            return

        tab_widget.setUpdatesEnabled(False)

        try:
            fungsi_tema()
            self._cache_tema_tab[cache_key] = signature

        except Exception as error:
            print(
                "[Tema] Gagal menerapkan tema pada "
                f"{tab_widget.__class__.__name__}: {error}"
            )

        finally:
            tab_widget.setUpdatesEnabled(True)
            tab_widget.update()


    def refresh_tab_utama_diklik(self, index):
        tab_aktif = self.tabs.widget(index)

        # Tema lokal diterapkan secara lazy hanya saat tab dibuka.
        self._terapkan_tema_lokal(
            tab_aktif
        )

        nama_tab = self.tabs.tabText(index)

        if "Data Resi" in nama_tab:
            if hasattr(
                self.tab_resi_widget,
                "auto_refresh_histori",
            ):
                self.tab_resi_widget.auto_refresh_histori()

    def update_session_ui(self):
        nama_pt = DATA_CLIENT.get('pt_nama', 'PT EKSPEDISI KARGO')
        nama_cabang = CURRENT_SESSION.get('nama_cabang', 'PUSAT')
        self.setWindowTitle(f"{nama_pt} - {nama_cabang} - PANEL ADMIN v1.0")
        self.lbl_info_cabang.setText(f"🏢 {nama_cabang}")

        if hasattr(self.tab_resi_widget, 'refresh_session_ui'):
            self.tab_resi_widget.refresh_session_ui()

    def toggle_theme(self):
        if self._sedang_ganti_tema:
            return

        self._sedang_ganti_tema = True

        try:
            self.current_theme = (
                "light"
                if self.current_theme == "dark"
                else "dark"
            )

            self.settings.setValue(
                "theme",
                self.current_theme,
            )

            self.apply_theme(force=True)

        finally:
            self._sedang_ganti_tema = False

    def apply_theme(self, force=False):
        is_dark = self.current_theme == "dark"
        style_btn, style_label = get_top_right_styles(
            is_dark
        )

        app = QApplication.instance()

        # QPalette jauh lebih ringan daripada mengganti QSS QApplication.
        # QApplication.setStyleSheet() memaksa Qt memoles ulang seluruh
        # widget, termasuk semua tab yang sedang tersembunyi.
        self.setUpdatesEnabled(False)

        try:
            if app is not None:
                app.setPalette(
                    get_theme_palette(is_dark)
                )

            shell_styles = get_main_shell_styles(
                is_dark
            )
            self.central_widget.setStyleSheet(
                shell_styles["central"]
            )
            self.tabs.setStyleSheet(
                shell_styles["tabs"]
            )
            self.custom_tab_bar.setStyleSheet(
                shell_styles["tab_bar"]
            )
            self.container_top_right.setStyleSheet(
                shell_styles["corner"]
            )

            self.custom_tab_bar.set_dark_theme(
                is_dark
            )

            self.btn_theme.setText(
                "☀️ Mode Terang"
                if is_dark
                else "🌙 Mode Gelap"
            )

            self.lbl_info_cabang.setStyleSheet(
                style_label
            )

            for button in (
                self.btn_theme,
                self.btn_zoom_in,
                self.btn_zoom_out,
                self.btn_setting,
            ):
                button.setStyleSheet(style_btn)

            # Hanya scrollbar yang diperbarui. Tidak ada
            # QApplication.setStyleSheet() ulang.
            self.scrollbar_manager.refresh_semua(
                force=force,
            )

        finally:
            self.setUpdatesEnabled(True)
            self.update()

        # Tema lokal tab aktif dijalankan pada putaran event berikutnya.
        # Shell aplikasi berubah lebih dahulu sehingga klik terasa instan.
        tab_aktif = self.tabs.currentWidget()

        if tab_aktif is not None:
            QTimer.singleShot(
                0,
                lambda tab=tab_aktif: self._terapkan_tema_lokal(
                    tab,
                    force=force,
                ),
            )

    def buka_dasbor_pengaturan(self):
        self.dialog_setting = QDialog(self)
        self.dialog_setting.setWindowTitle("PENGATURAN")
        self.dialog_setting.setMinimumSize(800, 600)

        main_layout = QVBoxLayout(self.dialog_setting)
        widget_setting = TabSettingSistem(self.dialog_setting)
        main_layout.addWidget(widget_setting)

        role_aktif = str(CURRENT_SESSION.get('role', '')).strip().upper()

        if role_aktif != "SUPER_ADMIN":
            overlay = QWidget(self.dialog_setting)
            overlay.setStyleSheet("background-color: rgba(25, 25, 30, 0.9); border-radius: 6px;")
            overlay.resize(self.dialog_setting.width(), self.dialog_setting.height())

            lbl_warning = QLabel(
                f"🔒 AKSES TERBATAS\n\nHanya akun SUPER ADMIN / OWNER yang memiliki otoritas\nuntuk mengubah struktur data perusahaan.\n\n(Role Anda Saat Ini: {role_aktif if role_aktif else 'TIDAK DIKETAHUI'})",
                overlay
            )
            lbl_warning.setAlignment(Qt.AlignCenter)
            lbl_warning.setStyleSheet("color: #ff4d4d; font-size: 16px; font-weight: bold; line-height: 150%;")

            overlay_layout = QVBoxLayout(overlay)
            overlay_layout.addWidget(lbl_warning)
            overlay.raise_()

            if hasattr(widget_setting, 'btn_simpan_all'):
                widget_setting.btn_simpan_all.setEnabled(False)
                widget_setting.btn_simpan_all.setText("❌ AKSES DITOLAK")

        self.dialog_setting.exec_()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, 'dialog_setting') and self.dialog_setting.isVisible():
            for child in self.dialog_setting.children():
                if isinstance(child, QWidget) and child.styleSheet().startswith("background-color: rgba"):
                    child.resize(self.dialog_setting.width(), self.dialog_setting.height())

    def ubah_zoom(self, step):
        active_tab = self.tabs.currentWidget()

        if active_tab is None:
            return

        tab_name = active_tab.__class__.__name__

        try:
            current_z = int(
                self.settings.value(
                    f"zoom_{tab_name}",
                    0,
                )
            )
        except (TypeError, ValueError):
            current_z = 0

        new_z = max(
            -4,
            min(current_z + step, 10),
        )

        self.settings.setValue(
            f"zoom_{tab_name}",
            new_z,
        )

        self._terapkan_tema_lokal(
            active_tab,
            force=True,
        )

    def wheelEvent(self, event):
        if event.modifiers() == Qt.ControlModifier:
            if event.angleDelta().y() > 0:
                self.ubah_zoom(1)
            else:
                self.ubah_zoom(-1)
            event.accept()
        else:
            super().wheelEvent(event)

    def penangkap_error_gaib(type, value, traceback_obj):
        import traceback
        traceback.print_exception(type, value, traceback_obj)

    sys.excepthook = penangkap_error_gaib

def load_fonts():
    font_folder = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "assets",
        "fonts",
    )

    if not os.path.exists(font_folder):
        print(
            f"❌ Folder font tidak ditemukan: {font_folder}"
        )
        return

    for filename in sorted(os.listdir(font_folder)):
        if not filename.lower().endswith((".ttf", ".otf")):
            continue

        font_path = os.path.join(
            font_folder,
            filename,
        )

        font_id = QFontDatabase.addApplicationFont(
            font_path
        )

        if font_id == -1:
            print(
                f"❌ Font gagal dimuat: {filename}"
            )
            continue

        families = QFontDatabase.applicationFontFamilies(
            font_id
        )

        print(
            f"✅ {filename} → "
            f"{', '.join(families)}"
        )


if __name__ == "__main__":
    # 1. BUAT DAN SIAPKAN DATABASE LEBIH DULU
    nama_db = CURRENT_SESSION.get('db_name', 'database_cargo.db')
    init_db(nama_db)
    db_service.inisialisasi_database()

    # 2. SINKRONISASI DATA PENGATURAN SECARA AMAN
    from config import muat_pengaturan_sistem, DATA_CLIENT

    # Update memori global dengan data asli dari tabel pengaturan_sistem
    DATA_CLIENT.update(muat_pengaturan_sistem())

    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except:
        pass

    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    from PyQt5.QtCore import QLocale

    QLocale.setDefault(QLocale(QLocale.Indonesian, QLocale.Indonesia))

    app = QApplication(sys.argv)

    app.setStyle('Fusion')

    placeholder_manager = GlobalPlaceholderManager()
    app.installEventFilter(placeholder_manager)

    # 1. Daftarkan seluruh file font ke Qt.
    load_fonts()

    # 2. Baca pilihan font terakhir dari QSettings.
    font_aktif = get_master_font()

    # 3. Periksa apakah font tersedia.
    font_tersedia = set(
        QFontDatabase().families()
    )

    if font_aktif not in font_tersedia:
        print(
            f"⚠️ Font '{font_aktif}' tidak tersedia."
        )

        if "Inter" in font_tersedia:
            font_aktif = "Inter"
        else:
            font_aktif = app.font().family()

    # 4. Terapkan font sebelum MainWindow dibuat.
    font_aplikasi = QFont(font_aktif)
    font_aplikasi.setPointSize(10)
    font_aplikasi.setWeight(QFont.Normal)
    font_aplikasi.setStyleStrategy(
        QFont.PreferAntialias
    )

    app.setFont(font_aplikasi)

    print("====================================")
    print("Font tersimpan :", get_master_font())
    print("Font diterapkan:", app.font().family())
    print("====================================")

    # MainWindow dibuat setelah font diterapkan.
    main_window = MainWindow()

    from PyQt5.QtGui import QFontInfo
    from PyQt5.QtWidgets import QWidget

    print("\n========== PEMERIKSAAN FONT ==========")

    widget_tes = {
        "Judul utama": main_window.tab_resi_widget.lbl_main_title,
        "Label tanggal": main_window.tab_resi_widget.lbl_tgl_tag,
        "Nomor resi": main_window.tab_resi_widget.txt_resi_display,
        "Input pengirim": main_window.tab_resi_widget.txt_pengirim,
        "Combo provinsi": main_window.tab_resi_widget.cb_provinsi,
        "Header tabel": main_window.tab_resi_widget.table_items.horizontalHeader(),
        "Isi tabel": main_window.tab_resi_widget.table_items,
        "Tombol tambah": main_window.tab_resi_widget.btn_tambah_baris,
        "Tombol simpan": main_window.tab_resi_widget.btn_generate_simpan,
        "Histori": main_window.tab_resi_widget.list_histori,
    }

    print("\n===== WIDGET YANG BUKAN INTER =====")

    jumlah_non_inter = 0

    for widget in main_window.findChildren(QWidget):
        font_aktual = QFontInfo(widget.font()).family()

        if font_aktual.casefold() != "inter":
            jumlah_non_inter += 1

            print(
                widget.metaObject().className(),
                "| objectName:",
                widget.objectName() or "-",
                "| font:",
                font_aktual,
            )

    print("Jumlah widget non-Inter:", jumlah_non_inter)
    print("===================================\n")


    for nama, widget in widget_tes.items():
        requested_font = widget.font().family()
        actual_font = QFontInfo(widget.font()).family()

        print(
            f"{nama:18} | "
            f"diminta: {requested_font:20} | "
            f"aktual: {actual_font}"
        )

    print("======================================\n")


    def buka_dashboard_kargo():
        main_window.update_session_ui()
        main_window.showMaximized()

        for w in main_window.findChildren((QLineEdit, QTextEdit)):
            if w.isVisible():
                w.style().unpolish(w)
                w.style().polish(w)
                w.update()

    login_window = LoginWindow(buka_dashboard_kargo)
    login_window.show()
    sys.exit(app.exec_())