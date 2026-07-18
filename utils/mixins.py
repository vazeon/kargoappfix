# utils/mixins.py
from PyQt5.QtCore import QSettings
import utils.zoom as zoom_helper


class ZoomTableMixin:
    """Mixin untuk mengotomatisasi kalkulasi lebar kolom saat di-zoom."""

    def _faktor_zoom_aktif(self, zoom_key="TabKontakArmada") -> float:
        zoom = zoom_helper.dapatkan_zoom_level(zoom_key)
        return max(0.68, min(1.0 + (zoom * 0.08), 1.80))

    def _lebar_dasar_tabel(self, table, zoom_key="TabKontakArmada") -> list:
        faktor = self._faktor_zoom_aktif(zoom_key)
        return [
            max(20, round(table.columnWidth(index) / faktor))
            for index in range(table.columnCount())
        ]

    def _perbarui_cache_lebar_zoom(self, table, widths: list) -> None:
        table._zoom_base_column_widths = {
            index: width for index, width in enumerate(widths)
        }

    def _set_style_dasar_zoom(self, widget, stylesheet):
        widget.setStyleSheet(stylesheet)
        if hasattr(widget, "_zoom_base_stylesheet"):
            delattr(widget, "_zoom_base_stylesheet")