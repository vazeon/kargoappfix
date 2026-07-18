from __future__ import annotations

from typing import Optional

from PyQt5.QtGui import QFont
from PyQt5.QtPrintSupport import QPrinter
from PyQt5.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from utils.typography import get_master_font

from .common import (
    JENIS_INVOICE,
    buat_dokumen_html,
    konfigurasi_printer,
    pastikan_ekstensi,
)


def simpan_html_ke_pdf(
    html_content: str,
    output_path: str,
) -> str:
    """Menyimpan HTML Invoice langsung ke file PDF."""
    output_path = pastikan_ekstensi(
        output_path,
        ".pdf",
    )

    if not output_path:
        raise ValueError(
            "Lokasi penyimpanan PDF tidak valid."
        )

    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(output_path)

    konfigurasi_printer(
        printer,
        JENIS_INVOICE,
    )

    document = buat_dokumen_html(
        html_content,
        printer,
        margin=0,
    )
    document.print_(printer)

    return output_path


def simpan_invoice_pdf(
    html_content: str,
    suggested_name: str,
    parent: Optional[QWidget] = None,
) -> Optional[str]:
    """Memilih lokasi penyimpanan lalu mengekspor Invoice ke PDF."""
    nama_file = str(
        suggested_name or "invoice_draft"
    ).strip() or "invoice_draft"

    nama_file = pastikan_ekstensi(
        nama_file,
        ".pdf",
    )

    output_path, _ = QFileDialog.getSaveFileName(
        parent,
        "Simpan Invoice PDF",
        nama_file,
        "PDF Files (*.pdf)",
    )

    if not output_path:
        return None

    try:
        hasil_path = simpan_html_ke_pdf(
            html_content,
            output_path,
        )

        QMessageBox.information(
            parent,
            "PDF Berhasil",
            (
                "Invoice berhasil disimpan:\n"
                f"{hasil_path}"
            ),
        )
        return hasil_path

    except Exception as exc:
        QMessageBox.critical(
            parent,
            "Gagal Membuat PDF",
            str(exc),
        )
        return None


class InvoicePreviewDialog(QDialog):
    """Dialog preview HTML Invoice dengan tombol simpan PDF."""

    def __init__(
        self,
        html_content: str,
        suggested_name: str,
        parent: Optional[QWidget] = None,
    ):
        super().__init__(parent)

        self.html_content = str(
            html_content or ""
        )
        self.suggested_name = str(
            suggested_name or "invoice_draft"
        ).strip() or "invoice_draft"

        self.setWindowTitle("Preview Invoice")
        self.resize(960, 760)
        self.setStyleSheet(
            f'font-family: "{get_master_font()}";'
        )

        layout = QVBoxLayout(self)

        self.browser = QTextBrowser(self)
        self.browser.document().setDefaultFont(
            QFont(get_master_font())
        )
        self.browser.setHtml(self.html_content)
        layout.addWidget(self.browser)

        actions = QHBoxLayout()
        actions.addStretch()

        self.btn_simpan_pdf = QPushButton(
            "Simpan PDF",
            self,
        )
        self.btn_tutup = QPushButton(
            "Tutup",
            self,
        )

        actions.addWidget(self.btn_simpan_pdf)
        actions.addWidget(self.btn_tutup)
        layout.addLayout(actions)

        self.btn_simpan_pdf.clicked.connect(
            self.simpan_pdf
        )
        self.btn_tutup.clicked.connect(
            self.accept
        )

    def simpan_pdf(self) -> None:
        simpan_invoice_pdf(
            html_content=self.html_content,
            suggested_name=self.suggested_name,
            parent=self,
        )


def tampilkan_preview_invoice(
    html_content: str,
    suggested_name: str,
    parent: Optional[QWidget] = None,
) -> None:
    """Menampilkan preview Invoice secara modal."""
    dialog = InvoicePreviewDialog(
        html_content=html_content,
        suggested_name=suggested_name,
        parent=parent,
    )
    dialog.exec_()