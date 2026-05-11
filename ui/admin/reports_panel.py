"""
reports_panel.py  –  Custom date-range reports for Admin.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import datetime
import csv
from tkinter import filedialog
from logic.sales_logic import get_custom_report
import utils.theme as T
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from tkcalendar import DateEntry

class ReportsPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=T.BG)
        self._build()
        self.refresh()

    def _build(self):
        # ── Header ───────────────────────────────────────────────────
        header = tk.Frame(self, bg=T.BG)
        header.pack(fill="x", padx=28, pady=(20, 10))

        tk.Label(header, text="Sales Reports", font=("Segoe UI", 16, "bold"), bg=T.BG, fg=T.FG).pack(side="left")

        # ── Date Filter Controls ─────────────────────────────────────
        filter_frame = tk.Frame(self, bg=T.CARD, padx=20, pady=15)
        filter_frame.pack(fill="x", padx=28, pady=(0, 20))

        tk.Label(filter_frame, text="From :", font=("Segoe UI", 10), bg=T.CARD, fg=T.FG_DIM).grid(row=0, column=0, padx=(0, 10))
        self._start_var = tk.StringVar()
        DateEntry(filter_frame, textvariable=self._start_var, date_pattern='yyyy-mm-dd', font=("Segoe UI", 10), width=12,
                  background='darkblue', foreground='white', borderwidth=2).grid(row=0, column=1, ipady=4, padx=(0, 20))

        tk.Label(filter_frame, text="To :", font=("Segoe UI", 10), bg=T.CARD, fg=T.FG_DIM).grid(row=0, column=2, padx=(0, 10))
        self._end_var = tk.StringVar()
        DateEntry(filter_frame, textvariable=self._end_var, date_pattern='yyyy-mm-dd', font=("Segoe UI", 10), width=12,
                  background='darkblue', foreground='white', borderwidth=2).grid(row=0, column=3, ipady=4, padx=(0, 20))

        tk.Button(filter_frame, text="Generate Report", font=("Segoe UI", 9, "bold"), bg=T.ACCENT, fg=T.FG, cursor="hand2", relief="flat", padx=15, pady=4, command=self._generate).grid(row=0, column=4)

        # Presets
        presets_frame = tk.Frame(filter_frame, bg=T.CARD)
        presets_frame.grid(row=1, column=0, columnspan=5, pady=(10, 0), sticky="w")
        tk.Label(presets_frame, text="Presets: ", font=("Segoe UI", 9), bg=T.CARD, fg=T.FG_DIM).pack(side="left")
        
        for p in ["Today", "Last 7 Days", "7 Weeks Ago"]:
            tk.Button(presets_frame, text=p, font=("Segoe UI", 8), bg=T.SECONDARY, fg=T.FG, cursor="hand2", relief="flat", padx=10, command=lambda x=p: self._set_preset(x)).pack(side="left", padx=5)

        # ── Notebook ───────────────────────────────────────────
        style = ttk.Style()
        style.configure("TNotebook.Tab", font=("Segoe UI", 10, "bold"), padding=[15, 5])
        self._notebook = ttk.Notebook(self)
        self._notebook.pack(fill="both", expand=True, padx=28)

        # Tab 1: Sales & Profit
        self._tab_sales = tk.Frame(self._notebook, bg=T.BG)
        self._notebook.add(self._tab_sales, text="Sales & Profit")

        # Tab 2: Category Performance
        self._tab_category = tk.Frame(self._notebook, bg=T.BG)
        self._notebook.add(self._tab_category, text="Category Performance")

        # Summary Cards
        self._cards_frame = tk.Frame(self._tab_sales, bg=T.BG)
        self._cards_frame.pack(fill="x", pady=(0, 20))

        self.lbl_rev = tk.StringVar(value="₱0.00")
        self.lbl_profit = tk.StringVar(value="₱0.00")
        self.lbl_items = tk.StringVar(value="0")
        self.lbl_refunds = tk.StringVar(value="0")

        self._make_card("Total Revenue", self.lbl_rev, T.CHART_ALT)
        self._make_card("Total Profit", self.lbl_profit, "#06d6a0")
        self._make_card("Items Sold", self.lbl_items, T.FG)
        self._make_card("Refunds", self.lbl_refunds, T.FG_DIM)

        # Content row (Tree + Chart)
        row_frame = tk.Frame(self._tab_sales, bg=T.BG)
        row_frame.pack(fill="both", expand=True, pady=(0, 20))

        # Left: Top Sellers
        left_pane = tk.Frame(row_frame, bg=T.BG)
        left_pane.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        tk.Label(left_pane, text="Top Sellers", font=("Segoe UI", 12, "bold"), bg=T.BG, fg=T.FG).pack(anchor="w", pady=(0, 10))

        T.apply_treeview_style("Report.Treeview")
        cols = ("name", "category", "qty", "revenue")
        self._tree = ttk.Treeview(left_pane, columns=cols, show="headings", style="Report.Treeview", height=8)
        
        self._tree.heading("name", text="Product Name")
        self._tree.heading("category", text="Category")
        self._tree.heading("qty", text="Units Sold")
        self._tree.heading("revenue", text="Revenue")

        self._tree.column("name", width=180)
        self._tree.column("category", width=90)
        self._tree.column("qty", width=80, anchor="center")
        self._tree.column("revenue", width=100, anchor="e")

        self._tree.pack(fill="both", expand=True)

        # Right: Chart
        right_pane = tk.Frame(row_frame, bg=T.BG)
        right_pane.pack(side="right", fill="both", expand=True, padx=(10, 0))
        self.lbl_chart_title = tk.Label(right_pane, text="Daily Revenue Trend", font=("Segoe UI", 12, "bold"), bg=T.BG, fg=T.FG)
        self.lbl_chart_title.pack(anchor="w", pady=(0, 10))
        
        self._chart_frame = tk.Frame(right_pane, bg=T.CARD)
        self._chart_frame.pack(fill="both", expand=True)

        # ── Export ───────────────────────────────────────────────────
        tk.Button(self._tab_sales, text="📥  Export Report", font=("Segoe UI", 10, "bold"), bg=T.CARD, fg=T.ACCENT, cursor="hand2", relief="flat", padx=20, pady=8, command=self._export).pack(anchor="e", pady=(0, 20))
        
        self._build_category_tab()

    def _build_category_tab(self):
        row_frame = tk.Frame(self._tab_category, bg=T.BG)
        row_frame.pack(fill="both", expand=True, pady=(20, 20))

        # Left: Data table
        left_pane = tk.Frame(row_frame, bg=T.BG)
        left_pane.pack(side="left", fill="both", expand=True, padx=(0, 10))
        tk.Label(left_pane, text="Category Breakdown", font=("Segoe UI", 12, "bold"), bg=T.BG, fg=T.FG).pack(anchor="w", pady=(0, 10))
        
        cols = ("category", "qty", "revenue")
        self._cat_tree = ttk.Treeview(left_pane, columns=cols, show="headings", style="Report.Treeview", height=10)
        self._cat_tree.heading("category", text="Category")
        self._cat_tree.heading("qty", text="Units Sold")
        self._cat_tree.heading("revenue", text="Revenue")
        self._cat_tree.column("category", width=150)
        self._cat_tree.column("qty", width=100, anchor="center")
        self._cat_tree.column("revenue", width=120, anchor="e")
        self._cat_tree.pack(fill="both", expand=True)

        # Right: Pie Chart
        right_pane = tk.Frame(row_frame, bg=T.BG)
        right_pane.pack(side="right", fill="both", expand=True, padx=(10, 0))
        tk.Label(right_pane, text="Revenue Split by Category", font=("Segoe UI", 12, "bold"), bg=T.BG, fg=T.FG).pack(anchor="w", pady=(0, 10))
        self._cat_chart_frame = tk.Frame(right_pane, bg=T.CARD)
        self._cat_chart_frame.pack(fill="both", expand=True)

    def _make_card(self, title, var, color):
        card = tk.Frame(self._cards_frame, bg=T.CARD, padx=20, pady=15)
        card.pack(side="left", fill="both", expand=True, padx=(0, 15))
        tk.Label(card, text=title, font=("Segoe UI", 10), bg=T.CARD, fg=T.FG_DIM).pack(anchor="w")
        tk.Label(card, textvariable=var, font=("Segoe UI", 18, "bold"), bg=T.CARD, fg=color).pack(anchor="w", pady=(5,0))

    def _set_preset(self, preset):
        today = datetime.date.today()
        end = today
        if preset == "Today":
            start = today
        elif preset == "Last 7 Days":
            start = today - datetime.timedelta(days=7)
        elif preset == "7 Weeks Ago":
            # From exactly 7 weeks ago until today
            start = today - datetime.timedelta(weeks=7)
        else:
            start = today
            
        self._start_var.set(start.strftime("%Y-%m-%d"))
        self._end_var.set(end.strftime("%Y-%m-%d"))
        self._generate()

    def _generate(self):
        start = self._start_var.get()
        end = self._end_var.get()
        
        if not start or not end:
            messagebox.showwarning("Invalid Dates", "Please enter start and end dates.")
            return
            
        chart_title = "Hourly Revenue Trend" if start == end else "Daily Revenue Trend"
        self.lbl_chart_title.config(text=chart_title)

        try:
            report = get_custom_report(start, end)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate report: {e}")
            return
            
        self.lbl_rev.set(f"₱{report['total_revenue']:,.2f}")
        self.lbl_profit.set(f"₱{report.get('total_profit', 0):,.2f}")
        self.lbl_items.set(f"{report['items_sold']:,}")
        self.lbl_refunds.set(f"{report['refund_count']:,}")
        
        self._tree.delete(*self._tree.get_children())
        for item in report['top_sellers']:
            self._tree.insert("", "end", values=(
                item["name"],
                item["category"],
                item["qty"],
                f"₱{item['revenue']:,.2f}"
            ))

        self._draw_chart(report)

    def _draw_chart(self, report):
        chart_data = report.get("chart_data", [])
        for w in self._chart_frame.winfo_children():
            w.destroy()

        if not chart_data:
            tk.Label(self._chart_frame, text="No data to plot.", bg=T.CARD, fg=T.FG_DIM).pack(expand=True)
        else:
            fig = Figure(figsize=(5, 3), dpi=96)
            ax = fig.add_subplot(111)
            
            dates = [d["date"][-5:] for d in chart_data] # MM-DD or HH:MM
            revs = [d["revenue"] for d in chart_data]

            ax.plot(dates, revs, color=T.CHART_BAR, marker="o", linewidth=2, markersize=5)
            ax.fill_between(dates, revs, alpha=0.2, color=T.CHART_BAR)
            
            ax.set_ylabel("Revenue (₱)", fontsize=8)
            ax.tick_params(axis='both', labelsize=8)
            ax.grid(True, linestyle="--", alpha=0.3)
            
            # Rotate dates if too many
            if len(dates) > 5:
                ax.set_xticks(range(len(dates)))
                ax.set_xticklabels(dates, rotation=45)

            fig.tight_layout(pad=1.0)
            
            canvas = FigureCanvasTkAgg(fig, master=self._chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)

        # ── Update Category Tab ──
        for item in self._cat_tree.get_children():
            self._cat_tree.delete(item)
            
        cat_labels = []
        cat_sizes = []
        
        for c in report.get("category_data", []):
            self._cat_tree.insert("", "end", values=(
                c["category"],
                f"{c['qty']:,}",
                f"₱{c['revenue']:,.2f}"
            ))
            if c["revenue"] > 0:
                cat_labels.append(c["category"])
                cat_sizes.append(c["revenue"])

        for widget in self._cat_chart_frame.winfo_children():
            widget.destroy()

        if cat_sizes:
            fig2 = Figure(figsize=(5, 4), dpi=100, facecolor=T.CARD)
            ax2 = fig2.add_subplot(111)
            colors = ["#4cc9f0", "#4361ee", "#7209b7", "#f72585", "#ffb703", "#fb8500"]
            
            ax2.pie(
                cat_sizes, labels=cat_labels, autopct='%1.1f%%',
                startangle=140, colors=colors,
                textprops=dict(color=T.FG),
                wedgeprops=dict(width=0.4, edgecolor=T.CARD)
            )
            ax2.axis('equal')
            fig2.tight_layout()

            canvas2 = FigureCanvasTkAgg(fig2, master=self._cat_chart_frame)
            canvas2.draw()
            canvas2.get_tk_widget().pack(fill="both", expand=True)
        else:
            tk.Label(self._cat_chart_frame, text="No category data available.", bg=T.CARD, fg=T.FG_DIM).pack(pady=50)

    def _export(self):
        start = self._start_var.get()
        end = self._end_var.get()
        
        items = self._tree.get_children()
        if not items:
            messagebox.showwarning("Empty Report", "Nothing to export.")
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile=f"Sales_Report_{start}_to_{end}.csv",
            title="Save Report As"
        )
        
        if not file_path:
            return # User cancelled
            
        try:
            with open(file_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # Write Summary Header
                writer.writerow(["Rosemen Ukay-Ukay Sales Report"])
                writer.writerow(["Period:", f"{start} to {end}"])
                writer.writerow([])
                
                writer.writerow(["Summary"])
                writer.writerow(["Total Revenue", self.lbl_rev.get()])
                writer.writerow(["Total Profit", self.lbl_profit.get()])
                writer.writerow(["Items Sold", self.lbl_items.get()])
                writer.writerow(["Refunds Processed", self.lbl_refunds.get()])
                writer.writerow([])
                
                # Write Top Sellers Table Header
                writer.writerow(["Top Sellers"])
                writer.writerow(["Product Name", "Category", "Units Sold", "Revenue Generated"])
                
                # Write Top Sellers Rows
                for item_id in items:
                    row_values = self._tree.item(item_id)["values"]
                    writer.writerow(row_values)
                    
            messagebox.showinfo("Export Successful", f"Report has been successfully saved to:\n\n{file_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"An error occurred while saving the CSV:\n{e}")

    def refresh(self):
        if not self._start_var.get():
            self._set_preset("Today")
        else:
            self._generate()
