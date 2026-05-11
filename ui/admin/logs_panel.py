"""
logs_panel.py  –  Activity log viewer (admin sees all, user sees own only).
"""

import tkinter as tk
from tkinter import ttk
from database.db_setup import get_connection
from auth.auth_manager import get_current_user
import utils.theme as T


def _fetch_logs(user_id: int | None = None) -> list[tuple]:
    conn = get_connection()
    if user_id:
        rows = conn.execute("""
            SELECT id, logged_at, username, action, COALESCE(details,'')
            FROM activity_logs WHERE user_id=?
            ORDER BY id DESC
        """, (user_id,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT id, logged_at, username, action, COALESCE(details,'')
            FROM activity_logs
            ORDER BY id DESC
        """).fetchall()
    conn.close()
    return rows


class LogsPanel(tk.Frame):
    def __init__(self, parent, own_only: bool = False):
        super().__init__(parent, bg=T.BG)
        self._own_only = own_only
        self._build()

    def _build(self):
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=24, pady=(20, 6))

        title = "My Activity Log" if self._own_only else "Activity Logs (All Users)"
        tk.Label(bar, text=title, font=("Segoe UI", 16, "bold"),
                 bg=T.BG, fg=T.FG).pack(side="left")
        tk.Button(bar, text="⟳  Refresh", font=("Segoe UI", 9),
                  bg=T.SECONDARY, fg=T.FG, relief="flat", cursor="hand2",
                  padx=10, pady=4, command=self.refresh).pack(side="right")

        # Filters
        sr = tk.Frame(self, bg=T.BG)
        sr.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(sr, text="Search:", font=("Segoe UI", 9),
                 bg=T.BG, fg=T.FG_DIM).pack(side="left")
        self._q = tk.StringVar()
        self._q.trace_add("write", lambda *_: self._filter())
        tk.Entry(sr, textvariable=self._q, font=("Segoe UI", 10),
                 bg=T.SECONDARY, fg=T.FG, insertbackground=T.FG,
                 relief="flat", width=30).pack(side="left", padx=8, ipady=4)
                 
        tk.Label(sr, text="Action:", font=("Segoe UI", 9),
                 bg=T.BG, fg=T.FG_DIM).pack(side="left", padx=(10, 0))

        if self._own_only:
            action_values = ["All", "LOGIN", "SALE", "REFUND"]
        else:
            action_values = ["All", "SALE", "LOGIN", "REFUND", "ADD_STOCK", "RESTOCK", "ERROR", "UPDATE"]

        self._filter_action = ttk.Combobox(sr, values=action_values,
                                           state="readonly", width=15)
        self._filter_action.set("All")
        self._filter_action.pack(side="left", padx=8)
        self._filter_action.bind("<<ComboboxSelected>>", lambda e: self._filter())

        # Treeview
        frame = tk.Frame(self, bg=T.CARD)
        frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        style = T.apply_treeview_style("Logs.Treeview")
        cols = ("id", "time", "user", "action", "details")
        self._tree = ttk.Treeview(frame, columns=cols,
                                  show="headings", style=style)

        widths = [("id","#",40),("time","Date & Time",155),
                  ("user","User",100),("action","Action",130),
                  ("details","Details",400)]
        for col, text, w in widths:
            self._tree.heading(col, text=text, command=lambda c=col: self._sort_tree(c, False))
            self._tree.column(col, width=w,
                              anchor="w" if col == "details" else "center")
                              
        self._tree.bind("<Double-1>", self._on_double_click)

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self._tree.pack(fill="both", expand=True)

        self._rows: list[tuple] = []
        self.refresh()

    def refresh(self):
        user = get_current_user()
        uid = user["id"] if self._own_only else None
        self._rows = _fetch_logs(uid)
        self._populate(self._rows)

    def _populate(self, rows):
        self._tree.delete(*self._tree.get_children())
        for r in rows:
            self._tree.insert("", "end", values=r)

    def _filter(self):
        q = self._q.get().lower()
        act = self._filter_action.get()
        filtered = []
        for r in self._rows:
            # r = (id, time, user, action, details)
            if act != "All" and r[3] != act:
                continue
            if q and not any(q in str(v).lower() for v in r):
                continue
            filtered.append(r)
        self._populate(filtered)

    def _sort_tree(self, col, reverse):
        l = [(self._tree.set(k, col), k) for k in self._tree.get_children("")]
        try:
            # Try numeric sort first (for IDs)
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            l.sort(reverse=reverse)
        for index, (val, k) in enumerate(l):
            self._tree.move(k, "", index)
        self._tree.heading(col, command=lambda: self._sort_tree(col, not reverse))

    def _on_double_click(self, event):
        item = self._tree.selection()
        if not item: return
        values = self._tree.item(item[0], "values")
        if values[3] == "SALE":
            # Extract txn_number from the details field (format: "TXN-... | ₱... — ...")
            details = str(values[4])
            txn_number = None
            if details.startswith("TXN-"):
                txn_number = details.split(" | ")[0].strip()
            
            if txn_number:
                from logic.sales_logic import get_receipt_by_txn
                from ui.user.pos_panel import _ReceiptDialog
                _ReceiptDialog(self, txn_number=txn_number)
            else:
                from tkinter import messagebox
                messagebox.showinfo("Receipt Summary", 
                                    f"ArimaS Receipt\n"
                                    f"------------------------\n"
                                    f"Txn ID: {values[0]}\n"
                                    f"Date: {values[1]}\n"
                                    f"Cashier: {values[2]}\n\n"
                                    f"Items:\n{values[4]}\n"
                                    f"------------------------\n"
                                    f"Thank you!", parent=self)

