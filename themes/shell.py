# themes/shell.py
"""Style ringan untuk kerangka utama aplikasi."""

from utils.typography import MASTER_FONT


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
