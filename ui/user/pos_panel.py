"""
pos_panel.py  –  Point of Sale for cashier/user role.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from logic.inventory_logic import get_all_products
from logic.sales_logic import process_sale, get_recent_sales_for_pos, refund_sale
from auth.auth_manager import get_current_user
import utils.theme as T
from PIL import Image, ImageTk
import os


class PosPanel(tk.Frame):
    def __init__(self, parent, on_logout=None):
        super().__init__(parent, bg=T.BG)
        self._on_logout = on_logout
        self._cart: list[dict] = []
        self._products: list[dict] = []
        self._build()

    # ── Layout ────────────────────────────────────────────────────────

    def _build(self):
        # Top bar
        bar = tk.Frame(self, bg=T.CARD, pady=10)
        bar.pack(fill="x")
        # Load logo
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "RosemenLOGO.png")
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                img.thumbnail((30, 30), Image.Resampling.LANCZOS)
                self._logo_photo = ImageTk.PhotoImage(img)
                tk.Label(bar, image=self._logo_photo, bg=T.CARD).pack(side="left", padx=(20, 5))
        except Exception as e:
            print("Failed to load logo in POS:", e)

        tk.Label(bar, text="Rosemen Ukay-Ukay  —  Point of Sale",
                 font=("Segoe UI", 13, "bold"), bg=T.CARD, fg=T.FG).pack(side="left")
        user = get_current_user()
        tk.Label(bar, text=f"👤 {user['username']}",
                 font=("Segoe UI", 9), bg=T.CARD, fg=T.FG_DIM).pack(side="right", padx=12)

        # Main two-column body
        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        self._build_left(body)
        self._build_right(body)

    def _build_left(self, parent):
        left = tk.Frame(parent, bg=T.BG)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(left, text="Products", font=("Segoe UI", 12, "bold"),
                 bg=T.BG, fg=T.FG).pack(anchor="w")

        # Search
        sr = tk.Frame(left, bg=T.BG)
        sr.pack(fill="x", pady=(4, 8))
        tk.Label(sr, text="🔍", bg=T.BG, fg=T.FG_DIM, font=("Segoe UI", 10)).pack(side="left")
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_products())
        tk.Entry(sr, textvariable=self._search_var, font=("Segoe UI", 10),
                 bg=T.SECONDARY, fg=T.FG, insertbackground=T.FG, relief="flat"
                 ).pack(side="left", fill="x", expand=True, padx=6, ipady=4)

        # Product treeview
        pf = tk.Frame(left, bg=T.CARD)
        pf.pack(fill="both", expand=True)

        style = T.apply_treeview_style("POS.Treeview")
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
                  font=("Segoe UI", 9), bg=T.SECONDARY, fg=T.FG,
                  relief="flat", cursor="hand2", pady=6,
                  command=self._add_to_cart).pack(fill="x", pady=(6, 0))

        self._load_products()

    def _build_right(self, parent):
        right = tk.Frame(parent, bg=T.BG, width=340)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        tk.Label(right, text="Cart", font=("Segoe UI", 12, "bold"),
                 bg=T.BG, fg=T.FG).pack(anchor="w")

        # Cart treeview
        cf = tk.Frame(right, bg=T.CARD)
        cf.pack(fill="both", expand=True, pady=(4, 0))

        style = T.apply_treeview_style("Cart.Treeview")
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
                  bg="#3a1a2e", fg=T.ACCENT, relief="flat", cursor="hand2",
                  pady=5, command=self._remove_from_cart).pack(fill="x", pady=(4, 0))

        # Total
        total_frame = tk.Frame(right, bg=T.CARD, pady=14)
        total_frame.pack(fill="x", pady=8)
        tk.Label(total_frame, text="TOTAL",
                 font=("Segoe UI", 10), bg=T.CARD, fg=T.FG_DIM).pack()
        self._total_var = tk.StringVar(value="₱ 0.00")
        tk.Label(total_frame, textvariable=self._total_var,
                 font=("Segoe UI", 22, "bold"), bg=T.CARD, fg=T.ACCENT).pack()

        # Checkout + Clear
        tk.Button(right, text="💳  CHECKOUT",
                  font=("Segoe UI", 12, "bold"),
                  bg=T.ACCENT, fg=T.FG, relief="flat", cursor="hand2",
                  pady=12, command=self._checkout).pack(fill="x")
        tk.Button(right, text="🗑  Clear Cart",
                  font=("Segoe UI", 9), bg=T.SECONDARY, fg=T.FG_DIM,
                  relief="flat", cursor="hand2", pady=5,
                  command=self._clear_cart).pack(fill="x", pady=(4, 0))
        tk.Button(right, text="🧾  Transactions",
                  font=("Segoe UI", 9, "bold"), bg=T.CARD, fg=T.FG_DIM,
                  relief="flat", cursor="hand2", pady=5,
                  command=self._show_transactions).pack(fill="x", pady=(8, 0))

    # ── Product list ──────────────────────────────────────────────────

    def _load_products(self):
        self._products = get_all_products(include_archived=False)
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
        self._prod_tree.tag_configure("out", foreground=T.FG_DIM)

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
        
        _CheckoutDialog(self.winfo_toplevel(), self._cart, self._on_checkout_complete)
        
    def _on_checkout_complete(self):
        self._cart.clear()
        self._refresh_cart()
        self._load_products()   # refresh stock counts

    def _show_transactions(self):
        _TransactionsDialog(self.winfo_toplevel())

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
        self.configure(bg=T.CARD)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"300x230+{(sw-300)//2}+{(sh-230)//2}")

    def _build(self):
        f = tk.Frame(self, bg=T.CARD, padx=24, pady=20)
        f.pack(fill="both", expand=True)

        tk.Label(f, text=self.product["name"],
                 font=("Segoe UI", 12, "bold"), bg=T.CARD, fg=T.FG).pack(anchor="w")
        tk.Label(f, text=f"Price: ₱{self.product['selling_price']:.2f} / unit  |  "
                         f"Stock: {self.product['stock_pieces']} pcs",
                 font=("Segoe UI", 9), bg=T.CARD, fg=T.FG_DIM).pack(anchor="w", pady=(2,14))

        tk.Label(f, text="Quantity (units):", font=("Segoe UI", 9),
                 bg=T.CARD, fg=T.FG_DIM).pack(anchor="w")

        self.v_qty = tk.StringVar(value="1")
        tk.Entry(f, textvariable=self.v_qty, font=("Segoe UI", 13),
                 bg=T.SECONDARY, fg=T.FG, insertbackground=T.FG,
                 relief="flat", justify="center").pack(fill="x", pady=(4, 14), ipady=6)

        tk.Button(f, text="Add to Cart", font=("Segoe UI", 10, "bold"),
                  bg=T.ACCENT, fg=T.FG, relief="flat", cursor="hand2",
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

# ── Checkout Dialog ───────────────────────────────────────────────────

class _CheckoutDialog(tk.Toplevel):
    def __init__(self, parent, cart: list[dict], on_success):
        super().__init__(parent)
        self.cart = cart
        self.on_success = on_success
        self.total = sum(i["qty"] * i["unit_price"] for i in self.cart)
        
        self.title("Checkout Confirmation")
        self.configure(bg=T.CARD)
        self.resizable(False, False)
        self.grab_set()
        
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"360x420+{(sw-360)//2}+{(sh-420)//2}")
        
    def _build(self):
        f = tk.Frame(self, bg=T.CARD, padx=24, pady=20)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="Confirm Transaction", font=("Segoe UI", 16, "bold"), bg=T.CARD, fg=T.FG).pack(anchor="w", pady=(0, 16))
        
        # Summary
        summary_frame = tk.Frame(f, bg=T.SECONDARY, padx=10, pady=10)
        summary_frame.pack(fill="x", pady=(0, 16))
        
        tk.Label(summary_frame, text=f"Total Items: {sum(i['qty'] for i in self.cart)}", font=("Segoe UI", 10), bg=T.SECONDARY, fg=T.FG_DIM).pack(anchor="w")
        tk.Label(summary_frame, text=f"Total Amount: ₱{self.total:,.2f}", font=("Segoe UI", 14, "bold"), bg=T.SECONDARY, fg=T.FG).pack(anchor="w", pady=(4,0))
        
        # Cash Tendered
        tk.Label(f, text="Cash Tendered (₱):", font=("Segoe UI", 10), bg=T.CARD, fg=T.FG_DIM).pack(anchor="w")
        
        self.v_tendered = tk.StringVar()
        self.v_tendered.trace_add("write", self._calc_change)
        
        ent = tk.Entry(f, textvariable=self.v_tendered, font=("Segoe UI", 16, "bold"),
                 bg=T.BG, fg=T.FG, insertbackground=T.FG, relief="flat", justify="right")
        ent.pack(fill="x", pady=(4, 16), ipady=8)
        ent.focus()

        # Change
        self.v_change = tk.StringVar(value="Change: ₱ 0.00")
        tk.Label(f, textvariable=self.v_change, font=("Segoe UI", 12, "bold"), bg=T.CARD, fg=T.ACCENT).pack(anchor="w", pady=(0, 24))

        # Confirm Button
        self.btn_confirm = tk.Button(f, text="Confirm Payment", font=("Segoe UI", 12, "bold"),
                  bg=T.ACCENT, fg=T.FG, relief="flat", cursor="hand2", pady=10, command=self._confirm)
        self.btn_confirm.pack(fill="x")
        
        self.bind("<Return>", lambda e: self._confirm())
        
    def _calc_change(self, *args):
        try:
            val = self.v_tendered.get().replace(",", "")
            if not val:
                self.v_change.set("Change: ₱ 0.00")
                return
            tendered = float(val)
            change = tendered - self.total
            if change >= 0:
                self.v_change.set(f"Change: ₱ {change:,.2f}")
                self.btn_confirm.config(state="normal")
            else:
                self.v_change.set(f"Change: ₱ {change:,.2f} (Insufficient)")
                self.btn_confirm.config(state="disabled")
        except ValueError:
            self.v_change.set("Invalid Amount")
            self.btn_confirm.config(state="disabled")

    def _confirm(self):
        try:
            tendered = float(self.v_tendered.get().replace(",", ""))
        except ValueError:
            messagebox.showerror("Invalid", "Please enter a valid amount.", parent=self)
            return
            
        change = tendered - self.total
        if change < 0:
            messagebox.showerror("Insufficient", "Tendered amount is less than total.", parent=self)
            return
            
        user = get_current_user()
        ok, msg = process_sale(self.cart, user["id"], user["username"], tendered=tendered, change=change)
        
        if ok:
            _ReceiptDialog(self.master, self.cart, self.total, tendered, change)
            self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)

# ── Receipt Dialog ────────────────────────────────────────────────────

class _ReceiptDialog(tk.Toplevel):
    def __init__(self, parent, cart, total, tendered, change):
        super().__init__(parent)
        self.title("Transaction Receipt")
        self.configure(bg="#ffffff") # receipts are usually white
        self.resizable(False, False)
        self.grab_set()
        
        self.cart = cart
        self.total = total
        self.tendered = tendered
        self.change = change
        
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 320, 480
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")
        
    def _build(self):
        f = tk.Frame(self, bg="#ffffff", padx=20, pady=20)
        f.pack(fill="both", expand=True)
        
        tk.Label(f, text="ROSEMEN UKAY-UKAY", font=("Trajan Pro 3", 16, "bold"), bg="#ffffff", fg="#000000").pack()
        #tk.Label(f, text="Inventory & Sales System", font=("Courier", 9), bg="#ffffff", fg="#000000").pack()
        tk.Label(f, text="--------------------------------", font=("Courier", 10), bg="#ffffff", fg="#000000").pack(pady=4)
        
        # Items
        items_frame = tk.Frame(f, bg="#ffffff")
        items_frame.pack(fill="both", expand=True)
        
        for item in self.cart:
            row = tk.Frame(items_frame, bg="#ffffff")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{item['qty']}x {item['name']}", font=("Courier", 10), bg="#ffffff", fg="#000000").pack(side="left")
            sub = item['qty'] * item['unit_price']
            tk.Label(row, text=f"{sub:,.2f}", font=("Courier", 10), bg="#ffffff", fg="#000000").pack(side="right")
            
        tk.Label(f, text="--------------------------------", font=("Courier", 10), bg="#ffffff", fg="#000000").pack(pady=4)
        
        # Totals
        totals_frame = tk.Frame(f, bg="#ffffff")
        totals_frame.pack(fill="x")
        
        def add_row(parent, label, value, bold=False):
            r = tk.Frame(parent, bg="#ffffff")
            r.pack(fill="x", pady=1)
            font = ("Courier", 10, "bold") if bold else ("Courier", 10)
            tk.Label(r, text=label, font=font, bg="#ffffff", fg="#000000").pack(side="left")
            tk.Label(r, text=value, font=font, bg="#ffffff", fg="#000000").pack(side="right")
            
        add_row(totals_frame, "TOTAL:", f"P {self.total:,.2f}", bold=True)
        add_row(totals_frame, "CASH:", f"P {self.tendered:,.2f}")
        add_row(totals_frame, "CHANGE:", f"P {self.change:,.2f}")
        
        tk.Label(f, text="--------------------------------", font=("Courier", 10), bg="#ffffff", fg="#000000").pack(pady=4)
        tk.Label(f, text="Thank you for shopping!", font=("Courier", 10, "bold"), bg="#ffffff", fg="#000000").pack(pady=10)
        
        tk.Button(f, text="Close Receipt", font=("Segoe UI", 10, "bold"), bg=T.ACCENT, fg=T.FG, 
                  relief="flat", cursor="hand2", pady=8, command=self.destroy).pack(fill="x", side="bottom")

# ── Transactions Dialog ───────────────────────────────────────────────

class _TransactionsDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Today's Transactions")
        self.configure(bg=T.BG)
        self.resizable(True, True)
        self.grab_set()
        
        self._build()
        self._load_data()
        
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"700x400+{(sw-700)//2}+{(sh-400)//2}")
        
    def _build(self):
        f = tk.Frame(self, bg=T.BG, padx=20, pady=20)
        f.pack(fill="both", expand=True)
        
        tk.Label(f, text="Recent Transactions (Today)", font=("Segoe UI", 14, "bold"), bg=T.BG, fg=T.FG).pack(anchor="w", pady=(0, 10))
        
        # Treeview
        columns = ("id", "time", "product", "qty", "total", "tendered", "change", "status", "cashier")
        self.tree = ttk.Treeview(f, columns=columns, show="headings", height=10)
        
        self.tree.heading("id", text="ID")
        self.tree.heading("time", text="Time")
        self.tree.heading("product", text="Product")
        self.tree.heading("qty", text="Qty")
        self.tree.heading("total", text="Total")
        self.tree.heading("tendered", text="Cash")
        self.tree.heading("change", text="Change")
        self.tree.heading("status", text="Status")
        self.tree.heading("cashier", text="Cashier")
        
        self.tree.column("id", width=40, anchor="center")
        self.tree.column("time", width=120)
        self.tree.column("product", width=140)
        self.tree.column("qty", width=40, anchor="center")
        self.tree.column("total", width=80, anchor="e")
        self.tree.column("tendered", width=80, anchor="e")
        self.tree.column("change", width=80, anchor="e")
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("cashier", width=80)
        
        self.tree.pack(fill="both", expand=True)
        T.apply_treeview_style()
        
        self.tree.tag_configure("refunded", foreground=T.FG_DIM)
        
        # Actions
        btn_frame = tk.Frame(f, bg=T.BG)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        tk.Button(btn_frame, text="Refund Selected", font=("Segoe UI", 10, "bold"),
                  bg=T.ACCENT, fg=T.FG, cursor="hand2", relief="flat", padx=15, pady=5,
                  command=self._do_refund).pack(side="left")
                  
    def _load_data(self):
        self.tree.delete(*self.tree.get_children())
        sales = get_recent_sales_for_pos()
        for s in sales:
            tag = "refunded" if s["status"] == "refunded" else ""
            self.tree.insert("", "end", iid=str(s["id"]), tags=(tag,), values=(
                s["id"],
                s["sold_at"],
                s["product"],
                s["qty"],
                f"₱{s['total']:,.2f}",
                f"₱{s['tendered']:,.2f}",
                f"₱{s['change']:,.2f}",
                s["status"].upper(),
                s["username"]
            ))

    def _do_refund(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select Transaction", "Please select a transaction to refund.", parent=self)
            return
            
        sale_id = int(sel[0])
        item = self.tree.item(sale_id)
        status = item["values"][7]
        
        if status == "REFUNDED":
            messagebox.showinfo("Already Refunded", "This transaction has already been refunded.", parent=self)
            return
            
        if not messagebox.askyesno("Confirm Refund", f"Are you sure you want to refund Transaction #{sale_id}?\nThis will restore the inventory stock.", parent=self):
            return
            
        user = get_current_user()
        ok, msg = refund_sale(sale_id, user["id"], user["username"])
        
        if ok:
            messagebox.showinfo("Refund Complete", msg, parent=self)
            self._load_data()
        else:
            messagebox.showerror("Refund Failed", msg, parent=self)
