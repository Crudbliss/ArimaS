"""
theme.py  –  Dual-theme system (Dark / Light) with mutable module-level color vars.

Toggle via:   import utils.theme as T; T.toggle_theme()
Check mode:   import utils.theme as T; T.is_dark()
"""

import tkinter as tk
from tkinter import ttk
import matplotlib

# ── Palette definitions ────────────────────────────────────────────────

_DARK = {
    "BG":        "#1a1a2e",
    "CARD":      "#16213e",
    "ACCENT":    "#e94560",
    "SECONDARY": "#0f3460",
    "FG":        "#ffffff",
    "FG_DIM":    "#a8a8b3",
    # Chart colours
    "CHART_BAR":  "#e94560",
    "CHART_HIST": "#4cc9f0",
    "CHART_ALT":  "#ffd166",
    "CHART_RF":   "#ffd166",
}

_LIGHT = {
    "BG":        "#FAF9F6",   # Pale Cream
    "CARD":      "#E6E3DE",   # Linen Beige
    "ACCENT":    "#8B5E3C",   # Dark Amber (readable on beige)
    "SECONDARY": "#A07850",   # Dark Warm Brown (nav active bg)
    "FG":        "#2E2416",   # Deep Espresso (primary text)
    "FG_DIM":    "#5C3D1E",   # Medium Espresso (secondary text / sidebar items)
    # Chart colours
    "CHART_BAR":  "#D4AF7C",
    "CHART_HIST": "#CE9D7A",
    "CHART_ALT":  "#8B6914",  # Dark amber (readable on cream/beige)
    "CHART_RF":   "#7A5C00",
}

_DARK_MPLRC = {
    "figure.facecolor": "#16213e",
    "axes.facecolor":   "#1a1a2e",
    "axes.edgecolor":   "#0f3460",
    "axes.labelcolor":  "#a8a8b3",
    "xtick.color":      "#a8a8b3",
    "ytick.color":      "#a8a8b3",
    "text.color":       "#ffffff",
    "grid.color":       "#0f3460",
    "grid.linestyle":   "--",
    "legend.facecolor": "#16213e",
    "legend.edgecolor": "#0f3460",
}

_LIGHT_MPLRC = {
    "figure.facecolor": "#E6E3DE",
    "axes.facecolor":   "#FAF9F6",
    "axes.edgecolor":   "#CE9D7A",
    "axes.labelcolor":  "#4A4433",
    "xtick.color":      "#4A4433",
    "ytick.color":      "#4A4433",
    "text.color":       "#4A4433",
    "grid.color":       "#CE9D7A",
    "grid.linestyle":   "--",
    "legend.facecolor": "#E6E3DE",
    "legend.edgecolor": "#CE9D7A",
}

# ── Mutable module-level colour vars ──────────────────────────────────
# All panels import these. They are updated in-place on toggle so that
# newly-created widgets (after rebuild) pick up the current values.

BG        = _LIGHT["BG"]
CARD      = _LIGHT["CARD"]
ACCENT    = _LIGHT["ACCENT"]
SECONDARY = _LIGHT["SECONDARY"]
FG        = _LIGHT["FG"]
FG_DIM    = _LIGHT["FG_DIM"]
CHART_BAR  = _LIGHT["CHART_BAR"]
CHART_HIST = _LIGHT["CHART_HIST"]
CHART_ALT  = _LIGHT["CHART_ALT"]
CHART_RF   = _LIGHT["CHART_RF"]

_dark_mode = False

# Apply light chart theme immediately so panels are correct on first boot
matplotlib.rcParams.update(_LIGHT_MPLRC)


def is_dark() -> bool:
    return _dark_mode


def toggle_theme():
    """Switch between dark and light mode. Updates all module-level vars."""
    global _dark_mode
    global BG, CARD, ACCENT, SECONDARY, FG, FG_DIM
    global CHART_BAR, CHART_HIST, CHART_ALT, CHART_RF

    _dark_mode = not _dark_mode
    palette = _DARK if _dark_mode else _LIGHT

    BG        = palette["BG"]
    CARD      = palette["CARD"]
    ACCENT    = palette["ACCENT"]
    SECONDARY = palette["SECONDARY"]
    FG        = palette["FG"]
    FG_DIM    = palette["FG_DIM"]
    CHART_BAR  = palette["CHART_BAR"]
    CHART_HIST = palette["CHART_HIST"]
    CHART_ALT  = palette["CHART_ALT"]
    CHART_RF   = palette["CHART_RF"]

    # Update matplotlib global rcParams so rebuilt charts use new colours
    matplotlib.rcParams.update(_DARK_MPLRC if _dark_mode else _LIGHT_MPLRC)


# ── Treeview styling ──────────────────────────────────────────────────

def apply_treeview_style(name: str = "Dark.Treeview") -> str:
    """Configure a ttk.Treeview style using current theme colours."""
    style = ttk.Style()
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(name,
        background=CARD,
        foreground=FG,
        rowheight=28,
        fieldbackground=CARD,
        borderwidth=0,
        font=("Segoe UI", 10),
    )
    style.configure(f"{name}.Heading",
        background=SECONDARY,
        foreground=FG,
        relief="flat",
        font=("Segoe UI", 10, "bold"),
    )
    style.map(name,
        background=[("selected", ACCENT)],
        foreground=[("selected", FG)],
    )
    return name


def apply_all_treeview_styles():
    """Refresh every named Treeview style used across the app."""
    for name in ("Dark.Treeview", "Home.Treeview", "Inv.Treeview",
                 "Logs.Treeview", "User.Treeview", "POS.Treeview",
                 "Cart.Treeview", "Rec.Treeview"):
        apply_treeview_style(name)
