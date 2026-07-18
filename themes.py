# themes.py
from PyQt5.QtGui import QColor, QPalette

from utils.typography import (
    MASTER_FONT,
    get_global_font_sizes,
)

GLOBAL_FONT_SIZES = get_global_font_sizes(0)
GLOBAL_BASE_SIZE = GLOBAL_FONT_SIZES["sz_base"]


# Style dasar ini dipasang satu kali saat aplikasi dibuat. Warna diambil
# dari QPalette sehingga pergantian tema tidak perlu mem-parsing ulang
# stylesheet seluruh QApplication.
BASE_STYLE = f"""
    QWidget {{
        font-family: "{MASTER_FONT}";
        font-size: {GLOBAL_BASE_SIZE}px;
    }}

    QLineEdit[custom_italic="true"][is_empty="true"],
    QTextEdit[custom_italic="true"][is_empty="true"] {{
        font-style: italic;
        color: palette(mid);
    }}

    QLineEdit[custom_italic="true"][is_empty="false"],
    QTextEdit[custom_italic="true"][is_empty="false"] {{
        font-style: normal;
    }}
"""


def get_main_shell_styles(is_dark: bool) -> dict:
    """
    Style ringan khusus kerangka utama aplikasi.

    Style dipasang hanya pada CentralWidget, tab utama, dan corner widget.
    Dengan demikian perubahan tema tidak memoles ulang seluruh isi tab.
    """
    if is_dark:
        bg_main = "#1a1d24"
        bg_pane = "#1a1d24"
        bg_tab = "#13161b"
        bg_tab_hover = "#1e222b"
        text = "#f8fafc"
        text_muted = "#94a3b8"
        accent = "#3b82f6"
        border = "#2d3139"
    else:
        bg_main = "#f8fafc"
        bg_pane = "#ffffff"
        bg_tab = "#f1f5f9"
        bg_tab_hover = "#e2e8f0"
        text = "#0f172a"
        text_muted = "#64748b"
        accent = "#2563eb"
        border = "#e2e8f0"

    return {
        "central": f"""
            QWidget#CentralWidget {{
                background-color: {bg_main};
                color: {text};
            }}
        """,
        "tabs": f"""
            QTabWidget#MainTabs {{
                background-color: transparent;
            }}
            QTabWidget#MainTabs::pane {{
                border: none;
                background-color: {bg_pane};
            }}
        """,
        "tab_bar": f"""
            QTabBar#MainTabBar {{
                background-color: transparent;
            }}
            QTabBar#MainTabBar::tab {{
                background-color: {bg_tab};
                color: {text_muted};
                font-weight: 500;
                border: none;
                border-right: 1px solid {border};
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                margin-top: 5px;
                padding: 12px 16px;
                min-width: 130px;
                font-family: "{MASTER_FONT}";
                font-size: 12px;
            }}
            QTabBar#MainTabBar::tab:selected {{
                background-color: {bg_pane};
                color: {accent};
                font-weight: bold;
                border: 1px solid {border};
                border-bottom: none;
                margin-bottom: -1px;
                font-size: 14px;
            }}
            QTabBar#MainTabBar::tab:hover:!selected {{
                background-color: {bg_tab_hover};
                color: {text};
            }}
        """,
        "corner": "background-color: transparent;",
    }

def get_theme_palette(is_dark: bool) -> QPalette:
    """Membuat palette gelap/terang tanpa mengganti stylesheet global."""
    palette = QPalette()

    if is_dark:
        colors = {
            QPalette.Window: "#1a1d24",
            QPalette.WindowText: "#f8fafc",
            QPalette.Base: "#1a1d24",
            QPalette.AlternateBase: "#20242b",
            QPalette.ToolTipBase: "#0f172a",
            QPalette.ToolTipText: "#f8fafc",
            QPalette.Text: "#f8fafc",
            QPalette.Button: "#1e222b",
            QPalette.ButtonText: "#f8fafc",
            QPalette.BrightText: "#ffffff",
            QPalette.Link: "#60a5fa",
            QPalette.Highlight: "#3b82f6",
            QPalette.HighlightedText: "#ffffff",
            QPalette.Light: "#475569",
            QPalette.Midlight: "#3f434d",
            QPalette.Mid: "#4c525e",
            QPalette.Dark: "#64748b",
            QPalette.Shadow: "#0f172a",
        }
    else:
        colors = {
            QPalette.Window: "#f8fafc",
            QPalette.WindowText: "#0f172a",
            QPalette.Base: "#ffffff",
            QPalette.AlternateBase: "#f1f5f9",
            QPalette.ToolTipBase: "#ffffff",
            QPalette.ToolTipText: "#0f172a",
            QPalette.Text: "#0f172a",
            QPalette.Button: "#e2e8f0",
            QPalette.ButtonText: "#0f172a",
            QPalette.BrightText: "#000000",
            QPalette.Link: "#2563eb",
            QPalette.Highlight: "#2563eb",
            QPalette.HighlightedText: "#ffffff",
            QPalette.Light: "#ffffff",
            QPalette.Midlight: "#e2e8f0",
            QPalette.Mid: "#94a3b8",
            QPalette.Dark: "#64748b",
            QPalette.Shadow: "#334155",
        }

    for role, color in colors.items():
        palette.setColor(role, QColor(color))

    palette.setColor(
        QPalette.Disabled,
        QPalette.Text,
        QColor("#94a3b8"),
    )
    palette.setColor(
        QPalette.Disabled,
        QPalette.ButtonText,
        QColor("#94a3b8"),
    )

    return palette

def _get_scrollbar_qss(is_dark: bool) -> str:
    warna_handle = "#3f434d" if is_dark else "#cbd5e1"
    warna_hover = "#4c525e" if is_dark else "#94a3b8"
    return f"""
        QScrollArea {{ background-color: transparent; border: none; }}
        QScrollBar:vertical {{ border: none; background: transparent; width: 12px; margin: 0px; }}
        QScrollBar::handle:vertical {{ background: {warna_handle}; border: 4px solid transparent; border-radius: 6px; min-height: 30px; }}
        QScrollBar::handle:vertical:hover {{ background: {warna_hover}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
        QScrollBar:horizontal {{ border: none; background: transparent; height: 12px; margin: 0px; }}
        QScrollBar::handle:horizontal {{ background: {warna_handle}; border-radius: 4px; min-width: 30px; margin: 2px 0px 2px 0px; }}
        QScrollBar::handle:horizontal:hover {{ background: {warna_hover}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}
    """


# STYLE GLOBAL TETAP DIPERTAHANKAN
DARK_STYLE = f"""
    QWidget {{ font-family: "{MASTER_FONT}"; font-size: {GLOBAL_BASE_SIZE}px; }}
    QMainWindow, #CentralWidget {{ background-color: #1a1d24; color: #f8fafc; }}
    QTabWidget, QTabBar {{ background-color: transparent; }}
    QTabWidget::pane {{ border: none; background-color: #1a1d24; }}
    QTabBar::tab {{ 
        background-color: #13161b; 
        color: #94a3b8; 
        font-weight: 500; 
        border: none; 
        border-right: 1px solid #2d3139; 
        border-top-left-radius: 5px; 
        border-top-right-radius: 5px; 
        margin-top: 5px; 
        padding: 12px 16px; 
        min-width: 130px; 
        font-family: '{MASTER_FONT}'; 
        font-size: 12px; /* 🎯 SET FIXED: Ukuran untuk tab di belakang (tidak aktif) */
    }}
    QTabBar::tab:selected {{ 
        background-color: #1a1d24; 
        color: #3b82f6; 
        font-weight: bold; 
        border: 1px solid #2d3139; 
        border-bottom: none; 
        margin-bottom: -1px; 
        font-size: 14px; /* 🎯 SET LEBIH BESAR: Memaksa tab terpilih berukuran lebih besar */
    }}
    QTabBar::tab:hover:!selected {{ background-color: #1e222b; color: #ffffff; }}
    QSplitter::handle {{ background-color: #334155; width: 1px; height: 1px; }}
    QLineEdit[custom_italic="true"][is_empty="true"], QTextEdit[custom_italic="true"][is_empty="true"] {{ font-style: italic; color: #9ca3af; }}
    QLineEdit[custom_italic="true"][is_empty="false"], QTextEdit[custom_italic="true"][is_empty="false"] {{ font-style: normal; }}
    {_get_scrollbar_qss(True)}
"""

LIGHT_STYLE = f"""
    QWidget {{ font-family: "{MASTER_FONT}"; font-size: {GLOBAL_BASE_SIZE}px; }}
    QMainWindow, #CentralWidget {{ background-color: #f8fafc; color: #0f172a; }}
    QTabWidget, QTabBar {{ background-color: transparent; }}
    QTabWidget::pane {{ border: none; background-color: #ffffff; }}
    QTabBar::tab {{ 
        background-color: #f1f5f9; 
        color: #64748b; 
        font-weight: 500; 
        border: none; 
        border-right: 1px solid #e2e8f0; 
        border-top-left-radius: 5px; 
        border-top-right-radius: 5px; 
        margin-top: 5px; 
        padding: 12px 16px; 
        min-width: 130px; 
        font-family: '{MASTER_FONT}'; 
        font-size: 12px; /* 🎯 SET FIXED: Ukuran untuk tab di belakang (tidak aktif) */
    }}
    QTabBar::tab:selected {{ 
        background-color: #ffffff; 
        color: #2563eb; 
        font-weight: bold; 
        border: 1px solid #e2e8f0; 
        border-bottom: none; 
        margin-bottom: -1px; 
        font-size: 14px; /* 🎯 SET LEBIH BESAR: Memaksa tab terpilih berukuran lebih besar */
    }}
    QTabBar::tab:hover:!selected {{ background-color: #e2e8f0; color: #0f172a; }}
    QSplitter::handle {{ background-color: #cbd5e1; width: 1px; height: 1px; }}
    QLineEdit[custom_italic="true"][is_empty="true"], QTextEdit[custom_italic="true"][is_empty="true"] {{ font-style: italic; color: #64748b; }}
    QLineEdit[custom_italic="true"][is_empty="false"], QTextEdit[custom_italic="true"][is_empty="false"] {{ font-style: normal; }}
    {_get_scrollbar_qss(False)}
"""

FADE_NOTIFICATION_STYLE = f"""
    QLabel {{ background-color: rgba(15, 23, 42, 0.95); color: #10b981; font-size: 22px; font-weight: bold; border-radius: 12px; padding: 20px 50px; border: 2px solid #10b981; font-family: '{MASTER_FONT}'; }}
"""

BTN_SIMPAN_CETAK_STYLE = f"""
    QPushButton {{ background-color: #22c55e; color: white; font-weight: bold; font-size: 14px; padding: 10px 40px; border-radius: 6px; border: none; font-family: '{MASTER_FONT}'; }}
    QPushButton:hover   {{ background-color: #16a34a; }}
    QPushButton:pressed {{ background-color: #15803d; }}
"""


# =========================================================
# TAB RESI (DIKEMBALIKAN KE BENTUK ASLI + FIX FONT-SIZE)
# =========================================================
def get_resi_styles(is_dark: bool, sz_title: int, sz_tag: int, sz_sm: int, sz_base: int, sz_input: int,
                    sz_total: int) -> dict:
    if is_dark:
        c_bg, c_card, c_bord, c_bord_card = "#1d2024", "#25282e", "#4c525e", "#3f434d"
        c_text, c_text_mut, c_text_dim = "#ffffff", "#cbd5e1", "#9ca3af"
        c_foc, c_bg_foc, c_head, c_grid = "#3b82f6", "#20242b", "#31353d", "#2d3139"
        c_hist_bg = "#25282e"
        c_resi_bg, c_resi_bord, c_resi_txt = "#1d2024", "#3b82f6", "#fbbf24"
        c_btn_add_bg, c_btn_add_txt, c_btn_add_bord = "#31353d", "#3b82f6", "#3b82f6"
        c_btn_del_bg, c_btn_del_txt, c_btn_del_bord = "#31353d", "#ef4444", "#4c525e"
    else:
        c_bg, c_card, c_bord, c_bord_card = "#ffffff", "#ffffff", "#cbd5e1", "#cbd5e1"
        c_text, c_text_mut, c_text_dim = "#0f172a", "#1e293b", "#64748b"
        c_foc, c_bg_foc, c_head, c_grid = "#2563eb", "#ffffff", "#243752", "#f1f5f9"
        c_hist_bg = "#f1f5f9"
        c_resi_bg, c_resi_bord, c_resi_txt = "#fef2f2", "#ef4444", "#b91c1c"
        c_btn_add_bg, c_btn_add_txt, c_btn_add_bord = "#ffffff", "#2563eb", "#2563eb"
        c_btn_del_bg, c_btn_del_txt, c_btn_del_bord = "#ffffff", "#dc2626", "#fca5a5"

    qss_group_umum = f"""
        QGroupBox {{ font-weight: bold; font-size: {sz_base}px; color: {c_text}; background-color: {c_card}; border: 1px solid {c_bord_card}; border-radius: 8px; margin-top: 2px; padding: 8px 12px; font-family: '{MASTER_FONT}'; }}
        QGroupBox::title {{ color: {c_text}; }}
        QLabel {{ color: {c_text_mut}; font-size: {sz_sm}px; font-weight: bold; background-color: transparent; font-family: '{MASTER_FONT}'; }}
        QLineEdit, QComboBox, QDateEdit {{ font-size: {sz_input}px; background-color: {c_bg}; color: {c_text}; border: 1px solid {c_bord}; border-radius: 4px; padding: 6px; font-family: '{MASTER_FONT}'; }}
        QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{ border: 1px solid {c_foc}; background-color: {c_bg_foc}; }}
        QLineEdit[custom_italic="true"][is_empty="true"], QTextEdit[custom_italic="true"][is_empty="true"] {{ font-style: italic; font-size: {sz_input}px; color: {c_text_dim}; }}
        QLineEdit[custom_italic="true"][is_empty="false"], QTextEdit[custom_italic="true"][is_empty="false"] {{ font-style: normal; }}
    """

    qss_group_tabel = f"""
        QGroupBox {{ font-weight: bold; font-size: {sz_base}px; color: {c_text}; background-color: {c_card}; border: 1px solid {c_bord_card}; border-radius: 8px; margin-top: 2px; padding: 6px 12px; font-family: '{MASTER_FONT}'; }}
        QGroupBox::title {{ color: {c_text}; }}
        QLabel {{ color: {c_text_mut}; font-size: {sz_sm}px; font-family: '{MASTER_FONT}'; }}
        QTableWidget {{ font-size: {sz_base}px; background-color: {c_bg}; color: {c_text}; border: 1px solid {c_bord}; gridline-color: {c_grid}; border-radius: 6px; font-family: '{MASTER_FONT}'; }}

        /* KOMPONEN PENTING: Mengatur gaya input DI DALAM tabel secara global agar tidak perlu diloop */
        QTableWidget QLineEdit {{ font-size: {sz_base}px; background-color: {c_bg}; color: {c_text}; border: 1px solid {c_bord}; border-radius: 4px; padding: 4px; font-family: '{MASTER_FONT}'; }}
        QTableWidget QLineEdit[custom_italic="true"][is_empty="true"] {{ font-style: italic; font-size: {sz_base}px; color: {c_text_dim}; }}

        QHeaderView::section {{ font-size: {sz_base}px; background-color: {c_head}; color: white; font-weight: bold; padding: 6px; border: none; font-family: '{MASTER_FONT}'; }}
        {_get_scrollbar_qss(is_dark)}
    """

    return {
        'lbl_main_title': f"color: {c_text}; font-size: {sz_title}px; font-weight: bold; margin-bottom: 1px; font-family: '{MASTER_FONT}';",
        'lbl_tgl_tag': f"color: {c_text_mut}; font-weight: bold; font-family: '{MASTER_FONT}'; font-size: {sz_tag}px;",
        'lbl_resi_tag': f"font-size: {sz_sm}px; color: {c_text_dim}; font-weight: bold; font-family: '{MASTER_FONT}';",
        'lbl_histori_title': f"color: {c_text}; font-size: {sz_base + 1}px; font-weight: bold; font-family: '{MASTER_FONT}';",
        'txt_resi_display': f"background-color: {c_resi_bg}; border: 2px solid {c_resi_bord}; border-radius: 6px; padding: 6px 12px; color: {c_resi_txt}; font-weight: bold; font-size: {sz_total}px; letter-spacing: 1px; font-family: '{MASTER_FONT}';",
        'date_input': f"font-size: {sz_input + 1}px; padding: 6px; border: 1px solid {c_bord}; border-radius: 4px; background-color: {c_bg}; color: {c_text}; font-family: '{MASTER_FONT}';",
        'date_histori': f"font-size: {sz_sm + 1}px; background-color: {c_hist_bg}; color: {c_text_mut}; border: 1px solid {c_bord}; border-radius: 4px; padding: 4px; font-family: '{MASTER_FONT}';",
        'list_histori': f"background-color: {c_bg}; color: {c_text_mut}; border: 1px solid {c_bord}; border-radius: 6px; padding: 5px; font-size: {sz_base}px; font-family: '{MASTER_FONT}';",
        'txt_search': f"QLineEdit {{ font-size: {sz_input}px; background-color: {c_bg}; color: {c_text}; border: 1px solid {c_bord}; border-radius: 4px; padding: 6px; font-family: '{MASTER_FONT}'; }} QLineEdit[custom_italic=\"true\"][is_empty=\"true\"] {{ font-style: italic; font-size: {sz_input}px; color: {c_text_dim}; }} QLineEdit[custom_italic=\"true\"][is_empty=\"false\"] {{ font-style: normal; }}",
        'btn_reset_tgl': f"background-color: #ef4444; color: white; font-weight: bold; border-radius: 4px; padding: 4px; font-size: {sz_sm}px; font-family: '{MASTER_FONT}';",
        'group_pengirim': qss_group_umum,
        'group_penerima': qss_group_umum,
        'group_finance': qss_group_umum,
        'group_tabel_container': qss_group_tabel,
        'btn_tambah_baris': f"font-size: {sz_base}px; background-color: {c_btn_add_bg}; color: {c_btn_add_txt}; border: 1px solid {c_btn_add_bord}; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-family: '{MASTER_FONT}';",
        'btn_hapus_baris': f"font-size: {sz_base}px; background-color: {c_btn_del_bg}; color: {c_btn_del_txt}; border: 1px solid {c_btn_del_bord}; padding: 6px 12px; border-radius: 4px; font-weight: bold; font-family: '{MASTER_FONT}';",

        # 🎯 KUNCI KAMUS TELAH DIUBAH MENJADI ONGKIR:
        'txt_total_ongkir': f"QLineEdit {{ font-size: {sz_total}px; font-weight: bold; color: {c_foc}; background-color: {c_bg}; border: 1px solid {c_bord}; padding: 6px; font-family: '{MASTER_FONT}'; }} QLineEdit[custom_italic=\"true\"][is_empty=\"true\"] {{ font-style: italic; font-size: {sz_total}px; color: {c_text_dim}; font-weight: normal; }}"
    }


# =========================================================
# TAB MANIFEST TETAP UTUH
# =========================================================
def get_manifest_styles(is_dark: bool, is_edit_mode: bool, z: int = 0) -> dict:
    sizes = get_global_font_sizes(z)
    sz_base, sz_input, sz_title = sizes['sz_base'], sizes['sz_input'], sizes['sz_title']

    warna_btn = "#f97316" if is_edit_mode else "#22c55e"
    warna_btn_hover = "#ea580c" if is_edit_mode else "#16a34a"

    if is_dark:
        lbl_title = f"color: #ffffff; font-size: {sz_title}px; font-weight: bold; font-family: '{MASTER_FONT}';"
        style_input = (
            f"font-size: {sz_input}px; background-color: #1d2024; color: #ffffff; border: 1px solid #4c525e; padding: 6px; border-radius: 4px; font-family: '{MASTER_FONT}';"
            f"QLineEdit[custom_italic=\"true\"][is_empty=\"true\"] {{ font-style: italic; font-size: {sz_input}px; color: #6b7280; }}"
            f"QLineEdit[custom_italic=\"true\"][is_empty=\"false\"] {{ font-style: normal; }}"
        )
        style_tabel = (
            f"QTableWidget {{ background-color: #1a1d24; alternate-background-color: #20242b; color: #f8fafc; gridline-color: #334155; font-size: {sz_base}px; font-family: '{MASTER_FONT}'; }}"
            f"QHeaderView::section {{ background-color: #1e293b; color: #f8fafc; border: 1px solid #334155; font-size: {sz_base}px; font-weight: bold; padding: 6px; font-family: '{MASTER_FONT}'; }}"
            f"QTableWidget::item:selected {{ background-color: #3b82f6; color: white; }} QTableWidget::indicator {{ width: {18 + z}px; height: {18 + z}px; }}"
        )
        list_histori = (
            f"QTreeWidget {{ background-color: #1d2024; color: #cbd5e1; border: 1px solid #4c525e; border-radius: 6px; padding: 5px; font-size: {sz_base}px; font-family: '{MASTER_FONT}'; }}"
            f"QTreeView::item {{ padding: 4px; }}"
        )
    else:
        lbl_title = f"color: #0f172a; font-size: {sz_title}px; font-weight: bold; font-family: '{MASTER_FONT}';"
        style_input = (
            f"font-size: {sz_input}px; background-color: #ffffff; color: #0f172a; border: 1px solid #cbd5e1; padding: 6px; border-radius: 4px; font-family: '{MASTER_FONT}';"
            f"QLineEdit[custom_italic=\"true\"][is_empty=\"true\"] {{ font-style: italic; font-size: {sz_input}px; color: #9ca3af; }}"
            f"QLineEdit[custom_italic=\"true\"][is_empty=\"false\"] {{ font-style: normal; }}"
        )
        style_tabel = (
            f"QTableWidget {{ background-color: #ffffff; alternate-background-color: #f1f5f9; color: #0f172a; gridline-color: #e2e8f0; font-size: {sz_base}px; font-family: '{MASTER_FONT}'; }}"
            f"QHeaderView::section {{ background-color: #243752; color: #ffffff; border: 1px solid #cbd5e1; font-size: {sz_base}px; font-weight: bold; padding: 6px; font-family: '{MASTER_FONT}'; }}"
            f"QTableWidget::item:selected {{ background-color: #2563eb; color: white; }} QTableWidget::indicator {{ width: {18 + z}px; height: {18 + z}px; }}"
        )
        list_histori = (
            f"QTreeWidget {{ background-color: #ffffff; color: #1e293b; border: 1px solid #cbd5e1; border-radius: 6px; padding: 5px; font-size: {sz_base}px; font-family: '{MASTER_FONT}'; }}"
            f"QTreeView::item {{ padding: 4px; }}"
        )

    btn_proses = (
        f"QPushButton {{ background-color: {warna_btn}; color: white; font-weight: bold; padding: 7px 20px; border-radius: 4px; font-size: {sz_base}px; font-family: '{MASTER_FONT}'; }} "
        f"QPushButton:hover {{ background-color: {warna_btn_hover}; }}"
    )
    warna_teks_label = "#ffffff" if is_dark else "#0f172a"
    panel_kiri = f"QWidget {{ border: none; background-color: transparent; }} QLabel {{ font-size: {sz_base}px; font-family: '{MASTER_FONT}'; color: {warna_teks_label}; }}"
    panel_kanan = f"QWidget {{ border: none; background-color: transparent; }} QLabel {{ font-size: {sz_base}px; font-family: '{MASTER_FONT}'; color: {warna_teks_label}; }}"

    return {'lbl_title': lbl_title, 'style_input': style_input, 'btn_proses': btn_proses, 'list_histori': list_histori,
            'style_tabel': style_tabel, 'panel_kiri': panel_kiri, 'panel_kanan': panel_kanan}


# =========================================================
# TAB SETTING (DIKEMBALIKAN + FIX FONT-SIZE PLACEHOLDER)
# =========================================================
def get_setting_styles(is_dark: bool, sz_base: int, sz_input: int, sz_title: int) -> dict:
    if is_dark:
        bg_page, bg_card, bg_input, bg_input_foc = "#1a1d24", "#25282e", "#1d2024", "#20242b"
        bg_header, bg_alt_row, border, border_focus = "#1e293b", "#20242b", "#4c525e", "#3b82f6"
        border_grid, text_primary, text_muted, text_title, lbl_color = "#334155", "#f8fafc", "#94a3b8", "#cbd5e1", "#94a3b8"
        bg_sidebar, bg_list_hover = "#14171c", "#1e222b"
        list_text_color, page_title_color = "#cbd5e1", "#ffffff"
    else:
        bg_page, bg_card, bg_input, bg_input_foc = "#f1f5f9", "#ffffff", "#ffffff", "#ffffff"
        bg_header, bg_alt_row, border, border_focus = "#243752", "#f8fafc", "#cbd5e1", "#2563eb"
        border_grid, text_primary, text_muted, text_title, lbl_color = "#e2e8f0", "#0f172a", "#64748b", "#0f172a", "#475569"
        bg_sidebar, bg_list_hover = "#e2e8f0", "#cbd5e1"
        list_text_color, page_title_color = "#334155", "#0f172a"

    return {
        'scroll_area': f"QScrollArea {{ background-color: transparent; border: none; }}",
        'groupbox': f"""
            QGroupBox {{ font-weight: bold; font-size: {sz_title}px; font-family: '{MASTER_FONT}'; color: {text_title}; background-color: {bg_card}; border: 1px solid {border}; border-radius: 10px; margin-top: 22px; padding-top: 22px; padding-left: 4px; padding-right: 4px; padding-bottom: 8px; }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 14px; top: 4px; padding: 0 6px; background-color: transparent; }}
        """,
        'form_label': f"color: {lbl_color}; font-size: {sz_base}px; font-family: '{MASTER_FONT}'; font-weight: 600;",
        'input_readonly': f"""
            QLineEdit {{ padding: 8px 12px; font-size: {sz_base}px; font-family: '{MASTER_FONT}'; border: 1px solid {border}; border-radius: 6px; background-color: {bg_alt_row}; color: {text_muted}; letter-spacing: 0.2px; }}
        """,
        'input': f"""
            QLineEdit, QTextEdit, QComboBox {{ padding: 8px 12px; font-size: {sz_input}px; font-family: '{MASTER_FONT}'; border: 1px solid {border}; border-radius: 6px; background-color: {bg_input}; color: {text_primary}; selection-background-color: #3b82f6; }}
            QLineEdit:focus, QTextEdit:focus, QComboBox:focus {{ border: 1px solid {border_focus}; background-color: {bg_input_foc}; }}
            QLineEdit:disabled, QTextEdit:disabled {{ color: {text_muted}; background-color: {bg_alt_row}; }}
            QTextEdit {{ padding: 6px 10px; line-height: 1.4; }}
            QDateEdit {{ font-size: {sz_input}px; padding: 2px 10px; }}
            /* FIX: Tambahkan font-size agar placeholder terzoom */
            QLineEdit[custom_italic="true"][is_empty="true"], QTextEdit[custom_italic="true"][is_empty="true"] {{ font-style: italic; font-size: {sz_input}px; color: {text_muted}; }}
            QLineEdit[custom_italic="true"][is_empty="false"], QTextEdit[custom_italic="true"][is_empty="false"] {{ font-style: normal; }}
            {_get_scrollbar_qss(is_dark)}
        """,
        'btn_simpan': f"""
            QPushButton {{ background-color: #2563eb; color: #ffffff; font-size: {sz_input}px; font-family: '{MASTER_FONT}'; font-weight: bold; letter-spacing: 0.8px; border: none; border-radius: 8px; padding: 12px 20px; margin-top: 6px; }}
            QPushButton:hover {{ background-color: #1d4ed8; }}
            QPushButton:pressed {{ background-color: #1e40af; }}
            QPushButton:disabled {{ background-color: #94a3b8; color: #e2e8f0; }}
        """,
        'btn_secondary': f"""
            QPushButton {{ background-color: transparent; color: #2563eb; font-size: {sz_base}px; font-family: '{MASTER_FONT}'; font-weight: 600; border: 1px solid #2563eb; border-radius: 6px; padding: 7px 16px; }}
            QPushButton:hover {{ background-color: #eff6ff; border-color: #1d4ed8; }}
            QPushButton:pressed {{ background-color: #dbeafe; }}
        """,
        'sidebar_container': f"background-color: {bg_sidebar};",
        'sidebar_list': f"""
            QListWidget {{ background-color: transparent; border: none; outline: none; font-family: '{MASTER_FONT}'; font-size: {sz_input}px; }}
            QListWidget::item {{ padding: 14px 16px; border-radius: 6px; margin-bottom: 4px; color: {list_text_color}; }}
            QListWidget::item:hover:!selected {{ background-color: {bg_list_hover}; }}
            QListWidget::item:selected {{ background-color: #3b82f6; color: #ffffff; font-weight: bold; }}
        """,
        'custom_groupbox': f"""
            QGroupBox {{ font-weight: bold; font-size: {sz_title}px; font-family: '{MASTER_FONT}'; color: {page_title_color}; background-color: transparent; border: none; margin-top: 10px; }}
            QGroupBox::title {{ padding: 0; background-color: transparent; }}
        """,
        'lbl_page_title': f""" font-size: {sz_title + 8}px; font-weight: bold; font-family: '{MASTER_FONT}'; margin-bottom: 20px; color: {page_title_color}; """,
        'lbl_hint': f"color: {text_muted}; font-size: {sz_base - 1}px;",
        'lbl_menu': f"font-weight: bold; font-size: 18px; color: #94a3b8; margin-bottom: 10px;"
    }


def get_top_right_styles(is_dark: bool) -> tuple:
    if is_dark:
        btn_style = f"QPushButton {{ font-family: '{MASTER_FONT}'; background-color: #1e293b; color: white; border: 1px solid #24334d; font-weight: bold; border-radius: 4px; }} QPushButton:hover {{ background-color: #2c3e50; border: 1px solid #3b82f6; }}"
    else:
        btn_style = f"QPushButton {{ font-family: '{MASTER_FONT}'; background-color: #edf2f7; color: #2d3748; border: 1px solid #cbd5e1; font-weight: bold; border-radius: 4px; }} QPushButton:hover {{ background-color: #e2e8f0; }}"
    lbl_style = f"font-family: '{MASTER_FONT}'; font-size: 13px; color: #f59e0b; padding: 5px; margin-right: 10px;"
    return btn_style, lbl_style