# tabs/tab_armada/tab_armada.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTabWidget

# Import ketiga sub-tab dari folder yang sama
from tabs.tab_armada.subtab_truk import SubTabTruk
from tabs.tab_armada.subtab_kapal import SubTabKapal


class TabArmada(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)

        # Membuat QTabWidget internal (Sub-Tab)
        self.tabs_internal = QTabWidget(self)

        # Inisialisasi masing-masing sub-tab
        self.subtab_truk = SubTabTruk()
        self.subtab_kapal = SubTabKapal()

        # Memasukkan ke dalam tab navigasi
        self.tabs_internal.addTab(self.subtab_truk, "Truk")
        self.tabs_internal.addTab(self.subtab_kapal, "Kapal")

        self.tabs_internal.currentChanged.connect(
            self._tema_subtab_aktif
        )

        layout.addWidget(self.tabs_internal)
        self.sesuaikan_tema_lokal()

    def _tema_subtab_aktif(self, _index=None):
        subtab = self.tabs_internal.currentWidget()

        if subtab is None:
            return

        fungsi_tema = getattr(
            subtab,
            "sesuaikan_tema_lokal",
            None,
        )

        if not callable(fungsi_tema):
            return

        subtab.setUpdatesEnabled(False)

        try:
            fungsi_tema()

        finally:
            subtab.setUpdatesEnabled(True)
            subtab.update()


    def sesuaikan_tema_lokal(self):
        """
        Meneruskan tema hanya ke subtab yang sedang terlihat.

        Subtab tersembunyi diperbarui ketika pengguna membukanya.
        """
        self._tema_subtab_aktif()

    def showEvent(self, event):
        super().showEvent(event)
        # Tema dikelola MainWindow dan currentChanged tab internal.
