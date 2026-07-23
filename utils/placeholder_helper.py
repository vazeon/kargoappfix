# utils/placeholder_helper.py
from typing import Optional

from PyQt5.QtWidgets import QLineEdit, QTextEdit, QWidget

from .widget_helpers import _refresh_style_widget


_INPUT_PLACEHOLDER = (QLineEdit, QTextEdit)


def _input_kosong(widget: QWidget) -> bool:
    """Mengembalikan ``True`` ketika input tidak memiliki isi bermakna."""
    if isinstance(widget, QLineEdit):
        return not widget.text().strip()

    if isinstance(widget, QTextEdit):
        return not widget.toPlainText().strip()

    return True


def setup_placeholder_dinamis(
    widget: QWidget,
    is_dark: bool = False,
) -> None:
    """
    Mengatur dynamic property placeholder pada QLineEdit/QTextEdit.

    Signal hanya dipasang satu kali. Pemanggilan berikutnya tetap dapat
    memperbarui property tema tanpa menduplikasi koneksi signal.
    """
    if not isinstance(widget, _INPUT_PLACEHOLDER):
        return

    if not widget.placeholderText():
        return

    def update_state() -> None:
        widget.setProperty(
            "is_empty",
            "true" if _input_kosong(widget) else "false",
        )
        _refresh_style_widget(widget)

    widget.setProperty("custom_italic", "true")
    widget.setProperty(
        "is_dark",
        "true" if bool(is_dark) else "false",
    )

    if not bool(widget.property("_placeholder_hooked")):
        widget.setProperty("_placeholder_hooked", True)

        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(
                lambda _teks: update_state()
            )
        else:
            widget.textChanged.connect(update_state)

    update_state()


def terap_semua_placeholder_dinamis(
    container_widget: QWidget,
    is_dark: Optional[bool] = None,
) -> None:
    """
    Menerapkan placeholder dinamis pada seluruh input di dalam container.

    ``is_dark`` dapat diberikan secara eksplisit. Jika tidak diberikan,
    helper mencoba membaca atribut ``current_theme`` milik container agar
    pemanggilan lama tetap kompatibel dengan light dan dark mode.
    """
    if is_dark is None:
        tema_aktif = str(
            getattr(container_widget, "current_theme", "light")
        ).strip().lower()
        is_dark = tema_aktif == "dark"

    for widget in container_widget.findChildren(QWidget):
        if isinstance(widget, _INPUT_PLACEHOLDER):
            setup_placeholder_dinamis(
                widget,
                is_dark=bool(is_dark),
            )