# utils/printer/print_manifest.py
from __future__ import annotations

import html
from decimal import Decimal
from typing import Any, Iterable

from config import DATA_CLIENT
from utils.number_formatters import (
    angka_indonesia_to_decimal,
    format_angka_indonesia,
    format_decimal_indonesia,
    jumlahkan_angka_dari_teks,
)
from utils.typography import get_master_font

from .common import (
    JENIS_MANIFEST,
    JendelaPreviewCustom,
    buat_dokumen_html,
    buat_printer,
)


_KUNCI_ITEM = (
    "no_resi",
    "pengirim",
    "penerima",
    "kota_tujuan",
    "nama_barang",
    "koli",
    "berat",
    "cbm",
)


def _esc(value: Any) -> str:
    return html.escape(
        str(value if value is not None else "")
    )


def _nilai_row(
    row: Iterable[Any],
    index: int,
    default: Any = "",
) -> Any:
    if isinstance(row, dict):
        try:
            return row.get(
                _KUNCI_ITEM[index],
                default,
            )
        except IndexError:
            return default

    try:
        return row[index]
    except (
        IndexError,
        KeyError,
        TypeError,
    ):
        return default


def _teks_koli(nilai: Any) -> str:
    """Menampilkan nilai KOLI sebagai teks bebas."""
    if nilai is None:
        return ""
    return str(nilai).strip().upper()


def _format_desimal(
    nilai: Any,
    maksimum_desimal: int = 2,
) -> str:
    return format_angka_indonesia(
        nilai,
        maksimum_desimal=maksimum_desimal,
        kosong_jika_nol=True,
        nilai_kosong="-",
    )


def cetak_manifest_ke_printer(
    data: dict,
    parent_window=None,
    tipe_kertas: str = "A4",
) -> None:
    """Membuat preview dan mencetak dokumen Manifest."""
    if not isinstance(data, dict):
        raise TypeError(
            "Data manifest harus berupa dictionary."
        )

    tipe_kertas = str(
        tipe_kertas or "A4"
    ).strip().upper()
    tipe_kertas = (
        "NCR"
        if tipe_kertas == "NCR"
        else "A4"
    )

    printer = buat_printer(
        JENIS_MANIFEST,
        tipe_kertas=tipe_kertas,
    )

    comp_name = str(
        DATA_CLIENT.get("nama_perusahaan")
        or "EKSPEDISI"
    ).strip()
    comp_address = str(
        DATA_CLIENT.get("alamat_perusahaan")
        or ""
    ).strip()
    comp_phone = str(
        DATA_CLIENT.get("telp_perusahaan")
        or ""
    ).strip()

    list_items = data.get("items", [])
    if not isinstance(list_items, (list, tuple)):
        list_items = []

    baris_tabel: list[str] = []
    total_berat = Decimal("0")
    total_cbm = Decimal("0")

    for index, row in enumerate(list_items):
        nomor = index + 1
        no_resi = _nilai_row(row, 0)
        pengirim = _nilai_row(row, 1)
        penerima = _nilai_row(row, 2)
        kota_raw = str(
            _nilai_row(row, 3, "")
        )
        nama_barang = _nilai_row(row, 4)
        nilai_koli = _nilai_row(row, 5, "")
        nilai_berat = _nilai_row(row, 6, 0)
        nilai_cbm = _nilai_row(row, 7, 0)

        total_berat += angka_indonesia_to_decimal(
            nilai_berat
        )
        total_cbm += angka_indonesia_to_decimal(
            nilai_cbm
        )

        kota_cetak = (
            kota_raw.split(" - ")[-1].strip()
            if " - " in kota_raw
            else kota_raw.strip()
        )

        baris_tabel.append(
            "<tr>"
            f'<td align="center">{nomor}</td>'
            f"<td>{_esc(no_resi)}</td>"
            f"<td>{_esc(pengirim)}</td>"
            f"<td>{_esc(penerima)}</td>"
            f"<td>{_esc(kota_cetak)}</td>"
            f"<td>{_esc(nama_barang)}</td>"
            f'<td align="center">{_esc(_teks_koli(nilai_koli))}</td>'
            f'<td align="center">{_format_desimal(nilai_berat)}</td>'
            f'<td align="center">{_format_desimal(nilai_cbm)}</td>'
            "</tr>"
        )

    if not baris_tabel:
        baris_tabel.append(
            '<tr><td colspan="9" align="center" '
            'style="padding:18px;color:#64748b;">'
            "Tidak ada muatan pada manifest."
            "</td></tr>"
        )

    total_koli = jumlahkan_angka_dari_teks(
        _nilai_row(row, 5, "")
        for row in list_items
    )
    total_koli_cetak = (
        format_decimal_indonesia(total_koli)
        if total_koli != 0
        else "-"
    )
    total_berat_cetak = _format_desimal(
        total_berat,
        maksimum_desimal=2,
    )
    total_cbm_cetak = _format_desimal(
        total_cbm,
        maksimum_desimal=2,
    )

    nomor_manifest = str(
        data.get("no_manifest", "")
        or "MANIFEST"
    ).strip().upper()
    armada = str(
        data.get("armada", "")
        or "-"
    ).strip().upper()
    tanggal = str(
        data.get("tanggal", "")
        or ""
    ).strip()

    font_dokumen = get_master_font()
    detail_perusahaan = "<br>".join(
        bagian
        for bagian in (
            _esc(comp_address),
            (
                f"Telp. {_esc(comp_phone)}"
                if comp_phone
                else ""
            ),
        )
        if bagian
    )

    html_content = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{
                font-family: "{font_dokumen}";
                font-size: 10pt;
                margin: 0;
                padding: 0;
                color: #000000;
            }}
            .title {{
                font-size: 16pt;
                font-weight: bold;
                text-align: center;
                margin-bottom: 3px;
                color: #0f172a;
            }}
            .company-detail {{
                text-align: center;
                font-size: 8.5pt;
                margin-bottom: 5px;
                color: #334155;
            }}
            .sub-title {{
                text-align: center;
                font-size: 10pt;
                font-weight: bold;
                margin-bottom: 14px;
                color: #475569;
            }}
            .info-manifest {{
                width: 100%;
                margin-bottom: 10px;
                font-size: 9.5pt;
                border-collapse: collapse;
            }}
            .info-manifest td {{
                padding: 3px 0;
            }}
            .table-data {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 5px;
                table-layout: fixed;
            }}
            .table-data th {{
                border: 1px solid #000000;
                padding: 5px 3px;
                background-color: #f1f5f9;
                font-size: 8.5pt;
                font-weight: bold;
            }}
            .table-data td {{
                border: 1px solid #000000;
                padding: 5px 3px;
                font-size: 8.5pt;
                word-wrap: break-word;
            }}
            .total-row {{
                font-weight: bold;
                background-color: #f8fafc;
            }}
        </style>
    </head>
    <body>
        <div class="title">
            {_esc(comp_name.upper())}
        </div>
        <div class="company-detail">
            {detail_perusahaan}
        </div>
        <div class="sub-title">
            SURAT JALAN MANIFEST PENGIRIMAN ARMADA
        </div>

        <table class="info-manifest">
            <tr>
                <td width="12%"><b>NO. MANIFEST</b></td>
                <td width="2%">:</td>
                <td width="20%"><b>{_esc(nomor_manifest)}</b></td>
                <td width="10%"><b>ARMADA</b></td>
                <td width="2%">:</td>
                <td width="22%"><b>{_esc(armada)}</b></td>
                <td width="10%"><b>TANGGAL</b></td>
                <td width="2%">:</td>
                <td width="21%">{_esc(tanggal)}</td>
            </tr>
        </table>

        <table class="table-data">
            <thead>
                <tr>
                    <th width="4%">NO</th>
                    <th width="12%">NO. RESI</th>
                    <th width="14%">PENGIRIM</th>
                    <th width="16%">PENERIMA</th>
                    <th width="14%">KOTA TUJUAN</th>
                    <th width="16%">JENIS MUATAN</th>
                    <th width="8%">KOLI</th>
                    <th width="8%">BERAT (KG)</th>
                    <th width="8%">KUBIKASI (M3)</th>
                </tr>
            </thead>
            <tbody>
                {''.join(baris_tabel)}
                <tr class="total-row">
                    <td colspan="6" align="right"
                        style="padding-right: 15px;">
                        TOTAL MUATAN :
                    </td>
                    <td align="center"><b>{total_koli_cetak}</b></td>
                    <td align="center"><b>{total_berat_cetak}</b></td>
                    <td align="center"><b>{total_cbm_cetak}</b></td>
                </tr>
            </tbody>
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
        jenis_dokumen=JENIS_MANIFEST,
        tipe_kertas=tipe_kertas,
        nomor_dokumen=nomor_manifest,
    )
    preview.exec_()