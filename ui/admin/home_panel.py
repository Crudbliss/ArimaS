"""
home_panel.py  –  Admin dashboard home:
  • Stat cards
  • Sales chart with Daily / Weekly / Monthly / Yearly toggle
  • Low Stock table (hidden when count = 0)
"""

import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from logic.inventory_logic import get_dashboard_stats, get_low_stock
from database.db_setup import get_connection
from utils.theme import BG, CARD, ACCENT, SECONDARY, FG, FG_DIM, apply_treeview_style

# ── Matplotlib dark theme ─────────────────────────────────────────────
matplotlib.rcParams.update({
    "figure.facecolor": "#16213e",
    "axes.facecolor":   "#1a1a2e",
    "axes.edgecolor":   "#0f3460",
    "axes.labelcolor":  "#a8a8b3",
    "xtick.color":      "#a8a8b3",
    "ytick.color":      "#a8a8b3",
    "text.color":       "#ffffff",
    "grid.color":       "#0f3460",
    "grid.linestyle":   "--",
})

PERIODS = ["Daily", "Weekly", "Monthly", "Yearly"]


def _fetch_sales_data(period: str) -> tuple[list[str], list[float]]:
    """Return (labels, revenue_values) for the selected period."""
    conn = get_connection()

    if period == "Daily":
        rows = conn.execute("""
            SELECT date(sold_at, 'localtime') AS d, COALESCE(SUM(total_amount),0)
            FROM sales
            WHERE date(sold_at,'localtime') >= date('now','localtime','-13 days')
            GROUP BY d ORDER BY d
        """).fetchall()
        labels = [r[0][5:] for r in rows]   # MM-DD

    elif period == "Weekly":
        rows = conn.execute("""
            SELECT strftime('%Y-W%W', sold_at, 'localtime') AS w,
                   COALESCE(SUM(total_amount),0)
            FROM sales
            WHERE date(sold_at,'localtime') >= date('now','localtime','-83 days')
            GROUP BY w ORDER BY w
        """).fetchall()
        labels = [r[0][5:] for r in rows]   # W##

    elif period == "Monthly":
        rows = conn.execute("""
            SELECT strftime('%Y-%m', sold_at, 'localtime') AS m,
                   COALESCE(SUM(total_amount),0)
            FROM sales
            WHERE date(sold_at,'localtime') >= date('now','localtime','-364 days')
            GROUP BY m ORDER BY m
        """).fetchall()
        labels = [r[0] for r in rows]

    else:   # Yearly
        rows = conn.execute("""
            SELECT strftime('%Y', sold_at, 'localtime') AS y,
                   COALESCE(SUM(total_amount),0)
            FROM sales
            GROUP BY y ORDER BY y
        """).fetchall()
        labels = [r[0] for r in rows]

    conn.close()
    values = [float(r[1]) for r in rows]
    return labels, values


class HomePanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self._period    = tk.StringVar(value="Daily")
        self._chart_canvas = None
        self._build()

    # ── Build ─────────────────────────────────────────────────────────

    def _build(self):
        # Make the panel scrollable by using a canvas + inner frame
        outer = tk.Frame(self, bg=BG)
        outer.pack(fill="both", expand=True)

        # ── Title row ────────────────────────────────────────────────
        title_row = tk.Frame(outer, bg=BG)
        title_row.pack(fill="x", padx=28, pady=(20, 4))
        tk.Label(title_row, text="Dashboard Overview",
                 font=("Segoe UI", 16, "bold"), bg=BG, fg=FG).pack(side="left")
        tk.Button(title_row, text="⟳  Refresh", font=("Segoe UI", 9),
                  bg=SECONDARY, fg=FG, relief="flat", cursor="hand2",
                  padx=10, pady=4, command=self.refresh).pack(side="right")

        # ── Stat cards ───────────────────────────────────────────────
        self._cards_frame = tk.Frame(outer, bg=BG)
        self._cards_frame.pack(fill="x", padx=20, pady=(0, 12))

        # ── Sales chart section ──────────────────────────────────────
        chart_section = tk.Frame(outer, bg=BG)
        chart_section.pack(fill="both", expand=True, padx=28, pady=(0, 10))

        # Chart header
        chart_hdr = tk.Frame(chart_section, bg=BG)
        chart_hdr.pack(fill="x", pady=(0, 6))
        tk.Label(chart_hdr, text="Sales Revenue",
                 font=("Segoe UI", 12, "bold"), bg=BG, fg=FG).pack(side="left")

        # Period toggle buttons
        toggle_frame = tk.Frame(chart_hdr, bg=BG)
        toggle_frame.pack(side="right")
        self._period_btns: dict[str, tk.Button] = {}
        for p in PERIODS:
            btn = tk.Button(
                toggle_frame, text=p, font=("Segoe UI", 9),
                relief="flat", cursor="hand2", padx=12, pady=4,
                command=lambda x=p: self._switch_period(x),
            )
            btn.pack(side="left", padx=2)
            self._period_btns[p] = btn

        # Chart container
        self._chart_frame = tk.Frame(chart_section, bg=CARD, height=240)
        self._chart_frame.pack(fill="x")
        self._chart_frame.pack_propagate(False)

        # ── Low Stock section (conditionally shown) ──────────────────
        self._low_section = tk.Frame(outer, bg=BG)
        self._low_section.pack(fill="x", padx=28, pady=(4, 16))

        self._low_title = tk.Label(
            self._low_section,
            text="Low / Out-of-Stock Alerts",
            font=("Segoe UI", 12, "bold"), bg=BG, fg=ACCENT,
        )
        tree_container = tk.Frame(self._low_section, bg=CARD)

        style = apply_treeview_style("Home.Treeview")
        cols = ("name", "stock", "reorder")
        self._tree = ttk.Treeview(tree_container, columns=cols,
                                  show="headings", style=style, height=5)
        self._tree.heading("name",    text="Product")
        self._tree.heading("stock",   text="Stock (pcs)")
        self._tree.heading("reorder", text="Reorder Level")
        self._tree.column("name",    width=260)
        self._tree.column("stock",   width=160, anchor="center")
        self._tree.column("reorder", width=160, anchor="center")

        vsb = ttk.Scrollbar(tree_container, orient="vertical",
                            command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="x")

        self._low_title_widget   = self._low_title
        self._tree_container     = tree_container

        self.refresh()

    # ── Cards helper ──────────────────────────────────────────────────

    def _make_card(self, parent, label: str, value: str, color: str):
        card = tk.Frame(parent, bg=CARD, padx=20, pady=14)
        card.pack(side="left", fill="x", expand=True, padx=6)
        tk.Label(card, text=value, font=("Segoe UI", 20, "bold"),
                 bg=CARD, fg=color).pack(anchor="w")
        tk.Label(card, text=label, font=("Segoe UI", 8),
                 bg=CARD, fg=FG_DIM).pack(anchor="w", pady=(2, 0))

    # ── Period toggle ─────────────────────────────────────────────────

    def _switch_period(self, period: str):
        self._period.set(period)
        self._draw_chart()
        # Update button highlight
        for p, btn in self._period_btns.items():
            if p == period:
                btn.config(bg=ACCENT, fg=FG)
            else:
                btn.config(bg=SECONDARY, fg=FG_DIM)

    # ── Chart ─────────────────────────────────────────────────────────

    def _draw_chart(self):
        period = self._period.get()
        labels, values = _fetch_sales_data(period)

        # Destroy old canvas
        for w in self._chart_frame.winfo_children():
            w.destroy()

        if not values:
            tk.Label(self._chart_frame, text="No sales data for this period.",
                     font=("Segoe UI", 11), bg=CARD, fg=FG_DIM
                     ).pack(expand=True)
            return

        fig = Figure(figsize=(8, 2.6), dpi=96)
        ax  = fig.add_subplot(111)

        # Bar chart
        x     = range(len(labels))
        bars  = ax.bar(x, values, color=ACCENT, alpha=0.85, width=0.6, zorder=3)

        # Highlight the last bar (most recent)
        if bars:
            bars[-1].set_color("#ffd166")

        # Value labels on bars (only if not too many)
        if len(labels) <= 15:
            for bar, val in zip(bars, values):
                ax.text(bar.get_x() + bar.get_width() / 2,
                        bar.get_height() + max(values) * 0.01,
                        f"₱{val:,.0f}", ha="center", va="bottom",
                        fontsize=6.5, color=FG_DIM)

        ax.set_xticks(list(x))
        ax.set_xticklabels(labels, rotation=30 if len(labels) > 7 else 0,
                           fontsize=7.5)
        ax.set_ylabel("Revenue (₱)", fontsize=8)
        ax.set_title(f"{period} Sales Revenue", fontsize=10, pad=6)
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        fig.tight_layout(pad=1.2)

        canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._chart_canvas = canvas

    # ── Low stock section ─────────────────────────────────────────────

    def _refresh_low_stock(self):
        low = get_low_stock()

        if not low:
            # Hide the whole section
            self._low_title_widget.pack_forget()
            self._tree_container.pack_forget()
        else:
            # Show section
            self._low_title_widget.pack(anchor="w", pady=(0, 6))
            self._tree_container.pack(fill="x")

            self._tree.delete(*self._tree.get_children())
            for item in low:
                tag = "critical" if item["stock"] == 0 else "low"
                self._tree.insert("", "end",
                                  values=(item["name"], item["stock"], item["reorder"]),
                                  tags=(tag,))
            self._tree.tag_configure("critical", foreground=ACCENT)
            self._tree.tag_configure("low",      foreground="#ffd166")

    # ── Full refresh ──────────────────────────────────────────────────

    def refresh(self):
        stats = get_dashboard_stats()

        # Rebuild stat cards
        for w in self._cards_frame.winfo_children():
            w.destroy()
        self._make_card(self._cards_frame, "Total Products",
                        str(stats["total_products"]), FG)
        self._make_card(self._cards_frame, "Total Stock (pcs)",
                        f"{stats['total_stock']:,}", "#4cc9f0")
        self._make_card(self._cards_frame, "Low Stock Alerts",
                        str(stats["low_stock"]), ACCENT if stats["low_stock"] else "#06d6a0")
        self._make_card(self._cards_frame, "Today's Sales",
                        str(stats["today_sales"]), "#06d6a0")
        self._make_card(self._cards_frame, "Today's Revenue",
                        f"P{stats['today_revenue']:,.2f}", "#ffd166")

        # Highlight active period button
        cur = self._period.get()
        for p, btn in self._period_btns.items():
            btn.config(bg=ACCENT if p == cur else SECONDARY,
                       fg=FG if p == cur else FG_DIM)

        self._draw_chart()
        self._refresh_low_stock()
