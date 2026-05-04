"""
forecast_panel.py  –  Demand forecast chart + reorder recommendations.
  • Model selector: Both | ARIMA | Random Forest
  • Clicking a recommendation row auto-selects the product and runs forecast
  • Combined chart shows both ARIMA and RF lines when "Both" is selected
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
import utils.theme as T
from utils.theme import apply_treeview_style

MODELS = ["Both", "ARIMA", "Random Forest"]


class ForecastPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=T.BG)
        self._products: list[dict] = []
        self._canvas = None
        self._build()

    # ── Build ─────────────────────────────────────────────────────────

    def _build(self):
        # Title bar
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=24, pady=(18, 6))
        tk.Label(bar, text="Demand Forecast & Reorder Recommendations",
                 font=("Segoe UI", 16, "bold"), bg=T.BG, fg=T.FG).pack(side="left")

        # Controls row
        ctrl = tk.Frame(self, bg=T.BG)
        ctrl.pack(fill="x", padx=24, pady=(0, 8))

        tk.Label(ctrl, text="Product:", font=("Segoe UI", 9),
                 bg=T.BG, fg=T.FG_DIM).pack(side="left")
        self._prod_var = tk.StringVar()
        self._prod_cb  = ttk.Combobox(ctrl, textvariable=self._prod_var,
                                      state="readonly", width=22,
                                      font=("Segoe UI", 10))
        self._prod_cb.pack(side="left", padx=(8, 20))

        tk.Label(ctrl, text="Model:", font=("Segoe UI", 9),
                 bg=T.BG, fg=T.FG_DIM).pack(side="left")
        self._model_var = tk.StringVar(value="Both")
        for m in MODELS:
            tk.Radiobutton(ctrl, text=m, variable=self._model_var, value=m,
                           bg=T.BG, fg=T.FG, selectcolor=T.SECONDARY,
                           activebackground=T.BG, font=("Segoe UI", 9),
                           command=self._run_forecast
                           ).pack(side="left", padx=6)

        tk.Button(ctrl, text="▶  Run Forecast", font=("Segoe UI", 9, "bold"),
                  bg=T.ACCENT, fg=T.FG, relief="flat", cursor="hand2",
                  padx=12, pady=4, command=self._run_forecast
                  ).pack(side="left", padx=(16, 0))

        self._status_var = tk.StringVar(value="Select a product and click Run Forecast.")
        tk.Label(ctrl, textvariable=self._status_var, font=("Segoe UI", 9),
                 bg=T.BG, fg=T.FG_DIM).pack(side="left", padx=16)

        # Main body — chart left, recommendations right
        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 12))

        # Left: chart
        self._chart_frame = tk.Frame(body, bg=T.CARD)
        self._chart_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(self._chart_frame,
                 text="📊\n\nSelect a product and model,\nthen click Run Forecast.",
                 font=("Segoe UI", 12), bg=T.CARD, fg=T.FG_DIM, justify="center"
                 ).pack(expand=True)

        # Right: recommendations
        right = tk.Frame(body, bg=T.BG, width=420)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        hdr = tk.Frame(right, bg=T.BG)
        hdr.pack(fill="x", pady=(0, 6))
        tk.Label(hdr, text="14-Day Reorder Recommendations",
                 font=("Segoe UI", 11, "bold"), bg=T.BG, fg=T.FG).pack(side="left")
        tk.Button(hdr, text="⟳", font=("Segoe UI", 10), bg=T.SECONDARY, fg=T.FG,
                  relief="flat", cursor="hand2", padx=8,
                  command=self._load_recommendations).pack(side="right")

        tk.Label(right, text="Click a row to run its forecast  •  ARIMA + RF averaged",
                 font=("Segoe UI", 8), bg=T.BG, fg=T.FG_DIM).pack(anchor="w", pady=(0, 6))

        rec_frame = tk.Frame(right, bg=T.CARD)
        rec_frame.pack(fill="both", expand=True)

        style = apply_treeview_style("Rec.Treeview")
        cols  = ("status", "name", "stock", "demand", "order")
        self._rec_tree = ttk.Treeview(rec_frame, columns=cols,
                                      show="headings", style=style)

        for col, text, w, anchor in [
            ("status", "Status",       68,  "center"),
            ("name",   "Product",     145,  "w"),
            ("stock",  "Stock",        58,  "center"),
            ("demand", "14d Demand",   80,  "center"),
            ("order",  "Sacks Needed", 80,  "center"),
        ]:
            self._rec_tree.heading(col, text=text)
            self._rec_tree.column(col, width=w, anchor=anchor, minwidth=w)

        vsb = ttk.Scrollbar(rec_frame, orient="vertical",
                            command=self._rec_tree.yview)
        self._rec_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._rec_tree.pack(fill="both", expand=True)

        self._rec_tree.bind("<<TreeviewSelect>>", self._on_rec_select)
        self._load_products()

    # ── Data ─────────────────────────────────────────────────────────

    def _load_products(self):
        self._products = get_all_products_basic()
        self._prod_cb["values"] = [p["name"] for p in self._products]
        if self._products:
            self._prod_cb.current(0)

    def refresh(self):
        self._load_products()
        self._load_recommendations()

    # ── Rec row click ─────────────────────────────────────────────────

    def _on_rec_select(self, _event):
        sel = self._rec_tree.selection()
        if not sel:
            return
        name = self._rec_tree.item(sel[0])["values"][1]
        if name in self._prod_cb["values"]:
            self._prod_var.set(name)
            self._run_forecast()

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
        model = self._model_var.get()

        def worker():
            if model == "ARIMA":
                a = arima_forecast(product["id"], 14)
                r = None
            elif model == "Random Forest":
                a = None
                r = rf_forecast(product["id"], 14)
            else:
                a = arima_forecast(product["id"], 14)
                r = rf_forecast(product["id"], 14)
            self.after(0, lambda: self._display(a, r, name, model))

        threading.Thread(target=worker, daemon=True).start()

    def _display(self, arima, rf, name: str, model: str):
        parts = []
        if arima and not arima["error"]:
            parts.append(f"ARIMA: {arima['total_predicted']:.1f} units")
        elif arima and arima["error"]:
            parts.append(f"ARIMA error: {arima['error']}")
        if rf and not rf["error"]:
            parts.append(f"RF: {rf['total_predicted']:.1f} units")
        elif rf and rf["error"]:
            parts.append(f"RF error: {rf['error']}")

        self._status_var.set(
            f"{name}  —  " + "  |  ".join(parts) if parts else "No forecast available."
        )
        self._draw_chart(arima, rf, name, model)

    def _draw_chart(self, arima, rf, name: str, model: str):
        for w in self._chart_frame.winfo_children():
            w.destroy()

        has_arima = arima and not arima.get("error")
        has_rf    = rf    and not rf.get("error")
        if not has_arima and not has_rf:
            tk.Label(self._chart_frame,
                     text="Not enough data to generate a forecast.",
                     font=("Segoe UI", 11), bg=T.CARD, fg=T.FG_DIM
                     ).pack(expand=True)
            return

        base     = arima if has_arima else rf
        h_dates  = base["history_dates"][-30:]
        h_values = base["history_values"][-30:]
        offset   = len(h_dates) - 1

        fig = Figure(figsize=(6, 3.8), dpi=96)
        ax  = fig.add_subplot(111)

        ax.plot(range(len(h_dates)), h_values,
                color=T.CHART_HIST, linewidth=1.8, label="Actual", zorder=3)
        ax.fill_between(range(len(h_dates)), h_values,
                        alpha=0.12, color=T.CHART_HIST)

        f_dates = base["forecast_dates"]

        def _plot_forecast(result, color, label):
            f_vals  = result["forecast_values"]
            f_range = range(offset, offset + len(f_vals))
            ax.plot(f_range, [h_values[-1]] + f_vals[:-1],
                    color=color, linewidth=2, linestyle="--", label=label, zorder=3)
            ax.fill_between(f_range, [h_values[-1]] + f_vals[:-1],
                            alpha=0.10, color=color)

        if has_arima:
            _plot_forecast(arima, T.CHART_BAR, "ARIMA")
        if has_rf:
            _plot_forecast(rf,    T.CHART_RF,  "Random Forest")

        ax.axvline(x=offset, color=T.FG_DIM, linewidth=1, linestyle=":", alpha=0.6)

        all_dates = h_dates + list(f_dates)
        tick_pos  = list(range(0, len(all_dates), 5))
        ax.set_xticks(tick_pos)
        ax.set_xticklabels([all_dates[i][5:] for i in tick_pos],
                           rotation=30, fontsize=7)
        ax.set_title(f"{name} — {model} Forecast (14 days)", fontsize=11, pad=8)
        ax.set_ylabel("Units / Day")
        ax.legend(fontsize=8, loc="upper left")
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
            self.after(0, lambda: self._display_recs(recs))

        threading.Thread(target=worker, daemon=True).start()

    def _display_recs(self, recs: list[dict]):
        self._rec_tree.delete(*self._rec_tree.get_children())
        for r in recs:
            tag  = "warn" if r["sacks_to_order"] > 0 else "ok"
            icon = "Reorder" if r["sacks_to_order"] > 0 else "OK"
            self._rec_tree.insert("", "end", tags=(tag,), values=(
                icon,
                r["name"],
                r["current_stock"],
                f"{r['predicted_14d']:.1f}",
                r["sacks_to_order"] if r["sacks_to_order"] > 0 else "-",
            ))
        self._rec_tree.tag_configure("warn", foreground=T.ACCENT)
        self._rec_tree.tag_configure("ok",   foreground="#06d6a0")
        self._status_var.set("Recommendations loaded. Click a row to forecast that product.")
