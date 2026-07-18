# utils/date_ind_format.py
from contextlib import contextmanager
from typing import Any, Iterator
from PyQt5.QtWidgets import QLineEdit


@contextmanager
def _blokir_signal_sementara(widget: Any) -> Iterator[None]:
    """
    Memblokir signal widget untuk sementara saat memanipulasi teks
    agar tidak memicu infinite loop pada event textChanged.
    """
    status_sebelumnya = widget.blockSignals(True)
    try:
        yield
    finally:
        widget.blockSignals(status_sebelumnya)


def _ambil_digit(nilai: Any) -> str:
    """Mengambil karakter angka/digit saja dari sebuah string."""
    return "".join(karakter for karakter in str(nilai) if karakter.isdigit())


def format_input_tanggal(edit_widget: QLineEdit) -> None:
    """
    Slot untuk QLineEdit agar otomatis menambahkan garis miring (/)
    saat user mengetik angka. Format akhir: DD/MM/YYYY.
    """
    text = edit_widget.text()

    # Ambil digitnya saja dan batasi maksimal 8 angka (DDMMYYYY)
    angka_saja = _ambil_digit(text)[:8]

    if not angka_saja:
        with _blokir_signal_sementara(edit_widget):
            edit_widget.clear()
        return

    # Susun format DD/MM/YYYY
    text_baru = ""
    for i, char in enumerate(angka_saja):
        if i == 2 or i == 4:
            text_baru += "/"
        text_baru += char

    # Jika tidak ada perubahan wujud, hentikan proses
    if text == text_baru:
        return

    pos_lama = edit_widget.cursorPosition()
    panjang_lama = len(text)

    with _blokir_signal_sementara(edit_widget):
        edit_widget.setText(text_baru)
        panjang_baru = len(text_baru)

        # Kalkulasi penyesuaian kursor (saat garis miring otomatis bertambah/berkurang)
        pos_baru = pos_lama + (panjang_baru - panjang_lama)

        # Cegah kursor melompat aneh saat user menghapus garis miring (Backspace)
        if panjang_baru < panjang_lama and text.endswith('/'):
            pos_baru -= 1

        edit_widget.setCursorPosition(max(0, min(pos_baru, panjang_baru)))


def format_tanggal_ke_db(tgl_ui: str) -> str:
    """
    Konversi dari Layar ke Database.
    Mengubah format 'DD/MM/YYYY' menjadi 'YYYY-MM-DD' (Standar Supabase/SQL).
    """
    if not tgl_ui:
        return ""

    parts = str(tgl_ui).replace("-", "/").split("/")

    if len(parts) == 3:
        return f"{parts[2]}-{parts[1]}-{parts[0]}"

    return str(tgl_ui)


def format_tanggal_ke_ui(tgl_db: str) -> str:
    """
    Konversi dari Database ke Layar.
    Mengubah format 'YYYY-MM-DD' atau 'YYYY-MM-DD HH:MM:SS'
    menjadi 'DD/MM/YYYY' untuk ditampilkan di tabel/UI lokal.
    """
    if not tgl_db:
        return ""

    # Buang komponen jam/waktu jika ada
    parts = str(tgl_db).split(" ")[0].split("-")

    if len(parts) == 3:
        return f"{parts[2]}/{parts[1]}/{parts[0]}"

    return str(tgl_db)