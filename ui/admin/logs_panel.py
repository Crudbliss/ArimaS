"""
logs_panel.py  –  Activity log viewer (admin sees all, user sees own only).
"""

import tkinter as tk
from tkinter import ttk
from database.db_setup import get_connection
from auth.auth_manager import get_current_user
from utils.theme import BG, CARD, SECONDARY, FG, FG_DIM, apply_treeview_style


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
        super().__init__(parent, bg=BG)
        self._own_only = own_only
        self._build()

    def _build(self):
        bar = tk.Frame(self, bg=BG)
        bar.pack(fill="x", padx=24, pady=(20, 6))

        title = "My Activity Log" if self._own_only else "Activity Logs (All Users)"
        tk.Label(bar, text=title, font=("Segoe UI", 16, "bold"),
                 bg=BG, fg=FG).pack(side="left")
        tk.Button(bar, text="⟳  Refresh", font=("Segoe UI", 9),
                  bg=SECONDARY, fg=FG, relief="flat", cursor="hand2",
                  padx=10, pady=4, command=self.refresh).pack(side="right")

        # Search
        sr = tk.Frame(self, bg=BG)
        sr.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(sr, text="Filter:", font=("Segoe UI", 9),
                 bg=BG, fg=FG_DIM).pack(side="left")
        self._q = tk.StringVar()
        self._q.trace_add("write", lambda *_: self._filter())
        tk.Entry(sr, textvariable=self._q, font=("Segoe UI", 10),
                 bg=SECONDARY, fg=FG, insertbackground=FG,
                 relief="flat", width=30).pack(side="left", padx=8, ipady=4)

        # Treeview
        frame = tk.Frame(self, bg=CARD)
        frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        style = apply_treeview_style("Logs.Treeview")
        cols = ("id", "time", "user", "action", "details")
        self._tree = ttk.Treeview(frame, columns=cols,
                                  show="headings", style=style)

        widths = [("id","#",40),("time","Date & Time",155),
                  ("user","User",100),("action","Action",130),
                  ("details","Details",400)]
        for col, text, w in widths:
            self._tree.heading(col, text=text)
            self._tree.column(col, width=w,
                              anchor="w" if col == "details" else "center")

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
        filtered = [r for r in self._rows
                    if any(q in str(v).lower() for v in r)]
        self._populate(filtered)
