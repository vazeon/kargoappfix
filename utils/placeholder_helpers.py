# utils/placeholder_helpers.py

from PyQt5.QtWidgets import (
    QLineEdit,
    QTextEdit,
    QWidget,
)

from .widget_helpers import (
    _refresh_style_widget,
)

def setup_placeholder_dinamis(
    widget: QWidget,
    is_dark: bool,
) -> None:
    """
    Mengatur font italic secara dinamis ketika input kosong
    dan placeholder sedang ditampilkan.

    Fungsi tidak mengubah atau menimpa teks placeholder asli.

    Syarat:
        themes.py memiliki selector QSS berikut:

        [custom_italic="true"][is_empty="true"]
    """
    if not isinstance(
        widget,
        (
            QLineEdit,
            QTextEdit,
        ),
    ):
        return

    if not widget.placeholderText():
        return

    def update_state() -> None:
        """
        Memperbarui dynamic property is_empty berdasarkan
        isi widget.
        """
        if isinstance(widget, QLineEdit):
            is_empty = not widget.text().strip()
        else:
            is_empty = not widget.toPlainText().strip()

        widget.setProperty(
            "is_empty",
            "true" if is_empty else "false",
        )

        _refresh_style_widget(widget)

    # Property ini digunakan oleh selector QSS.
    widget.setProperty(
        "custom_italic",
        "true",
    )

    # Parameter is_dark tetap dipertahankan dan disimpan
    # sebagai dynamic property agar dapat digunakan oleh QSS.
    widget.setProperty(
        "is_dark",
        "true" if is_dark else "false",
    )

    # Mencegah pemasangan signal yang sama secara berulang
    # apabila fungsi dipanggil lebih dari satu kali.
    sudah_dipasang = bool(
        widget.property("_placeholder_hooked")
    )

    if not sudah_dipasang:
        widget.setProperty(
            "_placeholder_hooked",
            True,
        )

        if isinstance(widget, QLineEdit):
            widget.textChanged.connect(
                lambda _text: update_state()
            )
        else:
            widget.textChanged.connect(
                update_state
            )

    # Menentukan kondisi awal widget.
    update_state()


def terap_semua_placeholder_dinamis(
    container_widget: QWidget,
) -> None:
    """
    Fungsi sapu jagat untuk menerapkan efek placeholder dinamis
    ke seluruh QLineEdit dan QTextEdit di dalam form atau tab.

    Nama fungsi tetap dipertahankan agar pemanggilan lama
    pada bagian aplikasi lain tidak mengalami error.
    """
    semua_widget = container_widget.findChildren(
        QWidget
    )

    for widget in semua_widget:
        if isinstance(
            widget,
            (
                QLineEdit,
                QTextEdit,
            ),
        ):
            setup_placeholder_dinamis(
                widget,
                is_dark=True,
            )