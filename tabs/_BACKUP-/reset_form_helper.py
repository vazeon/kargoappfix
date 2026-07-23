# utils/cursor_helper.py
from PyQt5.QtCore import QEvent, QObject, Qt
from PyQt5.QtWidgets import QAbstractItemView, QComboBox, QLineEdit, QPushButton, QToolButton


class GlobalCursorFilter(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.Enter:
            # 1. Semua jenis Tombol -> Kursor Tangan
            if isinstance(obj, (QPushButton, QToolButton)):
                obj.setCursor(Qt.PointingHandCursor)

            # 2. Input Box, Tabel, List, Dropdown -> Kursor Standar OS
            elif isinstance(obj, (QAbstractItemView, QLineEdit, QComboBox)):
                obj.unsetCursor()

        return super().eventFilter(obj, event)


def terapkan_kursor_global(app):
    cursor_filter = GlobalCursorFilter(app)
    app.installEventFilter(cursor_filter)
    # Simpan referensi agar tidak terhapus dari memori (garbage collected)
    app._cursor_filter = cursor_filter