"""
user_window.py  –  Cashier window with POS + own logs.
  • Clicking the 👗 logo toggles dark/light theme instantly and rebuilds the UI.
"""

import sys
import tkinter as tk
from tkinter import messagebox
import utils.theme as T
from auth.auth_manager import get_current_user

_PANEL_MODULES = ("ui.user.pos_panel", "ui.admin.logs_panel")


class UserWindow:
    def __init__(self, root: tk.Tk, on_logout):
        self.root      = root
        self.on_logout = on_logout
        self.user      = get_current_user()
        self._panels: dict[str, tk.Frame] = {}

        self.root.title("Point of Sale — Rosemen Ukay-Ukay")
        self.root.resizable(True, True)
        self.root.state("zoomed")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()

    # ── Full build ────────────────────────────────────────────────────

    def _build(self):
        self.root.configure(bg=T.BG)

        self.sidebar = tk.Frame(self.root, bg=T.CARD, width=190)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(self.root, bg=T.BG)
        self.content.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._create_panels()
        self._show("pos")

    # ── Sidebar ───────────────────────────────────────────────────────

    def _build_sidebar(self):
        sb = self.sidebar

        self._logo_btn = tk.Button(
            sb, text="👗", font=("Segoe UI", 26),
            bg=T.CARD, fg=T.ACCENT,
            relief="flat", cursor="hand2", bd=0,
            activebackground=T.CARD, activeforeground=T.SECONDARY,
            command=self._toggle_theme,
        )
        self._logo_btn.pack(pady=(22, 2))

        tk.Label(sb, text="Rosemen Ukay-Ukay",
                 font=("Trajan Pro 3", 11, "bold"),
                 bg=T.CARD, fg=T.FG, justify="center").pack()
        tk.Label(sb, text="Cashier",
                 font=("Segoe UI", 8), bg=T.CARD, fg=T.FG_DIM
                 ).pack(pady=(2, 4))

        mode_text = "🌙 Dark Mode" if T.is_dark() else "☀  Light Mode"
        tk.Button(
            sb, text=mode_text, font=("Segoe UI", 8),
            bg=T.CARD, fg=T.FG_DIM, relief="flat",
            cursor="hand2", bd=0, pady=2,
            activebackground=T.SECONDARY, activeforeground=T.FG,
            command=self._toggle_theme,
        ).pack(pady=(0, 12))

        tk.Frame(sb, bg=T.SECONDARY, height=1).pack(fill="x", padx=15)

        self._nav_btns: dict[str, tk.Button] = {}
        for key, label in [("pos", "🛒   Point of Sale"),
                            ("logs", "📋   My Activity Log")]:
            btn = tk.Button(
                sb, text=label, font=("Segoe UI", 10),
                bg=T.CARD, fg=T.FG_DIM, relief="flat",
                cursor="hand2", anchor="w", padx=20, pady=10,
                activebackground=T.SECONDARY, activeforeground=T.FG,
                command=lambda k=key: self._show(k),
            )
            btn.pack(fill="x", pady=1)
            self._nav_btns[key] = btn

        tk.Frame(sb, bg=T.SECONDARY, height=1).pack(
            fill="x", padx=15, side="bottom", pady=4)
        tk.Button(
            sb, text="⏻   Logout", font=("Segoe UI", 10),
            bg=T.CARD, fg=T.ACCENT, relief="flat",
            cursor="hand2", anchor="w", padx=20, pady=10,
            activebackground=T.ACCENT, activeforeground=T.FG,
            command=self._logout,
        ).pack(fill="x", side="bottom")
        tk.Label(sb, text=f"👤  {self.user['username']}",
                 font=("Segoe UI", 9), bg=T.CARD, fg=T.FG_DIM
                 ).pack(side="bottom", pady=6)

    # ── Panels ────────────────────────────────────────────────────────

    def _create_panels(self):
        from ui.user.pos_panel   import PosPanel
        from ui.admin.logs_panel import LogsPanel

        self._panels = {
            "pos":  PosPanel(self.content),
            "logs": LogsPanel(self.content, own_only=True),
        }

    def _show(self, key: str):
        for k, btn in self._nav_btns.items():
            btn.config(bg=T.SECONDARY if k == key else T.CARD,
                       fg=T.FG if k == key else T.FG_DIM)
        for k, panel in self._panels.items():
            if k == key:
                panel.pack(fill="both", expand=True)
                if hasattr(panel, "refresh"):
                    panel.refresh()
            else:
                panel.pack_forget()

    # ── Theme toggle ──────────────────────────────────────────────────

    def _toggle_theme(self):
        T.toggle_theme()
        T.apply_all_treeview_styles()

        for key in list(sys.modules.keys()):
            if any(key.startswith(p) for p in _PANEL_MODULES):
                del sys.modules[key]

        for widget in self.root.winfo_children():
            widget.destroy()

        self.sidebar  = None
        self.content  = None
        self._panels  = {}
        self._nav_btns = {}

        self._build()

    # ── Window / session ──────────────────────────────────────────────

    def _on_close(self):
        if messagebox.askyesno("Exit", "Are you sure you want to exit?",
                               parent=self.root):
            self.root.destroy()
            self.on_logout()

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?",
                               parent=self.root):
            self.root.destroy()
            self.on_logout()
