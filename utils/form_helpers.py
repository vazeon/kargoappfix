# utils/for_helpers.py

from PyQt5.QtWidgets import (
    QComboBox,
    QLineEdit,
    QTableWidget,
    QTextEdit,
    QWidget,
)

from .widget_helpers import (
    _blokir_signal_sementara,
    _refresh_style_widget,
)

def bersihkan_semua_inputan(
    container_widget: QWidget,
) -> None:
    """
    Secara otomatis mencari dan mengosongkan seluruh field input
    yang berada di dalam suatu widget atau groupbox.

    Jenis widget yang akan dibersihkan:
        - QLineEdit
        - QTextEdit
        - QComboBox
        - QTableWidget
    """
    tipe_input = (
        QLineEdit,
        QTextEdit,
        QComboBox,
        QTableWidget,
    )

    semua_widget = container_widget.findChildren(
        QWidget
    )

    for widget in semua_widget:
        if not isinstance(widget, tipe_input):
            continue

        with _blokir_signal_sementara(widget):
            if isinstance(widget, QLineEdit):
                widget.clear()
                widget.setProperty(
                    "is_empty",
                    "true",
                )

            elif isinstance(widget, QTextEdit):
                widget.clear()
                widget.setProperty(
                    "is_empty",
                    "true",
                )

            elif isinstance(widget, QComboBox):
                if widget.count() > 0:
                    widget.setCurrentIndex(0)
                else:
                    widget.setCurrentIndex(-1)

            elif isinstance(widget, QTableWidget):
                widget.setRowCount(0)

        # Memancing refresh style agar Qt merender ulang
        # property italic ketika field kembali kosong.
        if isinstance(
            widget,
            (
                QLineEdit,
                QTextEdit,
            ),
        ):
            _refresh_style_widget(widget)