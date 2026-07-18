# utils/table_helper.py
from PyQt5.QtWidgets import QTableWidgetItem
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QBrush, QColor


def buat_tabel_item(
        text: str,
        editable: bool = True,
        alignment: Qt.AlignmentFlag = None,
        bg_color: str = None,
        fg_color: str = None
) -> QTableWidgetItem:
    """
    Helper utility untuk membuat QTableWidgetItem secara instan.
    Mengotomatisasi setFlags, setAlignment, setBackground, dan setForeground dalam 1 baris.
    """
    # Pastikan data none diubah jadi string kosong agar tidak crash
    nilai_teks = str(text) if text is not None else ""
    item = QTableWidgetItem(nilai_teks)

    # 1. Atur Hak Akses Edit (Editable)
    if not editable:
        item.setFlags(item.flags() & ~Qt.ItemIsEditable)

    # 2. Atur Alignment Posisi Teks
    if alignment is not None:
        item.setTextAlignment(alignment)

    # 3. Atur Warna Latar (Background) jika ada
    if bg_color:
        item.setBackground(QBrush(QColor(bg_color)))

    # 4. Atur Warna Teks (Foreground) jika ada
    if fg_color:
        item.setForeground(QBrush(QColor(fg_color)))

    return item