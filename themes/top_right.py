# themes/top_right.py

"""Style widget pada bagian kanan atas aplikasi."""

from utils.typography import MASTER_FONT


def get_top_right_styles(is_dark: bool) -> tuple:
    if is_dark:
        btn_style = f"QPushButton {{ font-family: '{MASTER_FONT}'; background-color: #1e293b; color: white; border: 1px solid #24334d; font-weight: bold; border-radius: 4px; }} QPushButton:hover {{ background-color: #2c3e50; border: 1px solid #3b82f6; }}"
    else:
        btn_style = f"QPushButton {{ font-family: '{MASTER_FONT}'; background-color: #edf2f7; color: #2d3748; border: 1px solid #cbd5e1; font-weight: bold; border-radius: 4px; }} QPushButton:hover {{ background-color: #e2e8f0; }}"
    lbl_style = f"font-family: '{MASTER_FONT}'; font-size: 13px; color: #f59e0b; padding: 5px; margin-right: 10px;"
    return btn_style, lbl_style
