"""
home_panel.py  –  Admin dashboard home:
  • Stat cards (Low Stock hidden when 0; Total Stock cycles per-product on click)
  • Sales chart with Daily / Weekly / Monthly / Yearly toggle
  • Low Stock table directly below "Sales Revenue" label (hidden when 0)
"""

import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import utils.theme as T
from utils.theme import apply_treeview_style
from logic.inventory_logic import get_dashboard_stats, get_low_stock, get_all_products
from database.db_setup import get_connection

PERIODS = ["Daily", "Weekly", "Monthly", "Yearly"]


def _fetch_sales_data(period: str) -> tuple[list[str], list[float]]:
    conn = get_connection()
    if period == "Daily":
        rows = conn.execute("""
            SELECT date(sold_at,'localtime'), COALESCE(SUM(total_amount),0)
            FROM sales
            WHERE date(sold_at,'localtime') >= date('now','localtime','-13 days')
            GROUP BY date(sold_at,'localtime') ORDER BY 1
        """).fetchall()
        labels = [r[0][5:] for r in rows]
    elif period == "Weekly":
        rows = conn.execute("""
            SELECT strftime('%Y-W%W',sold_at,'localtime'), COALESCE(SUM(total_amount),0)
            FROM sales
            WHERE date(sold_at,'localtime') >= date('now','localtime','-83 days')
            GROUP BY 1 ORDER BY 1
        """).fetchall()
        labels = [r[0][5:] for r in rows]
    elif period == "Monthly":
        rows = conn.execute("""
            SELECT strftime('%Y-%m',sold_at,'localtime'), COALESCE(SUM(total_amount),0)
            FROM sales
            WHERE date(sold_at,'localtime') >= date('now','localtime','-364 days')
            GROUP BY 1 ORDER BY 1
        """).fetchall()
        labels = [r[0] for r in rows]
    else:
        rows = conn.execute("""
            SELECT strftime('%Y',sold_at,'localtime'), COALESCE(SUM(total_amount),0)
            FROM sales GROUP BY 1 ORDER BY 1
        """).fetchall()
        labels = [r[0] for r in rows]
    conn.close()
    return labels, [float(r[1]) for r in rows]


class HomePanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=T.BG)
        self._period        = tk.StringVar(value="Daily")
        self._chart_canvas  = None
        self._stock_idx     = -1
        self._all_products: list[dict] = []
        self._build()

    # ── Build ─────────────────────────────────────────────────────────

    def _build(self):
        outer = tk.Frame(self, bg=T.BG)
        outer.pack(fill="both", expand=True)

        # Title row
        title_row = tk.Frame(outer, bg=T.BG)
        title_row.pack(fill="x", padx=28, pady=(20, 6))
        tk.Label(title_row, text="Dashboard Overview",
                 font=("Segoe UI", 16, "bold"), bg=T.BG, fg=T.FG).pack(side="left")
        tk.Button(title_row, text="⟳  Refresh", font=("Segoe UI", 9),
                  bg=T.SECONDARY, fg=T.FG, relief="flat", cursor="hand2",
                  padx=10, pady=4, command=self.refresh).pack(side="right")

        # Stat cards row
        self._cards_frame = tk.Frame(outer, bg=T.BG)
        self._cards_frame.pack(fill="x", padx=20, pady=(0, 10))

        # ── Chart section ─────────────────────────────────────────────
        chart_section = tk.Frame(outer, bg=T.BG)
        chart_section.pack(fill="both", expand=True, padx=28, pady=(0, 16))

        # "Sales Revenue" header + toggle buttons
        chart_hdr = tk.Frame(chart_section, bg=T.BG)
        chart_hdr.pack(fill="x", pady=(0, 4))
        tk.Label(chart_hdr, text="Sales Revenue",
                 font=("Segoe UI", 12, "bold"), bg=T.BG, fg=T.FG).pack(side="left")
        toggle_frame = tk.Frame(chart_hdr, bg=T.BG)
        toggle_frame.pack(side="right")
        self._period_btns: dict[str, tk.Button] = {}
        for p in PERIODS:
            btn = tk.Button(toggle_frame, text=p, font=("Segoe UI", 9),
                            relief="flat", cursor="hand2", padx=12, pady=4,
                            command=lambda x=p: self._switch_period(x))
            btn.pack(side="left", padx=2)
            self._period_btns[p] = btn

        # Low Stock section — sits directly below "Sales Revenue" heading
        self._low_section = tk.Frame(chart_section, bg=T.BG)
        # (packed conditionally in _refresh_low_stock)

        self._low_title = tk.Label(
            self._low_section,
            text="Low / Out-of-Stock Alerts",
            font=("Segoe UI", 11, "bold"), bg=T.BG, fg=T.ACCENT,
        )
        tree_container = tk.Frame(self._low_section, bg=T.CARD)

        style = apply_treeview_style("Home.Treeview")
        self._low_tree = ttk.Treeview(tree_container, columns=("name","stock","reorder"),
                                      show="headings", style=style, height=4)
        self._low_tree.heading("name",    text="Product")
        self._low_tree.heading("stock",   text="Stock (pcs)")
        self._low_tree.heading("reorder", text="Reorder Level")
        self._low_tree.column("name",    width=240)
        self._low_tree.column("stock",   width=140, anchor="center")
        self._low_tree.column("reorder", width=140, anchor="center")
        vsb = ttk.Scrollbar(tree_container, orient="vertical",
                            command=self._low_tree.yview)
        self._low_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._low_tree.pack(fill="x")
        self._tree_container = tree_container

        # Chart frame — below low stock
        self._chart_frame = tk.Frame(chart_section, bg=T.CARD, height=230)
        self._chart_frame.pack(fill="both", expand=True)
        self._chart_frame.pack_propagate(False)

        self.refresh()

    # ── Stat Cards ────────────────────────────────────────────────────

    def _make_card(self, parent, label: str, value: str, color: str,
                   on_click=None) -> tuple[tk.Frame, tk.Label, tk.Label]:
        card = tk.Frame(parent, bg=T.CARD, padx=18, pady=14,
                        cursor="hand2" if on_click else "")
        card.pack(side="left", fill="x", expand=True, padx=6)
        val_lbl = tk.Label(card, text=value, font=("Segoe UI", 20, "bold"),
                           bg=T.CARD, fg=color)
        val_lbl.pack(anchor="w")
        sub_lbl = tk.Label(card, text=label, font=("Segoe UI", 8),
                           bg=T.CARD, fg=T.FG_DIM)
        sub_lbl.pack(anchor="w", pady=(2, 0))
        if on_click:
            for w in (card, val_lbl, sub_lbl):
                w.bind("<Button-1>", lambda e: on_click())
                w.bind("<Enter>", lambda e, f=card: f.config(bg="#1f2d4a"))
                w.bind("<Leave>", lambda e, f=card: f.config(bg=T.CARD))
        return card, val_lbl, sub_lbl

    def _build_cards(self, stats: dict):
        for w in self._cards_frame.winfo_children():
            w.destroy()

        self._make_card(self._cards_frame, "Total Products",
                        str(stats["total_products"]), T.FG)

        # Clickable Total Stock card — cycles through all products
        self._make_card(
            self._cards_frame,
            self._stock_card_sublabel(),
            self._stock_card_value(),
            T.CHART_HIST,
            on_click=self._cycle_stock,
        )

        # Low Stock card — hidden when 0
        if stats["low_stock"] > 0:
            self._make_card(self._cards_frame, "Low Stock Alerts",
                            str(stats["low_stock"]), T.ACCENT)

        self._make_card(self._cards_frame, "Today's Sales",
                        str(stats["today_sales"]), "#06d6a0")
        self._make_card(self._cards_frame, "Today's Revenue",
                        f"P{stats['today_revenue']:,.2f}", T.CHART_ALT)

    def _stock_card_value(self) -> str:
        if self._stock_idx == -1 or not self._all_products:
            total = sum(p["stock_pieces"] for p in self._all_products) if self._all_products else 0
            return f"{total:,}"
        p = self._all_products[self._stock_idx]
        return str(p["stock_pieces"])

    def _stock_card_sublabel(self) -> str:
        if self._stock_idx == -1 or not self._all_products:
            return "Total Stock (pcs)  [ click to filter ]"
        p = self._all_products[self._stock_idx]
        idx = self._stock_idx + 1
        total = len(self._all_products)
        return f"{p['name']} Stock  ({idx}/{total}) — click"

    def _cycle_stock(self):
        if not self._all_products:
            return
        self._stock_idx += 1
        if self._stock_idx >= len(self._all_products):
            self._stock_idx = -1
        # Rebuild only cards (cheap)
        stats = get_dashboard_stats()
        self._build_cards(stats)

    # ── Period toggle ─────────────────────────────────────────────────

    def _switch_period(self, period: str):
        self._period.set(period)
        self._draw_chart()
        for p, btn in self._period_btns.items():
            btn.config(bg=T.ACCENT if p == period else T.SECONDARY,
                       fg=T.FG if p == period else T.FG_DIM)

    # ── Chart ─────────────────────────────────────────────────────────

    def _draw_chart(self):
        period = self._period.get()
        labels, values = _fetch_sales_data(period)

        for w in self._chart_frame.winfo_children():
            w.destroy()

        if not values:
            tk.Label(self._chart_frame, text="No sales data for this period.",
                     font=("Segoe UI", 11), bg=T.CARD, fg=T.FG_DIM).pack(expand=True)
            return

        fig = Figure(figsize=(8, 2.5), dpi=96)
        ax  = fig.add_subplot(111)
        x   = range(len(labels))

        bars = ax.bar(x, values, color=T.CHART_BAR, alpha=0.85, width=0.6, zorder=3)
        if bars:
            bars[-1].set_color(T.CHART_ALT)

        if len(labels) <= 15:
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + max(values) * 0.015,
                        f"P{val:,.0f}", ha="center", va="bottom",
                        fontsize=6.5, color=T.FG_DIM)

        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=30 if len(labels) > 7 else 0,
                           fontsize=7.5)
        ax.set_ylabel("Revenue (P)", fontsize=8)
        ax.set_title(f"{period} Sales Revenue", fontsize=10, pad=6)
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        fig.tight_layout(pad=1.0)

        canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._chart_canvas = canvas

    # ── Low Stock ─────────────────────────────────────────────────────

    def _refresh_low_stock(self):
        low = get_low_stock()
        if not low:
            self._low_section.pack_forget()
        else:
            self._low_section.pack(fill="x", pady=(0, 8),
                                   before=self._chart_frame)
            self._low_title.pack(anchor="w", pady=(0, 4))
            self._tree_container.pack(fill="x")

            self._low_tree.delete(*self._low_tree.get_children())
            for item in low:
                tag = "critical" if item["stock"] == 0 else "low"
                self._low_tree.insert("", "end",
                                      values=(item["name"], item["stock"], item["reorder"]),
                                      tags=(tag,))
            self._low_tree.tag_configure("critical", foreground=T.ACCENT)
            self._low_tree.tag_configure("low",      foreground=T.CHART_ALT)

    # ── Full Refresh ──────────────────────────────────────────────────

    def refresh(self):
        self._all_products = get_all_products()
        stats = get_dashboard_stats()

        self._build_cards(stats)

        cur = self._period.get()
        for p, btn in self._period_btns.items():
            btn.config(bg=T.ACCENT if p == cur else T.SECONDARY,
                       fg=T.FG if p == cur else T.FG_DIM)

        self._draw_chart()
        self._refresh_low_stock()
