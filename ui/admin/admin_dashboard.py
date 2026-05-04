"""
admin_dashboard.py  –  Main admin window with sidebar navigation.
"""

import tkinter as tk
from tkinter import messagebox
from auth.auth_manager import get_current_user
from utils.theme import BG, CARD, ACCENT, SECONDARY, FG, FG_DIM


class AdminDashboard:
    def __init__(self, root: tk.Tk, on_logout):
        self.root     = root
        self.on_logout = on_logout
        self.user     = get_current_user()

        self.root.title("Admin — Rosemen Ukay-Ukay")
        self.root.configure(bg=BG)
        self._center(1150, 680)
        self.root.resizable(True, True)
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_layout()
        self._build_sidebar()
        self._create_panels()
        self._show("home")

    # ── Window helpers ────────────────────────────────────────────────

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

    # ── Layout ────────────────────────────────────────────────────────

    def _build_layout(self):
        # Left sidebar
        self.sidebar = tk.Frame(self.root, bg=CARD, width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Right content area
        self.content = tk.Frame(self.root, bg=BG)
        self.content.pack(side="left", fill="both", expand=True)

    def _build_sidebar(self):
        sb = self.sidebar

        # Logo block
        tk.Label(sb, text="👗", font=("Segoe UI", 28),
                 bg=CARD, fg=ACCENT).pack(pady=(24, 2))
        tk.Label(sb, text="Rosemen Ukay-Ukay", font=("Segoe UI", 11, "bold"),
                 bg=CARD, fg=FG, justify="center").pack()
        tk.Label(sb, text="Admin Panel", font=("Segoe UI", 8),
                 bg=CARD, fg=FG_DIM).pack(pady=(2, 16))

        tk.Frame(sb, bg=SECONDARY, height=1).pack(fill="x", padx=15)

        # Nav items
        self._nav_btns: dict[str, tk.Button] = {}
        nav = [
            ("home",      "🏠   Dashboard"),
            ("inventory", "📦   Inventory"),
            ("forecast",  "📈   Forecast"),
            ("logs",      "📋   Activity Logs"),
            ("users",     "👥   User Manager"),
        ]
        for key, label in nav:
            btn = tk.Button(
                sb, text=label, font=("Segoe UI", 10),
                bg=CARD, fg=FG_DIM, relief="flat",
                cursor="hand2", anchor="w", padx=20, pady=10,
                activebackground=SECONDARY, activeforeground=FG,
                command=lambda k=key: self._show(k),
            )
            btn.pack(fill="x", pady=1)
            self._nav_btns[key] = btn

        # Bottom section
        tk.Frame(sb, bg=SECONDARY, height=1).pack(
            fill="x", padx=15, side="bottom", pady=4)

        tk.Button(
            sb, text="⏻   Logout", font=("Segoe UI", 10),
            bg=CARD, fg=ACCENT, relief="flat",
            cursor="hand2", anchor="w", padx=20, pady=10,
            activebackground=ACCENT, activeforeground=FG,
            command=self._logout,
        ).pack(fill="x", side="bottom")

        tk.Label(sb, text=f"👤  {self.user['username']}",
                 font=("Segoe UI", 9), bg=CARD, fg=FG_DIM
                 ).pack(side="bottom", pady=6)

    # ── Panels ────────────────────────────────────────────────────────

    def _create_panels(self):
        from ui.admin.home_panel      import HomePanel
        from ui.admin.inventory_panel import InventoryPanel
        from ui.admin.logs_panel      import LogsPanel
        from ui.admin.user_manager    import UserManagerPanel
        from ui.admin.forecast_panel  import ForecastPanel

        self._panels: dict[str, tk.Frame] = {
            "home":      HomePanel(self.content),
            "inventory": InventoryPanel(self.content),
            "logs":      LogsPanel(self.content),
            "users":     UserManagerPanel(self.content),
            "forecast":  ForecastPanel(self.content),
        }

    def _show(self, key: str):
        for k, btn in self._nav_btns.items():
            if k == key:
                btn.config(bg=SECONDARY, fg=FG)
            else:
                btn.config(bg=CARD, fg=FG_DIM)

        for k, panel in self._panels.items():
            if k == key:
                panel.pack(fill="both", expand=True)
                if hasattr(panel, "refresh"):
                    panel.refresh()
            else:
                panel.pack_forget()

    # ── Logout ────────────────────────────────────────────────────────

    def _logout(self):
        if messagebox.askyesno("Logout", "Are you sure you want to logout?",
                               parent=self.root):
            self.root.destroy()
            self.on_logout()
