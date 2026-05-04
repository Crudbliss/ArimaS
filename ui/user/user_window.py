"""
user_window.py  –  Window container for the cashier/user role.
Has POS and their own read-only logs.
"""

import tkinter as tk
from tkinter import messagebox
from auth.auth_manager import get_current_user
from utils.theme import BG, CARD, ACCENT, SECONDARY, FG, FG_DIM


class UserWindow:
    def __init__(self, root: tk.Tk, on_logout):
        self.root      = root
        self.on_logout = on_logout
        self.user      = get_current_user()

        self.root.title("Point of Sale — Rosemen Ukay-Ukay")
        self.root.configure(bg=BG)
        self._center(1050, 650)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_layout()
        self._build_sidebar()
        self._create_panels()
        self._show("pos")

    def _center(self, w, h):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _on_close(self):
        if messagebox.askyesno("Exit", "Are you sure you want to exit?",
                               parent=self.root):
            self.root.destroy()
            self.on_logout()

    def _build_layout(self):
        self.sidebar = tk.Frame(self.root, bg=CARD, width=190)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)

    def _build_sidebar(self):
        sb = self.sidebar
        tk.Label(sb, text="👗", font=("Segoe UI", 26), bg=CARD, fg=ACCENT
                 ).pack(pady=(22, 2))
        tk.Label(sb, text="Rosemen Ukay-Ukay", font=("Segoe UI", 10, "bold"),
                 bg=CARD, fg=FG, justify="center").pack()
        tk.Label(sb, text="Cashier", font=("Segoe UI", 8),
                 bg=CARD, fg=FG_DIM).pack(pady=(2, 16))
        tk.Frame(sb, bg=SECONDARY, height=1).pack(fill="x", padx=15)

        self._nav_btns: dict[str, tk.Button] = {}
        for key, label in [("pos", "🛒   Point of Sale"),
                            ("logs", "📋   My Activity Log")]:
            btn = tk.Button(sb, text=label, font=("Segoe UI", 10),
                            bg=CARD, fg=FG_DIM, relief="flat",
                            cursor="hand2", anchor="w", padx=20, pady=10,
                            activebackground=SECONDARY, activeforeground=FG,
                            command=lambda k=key: self._show(k))
            btn.pack(fill="x", pady=1)
            self._nav_btns[key] = btn

        tk.Frame(sb, bg=SECONDARY, height=1).pack(
            fill="x", padx=15, side="bottom", pady=4)
        tk.Button(sb, text="⏻   Logout", font=("Segoe UI", 10),
                  bg=CARD, fg=ACCENT, relief="flat",
                  cursor="hand2", anchor="w", padx=20, pady=10,
                  activebackground=ACCENT, activeforeground=FG,
                  command=self._logout).pack(fill="x", side="bottom")
        tk.Label(sb, text=f"👤  {self.user['username']}",
                 font=("Segoe UI", 9), bg=CARD, fg=FG_DIM
                 ).pack(side="bottom", pady=6)

    def _create_panels(self):
        from ui.user.pos_panel  import PosPanel
        from ui.admin.logs_panel import LogsPanel   # reuse with own_only=True

        self._panels: dict[str, tk.Frame] = {
            "pos":  PosPanel(self.content),
            "logs": LogsPanel(self.content, own_only=True),
        }

    def _show(self, key: str):
        for k, btn in self._nav_btns.items():
            btn.config(bg=SECONDARY if k == key else CARD,
                       fg=FG if k == key else FG_DIM)
        for k, panel in self._panels.items():
            if k == key:
                panel.pack(fill="both", expand=True)
                if hasattr(panel, "refresh"):
                    panel.refresh()
            else:
                panel.pack_forget()

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?",
                               parent=self.root):
            self.root.destroy()
            self.on_logout()
