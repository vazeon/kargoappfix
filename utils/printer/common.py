# utils/printer/common.py
"""Komponen bersama untuk preview, cetak, dan ekspor dokumen."""

from __future__ import annotations

import urllib.parse
import webbrowser
from typing import Optional

from PyQt5.QtCore import QSizeF, Qt
from PyQt5.QtGui import QFont, QImage, QPageSize, QPainter, QTextDocument
from PyQt5.QtPrintSupport import (
    QPrintDialog,
    QPrinter,
    QPrinterInfo,
    QPrintPreviewWidget,
)
from PyQt5.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMenu,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config import DATA_CLIENT
from utils.typography import get_master_font


JENIS_RESI = "resi"
JENIS_MANIFEST = "manifest"
JENIS_INVOICE = "invoice"


def pastikan_ekstensi(path: str, ekstensi: str) -> str:
    """Memastikan path mempunyai ekstensi yang diminta."""
    path = str(path or "").strip()
    ekstensi = str(ekstensi or "").strip()

    if not path:
        return ""

    if ekstensi and not ekstensi.startswith("."):
        ekstensi = f".{ekstensi}"

    if ekstensi and not path.lower().endswith(ekstensi.lower()):
        path += ekstensi

    return path


def konfigurasi_printer(
    printer: QPrinter,
    jenis_dokumen: str,
    tipe_kertas: str = "A4",
) -> None:
    """Menerapkan ukuran kertas, orientasi, dan margin dokumen."""
    jenis = str(jenis_dokumen or JENIS_RESI).strip().lower()
    tipe = str(tipe_kertas or "A4").strip().upper()

    if jenis == JENIS_INVOICE:
        printer.setPageSize(QPageSize(QPageSize.A4))
        printer.setOrientation(QPrinter.Portrait)
        printer.setPageMargins(8, 8, 8, 8, QPrinter.Millimeter)
        return

    if jenis == JENIS_MANIFEST:
        page_size = (
            QPageSize(QPageSize.A5)
            if tipe == "NCR"
            else QPageSize(QPageSize.A4)
        )
        printer.setPageSize(page_size)
        printer.setOrientation(QPrinter.Landscape)
        printer.setPageMargins(2, 2, 2, 2, QPrinter.Millimeter)
        return

    # Nota/resi NCR ukuran 5,5 x 9,5 inci.
    ncr_size = QPageSize(
        QSizeF(139.7, 241.3),
        QPageSize.Millimeter,
    )
    printer.setPageSize(ncr_size)
    printer.setOrientation(QPrinter.Landscape)
    printer.setPageMargins(2, 2, 2, 2, QPrinter.Millimeter)


def buat_printer(
    jenis_dokumen: str,
    tipe_kertas: str = "A4",
    resolusi: int = 96,
) -> QPrinter:
    """Membuat objek QPrinter yang siap digunakan."""
    printer = QPrinter()
    printer.setResolution(int(resolusi))
    konfigurasi_printer(
        printer,
        jenis_dokumen,
        tipe_kertas,
    )
    return printer


def buat_dokumen_html(
    html_content: str,
    printer: QPrinter,
    margin: float = 0,
) -> QTextDocument:
    """Membuat QTextDocument dari HTML dengan font aplikasi."""
    document = QTextDocument()
    document.setDefaultFont(QFont(get_master_font()))
    document.setDocumentMargin(float(margin))

    if printer.orientation() == QPrinter.Landscape:
        lebar = max(printer.width(), printer.height())
        tinggi = min(printer.width(), printer.height())
    else:
        lebar = min(printer.width(), printer.height())
        tinggi = max(printer.width(), printer.height())

    document.setPageSize(QSizeF(lebar, tinggi))
    document.setHtml(str(html_content or ""))
    return document


class JendelaPreviewCustom(QDialog):
    """Preview bersama untuk Resi dan Manifest."""

    def __init__(
        self,
        printer: QPrinter,
        doc: QTextDocument,
        parent: Optional[QWidget] = None,
        jenis_dokumen: str = JENIS_RESI,
        tipe_kertas: str = "A4",
        nomor_dokumen: str = "",
    ):
        super().__init__(parent)

        self.printer_terikat = printer
        self.doc_terikat = doc
        self.jenis_dokumen = str(
            jenis_dokumen or JENIS_RESI
        ).strip().lower()
        self.tipe_kertas = str(
            tipe_kertas or "A4"
        ).strip().upper()
        self.nomor_dokumen = str(
            nomor_dokumen or ""
        ).strip()

        # Alias untuk kompatibilitas dengan kode lama.
        self.no_resi = self.nomor_dokumen

        nama_perusahaan = str(
            DATA_CLIENT.get(
                "nama_perusahaan",
                "EKSPEDISI",
            )
            or "EKSPEDISI"
        ).upper()

        self.setWindowTitle(
            f"Print Preview - {nama_perusahaan}"
        )
        self.setWindowFlags(
            self.windowFlags()
            | Qt.WindowMinMaxButtonsHint
        )
        self.resize(1050, 650)

        font_aktif = get_master_font()
        self.setStyleSheet(
            f'QDialog {{ background-color: #f8fafc; '
            f'font-family: "{font_aktif}"; }}'
        )

        layout_utama = QVBoxLayout(self)
        layout_utama.setContentsMargins(
            15,
            15,
            15,
            15,
        )
        layout_utama.setSpacing(10)

        toolbar_layout = QHBoxLayout()

        lbl_info = QLabel("✨ PREVIEW DOKUMEN")
        lbl_info.setStyleSheet(
            "font-weight: bold; color: #334155; "
            "font-size: 11pt; margin-right: 10px;"
        )
        toolbar_layout.addWidget(lbl_info)

        lbl_printer = QLabel("Printer:")
        lbl_printer.setStyleSheet(
            "font-weight: bold; font-size: 10pt; "
            "color: #1e293b;"
        )
        toolbar_layout.addWidget(lbl_printer)

        self.cb_printers = QComboBox()
        self.cb_printers.setStyleSheet(
            "QComboBox { border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 4px 10px; "
            "background-color: white; color: #0f172a; "
            "font-size: 10pt; min-width: 220px; }"
        )

        printer_names = QPrinterInfo.availablePrinterNames()
        self.cb_printers.addItems(printer_names)

        default_printer = QPrinterInfo.defaultPrinterName()
        if default_printer in printer_names:
            self.cb_printers.setCurrentText(
                default_printer
            )

        self.cb_printers.currentTextChanged.connect(
            self.ubah_printer
        )
        toolbar_layout.addWidget(self.cb_printers)

        self.btn_setting = QPushButton("⚙️")
        self.btn_setting.setCursor(Qt.PointingHandCursor)
        self.btn_setting.setStyleSheet(
            "QPushButton { border: 1px solid #cbd5e1; "
            "border-radius: 4px; padding: 4px 8px; "
            "background-color: white; color: #0f172a; "
            "font-size: 12pt; } "
            "QPushButton:hover { background-color: #e2e8f0; }"
        )
        self.btn_setting.clicked.connect(
            self.buka_dialog_setting_printer
        )
        toolbar_layout.addWidget(self.btn_setting)
        toolbar_layout.addStretch()

        self.btn_simpan_bagikan = QPushButton(
            "💾 SIMPAN / BAGIKAN  ▼"
        )
        self.btn_simpan_bagikan.setCursor(
            Qt.PointingHandCursor
        )
        self.btn_simpan_bagikan.setStyleSheet(
            """
            QPushButton {
                background-color: #475569;
                color: white;
                font-weight: bold;
                font-size: 10pt;
                padding: 8px 18px;
                border-radius: 5px;
                border: none;
            }
            QPushButton:hover {
                background-color: #334155;
            }
            QPushButton::menu-indicator {
                image: none;
            }
            """
        )

        self.menu_aksi = QMenu(self)
        self.menu_aksi.setStyleSheet(
            """
            QMenu {
                background-color: white;
                border: 1px solid #cbd5e1;
                border-radius: 6px;
                padding: 4px 0;
                color: #1e293b;
            }
            QMenu::item {
                padding: 8px 24px;
                font-size: 10pt;
            }
            QMenu::item:selected {
                background-color: #f1f5f9;
                color: #000000;
            }
            """
        )

        action_pdf = self.menu_aksi.addAction(
            "📄  Simpan Dokumen PDF"
        )
        action_gambar = self.menu_aksi.addAction(
            "🖼️  Simpan File Gambar"
        )
        action_wa = self.menu_aksi.addAction(
            "🟢  Bagikan ke WhatsApp"
        )

        action_pdf.triggered.connect(
            self.aksi_simpan_pdf
        )
        action_gambar.triggered.connect(
            self.aksi_simpan_gambar
        )
        action_wa.triggered.connect(
            self.aksi_share_whatsapp
        )

        self.btn_simpan_bagikan.setMenu(
            self.menu_aksi
        )

        self.btn_cetak_sekarang = QPushButton(
            "⚡ CETAK LANGSUNG"
        )
        self.btn_cetak_sekarang.setCursor(
            Qt.PointingHandCursor
        )
        self.btn_cetak_sekarang.setStyleSheet(
            "QPushButton { background-color: #2563eb; "
            "color: white; font-weight: bold; "
            "font-size: 10pt; padding: 8px 25px; "
            "border-radius: 5px; border: none; } "
            "QPushButton:hover { background-color: #1d4ed8; }"
        )

        toolbar_layout.addWidget(
            self.btn_simpan_bagikan
        )
        toolbar_layout.addWidget(
            self.btn_cetak_sekarang
        )
        layout_utama.addLayout(toolbar_layout)

        self.widget_preview = QPrintPreviewWidget(
            self.printer_terikat,
            self,
        )

        if (
            self.printer_terikat.orientation()
            == QPrinter.Landscape
        ):
            self.widget_preview.setLandscapeOrientation()
        else:
            self.widget_preview.setPortraitOrientation()

        self.widget_preview.paintRequested.connect(
            self.proses_menggambar_dokumen
        )
        self.widget_preview.setZoomMode(
            QPrintPreviewWidget.FitToWidth
        )
        self.widget_preview.setStyleSheet(
            "border: 1px solid #cbd5e1; "
            "background-color: #e2e8f0; "
            "border-radius: 6px;"
        )
        layout_utama.addWidget(self.widget_preview)

        self.btn_cetak_sekarang.clicked.connect(
            self.aksi_cetak_fisik
        )

        if self.cb_printers.currentText():
            self.ubah_printer(
                self.cb_printers.currentText()
            )

    def set_identitas_dokumen(
        self,
        nomor_dokumen: str,
        jenis_dokumen: Optional[str] = None,
        tipe_kertas: Optional[str] = None,
    ) -> None:
        self.nomor_dokumen = str(
            nomor_dokumen or ""
        ).strip()
        self.no_resi = self.nomor_dokumen

        if jenis_dokumen:
            self.jenis_dokumen = str(
                jenis_dokumen
            ).strip().lower()

        if tipe_kertas:
            self.tipe_kertas = str(
                tipe_kertas
            ).strip().upper()

    def set_nama_resi_export(
        self,
        no_resi: str,
    ) -> None:
        """Kompatibilitas dengan pemanggilan versi lama."""
        self.set_identitas_dokumen(no_resi)

    def ubah_printer(
        self,
        nama_printer: str,
    ) -> None:
        if nama_printer:
            self.printer_terikat.setPrinterName(
                nama_printer
            )

        konfigurasi_printer(
            self.printer_terikat,
            self.jenis_dokumen,
            self.tipe_kertas,
        )
        self.widget_preview.updatePreview()

    def buka_dialog_setting_printer(self) -> None:
        dialog = QPrintDialog(
            self.printer_terikat,
            self,
        )

        if dialog.exec_() == QPrintDialog.Accepted:
            self.doc_terikat.setPageSize(
                QSizeF(
                    self.printer_terikat.width(),
                    self.printer_terikat.height(),
                )
            )
            self.widget_preview.updatePreview()

    def proses_menggambar_dokumen(
        self,
        printer_target: QPrinter,
    ) -> None:
        konfigurasi_printer(
            printer_target,
            self.jenis_dokumen,
            self.tipe_kertas,
        )
        self.doc_terikat.print_(printer_target)

    def proses_menggambar_nota(
        self,
        printer_target: QPrinter,
    ) -> None:
        """Nama lama yang tetap dipertahankan."""
        self.proses_menggambar_dokumen(
            printer_target
        )

    def aksi_cetak_fisik(self) -> None:
        konfigurasi_printer(
            self.printer_terikat,
            self.jenis_dokumen,
            self.tipe_kertas,
        )
        self.doc_terikat.print_(
            self.printer_terikat
        )

    def _prefix_nama_file(self) -> str:
        if self.jenis_dokumen == JENIS_MANIFEST:
            return "Manifest"

        if self.jenis_dokumen == JENIS_INVOICE:
            return "Invoice"

        return "Nota"

    def aksi_simpan_pdf(self) -> None:
        prefix = self._prefix_nama_file()
        default_name = (
            f"{prefix}_{self.nomor_dokumen}.pdf"
            if self.nomor_dokumen
            else f"{prefix}.pdf"
        )

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Simpan sebagai PDF",
            default_name,
            "PDF Files (*.pdf)",
        )

        if not file_path:
            return

        file_path = pastikan_ekstensi(
            file_path,
            ".pdf",
        )

        try:
            pdf_printer = QPrinter(
                QPrinter.HighResolution
            )
            pdf_printer.setOutputFormat(
                QPrinter.PdfFormat
            )
            pdf_printer.setOutputFileName(
                file_path
            )
            konfigurasi_printer(
                pdf_printer,
                self.jenis_dokumen,
                self.tipe_kertas,
            )
            self.doc_terikat.print_(pdf_printer)

            QMessageBox.information(
                self,
                "Sukses",
                (
                    "File PDF berhasil disimpan di:\n"
                    f"{file_path}"
                ),
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Gagal Menyimpan PDF",
                str(exc),
            )

    def aksi_simpan_gambar(self) -> None:
        prefix = self._prefix_nama_file()
        default_name = (
            f"{prefix}_{self.nomor_dokumen}.png"
            if self.nomor_dokumen
            else f"{prefix}.png"
        )

        file_path, selected_filter = (
            QFileDialog.getSaveFileName(
                self,
                "Simpan sebagai Gambar",
                default_name,
                (
                    "PNG Image (*.png);;"
                    "JPEG Image (*.jpg *.jpeg)"
                ),
            )
        )

        if not file_path:
            return

        if "JPEG" in selected_filter:
            if not file_path.lower().endswith(
                (".jpg", ".jpeg")
            ):
                file_path += ".jpg"
        else:
            file_path = pastikan_ekstensi(
                file_path,
                ".png",
            )

        try:
            ukuran = self.doc_terikat.size().toSize()
            lebar = max(1, ukuran.width())
            tinggi = max(1, ukuran.height())

            gambar = QImage(
                lebar,
                tinggi,
                QImage.Format_ARGB32,
            )
            gambar.fill(Qt.white)

            painter = QPainter(gambar)
            self.doc_terikat.drawContents(painter)
            painter.end()

            if not gambar.save(file_path):
                raise RuntimeError(
                    "Gambar tidak dapat disimpan "
                    "pada lokasi tersebut."
                )

            QMessageBox.information(
                self,
                "Sukses",
                (
                    "Gambar berhasil disimpan di:\n"
                    f"{file_path}"
                ),
            )

        except Exception as exc:
            QMessageBox.critical(
                self,
                "Gagal Menyimpan Gambar",
                str(exc),
            )

    def aksi_share_whatsapp(self) -> None:
        if not self.nomor_dokumen:
            QMessageBox.warning(
                self,
                "Peringatan",
                (
                    "Nomor transaksi tidak valid "
                    "atau tidak ditemukan!"
                ),
            )
            return

        nama_perusahaan = str(
            DATA_CLIENT.get(
                "nama_perusahaan",
                "EKSPEDISI",
            )
            or "EKSPEDISI"
        ).upper()

        if self.jenis_dokumen == JENIS_MANIFEST:
            text_template = (
                "Halo, berikut diinformasikan nomor "
                "Surat Jalan Manifest pengiriman armada "
                f"dari *{nama_perusahaan}*:\n\n"
                f"📋 *No. Manifest:* {self.nomor_dokumen}\n\n"
                "Mohon armada yang bersangkutan segera "
                "melakukan pengecekan muatan gudang. "
                "Terima kasih."
            )

        elif self.jenis_dokumen == JENIS_INVOICE:
            text_template = (
                f"Halo, berikut invoice dari "
                f"*{nama_perusahaan}*:\n\n"
                f"🧾 *No. Invoice:* {self.nomor_dokumen}\n\n"
                "Silakan menghubungi admin apabila "
                "membutuhkan informasi lebih lanjut."
            )

        else:
            text_template = (
                "Halo, terima kasih telah memercayakan "
                f"pengiriman Anda kepada *{nama_perusahaan}*.\n\n"
                "Berikut nomor resi bukti pengiriman Anda:\n"
                f"📦 *No. Resi:* {self.nomor_dokumen}\n\n"
                "Status pengiriman dapat ditanyakan kepada "
                "admin cabang kami. Terima kasih."
            )

        text_encoded = urllib.parse.quote(
            text_template
        )
        webbrowser.open(
            "https://api.whatsapp.com/send?text="
            f"{text_encoded}"
        )