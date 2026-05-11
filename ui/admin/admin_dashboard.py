"""
admin_dashboard.py  –  Main admin window with sidebar navigation.
  • Clicking the 👗 logo toggles dark/light theme instantly and rebuilds the UI.
"""

import sys
import tkinter as tk
from tkinter import messagebox
import utils.theme as T
from auth.auth_manager import get_current_user

# Panel module paths to flush from sys.modules cache on theme toggle
_PANEL_MODULES = (
    "ui.admin.home_panel",
    "ui.admin.inventory_panel",
    "ui.admin.logs_panel",
    "ui.admin.user_manager",
    "ui.admin.forecast_panel",
)


class AdminDashboard:
    def __init__(self, root: tk.Tk, on_logout):
        self.root       = root
        self.on_logout  = on_logout
        self.user       = get_current_user()
        self._panels: dict[str, tk.Frame] = {}

        self.root.title("Admin — Rosemen Ukay-Ukay")
        self.root.resizable(True, True)
        self.root.state("zoomed")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build()

    # ── Full build ────────────────────────────────────────────────────

    def _build(self):
        self.root.configure(bg=T.BG)

        # Sidebar
        self.sidebar = tk.Frame(self.root, bg=T.CARD, width=210)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        # Content area
        self.content = tk.Frame(self.root, bg=T.BG)
        self.content.pack(side="left", fill="both", expand=True)

        self._build_sidebar()
        self._create_panels()
        self._show("home")

    # ── Sidebar ───────────────────────────────────────────────────────

    def _build_sidebar(self):
        sb = self.sidebar

        # Try to load logo
        try:
            from PIL import Image, ImageTk
            import os
            logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "RosemenLOGO.png"))
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                img.thumbnail((70, 70), Image.Resampling.LANCZOS)
                self._logo_photo = ImageTk.PhotoImage(img)
                self._logo_btn = tk.Button(
                    sb, image=self._logo_photo,
                    bg=T.CARD, relief="flat", cursor="hand2", bd=0,
                    activebackground=T.CARD,
                    command=self._toggle_theme,
                )
                self._logo_btn.image = self._logo_photo  # Prevent garbage collection
            else:
                raise FileNotFoundError
        except Exception:
            self._logo_btn = tk.Button(
                sb, text="👗", font=("Segoe UI", 28),
                bg=T.CARD, fg=T.ACCENT,
                relief="flat", cursor="hand2", bd=0,
                activebackground=T.CARD, activeforeground=T.SECONDARY,
                command=self._toggle_theme,
            )
            
        self._logo_btn.pack(pady=(24, 2))

        tk.Label(sb, text="Rosemen Ukay-Ukay",
                 font=("Trajan Pro 3", 11, "bold"),
                 bg=T.CARD, fg=T.FG, justify="center").pack()
        tk.Label(sb, text="Admin Panel",
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

        # Nav buttons
        self._nav_btns: dict[str, tk.Button] = {}
        nav = [
            ("home",      "🏠   Dashboard"),
            ("inventory", "📦   Inventory"),
            ("forecast",  "📈   Forecast"),
            ("reports",   "📊   Sales Reports"),
            ("logs",      "📋   Activity Logs"),
            ("users",     "👥   User Manager"),
        ]
        for key, label in nav:
            btn = tk.Button(
                sb, text=label, font=("Segoe UI", 10),
                bg=T.CARD, fg=T.FG_DIM, relief="flat",
                cursor="hand2", anchor="w", padx=20, pady=10,
                activebackground=T.SECONDARY, activeforeground=T.FG,
                command=lambda k=key: self._show(k),
            )
            btn.pack(fill="x", pady=1)
            self._nav_btns[key] = btn

        # Bottom
        tk.Frame(sb, bg=T.SECONDARY, height=1).pack(
            fill="x", padx=15, side="bottom", pady=4)
        tk.Button(
            sb, text="🚪   Logout", font=("Segoe UI", 10),
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
        from ui.admin.home_panel      import HomePanel
        from ui.admin.inventory_panel import InventoryPanel
        from ui.admin.logs_panel      import LogsPanel
        from ui.admin.user_manager    import UserManagerPanel
        from ui.admin.forecast_panel  import ForecastPanel
        from ui.admin.reports_panel   import ReportsPanel

        self._panels = {
            "home":      HomePanel(self.content, on_navigate=self._show),
            "inventory": InventoryPanel(self.content),
            "forecast":  ForecastPanel(self.content),
            "reports":   ReportsPanel(self.content),
            "logs":      LogsPanel(self.content),
            "users":     UserManagerPanel(self.content),
        }

    def _show(self, key: str, *args, **kwargs):
        for k, btn in self._nav_btns.items():
            btn.config(bg=T.SECONDARY if k == key else T.CARD,
                       fg=T.FG if k == key else T.FG_DIM)
        for k, panel in self._panels.items():
            if k == key:
                panel.pack(fill="both", expand=True)
                if hasattr(panel, "refresh"):
                    panel.refresh(*args, **kwargs)
            else:
                panel.pack_forget()

    # ── Theme toggle ──────────────────────────────────────────────────

    def _toggle_theme(self):
        """Toggle dark/light mode and rebuild the entire UI."""
        T.toggle_theme()
        T.apply_all_treeview_styles()

        # Flush panel module cache so re-imports pick up new colours
        for key in list(sys.modules.keys()):
            if any(key.startswith(p) for p in _PANEL_MODULES):
                del sys.modules[key]

        # Destroy all child widgets and rebuild from scratch
        for widget in self.root.winfo_children():
            widget.destroy()

        self.sidebar = None
        self.content = None
        self._panels = {}
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
