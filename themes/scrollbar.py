# themes/scrollbar.py
"""Style dan pengelola scrollbar global aplikasi."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from tempfile import gettempdir
from typing import Callable, Dict, Optional

from PyQt5.QtCore import QEvent, QObject
from PyQt5.QtWidgets import QApplication, QScrollBar, QWidget


@lru_cache(maxsize=2)
def _buat_icon_panah(is_dark: bool) -> Dict[str, str]:
    """
    Membuat ikon panah SVG secara otomatis di folder temporary.

    Ikon dibuat untuk:
    - panah atas;
    - panah bawah;
    - panah kiri;
    - panah kanan.

    Dengan cara ini, modul scrollbar tidak memerlukan file PNG atau SVG
    tambahan di dalam folder project. Ikon tetap tersedia ketika aplikasi
    dipindahkan atau dibundel menjadi executable.
    """
    warna_panah = "#d8dee9" if is_dark else "#475569"
    nama_tema = "dark" if is_dark else "light"

    folder_icon = (
        Path(gettempdir())
        / "global_scrollbar_icons"
        / nama_tema
    )
    folder_icon.mkdir(
        parents=True,
        exist_ok=True,
    )

    data_path = {
        "up": "M1.25 5.25 L4 2.5 L6.75 5.25",
        "down": "M1.25 2.75 L4 5.5 L6.75 2.75",
        "left": "M5.25 1.25 L2.5 4 L5.25 6.75",
        "right": "M2.75 1.25 L5.5 4 L2.75 6.75",
    }

    hasil: Dict[str, str] = {}

    for arah, path_data in data_path.items():
        file_path = folder_icon / f"arrow_{arah}.svg"

        isi_svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
            width="8"
            height="8"
            viewBox="0 0 8 8">
            <path
                d="{path_data}"
                fill="none"
                stroke="{warna_panah}"
                stroke-width="1.45"
                stroke-linecap="round"
                stroke-linejoin="round"
            />
        </svg>"""

        # Hindari menulis ulang file ikon jika isinya tidak berubah.
        if (
            not file_path.exists()
            or file_path.read_text(
                encoding="utf-8"
            ) != isi_svg
        ):
            file_path.write_text(
                isi_svg,
                encoding="utf-8",
            )

        # Qt Style Sheet lebih stabil menggunakan slash, termasuk di Windows.
        hasil[arah] = file_path.resolve().as_posix()

    return hasil


def get_scrollbar_style(is_dark: bool) -> str:
    """
    Menghasilkan satu style scrollbar yang konsisten untuk seluruh aplikasi.

    Style dibuat sama untuk:
    - QScrollArea
    - QTableWidget
    - QTreeWidget
    - QListWidget
    - QTextEdit
    - dialog dan widget lain yang memiliki QScrollBar

    Perilaku scrollbar:
    - track transparan ketika tidak disorot;
    - track terlihat ketika cursor berada di area scrollbar;
    - handle lebih terang ketika disorot;
    - handle memiliki warna khusus ketika ditekan;
    - tombol panah tersedia untuk vertikal dan horizontal;
    - tombol panah ikut ter-highlight ketika disorot atau ditekan.
    """
    # Warna asli tetap dipertahankan sebagai warna dasar handle.
    warna_handle = "#3f434d" if is_dark else "#cbd5e1"
    warna_hover = "#4c525e" if is_dark else "#94a3b8"

    if is_dark:
        warna_track_hover = "rgba(255, 255, 255, 18)"
        warna_pressed = "#858d9a"
        warna_tombol_hover = "rgba(255, 255, 255, 28)"
        warna_tombol_pressed = "rgba(255, 255, 255, 42)"
    else:
        warna_track_hover = "rgba(15, 23, 42, 18)"
        warna_pressed = "#64748b"
        warna_tombol_hover = "rgba(15, 23, 42, 24)"
        warna_tombol_pressed = "rgba(15, 23, 42, 38)"

    icon_panah = _buat_icon_panah(is_dark)

    # Ukuran 16px menyediakan ruang yang cukup untuk handle dan tombol panah.
    ukuran_scrollbar = 16
    ukuran_icon_panah = 8

    return f"""
        QScrollArea {{
            background-color: transparent;
            border: none;
        }}

        /* ================================================================
         * SCROLLBAR VERTIKAL
         * ================================================================ */

        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: {ukuran_scrollbar}px;
            margin: {ukuran_scrollbar}px 0px {ukuran_scrollbar}px 0px;
        }}

        QScrollBar:vertical:hover {{
            background: {warna_track_hover};
            border-radius: 7px;
        }}

        QScrollBar::handle:vertical {{
            background: {warna_handle};
            border: none;
            border-radius: 5px;
            min-height: 30px;
            margin: 2px 3px;
        }}

        QScrollBar::handle:vertical:hover {{
            background: {warna_hover};
        }}

        QScrollBar::handle:vertical:pressed {{
            background: {warna_pressed};
        }}

        QScrollBar::sub-line:vertical {{
            background: transparent;
            border: none;
            border-radius: 4px;
            height: {ukuran_scrollbar}px;
            subcontrol-origin: margin;
            subcontrol-position: top;
        }}

        QScrollBar::add-line:vertical {{
            background: transparent;
            border: none;
            border-radius: 4px;
            height: {ukuran_scrollbar}px;
            subcontrol-origin: margin;
            subcontrol-position: bottom;
        }}

        QScrollBar::sub-line:vertical:hover,
        QScrollBar::add-line:vertical:hover {{
            background: {warna_tombol_hover};
        }}

        QScrollBar::sub-line:vertical:pressed,
        QScrollBar::add-line:vertical:pressed {{
            background: {warna_tombol_pressed};
        }}

        QScrollBar::up-arrow:vertical {{
            image: url("{icon_panah['up']}");
            width: {ukuran_icon_panah}px;
            height: {ukuran_icon_panah}px;
        }}

        QScrollBar::down-arrow:vertical {{
            image: url("{icon_panah['down']}");
            width: {ukuran_icon_panah}px;
            height: {ukuran_icon_panah}px;
        }}

        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: transparent;
            border: none;
        }}

        /* ================================================================
         * SCROLLBAR HORIZONTAL
         * ================================================================ */

        QScrollBar:horizontal {{
            border: none;
            background: transparent;
            height: {ukuran_scrollbar}px;
            margin: 0px {ukuran_scrollbar}px 0px {ukuran_scrollbar}px;
        }}

        QScrollBar:horizontal:hover {{
            background: {warna_track_hover};
            border-radius: 7px;
        }}

        QScrollBar::handle:horizontal {{
            background: {warna_handle};
            border: none;
            border-radius: 5px;
            min-width: 30px;
            margin: 3px 2px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background: {warna_hover};
        }}

        QScrollBar::handle:horizontal:pressed {{
            background: {warna_pressed};
        }}

        QScrollBar::sub-line:horizontal {{
            background: transparent;
            border: none;
            border-radius: 4px;
            width: {ukuran_scrollbar}px;
            subcontrol-origin: margin;
            subcontrol-position: left;
        }}

        QScrollBar::add-line:horizontal {{
            background: transparent;
            border: none;
            border-radius: 4px;
            width: {ukuran_scrollbar}px;
            subcontrol-origin: margin;
            subcontrol-position: right;
        }}

        QScrollBar::sub-line:horizontal:hover,
        QScrollBar::add-line:horizontal:hover {{
            background: {warna_tombol_hover};
        }}

        QScrollBar::sub-line:horizontal:pressed,
        QScrollBar::add-line:horizontal:pressed {{
            background: {warna_tombol_pressed};
        }}

        QScrollBar::left-arrow:horizontal {{
            image: url("{icon_panah['left']}");
            width: {ukuran_icon_panah}px;
            height: {ukuran_icon_panah}px;
        }}

        QScrollBar::right-arrow:horizontal {{
            image: url("{icon_panah['right']}");
            width: {ukuran_icon_panah}px;
            height: {ukuran_icon_panah}px;
        }}

        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {{
            background: transparent;
            border: none;
        }}
    """


class GlobalScrollbarManager(QObject):
    """
    Memasang style scrollbar secara global tanpa mengganti stylesheet
    QApplication setiap kali tema berubah.

    Scrollbar yang sudah ada diperbarui melalui refresh_semua().
    Scrollbar yang dibuat kemudian akan tertangani otomatis oleh event filter.
    """

    def __init__(
        self,
        root_widget: QWidget,
        is_dark_getter: Callable[[], bool],
    ):
        super().__init__(root_widget)

        self.root_widget = root_widget
        self.is_dark_getter = is_dark_getter
        self._app: Optional[QApplication] = None
        self._installed = False

    def _is_dark(self) -> bool:
        try:
            return bool(self.is_dark_getter())
        except Exception:
            return False

    def _signature(self) -> str:
        return "dark" if self._is_dark() else "light"

    def install(
        self,
        app: Optional[QApplication] = None,
    ) -> None:
        """
        Memasang event filter satu kali pada QApplication.
        """
        if self._installed:
            return

        self._app = app or QApplication.instance()

        if self._app is None:
            return

        self._app.installEventFilter(self)
        self._installed = True

        # Tambahan: langsung terapkan style pada scrollbar yang sudah dibuat
        # sebelum event filter dipasang.
        self.refresh_semua(force=True)

    def uninstall(self) -> None:
        """
        Melepas event filter apabila aplikasi perlu dibersihkan.
        """
        if self._app is not None and self._installed:
            self._app.removeEventFilter(self)

        self._installed = False
        self._app = None

    def terapkan_ke_scrollbar(
        self,
        scrollbar: QScrollBar,
        force: bool = False,
    ) -> None:
        """
        Menerapkan style hanya jika tema scrollbar berubah.
        """
        if not isinstance(scrollbar, QScrollBar):
            return

        signature = self._signature()

        if (
            not force
            and scrollbar.property(
                "_global_scrollbar_theme"
            ) == signature
        ):
            return

        # Property dipasang sebelum setStyleSheet untuk mencegah
        # event Polish memicu penerapan berulang.
        scrollbar.setProperty(
            "_global_scrollbar_theme",
            signature,
        )

        scrollbar.setStyleSheet(
            get_scrollbar_style(
                signature == "dark"
            )
        )

    def refresh_semua(
        self,
        force: bool = False,
    ) -> None:
        """
        Memperbarui seluruh scrollbar yang sudah berada di dalam MainWindow.
        """
        if self.root_widget is None:
            return

        for scrollbar in self.root_widget.findChildren(
            QScrollBar
        ):
            self.terapkan_ke_scrollbar(
                scrollbar,
                force=force,
            )

    def eventFilter(
        self,
        obj,
        event,
    ):
        """
        Menangani scrollbar baru dari tab, popup, dan dialog secara otomatis.
        """
        if (
            isinstance(obj, QScrollBar)
            and event.type()
            in (
                QEvent.Polish,
                QEvent.Show,
            )
        ):
            self.terapkan_ke_scrollbar(obj)

        return False
