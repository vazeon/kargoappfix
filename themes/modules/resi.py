"""Style khusus tab Resi.

Seluruh definisi warna, QSS, dan style dinamis milik TabResi ditempatkan
pada modul ini agar file tab hanya menangani logika dan penerapan style.
"""

from utils.typography import MASTER_FONT, get_global_font_sizes

from themes.scrollbar import get_scrollbar_style


def get_resi_static_styles(is_dark: bool) -> dict:
    """Style awal yang dapat dipakai sebelum proses refresh tema lengkap."""
    if is_dark:
        bg_card = "#1d2024"
        border_card = "#3f434d"
    else:
        bg_card = "#f8fafc"
        border_card = "#cbd5e1"

    return {
        "scroll_kiri": (
            "QScrollArea { background-color: transparent; border: none; }"
        ),
        "rekening_card": (
            f"background-color: {bg_card}; "
            f"border: 1px solid {border_card}; "
            "border-radius: 6px;"
        ),
    }


def get_resi_rekening_styles(is_dark: bool, z: int = 0) -> dict:
    """Style dinamis kartu dan kelompok rekening pada TabResi."""
    txt_top_color = "#ffffff" if is_dark else "#0f172a"
    txt_bottom_color = "#64748b"
    bg_card = "#1d2024" if is_dark else "#f8fafc"
    border_card = "#3f434d" if is_dark else "#cbd5e1"
    group_text = "#94a3b8" if is_dark else "#64748b"
    group_bg = "#181a1e" if is_dark else "#ffffff"

    sizes = get_global_font_sizes(z)
    sz_sm = sizes["sz_sm"]
    sz_card_title = max(11, 13 + z)
    sz_card_desc = max(10, 12 + z)

    return {
        "group_box": f"""
            QGroupBox {{
                font-weight: bold;
                font-size: {sz_sm}px;
                font-family: '{MASTER_FONT}';
                color: {group_text};
                border: 1px solid {border_card};
                border-radius: 8px;
                margin-top: 3px;
                padding-top: 20px;
                background-color: {group_bg};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                left: 10px;
                top: 10px;
                padding: 0 4px;
            }}
        """,
        "label_top": (
            f"color: {txt_top_color}; "
            f"font-size: {sz_card_title}px; "
            "border: none; "
            "background: transparent; "
            f"font-family: '{MASTER_FONT}';"
        ),
        "label_bottom": (
            f"color: {txt_bottom_color}; "
            f"font-size: {sz_card_desc}px; "
            "font-weight: normal; "
            "border: none; "
            "background: transparent; "
            f"font-family: '{MASTER_FONT}';"
        ),
        "card": (
            f"background-color: {bg_card}; "
            f"border: 1px solid {border_card}; "
            "border-radius: 6px;"
        ),
    }


def get_resi_styles(
    is_dark: bool,
    sz_title: int,
    sz_tag: int,
    sz_sm: int,
    sz_base: int,
    sz_input: int,
    sz_total: int,
    z: int = 0,
) -> dict:
    """Menghasilkan seluruh style UI untuk TabResi."""
    if is_dark:
        c_bg, c_card, c_bord, c_bord_card = (
            "#1d2024",
            "#25282e",
            "#4c525e",
            "#3f434d",
        )
        c_text, c_text_mut, c_text_dim = "#ffffff", "#cbd5e1", "#9ca3af"
        c_foc, c_bg_foc, c_head, c_grid = (
            "#3b82f6",
            "#20242b",
            "#31353d",
            "#2d3139",
        )
        c_hist_bg = "#25282e"
        c_resi_bg, c_resi_bord, c_resi_txt = "#1d2024", "#3b82f6", "#fbbf24"
        c_btn_add_bg, c_btn_add_txt, c_btn_add_bord = "#31353d", "#3b82f6", "#3b82f6"
        c_btn_del_bg, c_btn_del_txt, c_btn_del_bord = "#31353d", "#ef4444", "#4c525e"
    else:
        c_bg, c_card, c_bord, c_bord_card = (
            "#ffffff",
            "#ffffff",
            "#cbd5e1",
            "#cbd5e1",
        )
        c_text, c_text_mut, c_text_dim = "#0f172a", "#1e293b", "#64748b"
        c_foc, c_bg_foc, c_head, c_grid = (
            "#2563eb",
            "#ffffff",
            "#243752",
            "#f1f5f9",
        )
        c_hist_bg = "#f1f5f9"
        c_resi_bg, c_resi_bord, c_resi_txt = "#fef2f2", "#ef4444", "#b91c1c"
        c_btn_add_bg, c_btn_add_txt, c_btn_add_bord = "#ffffff", "#2563eb", "#2563eb"
        c_btn_del_bg, c_btn_del_txt, c_btn_del_bord = "#ffffff", "#dc2626", "#fca5a5"

    input_style = f"""
        QLineEdit, QTextEdit, QComboBox, QDateEdit {{
            font-size: {sz_input}px;
            background-color: {c_bg};
            color: {c_text};
            border: 1px solid {c_bord};
            border-radius: 4px;
            padding: 6px;
            font-family: '{MASTER_FONT}';
        }}
        QLineEdit:focus, QTextEdit:focus, QComboBox:focus, QDateEdit:focus {{
            border: 1px solid {c_foc};
            background-color: {c_bg_foc};
        }}
        QLineEdit[custom_italic="true"][is_empty="true"],
        QTextEdit[custom_italic="true"][is_empty="true"] {{
            font-style: italic;
            font-size: {sz_input}px;
            color: {c_text_dim};
        }}
        QLineEdit[custom_italic="true"][is_empty="false"],
        QTextEdit[custom_italic="true"][is_empty="false"] {{
            font-style: normal;
        }}
    """

    qss_group_umum = f"""
        QGroupBox {{
            font-weight: bold;
            font-size: {sz_base}px;
            color: {c_text};
            background-color: {c_card};
            border: 1px solid {c_bord_card};
            border-radius: 8px;
            margin-top: 2px;
            padding: 8px 12px;
            font-family: '{MASTER_FONT}';
        }}
        QGroupBox::title {{ color: {c_text}; }}
        QLabel {{
            color: {c_text_mut};
            font-size: {sz_sm}px;
            font-weight: bold;
            background-color: transparent;
            font-family: '{MASTER_FONT}';
        }}
        {input_style}
    """

    qss_group_tabel = f"""
        QGroupBox {{
            font-weight: bold;
            font-size: {sz_base}px;
            color: {c_text};
            background-color: {c_card};
            border: 1px solid {c_bord_card};
            border-radius: 8px;
            margin-top: 2px;
            padding: 6px 12px;
            font-family: '{MASTER_FONT}';
        }}
        QGroupBox::title {{ color: {c_text}; }}
        QLabel {{
            color: {c_text_mut};
            font-size: {sz_sm}px;
            font-family: '{MASTER_FONT}';
        }}
        QTableWidget {{
            font-size: {sz_base}px;
            background-color: {c_bg};
            color: {c_text};
            border: 1px solid {c_bord};
            gridline-color: {c_grid};
            border-radius: 6px;
            font-family: '{MASTER_FONT}';
        }}
        QTableWidget QLineEdit {{
            font-size: {sz_base}px;
            background-color: {c_bg};
            color: {c_text};
            border: 1px solid {c_bord};
            border-radius: 4px;
            padding: 4px;
            font-family: '{MASTER_FONT}';
        }}
        QTableWidget QLineEdit[custom_italic="true"][is_empty="true"] {{
            font-style: italic;
            font-size: {sz_base}px;
            color: {c_text_dim};
        }}
        QHeaderView::section {{
            font-size: {sz_base}px;
            background-color: {c_head};
            color: white;
            font-weight: bold;
            padding: 6px;
            border: none;
            font-family: '{MASTER_FONT}';
        }}
        {get_scrollbar_style(is_dark)}
    """

    rekening_styles = get_resi_rekening_styles(is_dark, z)
    static_styles = get_resi_static_styles(is_dark)

    return {
        "lbl_main_title": (
            f"color: {c_text}; font-size: {sz_title}px; font-weight: bold; "
            f"margin-bottom: 1px; font-family: '{MASTER_FONT}';"
        ),
        "lbl_tgl_tag": (
            f"color: {c_text_mut}; font-weight: bold; "
            f"font-family: '{MASTER_FONT}'; font-size: {sz_tag}px;"
        ),
        "lbl_resi_tag": (
            f"font-size: {sz_sm}px; color: {c_text_dim}; font-weight: bold; "
            f"font-family: '{MASTER_FONT}';"
        ),
        "lbl_histori_title": (
            f"color: {c_text}; font-size: {sz_base + 1}px; font-weight: bold; "
            f"font-family: '{MASTER_FONT}';"
        ),
        "txt_resi_display": (
            f"background-color: {c_resi_bg}; border: 2px solid {c_resi_bord}; "
            f"border-radius: 6px; padding: 6px 12px; color: {c_resi_txt}; "
            f"font-weight: bold; font-size: {sz_total}px; letter-spacing: 1px; "
            f"font-family: '{MASTER_FONT}';"
        ),
        "date_input": (
            f"QDateEdit {{ font-size: {sz_input}px; font-family: '{MASTER_FONT}'; "
            f"padding: 2px 10px; border: 1px solid {c_bord}; border-radius: 4px; "
            f"background-color: {c_bg}; color: {c_text}; }}"
        ),
        "date_histori": (
            f"QDateEdit {{ font-size: {sz_input}px; font-family: '{MASTER_FONT}'; "
            f"padding: 2px 10px; background-color: {c_hist_bg}; color: {c_text_mut}; "
            f"border: 1px solid {c_bord}; border-radius: 4px; }}"
        ),
        "list_histori": f"""
            QListWidget {{
                background-color: {c_bg};
                color: {c_text_mut};
                border: 1px solid {c_bord};
                border-radius: 6px;
                padding: 5px;
                font-size: {sz_base}px;
                font-family: '{MASTER_FONT}';
            }}
            QListWidget::item {{ padding: {6 + (z // 2)}px; }}
        """,
        "txt_search": f"""
            QLineEdit {{
                font-size: {sz_input}px;
                background-color: {c_bg};
                color: {c_text};
                border: 1px solid {c_bord};
                border-radius: 4px;
                padding: 6px;
                font-family: '{MASTER_FONT}';
            }}
            QLineEdit[custom_italic="true"][is_empty="true"] {{
                font-style: italic;
                font-size: {sz_input}px;
                color: {c_text_dim};
            }}
            QLineEdit[custom_italic="true"][is_empty="false"] {{
                font-style: normal;
            }}
        """,
        "btn_reset_tgl": (
            f"background-color: #ef4444; color: white; font-weight: bold; "
            f"border-radius: 4px; padding: 4px; font-size: {sz_sm}px; "
            f"font-family: '{MASTER_FONT}';"
        ),
        "group_pengirim": qss_group_umum,
        "group_penerima": qss_group_umum,
        "group_finance": qss_group_umum,
        "group_tabel_container": qss_group_tabel,
        "btn_tambah_baris": (
            f"font-size: {sz_base}px; background-color: {c_btn_add_bg}; "
            f"color: {c_btn_add_txt}; border: 1px solid {c_btn_add_bord}; "
            f"padding: 6px 12px; border-radius: 4px; font-weight: bold; "
            f"font-family: '{MASTER_FONT}';"
        ),
        "btn_hapus_baris": (
            f"font-size: {sz_base}px; background-color: {c_btn_del_bg}; "
            f"color: {c_btn_del_txt}; border: 1px solid {c_btn_del_bord}; "
            f"padding: 6px 12px; border-radius: 4px; font-weight: bold; "
            f"font-family: '{MASTER_FONT}';"
        ),
        "txt_total_ongkir": f"""
            QLineEdit {{
                font-size: {sz_total}px;
                font-weight: bold;
                color: {c_foc};
                background-color: {c_bg};
                border: 1px solid {c_bord};
                padding: 6px;
                font-family: '{MASTER_FONT}';
            }}
            QLineEdit[custom_italic="true"][is_empty="true"] {{
                font-style: italic;
                font-size: {sz_total}px;
                color: {c_text_dim};
                font-weight: normal;
            }}
        """,
        "input_utama": input_style,
        "widget_kiri": "background-color: transparent;",
        "scroll_kiri": static_styles["scroll_kiri"],
        "splitter": "QSplitter::handle { background-color: transparent; }",
        "btn_generate_simpan": f"""
            QPushButton {{
                background-color: #22c55e;
                color: white;
                font-weight: bold;
                font-size: {14 + z}px;
                padding: {10 + (z // 2)}px {40 + z}px;
                border-radius: 6px;
                border: none;
                font-family: '{MASTER_FONT}';
            }}
            QPushButton:hover {{ background-color: #16a34a; }}
            QPushButton:pressed {{ background-color: #15803d; }}
        """,
        "box_np": rekening_styles["group_box"],
        "box_p": rekening_styles["group_box"],
    }
