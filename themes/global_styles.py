# themes/global_styles.py

"""Stylesheet global kompatibel dengan implementasi themes.py lama."""

from utils.typography import MASTER_FONT

from .base import GLOBAL_BASE_SIZE
from .scrollbar import get_scrollbar_style


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
    {get_scrollbar_style(True)}
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
    {get_scrollbar_style(False)}
"""
