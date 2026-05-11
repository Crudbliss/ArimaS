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
import utils.theme as T
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
        labels = [r[0] for r in rows]
    elif period == "Weekly":
        rows = conn.execute("""
            SELECT strftime('%Y-W%W',sold_at,'localtime'), COALESCE(SUM(total_amount),0)
            FROM sales
            WHERE date(sold_at,'localtime') >= date('now','localtime','-83 days')
            GROUP BY 1 ORDER BY 1
        """).fetchall()
        labels = [r[0] for r in rows]
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

def _fetch_category_data(period: str) -> list[dict]:
    conn = get_connection()
    if period == "Daily":
        where_clause = "date(s.sold_at,'localtime') >= date('now','localtime','-13 days')"
    elif period == "Weekly":
        where_clause = "date(s.sold_at,'localtime') >= date('now','localtime','-83 days')"
    elif period == "Monthly":
        where_clause = "date(s.sold_at,'localtime') >= date('now','localtime','-364 days')"
    else:
        where_clause = "1=1"
        
    rows = conn.execute(f"""
        SELECT p.category, SUM(s.total_amount)
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE s.status = 'completed' AND {where_clause}
        GROUP BY p.category
        ORDER BY SUM(s.total_amount) DESC
    """).fetchall()
    conn.close()
    return [{"category": r[0] or "Uncategorized", "revenue": float(r[1])} for r in rows]


class HomePanel(tk.Frame):
    def __init__(self, parent, on_navigate=None):
        super().__init__(parent, bg=T.BG)
        self.on_navigate = on_navigate
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

        # ── Low Stock section — directly below cards ──────────────────
        self._low_section = tk.Frame(outer, bg=T.BG)
        # (packed conditionally in _refresh_low_stock)

        self._low_title = tk.Label(
            self._low_section,
            text="Low / Out-of-Stock Alerts",
            font=("Segoe UI", 11, "bold"), bg=T.BG, fg=T.ACCENT,
        )
        tree_container = tk.Frame(self._low_section, bg=T.CARD)

        style = T.apply_treeview_style("Home.Treeview")
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

        # ── Chart section — below low stock ───────────────────────────
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

        # Chart frames
        self._charts_container = tk.Frame(chart_section, bg=T.BG, height=400)
        self._charts_container.pack(fill="both", expand=True)
        self._charts_container.pack_propagate(False)

        self._chart_frame = tk.Frame(self._charts_container, bg=T.CARD)
        self._chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))

        self._cat_chart_frame = tk.Frame(self._charts_container, bg=T.CARD)
        self._cat_chart_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))

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
                w.bind("<Enter>", lambda e, f=card: f.config(bg=T.SECONDARY))
                w.bind("<Leave>", lambda e, f=card: f.config(bg=T.CARD))
        return card, val_lbl, sub_lbl

    def _build_cards(self, stats: dict):
        for w in self._cards_frame.winfo_children():
            w.destroy()

        self._make_card(self._cards_frame, "Total Products",
                        str(stats["total_products"]), T.FG,
                        on_click=lambda: self.on_navigate("inventory") if self.on_navigate else None)

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
                            str(stats["low_stock"]), T.ACCENT,
                            on_click=lambda: self.on_navigate("inventory") if self.on_navigate else None)

        self._make_card(self._cards_frame, "Today's Sales",
                        str(stats["today_sales"]), "#06d6a0",
                        on_click=lambda: self.on_navigate("reports") if self.on_navigate else None)
        self._make_card(self._cards_frame, "Today's Revenue",
                        f"P{stats['today_revenue']:,.2f}", T.CHART_ALT,
                        on_click=lambda: self.on_navigate("reports") if self.on_navigate else None)

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

        import datetime
        formatted_labels = []
        footnote = ""

        if period == "Daily":
            for lbl in labels:
                try:
                    dt = datetime.datetime.strptime(lbl, "%Y-%m-%d")
                    formatted_labels.append(dt.strftime("%A"))
                except ValueError:
                    formatted_labels.append(lbl)
            if labels:
                try:
                    dt_first = datetime.datetime.strptime(labels[0], "%Y-%m-%d")
                    footnote = f"Week of {dt_first.strftime('%B %d, %Y')}"
                except ValueError:
                    pass

        elif period == "Weekly":
            for lbl in labels:
                try:
                    year, week = lbl.split('-W')
                    dt = datetime.datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
                    day_of_month = dt.day
                    week_of_month = (day_of_month - 1) // 7 + 1
                    week_str = ["1st", "2nd", "3rd", "4th", "5th"][min(week_of_month-1, 4)] + " Week"
                    formatted_labels.append(week_str)
                except Exception:
                    formatted_labels.append(lbl)
            if labels:
                try:
                    year, week = labels[0].split('-W')
                    dt_first = datetime.datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
                    year_last, week_last = labels[-1].split('-W')
                    dt_last = datetime.datetime.strptime(f"{year_last}-W{week_last}-1", "%Y-W%W-%w")
                    if dt_first.strftime('%B %Y') == dt_last.strftime('%B %Y'):
                        footnote = f"For the month of {dt_first.strftime('%B %Y')}"
                    else:
                        footnote = f"From {dt_first.strftime('%B %Y')} to {dt_last.strftime('%B %Y')}"
                except Exception:
                    pass

        elif period == "Monthly":
            for lbl in labels:
                try:
                    dt = datetime.datetime.strptime(lbl, "%Y-%m")
                    formatted_labels.append(dt.strftime("%B"))
                except ValueError:
                    formatted_labels.append(lbl)
            if labels:
                try:
                    dt_first = datetime.datetime.strptime(labels[0], "%Y-%m")
                    dt_last = datetime.datetime.strptime(labels[-1], "%Y-%m")
                    if dt_first.year == dt_last.year:
                        footnote = f"Year {dt_first.year}"
                    else:
                        footnote = f"Years {dt_first.year} - {dt_last.year}"
                except ValueError:
                    pass

        else:
            formatted_labels = labels

        fig = Figure(figsize=(8, 3.8), dpi=96)
        ax  = fig.add_subplot(111)
        ax.set_facecolor(T.CARD)
        fig.patch.set_facecolor(T.CARD)
        x   = range(len(labels))

        # Use a sleek line graph with filled area instead of bars
        ax.plot(x, values, color=T.CHART_BAR, marker="o", linewidth=2.5, markersize=6, zorder=3, picker=True, pickradius=8)
        ax.fill_between(x, values, alpha=0.15, color=T.CHART_BAR, zorder=2)
        
        # Highlight the last point
        if values:
            ax.plot(x[-1], values[-1], marker="o", color=T.CHART_ALT, markersize=8, zorder=4)

        if len(labels) <= 15:
            for i, val in enumerate(values):
                ax.text(i, val + max(values) * 0.05,
                        f"P{val:,.0f}", ha="center", va="bottom",
                        fontsize=7, color=T.FG_DIM, zorder=5)

        ax.set_xticks(list(x))
        ax.set_xticklabels(formatted_labels, rotation=30 if len(formatted_labels) > 7 else 0,
                           fontsize=7.5)
        ax.set_ylabel("Revenue (P)", fontsize=8)
        
        if footnote:
            ax.set_xlabel(footnote, fontsize=8, color=T.FG_DIM, labelpad=8)
            
        ax.set_title(f"{period} Sales Revenue", fontsize=10, pad=6)
        ax.grid(axis="y", alpha=0.3)
        ax.set_axisbelow(True)
        fig.subplots_adjust(top=0.82, bottom=0.22, left=0.10, right=0.97)
        
        # Connect click event
        fig.canvas.mpl_connect('pick_event', self._on_pick)

        canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._chart_canvas = canvas

        # Draw Category Pie Chart
        for w in self._cat_chart_frame.winfo_children():
            w.destroy()

        cat_data = _fetch_category_data(period)
        if cat_data:
            cat_sizes = [c["revenue"] for c in cat_data if c["revenue"] > 0]
            cat_labels = [c["category"] for c in cat_data if c["revenue"] > 0]

            if cat_sizes:
                fig2 = Figure(figsize=(3, 3.8), dpi=96, facecolor=T.CARD)
                ax2 = fig2.add_subplot(111)
                colors = ["#4cc9f0", "#4361ee", "#7209b7", "#f72585", "#ffb703", "#fb8500"]
                
                ax2.pie(
                    cat_sizes, labels=cat_labels, autopct='%1.1f%%',
                    startangle=140, colors=colors,
                    textprops=dict(color=T.FG, fontsize=7),
                    wedgeprops=dict(width=0.4, edgecolor=T.CARD)
                )
                ax2.axis('equal')
                ax2.set_title(f"{period} Categories", fontsize=10, pad=6, color=T.FG)
                fig2.subplots_adjust(top=0.85, bottom=0.05, left=0.05, right=0.95)

                canvas2 = FigureCanvasTkAgg(fig2, master=self._cat_chart_frame)
                canvas2.draw()
                canvas2.get_tk_widget().pack(fill="both", expand=True)
            else:
                tk.Label(self._cat_chart_frame, text="No category data.", bg=T.CARD, fg=T.FG_DIM).pack(expand=True)
        else:
            tk.Label(self._cat_chart_frame, text="No category data.", bg=T.CARD, fg=T.FG_DIM).pack(expand=True)

    def _on_pick(self, event):
        ind = event.ind[0]
        period = self._period.get()
        labels, values = _fetch_sales_data(period)
        raw_label = labels[ind]
        
        import datetime
        if period == "Daily":
            start_date = raw_label
            end_date = raw_label
        elif period == "Weekly":
            year, week = raw_label.split('-W')
            dt_first = datetime.datetime.strptime(f"{year}-W{week}-1", "%Y-W%W-%w")
            dt_last = dt_first + datetime.timedelta(days=6)
            start_date = dt_first.strftime("%Y-%m-%d")
            end_date = dt_last.strftime("%Y-%m-%d")
        elif period == "Monthly":
            dt_first = datetime.datetime.strptime(raw_label, "%Y-%m")
            if dt_first.month == 12:
                dt_last = dt_first.replace(day=31)
            else:
                dt_last = dt_first.replace(month=dt_first.month+1, day=1) - datetime.timedelta(days=1)
            start_date = dt_first.strftime("%Y-%m-%d")
            end_date = dt_last.strftime("%Y-%m-%d")
        else: # Yearly
            start_date = f"{raw_label}-01-01"
            end_date = f"{raw_label}-12-31"

        if self.on_navigate:
            self.on_navigate("reports", start_date, end_date)

    # ── Low Stock ─────────────────────────────────────────────────────

    def _refresh_low_stock(self):
        low = get_low_stock()
        if not low:
            self._low_section.pack_forget()
        else:
            self._low_section.pack(fill="x", padx=28, pady=(0, 8),
                                   after=self._cards_frame)
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
