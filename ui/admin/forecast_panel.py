"""
forecast_panel.py  –  Admin panel: demand forecast chart + reorder recommendations.
"""

import threading
import tkinter as tk
from tkinter import ttk
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from logic.forecast_logic import (
    arima_forecast, rf_forecast, generate_recommendations,
    get_all_products_basic,
)
from utils.theme import BG, CARD, ACCENT, SECONDARY, FG, FG_DIM, apply_treeview_style

# Matplotlib dark style
matplotlib.rcParams.update({
    "figure.facecolor":  "#16213e",
    "axes.facecolor":    "#1a1a2e",
    "axes.edgecolor":    "#0f3460",
    "axes.labelcolor":   "#a8a8b3",
    "xtick.color":       "#a8a8b3",
    "ytick.color":       "#a8a8b3",
    "text.color":        "#ffffff",
    "grid.color":        "#0f3460",
    "grid.linestyle":    "--",
    "legend.facecolor":  "#16213e",
    "legend.edgecolor":  "#0f3460",
})


class ForecastPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG)
        self._products: list[dict] = []
        self._canvas   = None
        self._build()

    # ── Layout ────────────────────────────────────────────────────────

    def _build(self):
        # ── Title bar ────────────────────────────────────────────────
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=24, pady=(18, 6))
        tk.Label(bar, text="Demand Forecast & Reorder Recommendations",
                 font=("Segoe UI", 16, "bold"), bg=BG, fg=FG).pack(side="left")

        # ── Controls row ─────────────────────────────────────────────
        ctrl = tk.Frame(self, bg=BG)
        ctrl.pack(fill="x", padx=24, pady=(0, 8))

        tk.Label(ctrl, text="Product:", font=("Segoe UI", 9),
                 bg=BG, fg=FG_DIM).pack(side="left")
        self._prod_var = tk.StringVar()
        self._prod_cb  = ttk.Combobox(ctrl, textvariable=self._prod_var,
                                      state="readonly", width=22,
                                      font=("Segoe UI", 10))
        self._prod_cb.pack(side="left", padx=(8, 20))

        tk.Label(ctrl, text="Model:", font=("Segoe UI", 9),
                 bg=BG, fg=FG_DIM).pack(side="left")
        self._model_var = tk.StringVar(value="ARIMA")
        for m in ("ARIMA", "Random Forest"):
            tk.Radiobutton(ctrl, text=m, variable=self._model_var, value=m,
                           bg=BG, fg=FG, selectcolor=SECONDARY,
                           activebackground=BG, font=("Segoe UI", 9),
                           command=self._run_forecast
                           ).pack(side="left", padx=6)

        tk.Button(ctrl, text="▶  Run Forecast", font=("Segoe UI", 9, "bold"),
                  bg=ACCENT, fg=FG, relief="flat", cursor="hand2",
                  padx=12, pady=4, command=self._run_forecast
                  ).pack(side="left", padx=(16, 0))

        self._status_var = tk.StringVar(value="Select a product and click Run Forecast.")
        tk.Label(ctrl, textvariable=self._status_var, font=("Segoe UI", 9),
                 bg=BG, fg=FG_DIM).pack(side="left", padx=16)

        # ── Main two-panel split ──────────────────────────────────────
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        # Left: chart
        self._chart_frame = tk.Frame(body, bg=CARD)
        self._chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        self._placeholder = tk.Label(
            self._chart_frame,
            text="📊\n\nSelect a product and model,\nthen click Run Forecast.",
            font=("Segoe UI", 12), bg=CARD, fg=FG_DIM, justify="center"
        )
        self._placeholder.pack(expand=True)

        # Right: recommendations table
        right = tk.Frame(body, bg=BG, width=370)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text="14-Day Reorder Recommendations",
                 font=("Segoe UI", 11, "bold"), bg=BG, fg=FG).pack(anchor="w")
        tk.Label(right, text="(ARIMA + RF averaged)",
                 font=("Segoe UI", 8), bg=BG, fg=FG_DIM).pack(anchor="w", pady=(0, 6))

        tk.Button(right, text="⟳  Refresh Recommendations",
                  font=("Segoe UI", 9), bg=SECONDARY, fg=FG,
                  relief="flat", cursor="hand2", pady=4,
                  command=self._load_recommendations
                  ).pack(fill="x", pady=(0, 8))

        rec_frame = tk.Frame(right, bg=CARD)
        rec_frame.pack(fill="both", expand=True)

        style = apply_treeview_style("Rec.Treeview")
        cols  = ("name", "stock", "demand", "order", "status")
        self._rec_tree = ttk.Treeview(rec_frame, columns=cols,
                                      show="headings", style=style)
        for col, text, w in [
            ("name",   "Product",    130),
            ("stock",  "Stock",       55),
            ("demand", "14d Demand",  80),
            ("order",  "Sacks?",      55),
            ("status", "Status",      70),
        ]:
            self._rec_tree.heading(col, text=text)
            self._rec_tree.column(col, width=w,
                                  anchor="w" if col == "name" else "center")

        vsb = ttk.Scrollbar(rec_frame, orient="vertical",
                            command=self._rec_tree.yview)
        self._rec_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._rec_tree.pack(fill="both", expand=True)

        self._load_products()

    # ── Data loading ─────────────────────────────────────────────────

    def _load_products(self):
        self._products = get_all_products_basic()
        names = [p["name"] for p in self._products]
        self._prod_cb["values"] = names
        if names:
            self._prod_cb.current(0)

    def refresh(self):
        self._load_products()
        self._load_recommendations()

    # ── Forecast ─────────────────────────────────────────────────────

    def _run_forecast(self):
        name = self._prod_var.get()
        if not name:
            return
        product = next((p for p in self._products if p["name"] == name), None)
        if not product:
            return

        self._status_var.set("Running forecast…")
        self.update()

        def worker():
            model = self._model_var.get()
            if model == "ARIMA":
                result = arima_forecast(product["id"], horizon=14)
            else:
                result = rf_forecast(product["id"], horizon=14)
            self.after(0, lambda: self._display_forecast(result, name, model))

        threading.Thread(target=worker, daemon=True).start()

    def _display_forecast(self, result: dict, name: str, model: str):
        if result["error"]:
            self._status_var.set(f"Error: {result['error']}")
            return

        self._status_var.set(
            f"{model} — 14-day predicted demand: "
            f"{result['total_predicted']:.1f} units"
        )
        self._draw_chart(result, name, model)

    def _draw_chart(self, result: dict, name: str, model: str):
        # Destroy old canvas
        for w in self._chart_frame.winfo_children():
            w.destroy()

        fig = Figure(figsize=(6, 3.8), dpi=96)
        ax  = fig.add_subplot(111)

        h_dates = result["history_dates"][-30:]   # last 30 days
        h_vals  = result["history_values"][-30:]
        f_dates = result["forecast_dates"]
        f_vals  = result["forecast_values"]

        ax.plot(range(len(h_dates)), h_vals,
                color="#4cc9f0", linewidth=1.8, label="Actual Sales", zorder=3)
        ax.fill_between(range(len(h_dates)), h_vals,
                        alpha=0.15, color="#4cc9f0")

        offset  = len(h_dates) - 1
        f_range = range(offset, offset + len(f_dates))
        ax.plot(f_range, [h_vals[-1]] + f_vals[:-1],
                color=ACCENT, linewidth=2, linestyle="--",
                label=f"{model} Forecast", zorder=3)
        ax.fill_between(f_range, [h_vals[-1]] + f_vals[:-1],
                        alpha=0.15, color=ACCENT)

        # Vertical separator
        ax.axvline(x=offset, color="#ffd166", linewidth=1, linestyle=":", alpha=0.7)

        # Tick labels: show every 5th date
        all_dates = h_dates + f_dates
        tick_pos  = list(range(0, len(all_dates), 5))
        ax.set_xticks(tick_pos)
        ax.set_xticklabels([all_dates[i][5:] for i in tick_pos],
                           rotation=30, fontsize=7)

        ax.set_title(f"{name} — Demand Forecast ({model})",
                     fontsize=11, pad=8)
        ax.set_ylabel("Units Sold / Day")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        fig.tight_layout()

        canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        self._canvas = canvas

    # ── Recommendations ───────────────────────────────────────────────

    def _load_recommendations(self):
        self._status_var.set("Calculating recommendations…")
        self.update()

        def worker():
            recs = generate_recommendations()
            self.after(0, lambda: self._display_recommendations(recs))

        threading.Thread(target=worker, daemon=True).start()

    def _display_recommendations(self, recs: list[dict]):
        self._rec_tree.delete(*self._rec_tree.get_children())
        for r in recs:
            tag = "warn" if r["sacks_to_order"] > 0 else "ok"
            self._rec_tree.insert("", "end", tags=(tag,), values=(
                r["name"],
                r["current_stock"],
                f"{r['predicted_14d']:.1f}",
                r["sacks_to_order"] if r["sacks_to_order"] > 0 else "—",
                r["status"],
            ))
        self._rec_tree.tag_configure("warn", foreground=ACCENT)
        self._rec_tree.tag_configure("ok",   foreground="#06d6a0")
        self._status_var.set("Recommendations updated.")
