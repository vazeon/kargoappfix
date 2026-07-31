# utils/frozen_table_helper.py
from PyQt5.QtWidgets import QTableWidget, QTableView, QHeaderView, QAbstractItemView, QFrame, QGraphicsDropShadowEffect
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt


class FrozenTableWidget(QTableWidget):

    def __init__(self, frozen_cols=2, fixed_cols=None, fixed_widths=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.frozen_cols = frozen_cols
        self.fixed_cols = fixed_cols or []
        self.fixed_widths = fixed_widths or {}

        # Tabel bayangan untuk freeze column
        self.frozen_table = QTableView(self)
        self.frozen_table.setFrameShape(QFrame.NoFrame)
        self.frozen_table.setModel(self.model())
        self.frozen_table.setSelectionModel(self.selectionModel())
        self.frozen_table.setFocusPolicy(Qt.NoFocus)
        self.frozen_table.verticalHeader().hide()

        # Mode header interaktif secara umum
        self.frozen_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        self.viewport().stackUnder(self.frozen_table)

        # Efek Drop Shadow Dinamis
        self.shadow_effect = QGraphicsDropShadowEffect(self)
        self.shadow_effect.setBlurRadius(15)
        self.shadow_effect.setXOffset(5)
        self.shadow_effect.setYOffset(0)
        self.shadow_effect.setColor(QColor(0, 0, 0, 60))
        self.shadow_effect.setEnabled(False)
        self.frozen_table.setGraphicsEffect(self.shadow_effect)

        self.horizontalScrollBar().valueChanged.connect(self.update_shadow)

        # Scrolling Vertikal Presisi 1:1 (ScrollPerPixel)
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.frozen_table.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalHeader().sectionResized.connect(self.frozen_table.verticalHeader().resizeSection)
        self.frozen_table.verticalHeader().sectionResized.connect(self.verticalHeader().resizeSection)

        self.verticalScrollBar().valueChanged.connect(self.frozen_table.verticalScrollBar().setValue)
        self.frozen_table.verticalScrollBar().valueChanged.connect(self.verticalScrollBar().setValue)

        # Sinkronisasi batas bawah scroll
        self.verticalScrollBar().rangeChanged.connect(
            lambda min_v, max_v: self.frozen_table.verticalScrollBar().setRange(min_v, max_v)
        )

        self.frozen_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.frozen_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.frozen_table.show()

        # Sinkronisasi 2 arah lebar kolom
        self.horizontalHeader().sectionResized.connect(self.update_section_width)
        self.frozen_table.horizontalHeader().sectionResized.connect(self.update_main_section_width)

        self.frozen_table.setAlternatingRowColors(True)

        # Context Menu (Klik Kanan)
        self.frozen_table.horizontalHeader().setContextMenuPolicy(Qt.CustomContextMenu)
        self.frozen_table.horizontalHeader().customContextMenuRequested.connect(
            self.horizontalHeader().customContextMenuRequested.emit
        )
        self.frozen_table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.frozen_table.customContextMenuRequested.connect(
            self.customContextMenuRequested.emit
        )

    def update_shadow(self, value):
        if value > 0:
            self.shadow_effect.setEnabled(True)
        else:
            self.shadow_effect.setEnabled(False)

    def update_section_width(self, logicalIndex, oldSize, newSize):
        if logicalIndex < self.frozen_cols:
            self.frozen_table.blockSignals(True)
            self.frozen_table.setColumnWidth(logicalIndex, newSize)
            self.frozen_table.blockSignals(False)
            self.update_frozen_geometry()

    def update_main_section_width(self, logicalIndex, oldSize, newSize):
        if logicalIndex < self.frozen_cols:
            self.blockSignals(True)
            self.setColumnWidth(logicalIndex, newSize)
            self.blockSignals(False)
            self.update_frozen_geometry()

    def update_frozen_geometry(self):
        total_w = sum(
            self.columnWidth(col)
            for col in range(self.frozen_cols)
            if not self.isColumnHidden(col)
        )

        self.frozen_table.setGeometry(
            self.verticalHeader().width() + self.frameWidth(),
            self.frameWidth(),
            total_w,
            self.viewport().height() + self.horizontalHeader().height()
        )

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_frozen_geometry()

    def scrollTo(self, index, hint=QAbstractItemView.EnsureVisible):
        if index.column() >= self.frozen_cols:
            super().scrollTo(index, hint)

    def setColumnCount(self, count):
        super().setColumnCount(count)
        # Sembunyikan kolom setelah batas frozen_cols pada tabel bayangan
        for col in range(self.frozen_cols, count):
            self.frozen_table.setColumnHidden(col, True)

        # Terapkan penguncian kolom fixed jika dikonfigurasi
        if count > 0:
            for col in self.fixed_cols:
                if col < count:
                    self.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
                    self.frozen_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.Fixed)
                    if col in self.fixed_widths:
                        w = self.fixed_widths[col]
                        self.setColumnWidth(col, w)
                        self.frozen_table.setColumnWidth(col, w)

    def setColumnWidth(self, column, width):
        super().setColumnWidth(column, width)
        if column < self.frozen_cols:
            self.frozen_table.setColumnWidth(column, width)
            self.update_frozen_geometry()

    def setRowHidden(self, row, hide):
        super().setRowHidden(row, hide)
        self.frozen_table.setRowHidden(row, hide)

    def setStyleSheet(self, styleSheet):
        super().setStyleSheet(styleSheet)
        style_tabel_bayangan = styleSheet.replace("QTableWidget", "QTableView")

        css_center_checkbox = """
            QTableWidget::indicator, QTableView::indicator {
                subcontrol-origin: padding;
                subcontrol-position: center;
            }
        """

        self.frozen_table.setStyleSheet(style_tabel_bayangan + css_center_checkbox)
        self.frozen_table.setPalette(self.palette())
        self.frozen_table.setGridStyle(self.gridStyle())

        super().setStyleSheet(styleSheet + css_center_checkbox)

    def setSelectionMode(self, mode):
        super().setSelectionMode(mode)
        self.frozen_table.setSelectionMode(mode)

    def setSelectionBehavior(self, behavior):
        super().setSelectionBehavior(behavior)
        self.frozen_table.setSelectionBehavior(behavior)