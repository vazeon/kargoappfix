# utils/printer/print_resi.py
from __future__ import annotations

import html
import json
from typing import Any

from config import CURRENT_SESSION, DATA_CLIENT
from utils.number_formatters import (
    format_angka_indonesia,
    format_decimal_indonesia,
    format_ke_rupiah,
    jumlahkan_angka_dari_teks,
)
from utils.typography import get_master_font

from .common import (
    JENIS_RESI,
    JendelaPreviewCustom,
    buat_dokumen_html,
    buat_printer,
)


def _esc(value: Any) -> str:
    return html.escape(
        str(value if value is not None else "")
    )


def _teks_koli(nilai: Any) -> str:
    """Menampilkan KOLI sebagai teks bebas tanpa mengubah satuannya."""
    if nilai is None:
        return ""

    return str(nilai).strip().upper()


def _format_rupiah(
    nilai: Any,
    kosong_jika_nol: bool = True,
) -> str:
    hasil = format_ke_rupiah(nilai)

    if kosong_jika_nol and hasil in {
        "",
        "0",
        "-0",
    }:
        return ""

    return hasil


def _format_desimal(
    nilai: Any,
    kosong_jika_nol: bool = True,
) -> str:
    return format_angka_indonesia(
        nilai,
        maksimum_desimal=2,
        kosong_jika_nol=kosong_jika_nol,
        nilai_kosong="",
    )


def _ambil_rekening(
    tipe_pajak: str,
) -> list[str]:
    key = (
        "rekening_pajak"
        if tipe_pajak == "PAJAK"
        else "rekening_nonpajak"
    )

    rekening = DATA_CLIENT.get(key, [])

    if isinstance(rekening, str):
        try:
            rekening = json.loads(rekening)
        except (
            TypeError,
            ValueError,
            json.JSONDecodeError,
        ):
            rekening = []

    return (
        rekening
        if isinstance(rekening, list)
        else []
    )


def _buat_html_rekening(
    tipe_pajak: str,
) -> str:
    hasil = [
        "<strong>PEMBAYARAN :</strong><br>"
    ]

    for rekening in _ambil_rekening(
        tipe_pajak
    ):
        if not rekening:
            continue

        parts = [
            bagian.strip()
            for bagian in str(rekening).split(",")
        ]

        if len(parts) >= 3:
            hasil.append(
                f"<b>{_esc(parts[0])}</b> "
                f"{_esc(parts[1])}<br>"
                f"a.n. {_esc(parts[2])}<br><br>"
            )

        elif len(parts) == 2:
            hasil.append(
                f"<b>{_esc(parts[0])}</b><br>"
                f"a.n. {_esc(parts[1])}<br><br>"
            )

        else:
            hasil.append(
                f"<b>{_esc(rekening)}</b><br><br>"
            )

    return "".join(hasil)


def cetak_resi_ke_printer(
    data: dict,
    parent_window=None,
) -> None:
    """Membuat preview dan mencetak dokumen Resi."""
    printer = buat_printer(JENIS_RESI)

    comp_name = (
        DATA_CLIENT.get("nama_perusahaan")
        or ""
    )
    comp_address = (
        DATA_CLIENT.get("alamat")
        or ""
    )
    comp_phone = (
        DATA_CLIENT.get("telp")
        or ""
    )
    logo_text_html = (
        DATA_CLIENT.get("logo_text_html")
        or _esc(comp_name)
    )

    tipe_pajak = str(
        data.get("tipe_pajak", "NON-PAJAK")
    ).strip().upper()

    teks_rekening = _buat_html_rekening(
        tipe_pajak
    )

    list_barang = data.get(
        "list_barang",
        [],
    )

    if not isinstance(list_barang, list):
        list_barang = []

    baris_tabel: list[str] = []
    maksimum_baris = max(
        4,
        len(list_barang),
    )

    for index in range(maksimum_baris):
        nomor = index + 1

        if index < len(list_barang):
            barang = list_barang[index] or {}

            koli = _teks_koli(
                barang.get("qty", "")
            )
            berat = _format_desimal(
                barang.get("berat", "")
            )
            cbm = _format_desimal(
                barang.get("cbm", "")
            )

            baris_tabel.append(
                '<tr class="fixed-row">'
                f'<td align="center">{nomor}</td>'
                f"<td>{_esc(barang.get('nama', ''))}</td>"
                f'<td align="center">{_esc(koli)}</td>'
                f'<td align="center">{berat}</td>'
                f'<td align="center">{cbm}</td>'
                "</tr>"
            )

        else:
            baris_tabel.append(
                '<tr class="fixed-row">'
                f'<td align="center">{nomor}</td>'
                "<td></td><td></td><td></td><td></td>"
                "</tr>"
            )

    total_koli = jumlahkan_angka_dari_teks(
        barang.get("qty", "")
        for barang in list_barang
        if isinstance(barang, dict)
    )

    # Fallback untuk data lama yang hanya mengirim total_qty.
    if total_koli == 0:
        total_koli = jumlahkan_angka_dari_teks(
            [data.get("total_qty", "")]
        )

    total_koli_cetak = (
        format_decimal_indonesia(total_koli)
        if total_koli != 0
        else "-"
    )

    total_berat = _format_desimal(
        data.get("total_berat", "")
    ) or "-"

    total_cbm = _format_desimal(
        data.get("total_cbm", "")
    ) or "-"

    tarif_kg = (
        data.get("tarif_kg_raw", "")
        or data.get("tarif_kg", "")
    )
    tarif_m3 = (
        data.get("tarif_m3_raw", "")
        or data.get("tarif_m3", "")
    )

    teks_tarif_satuan = ""
    tarif_kg_cetak = _format_rupiah(tarif_kg)
    tarif_m3_cetak = _format_rupiah(tarif_m3)

    if tarif_kg_cetak:
        teks_tarif_satuan = (
            '<div class="tarif-satuan">'
            f"Tarif: Rp {tarif_kg_cetak} / Kg"
            "</div>"
        )

    elif tarif_m3_cetak:
        teks_tarif_satuan = (
            '<div class="tarif-satuan">'
            f"Tarif: Rp {tarif_m3_cetak} / M3"
            "</div>"
        )

    total_ongkir = _format_rupiah(
        data.get(
            "total_jumlah_ongkir",
            "",
        )
    )

    if total_ongkir:
        html_kolom_tagihan = f"""
        <td width="25%" class="tagihan-box">
            <strong>TOTAL TAGIHAN</strong><br><br>
            <span class="total-tagihan">
                Rp. {total_ongkir}
            </span>
            {teks_tarif_satuan}
        </td>
        """

    elif teks_tarif_satuan:
        html_kolom_tagihan = f"""
        <td width="25%" class="tagihan-box">
            {teks_tarif_satuan}
        </td>
        """

    else:
        html_kolom_tagihan = (
            '<td width="25%" '
            'style="vertical-align: top;"></td>'
        )

    kota_db = str(
        data.get("penerima_kota", "")
        or ""
    ).strip()

    if (
        not kota_db
        or kota_db.lower() == "none"
    ):
        kota_db = str(
            data.get("kota_tujuan", "")
            or ""
        ).strip()

    if (
        kota_db
        and kota_db.lower() != "none"
        and kota_db != "-"
    ):
        kota_penerima = (
            kota_db.split(" - ")[-1].strip()
        )
        str_kota = (
            "<br>KOTA: "
            f"<strong>{_esc(kota_penerima.upper())}</strong>"
        )
    else:
        str_kota = ""

    nama_admin = str(
        CURRENT_SESSION.get("username")
        or "ADMIN"
    ).strip().upper()

    if not nama_admin:
        nama_admin = "..................."

    font_dokumen = get_master_font()

    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                width: 100%;
                font-family: "{font_dokumen}";
                font-size: 9pt;
                color: #000000;
            }}
            .header-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 5px;
            }}
            .logo-text {{
                font-size: 16pt;
                font-weight: bold;
                color: #0d47a1;
                white-space: nowrap;
            }}
            .comp-details {{
                font-size: 8pt;
                line-height: 1.2;
                white-space: nowrap;
            }}
            .box-resi {{
                border: 1px solid #000000;
                border-collapse: collapse;
                text-align: center;
            }}
            .box-resi th {{
                border: 1px solid #000000;
                padding: 3px;
                font-size: 8pt;
                font-weight: bold;
                background-color: #ffffff;
                white-space: nowrap;
            }}
            .box-resi td {{
                border: 1px solid #000000;
                padding: 3px;
                font-weight: bold;
                font-size: 10pt;
                letter-spacing: 0.5px;
                white-space: nowrap;
            }}
            .info-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 6px;
            }}
            .info-title {{
                font-weight: bold;
                font-size: 8.5pt;
                margin-bottom: 2px;
            }}
            .barang-table {{
                width: 100%;
                border-collapse: collapse;
                margin-bottom: 6px;
            }}
            .barang-table th {{
                border: 1px solid #000000;
                padding: 4px;
                font-size: 8pt;
                font-weight: bold;
                text-align: center;
                background-color: #ffffff;
                white-space: nowrap;
            }}
            .barang-table td {{
                border-left: 1px solid #000000;
                border-right: 1px solid #000000;
                border-top: none;
                border-bottom: none;
                padding: 4px;
                font-size: 9pt;
            }}
            .barang-table .fixed-row td {{
                height: 16px;
            }}
            .barang-table .total-row td {{
                border: 1px solid #000000;
                font-weight: bold;
                background-color: #ffffff;
            }}
            .footer-table {{
                width: 100%;
                border-collapse: collapse;
            }}
            .ttd-cell {{
                text-align: center;
                vertical-align: top;
                font-size: 8.5pt;
                white-space: nowrap;
                padding-top: 5px;
            }}
            .tagihan-box {{
                vertical-align: top;
                padding-left: 15px;
                padding-top: 5px;
                font-size: 8.5pt;
                border-left: 1px dashed #cccccc;
            }}
            .pembayaran-box {{
                vertical-align: top;
                font-size: 8.5pt;
                line-height: 1.3;
                padding-left: 15px;
                padding-top: 5px;
                white-space: nowrap;
            }}
            .total-tagihan {{
                font-size: 13pt;
                font-weight: bold;
                color: #000000;
                display: block;
                margin-top: 2px;
            }}
            .tarif-satuan {{
                font-size: 8.5pt;
                color: #475569;
                margin-top: 5px;
                font-weight: normal;
                font-style: italic;
            }}
        </style>
    </head>
    <body>
        <table class="header-table">
            <tr>
                <td width="35%" valign="middle"
                    style="white-space: nowrap;">
                    <span class="logo-text">
                        {logo_text_html}
                    </span>
                </td>
                <td width="40%" class="comp-details"
                    valign="middle">
                    <strong>{_esc(comp_name)}</strong><br>
                    📍 {_esc(comp_address)}<br>
                    📞 {_esc(comp_phone)}
                </td>
                <td width="25%" valign="middle">
                    <table class="box-resi" width="100%">
                        <tr>
                            <th align="center">TGL.</th>
                            <th align="center">NO. RESI</th>
                        </tr>
                        <tr>
                            <td align="center">
                                {_esc(data.get('tanggal', ''))}
                            </td>
                            <td align="center">
                                {_esc(data.get('no_resi', ''))}
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>

        <table class="info-table">
            <tr>
                <td width="50%" valign="top"
                    style="padding-right: 10px;">
                    <div class="info-title">PENGIRIM :</div>
                    <strong>
                        {_esc(data.get('pengirim_nama', ''))}
                    </strong><br>
                    {_esc(data.get('pengirim_telp', ''))}<br>
                    {_esc(data.get('pengirim_alamat', ''))}
                </td>
                <td width="50%" valign="top"
                    style="padding-left: 10px;">
                    <div class="info-title">PENERIMA :</div>
                    <strong>
                        {_esc(data.get('penerima_nama', ''))}
                    </strong><br>
                    {_esc(data.get('penerima_telp', ''))}<br>
                    {_esc(data.get('penerima_alamat', ''))}
                    {str_kota}
                </td>
            </tr>
        </table>

        <table class="barang-table">
            <thead>
                <tr>
                    <th width="5%">NO</th>
                    <th width="55%">DESKRIPSI BARANG</th>
                    <th width="10%">KOLI</th>
                    <th width="15%">BERAT (KG)</th>
                    <th width="15%">KUBIKASI (M3)</th>
                </tr>
            </thead>
            <tbody>
                {''.join(baris_tabel)}
                <tr class="total-row">
                    <td colspan="2"
                        style="padding: 0; border: 1px solid #000000;">
                        <table width="100%" cellpadding="0"
                            cellspacing="0" style="border: none;">
                            <tr>
                                <td align="left"
                                    style="border: none; font-size: 7pt;
                                    font-weight: normal; font-style: italic;
                                    padding-left: 5px;">
                                    NOTE: ISI PAKET TIDAK DIPERIKSA
                                </td>
                                <td align="right"
                                    style="border: none; font-weight: bold;
                                    padding-right: 10px;">
                                    TOTAL :
                                </td>
                            </tr>
                        </table>
                    </td>
                    <td align="center">
                        {total_koli_cetak}
                    </td>
                    <td align="center">
                        {total_berat}
                    </td>
                    <td align="center">
                        {total_cbm}
                    </td>
                </tr>
            </tbody>
        </table>

        <table class="footer-table">
            <tr>
                <td width="15%" class="ttd-cell">
                    <strong>ADMIN</strong><br><br><br><br><br>
                    ( <b>{_esc(nama_admin)}</b> )
                </td>
                <td width="15%" class="ttd-cell">
                    <strong>DRIVER</strong><br><br><br><br><br>
                    ( ................... )
                </td>
                <td width="15%" class="ttd-cell">
                    <strong>PENERIMA</strong><br><br><br><br><br>
                    ( ................... )
                </td>
                {html_kolom_tagihan}
                <td width="30%" class="pembayaran-box">
                    {teks_rekening}
                </td>
            </tr>
        </table>
    </body>
    </html>
    """

    document = buat_dokumen_html(
        html_content,
        printer,
        margin=0,
    )

    preview = JendelaPreviewCustom(
        printer,
        document,
        parent_window,
        jenis_dokumen=JENIS_RESI,
        nomor_dokumen=str(
            data.get("no_resi", "")
            or ""
        ),
    )
    preview.exec_()