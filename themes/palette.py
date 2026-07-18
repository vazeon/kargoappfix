# themes/pallete.py

"""Palette warna terang dan gelap aplikasi."""

from PyQt5.QtGui import QColor, QPalette


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
