"""
pos_panel.py  –  Point of Sale for cashier/user role.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from logic.inventory_logic import get_all_products
from logic.sales_logic import process_sale
from auth.auth_manager import get_current_user
from utils.theme import BG, CARD, ACCENT, SECONDARY, FG, FG_DIM, apply_treeview_style


class PosPanel(tk.Frame):
    def __init__(self, parent, on_logout=None):
        super().__init__(parent, bg=BG)
        self._on_logout = on_logout
        self._cart: list[dict] = []
        self._products: list[dict] = []
        self._build()

    # ── Layout ────────────────────────────────────────────────────────

    def _build(self):
        # Top bar
        bar = tk.Frame(self, bg=CARD, pady=10)
        bar.pack(fill="x")
        tk.Label(bar, text="👗  Rosemen Ukay-Ukay  —  Point of Sale",
                 font=("Segoe UI", 13, "bold"), bg=CARD, fg=FG).pack(side="left", padx=20)
        user = get_current_user()
        tk.Label(bar, text=f"👤 {user['username']}",
                 font=("Segoe UI", 9), bg=CARD, fg=FG_DIM).pack(side="right", padx=12)

        # Main two-column body
        body = tk.Frame(self, bg=BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_left(body)
        self._build_right(body)

    def _build_left(self, parent):
        left = tk.Frame(parent, bg=BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(left, text="Products", font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=FG).pack(anchor="w")

        # Search
        sr = tk.Frame(left, bg=BG)
        sr.pack(fill="x", pady=(4, 8))
        tk.Label(sr, text="🔍", bg=BG, fg=FG_DIM, font=("Segoe UI", 10)).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_products())
        tk.Entry(sr, textvariable=self._search_var, font=("Segoe UI", 10),
                 bg=SECONDARY, fg=FG, insertbackground=FG, relief="flat"
                 ).pack(side="left", fill="x", expand=True, padx=6, ipady=4)

        # Product treeview
        pf = tk.Frame(left, bg=CARD)
        pf.pack(fill="both", expand=True)

        style = apply_treeview_style("POS.Treeview")
        cols = ("name", "price", "bundle", "stock")
        self._prod_tree = ttk.Treeview(pf, columns=cols,
                                       show="headings", style=style)
        for col, text, w in [("name","Product",200), ("price","Price/Unit (₱)",130),
                              ("bundle","Bundle",80), ("stock","Stock (pcs)",100)]:
            self._prod_tree.heading(col, text=text)
            self._prod_tree.column(col, width=w,
                                   anchor="w" if col == "name" else "center")

        vsb = ttk.Scrollbar(pf, orient="vertical", command=self._prod_tree.yview)
        self._prod_tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._prod_tree.pack(fill="both", expand=True)
        self._prod_tree.bind("<Double-1>", lambda e: self._add_to_cart())

        tk.Button(left, text="+ Add to Cart  (or double-click)",
                  font=("Segoe UI", 9), bg=SECONDARY, fg=FG,
                  relief="flat", cursor="hand2", pady=6,
                  command=self._add_to_cart).pack(fill="x", pady=(6, 0))

        self._load_products()

    def _build_right(self, parent):
        right = tk.Frame(parent, bg=BG, width=340)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text="Cart", font=("Segoe UI", 12, "bold"),
                 bg=BG, fg=FG).pack(anchor="w")

        # Cart treeview
        cf = tk.Frame(right, bg=CARD)
        cf.pack(fill="both", expand=True, pady=(4, 0))

        style = apply_treeview_style("Cart.Treeview")
        cols = ("name", "qty", "price", "sub")
        self._cart_tree = ttk.Treeview(cf, columns=cols,
                                       show="headings", style=style)
        for col, text, w in [("name","Item",140),("qty","Qty",50),
                              ("price","Price",80),("sub","Subtotal",90)]:
            self._cart_tree.heading(col, text=text)
            self._cart_tree.column(col, width=w,
                                   anchor="w" if col == "name" else "center")
        self._cart_tree.pack(fill="both", expand=True)

        # Remove button
        tk.Button(right, text="✕  Remove Selected", font=("Segoe UI", 9),
                  bg="#3a1a2e", fg=ACCENT, relief="flat", cursor="hand2",
                  pady=5, command=self._remove_from_cart).pack(fill="x", pady=(4, 0))

        # Total
        total_frame = tk.Frame(right, bg=CARD, pady=14)
        total_frame.pack(fill="x", pady=8)
        tk.Label(total_frame, text="TOTAL",
                 font=("Segoe UI", 10), bg=CARD, fg=FG_DIM).pack()
        self._total_var = tk.StringVar(value="₱ 0.00")
        tk.Label(total_frame, textvariable=self._total_var,
                 font=("Segoe UI", 22, "bold"), bg=CARD, fg=ACCENT).pack()

        # Checkout + Clear
        tk.Button(right, text="💳  CHECKOUT",
                  font=("Segoe UI", 12, "bold"),
                  bg=ACCENT, fg=FG, relief="flat", cursor="hand2",
                  pady=12, command=self._checkout).pack(fill="x")
        tk.Button(right, text="🗑  Clear Cart",
                  font=("Segoe UI", 9), bg=SECONDARY, fg=FG_DIM,
                  relief="flat", cursor="hand2", pady=5,
                  command=self._clear_cart).pack(fill="x", pady=(4, 0))

    # ── Product list ──────────────────────────────────────────────────

    def _load_products(self):
        self._products = get_all_products()
        self._display_products(self._products)

    def _display_products(self, products):
        self._prod_tree.delete(*self._prod_tree.get_children())
        for p in products:
            label = f"₱{p['selling_price']:.2f}"
            bundle = f"{p['bundle_qty']} pc(s)" if p["bundle_qty"] == 1 \
                else f"{p['bundle_qty']} pcs"
            tag = "out" if p["stock_pieces"] == 0 else ""
            self._prod_tree.insert("", "end", iid=str(p["id"]),
                                   tags=(tag,),
                                   values=(p["name"], label, bundle, p["stock_pieces"]))
        self._prod_tree.tag_configure("out", foreground=FG_DIM)

    def _filter_products(self):
        q = self._search_var.get().lower()
        filtered = [p for p in self._products if q in p["name"].lower()]
        self._display_products(filtered)

    # ── Cart ──────────────────────────────────────────────────────────

    def _add_to_cart(self):
        sel = self._prod_tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a product first.",
                                   parent=self.winfo_toplevel())
            return
        pid = int(sel[0])
        product = next((p for p in self._products if p["id"] == pid), None)
        if not product:
            return
        if product["stock_pieces"] == 0:
            messagebox.showwarning("Out of Stock",
                                   f"'{product['name']}' is out of stock.",
                                   parent=self.winfo_toplevel())
            return

        _QtyDialog(self.winfo_toplevel(), product, self._on_qty_confirm)

    def _on_qty_confirm(self, product: dict, qty: int):
        # Check if already in cart
        for item in self._cart:
            if item["product_id"] == product["id"]:
                item["qty"] += qty
                self._refresh_cart()
                return
        self._cart.append({
            "product_id": product["id"],
            "name":       product["name"],
            "qty":        qty,
            "unit_price": product["selling_price"],
            "bundle_qty": product["bundle_qty"],
        })
        self._refresh_cart()

    def _refresh_cart(self):
        self._cart_tree.delete(*self._cart_tree.get_children())
        total = 0.0
        for item in self._cart:
            sub = item["qty"] * item["unit_price"]
            total += sub
            self._cart_tree.insert("", "end",
                                   iid=str(item["product_id"]),
                                   values=(item["name"], item["qty"],
                                           f"₱{item['unit_price']:.2f}",
                                           f"₱{sub:.2f}"))
        self._total_var.set(f"₱ {total:,.2f}")

    def _remove_from_cart(self):
        sel = self._cart_tree.selection()
        if not sel:
            return
        pid = int(sel[0])
        self._cart = [i for i in self._cart if i["product_id"] != pid]
        self._refresh_cart()

    def _clear_cart(self):
        self._cart.clear()
        self._refresh_cart()

    def _checkout(self):
        if not self._cart:
            messagebox.showwarning("Empty Cart", "Add items to the cart first.",
                                   parent=self.winfo_toplevel())
            return
        total = sum(i["qty"] * i["unit_price"] for i in self._cart)
        if not messagebox.askyesno("Confirm Sale",
                f"Process sale for ₱{total:,.2f}?",
                parent=self.winfo_toplevel()):
            return
        user = get_current_user()
        ok, msg = process_sale(self._cart, user["id"], user["username"])
        if ok:
            messagebox.showinfo("Sale Complete", msg, parent=self.winfo_toplevel())
            self._cart.clear()
            self._refresh_cart()
            self._load_products()   # refresh stock counts
        else:
            messagebox.showerror("Error", msg, parent=self.winfo_toplevel())

    # ── Public refresh (called when panel is shown) ───────────────────

    def refresh(self):
        self._load_products()


# ── Quantity Dialog ───────────────────────────────────────────────────

class _QtyDialog(tk.Toplevel):
    def __init__(self, parent, product: dict, on_confirm):
        super().__init__(parent)
        self.product    = product
        self.on_confirm = on_confirm
        self.title("Enter Quantity")
        self.configure(bg=CARD)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"300x230+{(sw-300)//2}+{(sh-230)//2}")

    def _build(self):
        f = tk.Frame(self, bg=CARD, padx=24, pady=20)
        f.pack(fill="both", expand=True)

        tk.Label(f, text=self.product["name"],
                 font=("Segoe UI", 12, "bold"), bg=CARD, fg=FG).pack(anchor="w")
        tk.Label(f, text=f"Price: ₱{self.product['selling_price']:.2f} / unit  |  "
                         f"Stock: {self.product['stock_pieces']} pcs",
                 font=("Segoe UI", 9), bg=CARD, fg=FG_DIM).pack(anchor="w", pady=(2,14))

        tk.Label(f, text="Quantity (units):", font=("Segoe UI", 9),
                 bg=CARD, fg=FG_DIM).pack(anchor="w")

        self.v_qty = tk.StringVar(value="1")
        tk.Entry(f, textvariable=self.v_qty, font=("Segoe UI", 13),
                 bg=SECONDARY, fg=FG, insertbackground=FG,
                 relief="flat", justify="center").pack(fill="x", pady=(4, 14), ipady=6)

        tk.Button(f, text="Add to Cart", font=("Segoe UI", 10, "bold"),
                  bg=ACCENT, fg=FG, relief="flat", cursor="hand2",
                  pady=8, command=self._confirm).pack(fill="x")

        self.bind("<Return>", lambda e: self._confirm())

    def _confirm(self):
        try:
            qty = int(self.v_qty.get())
        except ValueError:
            messagebox.showerror("Invalid", "Enter a whole number.", parent=self)
            return
        if qty < 1:
            messagebox.showerror("Invalid", "Quantity must be at least 1.", parent=self)
            return
        pieces_needed = qty * self.product["bundle_qty"]
        if pieces_needed > self.product["stock_pieces"]:
            messagebox.showerror("Insufficient Stock",
                                 f"Need {pieces_needed} pcs but only "
                                 f"{self.product['stock_pieces']} available.",
                                 parent=self)
            return
        self.on_confirm(self.product, qty)
        self.destroy()
