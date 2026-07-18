# utils/widget_helpers.py

from contextlib import contextmanager
from typing import Any, Iterator

from PyQt5.QtWidgets import (
    QLineEdit,
    QWidget,
)

@contextmanager
def _blokir_signal_sementara(
    widget: Any,
) -> Iterator[None]:
    """
    Memblokir signal widget untuk sementara.

    Status signal sebelumnya akan dikembalikan setelah proses
    selesai, termasuk apabila terjadi exception.
    """
    status_sebelumnya = widget.blockSignals(True)

    try:
        yield
    finally:
        widget.blockSignals(status_sebelumnya)


def _refresh_style_widget(
    widget: QWidget,
) -> None:
    """
    Memaksa Qt mengevaluasi ulang dynamic property
    yang digunakan pada stylesheet.
    """
    style = widget.style()

    if style is not None:
        style.unpolish(widget)
        style.polish(widget)

    widget.update()


def paksa_kapital_lineedit(
    edit_widget: QLineEdit,
) -> None:
    """
    Slot atau fungsi global untuk memaksa isi QLineEdit
    menjadi huruf kapital melalui signal textChanged.
    """
    teks_lama = edit_widget.text()
    teks_baru = teks_lama.upper()

    # Tidak perlu mengubah widget apabila teks sudah kapital.
    if teks_baru == teks_lama:
        return

    pos_lama = edit_widget.cursorPosition()

    with _blokir_signal_sementara(edit_widget):
        edit_widget.setText(teks_baru)

        edit_widget.setCursorPosition(
            min(
                pos_lama,
                len(teks_baru),
            )
        )