"""Style komponen umum yang dipakai lintas tab."""

from utils.typography import MASTER_FONT


FADE_NOTIFICATION_STYLE = f"""
    QLabel {{ background-color: rgba(15, 23, 42, 0.95); color: #10b981; font-size: 22px; font-weight: bold; border-radius: 12px; padding: 20px 50px; border: 2px solid #10b981; font-family: '{MASTER_FONT}'; }}
"""

BTN_SIMPAN_CETAK_STYLE = f"""
    QPushButton {{ background-color: #22c55e; color: white; font-weight: bold; font-size: 14px; padding: 10px 40px; border-radius: 6px; border: none; font-family: '{MASTER_FONT}'; }}
    QPushButton:hover   {{ background-color: #16a34a; }}
    QPushButton:pressed {{ background-color: #15803d; }}
"""
