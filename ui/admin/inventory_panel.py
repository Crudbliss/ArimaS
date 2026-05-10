"""
inventory_panel.py  –  Full CRUD for products + sack stock additions.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from logic.inventory_logic import (get_all_products, add_product, update_product,
                                   delete_product, add_stock)
from auth.auth_manager import get_current_user
import utils.theme as T

CATEGORIES = ["Tops", "Bottoms", "Outerwear", "Kids", "Other"]


class InventoryPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=T.BG)
        self._build()

    def _build(self):
        # ── Toolbar ──────────────────────────────────────────────────
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=24, pady=(20, 6))

        tk.Label(bar, text="Inventory Management",
                 font=("Segoe UI", 16, "bold"), bg=T.BG, fg=T.FG).pack(side="left")

        for label, cmd in [
            ("⟳ Refresh",     self.refresh),
            ("+ Add Product",  self._open_add),
            ("✎ Edit",         self._open_edit),
            ("🗑 Delete",       self._delete),
            ("📦 Add Stock",    self._open_stock),
        ]:
            tk.Button(bar, text=label, font=("Segoe UI", 9),
                      bg=T.SECONDARY, fg=T.FG, relief="flat", cursor="hand2",
                      padx=10, pady=4, command=cmd).pack(side="right", padx=3)

        # ── Search ───────────────────────────────────────────────────
        search_row = tk.Frame(self, bg=T.BG)
        search_row.pack(fill="x", padx=24, pady=(0, 8))
        tk.Label(search_row, text="Search:", font=("Segoe UI", 9),
                 bg=T.BG, fg=T.FG_DIM).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter())
        tk.Entry(search_row, textvariable=self._search_var, font=("Segoe UI", 10),
                 bg=T.SECONDARY, fg=T.FG, insertbackground=T.FG, relief="flat",
                 width=30).pack(side="left", padx=8, ipady=4)

        # ── Treeview ─────────────────────────────────────────────────
        frame = tk.Frame(self, bg=T.CARD)
        frame.pack(fill="both", expand=True, padx=24, pady=(0, 20))

        style = T.apply_treeview_style("Inv.Treeview")
        cols = ("id","name","category","buy","sell","bundle","stock","reorder")
        self._tree = ttk.Treeview(frame, columns=cols,
                                  show="headings", style=style)

        hdrs = [("id","ID",40),("name","Product Name",200),
                ("category","Category",100),("buy","Buy/Sack (₱)",110),
                ("sell","Sell/Unit (₱)",110),("bundle","Bundle Qty",90),
                ("stock","Stock (pcs)",100),("reorder","Reorder Lvl",100)]
        for col, text, w in hdrs:
            self._tree.heading(col, text=text)
            self._tree.column(col, width=w, anchor="center" if col != "name" else "w")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        self._all_rows: list[dict] = []
        self.refresh()

    # ── Data ─────────────────────────────────────────────────────────

    def refresh(self):
        self._all_rows = get_all_products()
        self._populate(self._all_rows)

    def _populate(self, rows: list[dict]):
        self._tree.delete(*self._tree.get_children())
        for p in rows:
            tag = "low" if p["stock_pieces"] <= p["reorder_level"] else ""
            self._tree.insert("", "end", iid=str(p["id"]), tags=(tag,),
                              values=(p["id"], p["name"], p["category"],
                                      f"₱{p['buying_price']:,.2f}",
                                      f"₱{p['selling_price']:,.2f}",
                                      p["bundle_qty"],
                                      p["stock_pieces"], p["reorder_level"]))
        self._tree.tag_configure("low", foreground="#ffd166")

    def _filter(self):
        q = self._search_var.get().lower()
        filtered = [p for p in self._all_rows
                    if q in p["name"].lower() or q in p["category"].lower()]
        self._populate(filtered)

    def _selected_product(self) -> dict | None:
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Please select a product first.")
            return None
        pid = int(sel[0])
        return next((p for p in self._all_rows if p["id"] == pid), None)

    # ── Actions ──────────────────────────────────────────────────────

    def _open_add(self):
        _ProductDialog(self, mode="add", product=None, on_save=self.refresh)

    def _open_edit(self):
        p = self._selected_product()
        if p:
            _ProductDialog(self, mode="edit", product=p, on_save=self.refresh)

    def _delete(self):
        p = self._selected_product()
        if not p:
            return
        if not messagebox.askyesno("Delete",
                f"Delete '{p['name']}'? This cannot be undone."):
            return
        user = get_current_user()
        ok, msg = delete_product(p["id"], user["id"], user["username"])
        if ok:
            messagebox.showinfo("Deleted", msg)
            self.refresh()
        else:
            messagebox.showerror("Error", msg)

    def _open_stock(self):
        p = self._selected_product()
        if p:
            _AddStockDialog(self, product=p, on_save=self.refresh)


# ── Product Dialog ────────────────────────────────────────────────────

class _ProductDialog(tk.Toplevel):
    def __init__(self, parent, mode: str, product: dict | None, on_save):
        super().__init__(parent)
        self.mode     = mode
        self.product  = product
        self.on_save  = on_save
        self.title("Add Product" if mode == "add" else "Edit Product")
        self.configure(bg=T.CARD)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        if mode == "edit" and product:
            self._populate()
        self._center(420, 420)

    def _center(self, w, h):
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _field(self, parent, label, var, row):
        tk.Label(parent, text=label, font=("Segoe UI", 9),
                 bg=T.CARD, fg=T.FG_DIM).grid(row=row, column=0, sticky="w", pady=4)
        e = tk.Entry(parent, textvariable=var, font=("Segoe UI", 10),
                     bg=T.SECONDARY, fg=T.FG, insertbackground=T.FG,
                     relief="flat", width=28)
        e.grid(row=row, column=1, padx=(12, 0), pady=4, ipady=4)
        return e

    def _build(self):
        f = tk.Frame(self, bg=T.CARD, padx=30, pady=20)
        f.pack(fill="both", expand=True)

        self.v_name    = tk.StringVar()
        self.v_cat     = tk.StringVar(value=CATEGORIES[0])
        self.v_buy     = tk.StringVar()
        self.v_sell    = tk.StringVar()
        self.v_bundle  = tk.StringVar(value="1")
        self.v_reorder = tk.StringVar(value="10")

        self._field(f, "Product Name",   self.v_name,    0)
        tk.Label(f, text="Category", font=("Segoe UI", 9),
                 bg=T.CARD, fg=T.FG_DIM).grid(row=1, column=0, sticky="w", pady=4)
        ttk.Combobox(f, textvariable=self.v_cat, values=CATEGORIES,
                     state="readonly", width=26
                     ).grid(row=1, column=1, padx=(12, 0), pady=4)
        self._field(f, "Buying Price/Sack (₱)", self.v_buy,     2)
        self._field(f, "Selling Price/Unit (₱)", self.v_sell,   3)
        self._field(f, "Bundle Qty (pcs/unit)",  self.v_bundle,  4)
        self._field(f, "Reorder Level (pcs)",    self.v_reorder, 5)

        tk.Button(f, text="Save", font=("Segoe UI", 10, "bold"),
                  bg=T.ACCENT, fg=T.FG, relief="flat", cursor="hand2",
                  pady=8, command=self._save).grid(
                  row=6, column=0, columnspan=2, sticky="ew", pady=(20, 0))

    def _populate(self):
        p = self.product
        self.v_name.set(p["name"])
        self.v_cat.set(p["category"])
        self.v_buy.set(p["buying_price"])
        self.v_sell.set(p["selling_price"])
        self.v_bundle.set(p["bundle_qty"])
        self.v_reorder.set(p["reorder_level"])

    def _save(self):
        try:
            name    = self.v_name.get().strip()
            cat     = self.v_cat.get()
            buy     = float(self.v_buy.get())
            sell    = float(self.v_sell.get())
            bundle  = int(self.v_bundle.get())
            reorder = int(self.v_reorder.get())
        except ValueError:
            messagebox.showerror("Invalid", "Check numeric fields.", parent=self)
            return

        if not name:
            messagebox.showerror("Invalid", "Product name is required.", parent=self)
            return

        user = get_current_user()
        if self.mode == "add":
            ok, msg = add_product(name, cat, buy, sell, bundle, reorder,
                                  user["id"], user["username"])
        else:
            ok, msg = update_product(self.product["id"], name, cat, buy, sell,
                                     bundle, reorder, user["id"], user["username"])
        if ok:
            messagebox.showinfo("Success", msg, parent=self)
            self.on_save()
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)


# ── Add Stock Dialog ──────────────────────────────────────────────────

class _AddStockDialog(tk.Toplevel):
    def __init__(self, parent, product: dict, on_save):
        super().__init__(parent)
        self.product = product
        self.on_save = on_save
        self.title(f"Add Stock — {product['name']}")
        self.configure(bg=T.CARD)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"400x360+{(sw-400)//2}+{(sh-360)//2}")

    def _build(self):
        f = tk.Frame(self, bg=T.CARD, padx=30, pady=20)
        f.pack(fill="both", expand=True)

        # Header info
        tk.Label(f, text=f"Product: {self.product['name']}",
                 font=("Segoe UI", 11, "bold"), bg=T.CARD, fg=T.FG).pack(anchor="w")
        tk.Label(f, text=f"Current Stock: {self.product['stock_pieces']} pcs  |  "
                         f"Default: {self.product['pieces_per_sack']} pcs/sack",
                 font=("Segoe UI", 9), bg=T.CARD, fg=T.FG_DIM).pack(anchor="w", pady=(2, 16))

        # Sacks Bought
        self.v_sacks = tk.StringVar(value="1")
        self._row(f, "Sacks Bought:", self.v_sacks)

        # Pieces per Sack (editable default)
        default_pps = self.product.get("pieces_per_sack", 0)
        self.v_pps = tk.StringVar(value=str(default_pps))
        self._row(f, "Pieces per Sack:", self.v_pps)

        tk.Label(f, text="↑ Pre-filled from product default — edit if needed",
                 font=("Segoe UI", 8), bg=T.CARD, fg=T.FG_DIM).pack(anchor="w", pady=(0, 10))

        # Total Pieces (auto-calculated, but editable)
        self.v_total = tk.StringVar()
        total_row = tk.Frame(f, bg=T.CARD)
        total_row.pack(fill="x", pady=4)
        tk.Label(total_row, text="Total Pieces:", font=("Segoe UI", 9),
                 bg=T.CARD, fg=T.FG_DIM, width=18, anchor="w").pack(side="left")
        self._total_entry = tk.Entry(total_row, textvariable=self.v_total,
                                     font=("Segoe UI", 10), bg="#0f4a30",
                                     fg="#06d6a0", insertbackground="#06d6a0",
                                     relief="flat", width=14)
        self._total_entry.pack(side="left", ipady=4, padx=(8, 0))
        tk.Label(total_row, text=" ← editable", font=("Segoe UI", 8),
                 bg=T.CARD, fg=T.FG_DIM).pack(side="left", padx=6)

        # Auto-calculate on sacks/pps change
        self.v_sacks.trace_add("write", lambda *_: self._recalculate())
        self.v_pps.trace_add("write", lambda *_: self._recalculate())
        self._recalculate()

        tk.Button(f, text="Add to Stock", font=("Segoe UI", 10, "bold"),
                  bg=T.ACCENT, fg=T.FG, relief="flat", cursor="hand2",
                  pady=8, command=self._save).pack(fill="x", pady=(20, 0))

    def _row(self, parent, label, var):
        r = tk.Frame(parent, bg=T.CARD)
        r.pack(fill="x", pady=4)
        tk.Label(r, text=label, font=("Segoe UI", 9),
                 bg=T.CARD, fg=T.FG_DIM, width=18, anchor="w").pack(side="left")
        tk.Entry(r, textvariable=var, font=("Segoe UI", 10),
                 bg=T.SECONDARY, fg=T.FG, insertbackground=T.FG,
                 relief="flat", width=14).pack(side="left", ipady=4, padx=(8, 0))

    def _recalculate(self):
        """Auto-fill Total Pieces = sacks × pieces_per_sack."""
        try:
            sacks = int(self.v_sacks.get())
            pps   = int(self.v_pps.get())
            self.v_total.set(str(sacks * pps))
        except ValueError:
            self.v_total.set("")

    def _save(self):
        try:
            sacks  = int(self.v_sacks.get())
            total  = int(self.v_total.get())
        except ValueError:
            messagebox.showerror("Invalid", "Enter valid whole numbers.", parent=self)
            return
        if sacks < 1 or total < 1:
            messagebox.showerror("Invalid", "Values must be at least 1.", parent=self)
            return

        user = get_current_user()
        ok, msg = add_stock(self.product["id"], sacks,
                            self.product["buying_price"], total,
                            user["id"], user["username"])
        if ok:
            messagebox.showinfo("Stock Added", msg, parent=self)
            self.on_save()
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)

