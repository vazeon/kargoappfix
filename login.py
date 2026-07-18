# login.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
                             QPushButton, QLabel, QMessageBox, QGraphicsDropShadowEffect,
                             QApplication, QDesktopWidget)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QCursor

# Mengambil variabel sesi dan data klien (Tidak pakai ACCOUNTS lagi)
from config import DATA_CLIENT, CURRENT_SESSION
from database_manager import init_db


class LoginWindow(QWidget):
    def __init__(self, switch_to_main_callback):
        super().__init__()
        self.switch_to_main = switch_to_main_callback
        self._drag_pos = None

        # Jendela dikunci Frameless dan Transparan semenjak lahir
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

        self.init_ui()
        self.center_window()

    def init_ui(self):
        self.setObjectName("LoginWidgetRoot")
        self.setStyleSheet("""
            #LoginWidgetRoot { background: transparent; }
            QWidget { color: #1e293b; font-family: 'Segoe UI', Arial, sans-serif; }
            #LoginCard { background-color: #ffffff; border: 1px solid #cbd5e1; border-radius: 12px; }
            QLineEdit { background-color: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; padding: 11px 15px; color: #0f172a; font-size: 13px; }
            QLineEdit:focus { border: 1px solid #2563eb; background-color: #ffffff; }
            QPushButton#BtnEnter { background-color: #2563eb; color: white; border: none; border-radius: 6px; padding: 12px; font-weight: bold; font-size: 13px; letter-spacing: 1px; }
            QPushButton#BtnEnter:hover { background-color: #1d4ed8; }

            QPushButton#BtnCloseTop { 
                background-color: transparent; 
                color: #94a3b8; 
                font-size: 22px; 
                font-weight: bold; 
                border: none; 
                border-radius: 4px;
            }
            QPushButton#BtnCloseTop:hover { 
                background-color: #ef4444; 
                color: white; 
            }
        """)

        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setAlignment(Qt.AlignCenter)

        card_widget = QWidget()
        card_widget.setObjectName("LoginCard")
        card_widget.setFixedSize(360, 370)
        card_layout = QVBoxLayout(card_widget)
        card_layout.setContentsMargins(25, 15, 25, 30)
        card_layout.setSpacing(14)

        # Efek bayangan (shadow) diperhalus agar estetik di background terang
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 0, 0, 45))
        shadow.setOffset(0, 6)
        card_widget.setGraphicsEffect(shadow)

        top_bar_layout = QHBoxLayout()
        top_bar_layout.setContentsMargins(0, 0, 0, 0)
        top_bar_layout.addStretch()

        btn_close = QPushButton("×", card_widget)
        btn_close.setObjectName("BtnCloseTop")
        btn_close.setFixedSize(28, 28)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(QApplication.instance().quit)
        top_bar_layout.addWidget(btn_close)
        card_layout.addLayout(top_bar_layout)

        # Ambil nama PT dinamis dari DATA_CLIENT
        nama_pt = DATA_CLIENT.get("pt_nama", "SISTEM EKSPEDISI KARGO")
        lbl_title = QLabel(nama_pt)
        lbl_title.setAlignment(Qt.AlignCenter)
        lbl_title.setWordWrap(True)
        lbl_title.setStyleSheet(
            "font-size: 15px; font-weight: bold; color: #0f172a; letter-spacing: 1px; text-transform: uppercase; margin-top: -10px;")
        card_layout.addWidget(lbl_title)

        lbl_subtitle = QLabel("PANEL ADMIN")
        lbl_subtitle.setAlignment(Qt.AlignCenter)
        lbl_subtitle.setStyleSheet(
            "font-size: 10px; letter-spacing: 3px; color: #2563eb; font-weight: bold; margin-bottom: 5px;")
        card_layout.addWidget(lbl_subtitle)

        self.txt_user = QLineEdit()
        self.txt_user.setPlaceholderText("Username")
        card_layout.addWidget(self.txt_user)

        self.txt_pwd = QLineEdit()
        self.txt_pwd.setPlaceholderText("Password")
        self.txt_pwd.setEchoMode(QLineEdit.Password)
        card_layout.addWidget(self.txt_pwd)

        card_layout.addSpacing(5)

        btn_login = QPushButton("MASUK")
        btn_login.setObjectName("BtnEnter")
        btn_login.setCursor(Qt.PointingHandCursor)
        btn_login.clicked.connect(self.handle_login)
        card_layout.addWidget(btn_login)

        # LINK TRIGGER TOMBOL ENTER
        self.txt_user.returnPressed.connect(self.handle_login)
        self.txt_pwd.returnPressed.connect(self.handle_login)
        btn_login.setDefault(True)

        main_layout.addWidget(card_widget)
        self.setLayout(main_layout)

    def showEvent(self, event):
        super().showEvent(event)
        self.txt_user.setFocus()

    # =================================================================
    # 🌟 LOGIKA LOGIN BARU (ANTI-SILENT CRASH & TANPA POP-UP)
    # =================================================================
    def handle_login(self):
        try:
            user = self.txt_user.text().strip()
            pwd = self.txt_pwd.text().strip()

            if not user or not pwd:
                QMessageBox.warning(None, "Peringatan", "Username dan Password tidak boleh kosong!")
                return

            # Panggil fungsi pintar dari config.py
            from config import verifikasi_login_sistem

            sukses, role_user, nama_lengkap = verifikasi_login_sistem(user, pwd)

            if sukses:
                # Sesi (CURRENT_SESSION) sudah otomatis di-update di config.py
                init_db(CURRENT_SESSION["db_name"])

                # 🚀 POP-UP DIHAPUS! Langsung loncat ke dashboard utama!
                self.switch_to_main()
                self.close()
            else:
                # Jika gagal, kosongkan kolom password biar user sadar kalau klikannya merespon
                self.txt_pwd.clear()
                QMessageBox.critical(None, "Akses Ditolak",
                                     "Username atau Password salah!\nPastikan huruf besar/kecil sesuai.")

        except Exception as e:
            # Ini penangkap error gaib! Kalau ada crash, tidak akan diam saja.
            QMessageBox.critical(None, "Fatal Error", f"Terjadi kerusakan sistem saat memproses login:\n\n{str(e)}")

    # =================================================================
    # LOGIKA DRAG/GESER JENDELA FRAMELESS
    # =================================================================
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos is not None:
            self.move(event.globalPos() - self._drag_pos)
            event.accept()

    def mouseReleaseEvent(self, event):
        self._drag_pos = None
        event.accept()

    def center_window(self):
        desktop = QApplication.desktop()
        current_screen = desktop.screenNumber(QCursor.pos())
        screen_geo = desktop.availableGeometry(current_screen)

        qr = self.frameGeometry()
        qr.moveCenter(screen_geo.center())
        self.move(qr.topLeft())