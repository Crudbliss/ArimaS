"""
home_panel.py  –  Admin dashboard home with summary stat cards + low stock list.
"""

import tkinter as tk
from tkinter import ttk
from logic.inventory_logic import get_dashboard_stats, get_low_stock
from utils.theme import BG, CARD, ACCENT, SECONDARY, FG, FG_DIM, apply_treeview_style


class HomePanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self._build()

    # ── Build ─────────────────────────────────────────────────────────

    def _build(self):
        # Title row
        title_row = tk.Frame(self, bg=BG)
        title_row.pack(fill="x", padx=30, pady=(24, 4))
        tk.Label(title_row, text="Dashboard Overview",
                 font=("Segoe UI", 16, "bold"), bg=BG, fg=FG).pack(side="left")
        tk.Button(title_row, text="⟳  Refresh", font=("Segoe UI", 9),
                  bg=SECONDARY, fg=FG, relief="flat", cursor="hand2",
                  padx=10, pady=4, command=self.refresh).pack(side="right")

        # Stat cards row
        self._cards_frame = tk.Frame(self, bg=BG)
        self._cards_frame.pack(fill="x", padx=30, pady=10)

        # Low stock section
        tk.Label(self, text="⚠  Low / Out-of-Stock Items",
                 font=("Segoe UI", 12, "bold"), bg=BG, fg=ACCENT
                 ).pack(anchor="w", padx=30, pady=(10, 4))

        tree_frame = tk.Frame(self, bg=CARD)
        tree_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))

        style_name = apply_treeview_style("Home.Treeview")
        cols = ("name", "stock", "reorder")
        self._tree = ttk.Treeview(tree_frame, columns=cols,
                                  show="headings", style=style_name)
        self._tree.heading("name",    text="Product")
        self._tree.heading("stock",   text="Current Stock (pcs)")
        self._tree.heading("reorder", text="Reorder Level")
        self._tree.column("name",    width=250)
        self._tree.column("stock",   width=180, anchor="center")
        self._tree.column("reorder", width=160, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        self.refresh()

    # ── Stat Card helper ──────────────────────────────────────────────

    def _make_card(self, parent, label: str, value: str, color: str):
        card = tk.Frame(parent, bg=CARD, padx=20, pady=16)
        card.pack(side="left", fill="x", expand=True, padx=8)
        tk.Label(card, text=value, font=("Segoe UI", 22, "bold"),
                 bg=CARD, fg=color).pack(anchor="w")
        tk.Label(card, text=label, font=("Segoe UI", 9),
                 bg=CARD, fg=FG_DIM).pack(anchor="w", pady=(2, 0))

    # ── Refresh ───────────────────────────────────────────────────────

    def refresh(self):
        stats = get_dashboard_stats()

        # Rebuild cards
        for w in self._cards_frame.winfo_children():
            w.destroy()

        self._make_card(self._cards_frame, "Total Products",
                        str(stats["total_products"]), FG)
        self._make_card(self._cards_frame, "Total Stock (pcs)",
                        str(stats["total_stock"]), "#4cc9f0")
        self._make_card(self._cards_frame, "Low Stock Alerts",
                        str(stats["low_stock"]), ACCENT)
        self._make_card(self._cards_frame, "Today's Sales",
                        str(stats["today_sales"]), "#06d6a0")
        self._make_card(self._cards_frame, "Today's Revenue",
                        f"₱{stats['today_revenue']:,.2f}", "#ffd166")

        # Rebuild low-stock tree
        self._tree.delete(*self._tree.get_children())
        for item in get_low_stock():
            tag = "critical" if item["stock"] == 0 else "low"
            self._tree.insert("", "end",
                              values=(item["name"], item["stock"], item["reorder"]),
                              tags=(tag,))

        self._tree.tag_configure("critical", foreground=ACCENT)
        self._tree.tag_configure("low",      foreground="#ffd166")
