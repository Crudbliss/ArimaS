"""
theme.py  –  Shared dark-mode styling for ttk widgets.
"""

from tkinter import ttk

BG        = "#1a1a2e"
CARD      = "#16213e"
ACCENT    = "#e94560"
SECONDARY = "#0f3460"
FG        = "#ffffff"
FG_DIM    = "#a8a8b3"


def apply_treeview_style(name: str = "Dark.Treeview"):
    """Configure a dark ttk.Treeview style. Use name in widget's style= param."""
    style = ttk.Style()
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
