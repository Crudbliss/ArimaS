"""
pos_panel.py  –  Point of Sale for cashier/user role.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from logic.inventory_logic import get_all_products
from logic.sales_logic import process_sale, get_recent_sales_for_pos, refund_sale, get_receipt_by_txn
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
        self._view_mode = tk.StringVar(value="grid")  # "list" or "grid"
        self._search_var = tk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._filter_products())
        self._build()

    # ── Layout ────────────────────────────────────────────────────────

    def _build(self):
        # Top bar
        bar = tk.Frame(self, bg=T.CARD, pady=10)
        bar.pack(fill="x")
        # Load logo
        try:
            logo_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "RosemenLOGO.png"))
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                img.thumbnail((30, 30), Image.Resampling.LANCZOS)
                self._logo_photo = ImageTk.PhotoImage(img)
                lbl = tk.Label(bar, image=self._logo_photo, bg=T.CARD)
                lbl.image = self._logo_photo  # Prevent garbage collection
                lbl.pack(side="left", padx=(20, 5))
        except Exception as e:
            print("Failed to load logo in POS:", e)

        tk.Label(bar, text="Rosemen Ukay-Ukay  —  Point of Sale",
                 font=("Segoe UI", 13, "bold"), bg=T.CARD, fg=T.FG).pack(side="left")
        user = get_current_user()
        tk.Label(bar, text=f"👤 {user['username']}",
                 font=("Segoe UI", 9), bg=T.CARD, fg=T.FG_DIM).pack(side="right", padx=12)

        # View mode toggle
        self._toggle_btn = tk.Button(
            bar, text="☰  List View",
            font=("Segoe UI", 9, "bold"), bg=T.SECONDARY, fg=T.FG,
            relief="flat", cursor="hand2", padx=12, pady=4,
            command=self._toggle_view
        )
        self._toggle_btn.pack(side="right", padx=(0, 8))

        # Main two-column body
        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=16, pady=12)

        # Left panel container — swappable
        self._left_container = tk.Frame(body, bg=T.BG)
        self._left_container.pack(side="left", fill="both", expand=True, padx=(0, 8))

        self._build_grid_view()
        self._build_right(body)

    def _build_left(self):
        """List view — classic Treeview."""
        for w in self._left_container.winfo_children():
            w.destroy()

        left = tk.Frame(self._left_container, bg=T.BG)
        left.pack(fill="both", expand=True)
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
        right = tk.Frame(parent, bg=T.BG, width=360)
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

    def _load_products(self):
        self._products = get_all_products(include_archived=False)
        if self._view_mode.get() == "grid":
            self._render_grid(self._products)
        else:
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
        if self._view_mode.get() == "grid":
            self._render_grid(filtered)
        else:
            self._display_products(filtered)

    # ── View Toggle ───────────────────────────────────────────────────

    def _toggle_view(self):
        if self._view_mode.get() == "list":
            self._view_mode.set("grid")
            self._toggle_btn.config(text="☰  List View")
            self._build_grid_view()
        else:
            self._view_mode.set("list")
            self._toggle_btn.config(text="⊞  Grid View")
            self._build_left()

    def _build_grid_view(self):
        """Grid view — clickable product card tiles (no scroll, static grid)."""
        for w in self._left_container.winfo_children():
            w.destroy()

        # Load products FIRST so category buttons are built correctly
        self._products = get_all_products(include_archived=False)

        left = tk.Frame(self._left_container, bg=T.BG)
        left.pack(fill="both", expand=True)

        # Header
        tk.Label(left, text="Products", font=("Segoe UI", 12, "bold"),
                 bg=T.BG, fg=T.FG).pack(anchor="w")

        # Search box
        sr = tk.Frame(left, bg=T.BG)
        sr.pack(fill="x", pady=(4, 4))
        tk.Label(sr, text="🔍", bg=T.BG, fg=T.FG_DIM, font=("Segoe UI", 10)).pack(side="left")
        tk.Entry(sr, textvariable=self._search_var, font=("Segoe UI", 10),
                 bg=T.SECONDARY, fg=T.FG, insertbackground=T.FG, relief="flat"
                 ).pack(side="left", fill="x", expand=True, padx=6, ipady=4)

        # Category filter buttons
        self._cat_filter = tk.StringVar(value="All")
        cats_frame = tk.Frame(left, bg=T.BG)
        cats_frame.pack(fill="x", pady=(0, 4))
        categories = ["All"] + sorted(set(p["category"] for p in self._products if p.get("category")))
        for cat in categories:
            btn = tk.Button(
                cats_frame, text=cat,
                font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2",
                padx=10, pady=4,
                command=lambda c=cat: self._filter_by_category(c)
            )
            btn.pack(side="left", padx=2)
            btn._cat = cat

        self._cat_btns_frame = cats_frame
        self._update_cat_btn_styles("All")

        # Plain (non-scrollable) grid frame
        self._grid_inner = tk.Frame(left, bg=T.BG)
        self._grid_inner.pack(fill="both", expand=True)

        self._render_grid(self._products)

    def _update_cat_btn_styles(self, active):
        for btn in self._cat_btns_frame.winfo_children():
            if hasattr(btn, "_cat"):
                is_active = btn._cat == active
                btn.config(
                    bg=T.ACCENT if is_active else T.SECONDARY,
                    fg=T.FG if is_active else T.FG_DIM
                )

    def _filter_by_category(self, cat):
        self._cat_filter.set(cat)
        self._update_cat_btn_styles(cat)
        q = self._search_var.get().lower()
        filtered = [
            p for p in self._products
            if (cat == "All" or p.get("category") == cat)
            and (not q or q in p["name"].lower())
        ]
        self._render_grid(filtered)

    CARD_COLORS = {
        "Tops":      "#4361ee",
        "Bottoms":   "#7209b7",
        "Outerwear": "#3a0ca3",
        "Kids":      "#4cc9f0",
        "Dresses":   "#f72585",
        "Others":    "#560bad",
    }

    def _render_grid(self, products):
        for w in self._grid_inner.winfo_children():
            w.destroy()

        COLS = 10
        for col in range(COLS):
            self._grid_inner.columnconfigure(col, weight=1, uniform="card")

        for idx, p in enumerate(products):
            row, col = divmod(idx, COLS)
            out_of_stock = p["stock_pieces"] == 0

            color = self.CARD_COLORS.get(p.get("category", ""), "#334155")
            card_bg = color if not out_of_stock else "#2a2a2a"

            card = tk.Frame(self._grid_inner, bg=card_bg, padx=6, pady=8,
                            cursor="hand2" if not out_of_stock else "")
            card.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")

            # Category badge
            tk.Label(card, text=p.get("category", "").upper(),
                     font=("Segoe UI", 6, "bold"), bg=card_bg,
                     fg="#ccccff" if not out_of_stock else "#555555").pack(anchor="w")

            # Product name
            tk.Label(card, text=p["name"], font=("Segoe UI", 9, "bold"),
                     bg=card_bg, fg="#ffffff" if not out_of_stock else "#555555",
                     wraplength=90, justify="left").pack(anchor="w", pady=(2, 4))

            # Price
            tk.Label(card, text=f"₱{p['selling_price']:,.2f}",
                     font=("Segoe UI", 10, "bold"),
                     bg=card_bg, fg="#ffffff" if not out_of_stock else "#555555").pack(anchor="w")

            # Stock badge
            stock_txt = f"In stock: {p['stock_pieces']}" if not out_of_stock else "OUT OF STOCK"
            tk.Label(card, text=stock_txt, font=("Segoe UI", 6),
                     bg=card_bg, fg="#bbffbb" if not out_of_stock else "#cc4444").pack(anchor="e", pady=(2, 0))

            # Bind click
            if not out_of_stock:
                for widget in [card] + list(card.winfo_children()):
                    widget.bind("<Button-1>", lambda e, prod=p: self._grid_add_to_cart(prod))
                    widget.bind("<Enter>", lambda e, c=card, bg=card_bg: c.config(bg=self._lighten(bg)))
                    widget.bind("<Leave>", lambda e, c=card, bg=card_bg: c.config(bg=bg))

    def _lighten(self, hex_color):
        """Lighten a hex color slightly for hover effect."""
        try:
            r = min(255, int(hex_color[1:3], 16) + 20)
            g = min(255, int(hex_color[3:5], 16) + 20)
            b = min(255, int(hex_color[5:7], 16) + 20)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    def _grid_add_to_cart(self, product):
        """Single-click adds 1 unit. Clicking again increments."""
        if product["stock_pieces"] == 0:
            return
        for item in self._cart:
            if item["product_id"] == product["id"]:
                item["qty"] += 1
                self._refresh_cart()
                return
        self._cart.append({
            "product_id": product["id"],
            "name":       product["name"],
            "qty":        1,
            "unit_price": product["selling_price"],
            "bundle_qty": product["bundle_qty"],
        })
        self._refresh_cart()



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
        self.geometry(f"360x500+{(sw-360)//2}+{(sh-500)//2}")
        
    def _build(self):
        f = tk.Frame(self, bg=T.CARD, padx=24, pady=20)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="Confirm Transaction", font=("Segoe UI", 16, "bold"), bg=T.CARD, fg=T.FG).pack(anchor="w", pady=(0, 12))

        # Summary
        summary_frame = tk.Frame(f, bg=T.SECONDARY, padx=10, pady=10)
        summary_frame.pack(fill="x", pady=(0, 12))
        tk.Label(summary_frame, text=f"Total Items: {sum(i['qty'] for i in self.cart)}", font=("Segoe UI", 10), bg=T.SECONDARY, fg=T.FG_DIM).pack(anchor="w")
        tk.Label(summary_frame, text=f"Total Amount: \N{PESO SIGN}{self.total:,.2f}", font=("Segoe UI", 14, "bold"), bg=T.SECONDARY, fg=T.FG).pack(anchor="w", pady=(4, 0))

        # Payment Method
        tk.Label(f, text="Payment Method:", font=("Segoe UI", 10), bg=T.CARD, fg=T.FG_DIM).pack(anchor="w")
        self.v_payment = tk.StringVar(value="Cash")
        radio_frame = tk.Frame(f, bg=T.CARD)
        radio_frame.pack(fill="x", pady=(4, 12))
        for method in ("Cash", "GCash"):
            tk.Radiobutton(
                radio_frame, text=method, variable=self.v_payment, value=method,
                font=("Segoe UI", 10), bg=T.CARD, fg=T.FG,
                selectcolor=T.SECONDARY, activebackground=T.CARD,
                command=self._on_payment_change
            ).pack(side="left", padx=(0, 12))

        # Cash Tendered frame (hidden for non-Cash)
        self.tendered_frame = tk.Frame(f, bg=T.CARD)
        tk.Label(self.tendered_frame, text="Cash Tendered (\N{PESO SIGN}):", font=("Segoe UI", 10), bg=T.CARD, fg=T.FG_DIM).pack(anchor="w")
        self.v_tendered = tk.StringVar()
        self.v_tendered.trace_add("write", self._calc_change)
        ent = tk.Entry(self.tendered_frame, textvariable=self.v_tendered, font=("Segoe UI", 16, "bold"),
                 bg=T.BG, fg=T.FG, insertbackground=T.FG, relief="flat", justify="right")
        ent.pack(fill="x", pady=(4, 8), ipady=8)
        ent.focus()

        # Change display
        self.v_change = tk.StringVar(value="Change: \N{PESO SIGN} 0.00")
        self.change_label = tk.Label(f, textvariable=self.v_change, font=("Segoe UI", 12, "bold"), bg=T.CARD, fg=T.ACCENT)

        # Confirm Button (always at bottom)
        self.btn_confirm = tk.Button(f, text="Confirm Payment", font=("Segoe UI", 12, "bold"),
                  bg=T.ACCENT, fg=T.FG, relief="flat", cursor="hand2", pady=10, command=self._confirm)
        self.btn_confirm.pack(fill="x", side="bottom")

        self.bind("<Return>", lambda e: self._confirm())
        self._on_payment_change()  # initial state


    def _on_payment_change(self):
        """Show tendered/change only for Cash; auto-confirm for digital payments."""
        is_cash = self.v_payment.get() == "Cash"
        if is_cash:
            self.tendered_frame.pack(fill="x", before=self.change_label)
            self.change_label.pack(anchor="w", pady=(0, 16))
            self._calc_change()
        else:
            self.tendered_frame.pack_forget()
            self.change_label.pack_forget()
            self.btn_confirm.config(state="normal")

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
        method = self.v_payment.get()
        if method == "Cash":
            try:
                tendered = float(self.v_tendered.get().replace(",", ""))
            except ValueError:
                messagebox.showerror("Invalid", "Please enter a valid amount.", parent=self)
                return
            change = tendered - self.total
            if change < 0:
                messagebox.showerror("Insufficient", "Tendered amount is less than total.", parent=self)
                return
        else:
            tendered = self.total
            change = 0.0

        user = get_current_user()
        ok, msg, txn_number = process_sale(
            self.cart, user["id"], user["username"],
            tendered=tendered, change=change, payment_method=method
        )
        
        if ok:
            _ReceiptDialog(self.master, cart=self.cart, total=self.total,
                           tendered=tendered, change=change,
                           txn_number=txn_number, payment_method=method)
            self.on_success()
            self.destroy()
        else:
            messagebox.showerror("Error", msg, parent=self)

# ── Receipt Dialog ────────────────────────────────────────────────────

class _ReceiptDialog(tk.Toplevel):
    """Shows a receipt. Can be used from fresh checkout (cart mode) or from
    a transaction lookup (txn_number mode)."""
    def __init__(self, parent, *, cart=None, total=None, tendered=None, change=None, txn_number=None, payment_method="Cash"):
        super().__init__(parent)
        self.title("Transaction Receipt")
        self.configure(bg="#ffffff")
        self.resizable(False, False)
        self.grab_set()

        # If we have a txn_number, load from DB
        if txn_number and cart is None:
            data = get_receipt_by_txn(txn_number)
            if data:
                self.items = data["items"]
                self.total = data["total"]
                self.tendered = data["tendered"]
                self.change = data["change"]
                self.txn_number = data["txn_number"]
                self.sold_at = data["sold_at"]
                self.cashier = data["cashier"]
                self.payment_method = data.get("payment_method", "Cash")
            else:
                self.items = []
                self.total = 0
                self.tendered = 0
                self.change = 0
                self.txn_number = txn_number
                self.sold_at = ""
                self.cashier = ""
                self.payment_method = "Cash"
        else:
            # Fresh checkout mode
            self.items = [{"name": i["name"], "qty": i["qty"], "unit_price": i["unit_price"], "subtotal": i["qty"] * i["unit_price"]} for i in (cart or [])]
            self.total = total or 0
            self.tendered = tendered or 0
            self.change = change or 0
            self.txn_number = txn_number or ""
            self.sold_at = ""
            self.cashier = ""
            self.payment_method = payment_method or "Cash"

        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        w, h = 340, 600
        self.geometry(f"{w}x{h}+{(sw-w)//2}+{(sh-h)//2}")

    def _build(self):
        f = tk.Frame(self, bg="#ffffff", padx=20, pady=20)
        f.pack(fill="both", expand=True)

        # Try to show logo image
        try:
            logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "RosemenLOGO.png")
            logo_path = os.path.normpath(logo_path)
            if os.path.exists(logo_path):
                img = Image.open(logo_path).convert("RGBA")
                img.thumbnail((120, 120), Image.LANCZOS)
                # Paste onto white background (receipts are white)
                bg_img = Image.new("RGB", img.size, (255, 255, 255))
                bg_img.paste(img, mask=img.split()[3])
                self._logo_photo = ImageTk.PhotoImage(bg_img)
                lbl = tk.Label(f, image=self._logo_photo, bg="#ffffff")
                lbl.pack(pady=(0, 4))
            else:
                raise FileNotFoundError
        except Exception:
            tk.Label(f, text="ROSEMEN UKAY-UKAY", font=("Trajan Pro 3", 14, "bold"), bg="#ffffff", fg="#000000").pack()

        tk.Label(f, text="ROSEMEN UKAY-UKAY", font=("Courier", 11, "bold"), bg="#ffffff", fg="#000000").pack()
        tk.Label(f, text="--------------------------------", font=("Courier", 10), bg="#ffffff", fg="#000000").pack(pady=4)

        # Transaction info
        if self.txn_number:
            tk.Label(f, text=f"TXN#: {self.txn_number}", font=("Courier", 8), bg="#ffffff", fg="#555555").pack(anchor="w")
        if self.sold_at:
            tk.Label(f, text=f"Date: {self.sold_at}", font=("Courier", 8), bg="#ffffff", fg="#555555").pack(anchor="w")
        if self.cashier:
            tk.Label(f, text=f"Cashier: {self.cashier}", font=("Courier", 8), bg="#ffffff", fg="#555555").pack(anchor="w")
        if self.txn_number or self.sold_at or self.cashier:
            tk.Label(f, text="--------------------------------", font=("Courier", 10), bg="#ffffff", fg="#000000").pack(pady=4)

        # Items
        items_frame = tk.Frame(f, bg="#ffffff")
        items_frame.pack(fill="both", expand=True)

        for item in self.items:
            row = tk.Frame(items_frame, bg="#ffffff")
            row.pack(fill="x", pady=2)
            tk.Label(row, text=f"{item['qty']}x {item['name']}", font=("Courier", 10), bg="#ffffff", fg="#000000").pack(side="left")
            tk.Label(row, text=f"{item['subtotal']:,.2f}", font=("Courier", 10), bg="#ffffff", fg="#000000").pack(side="right")

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
        add_row(totals_frame, "METHOD:", self.payment_method)
        if self.payment_method == "Cash":
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
        self.geometry(f"800x420+{(sw-800)//2}+{(sh-420)//2}")
        
    def _build(self):
        f = tk.Frame(self, bg=T.BG, padx=20, pady=20)
        f.pack(fill="both", expand=True)
        
        tk.Label(f, text="Recent Transactions (Today)", font=("Segoe UI", 14, "bold"), bg=T.BG, fg=T.FG).pack(anchor="w", pady=(0, 10))
        
        # Treeview
        columns = ("txn", "time", "product", "qty", "total", "tendered", "change", "status", "cashier")
        self.tree = ttk.Treeview(f, columns=columns, show="headings", height=10)
        
        self.tree.heading("txn", text="TXN#")
        self.tree.heading("time", text="Time")
        self.tree.heading("product", text="Product")
        self.tree.heading("qty", text="Qty")
        self.tree.heading("total", text="Total")
        self.tree.heading("tendered", text="Cash")
        self.tree.heading("change", text="Change")
        self.tree.heading("status", text="Status")
        self.tree.heading("cashier", text="Cashier")
        
        self.tree.column("txn", width=160)
        self.tree.column("time", width=120)
        self.tree.column("product", width=130)
        self.tree.column("qty", width=40, anchor="center")
        self.tree.column("total", width=80, anchor="e")
        self.tree.column("tendered", width=80, anchor="e")
        self.tree.column("change", width=80, anchor="e")
        self.tree.column("status", width=80, anchor="center")
        self.tree.column("cashier", width=80)
        
        self.tree.pack(fill="both", expand=True)
        T.apply_treeview_style()
        
        self.tree.tag_configure("refunded", foreground=T.FG_DIM)
        self.tree.bind("<Double-1>", self._on_double_click)
        
        # Actions
        btn_frame = tk.Frame(f, bg=T.BG)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        tk.Button(btn_frame, text="🧾  View Receipt", font=("Segoe UI", 10, "bold"),
                  bg=T.SECONDARY, fg=T.FG, cursor="hand2", relief="flat", padx=15, pady=5,
                  command=self._view_receipt).pack(side="left", padx=(0, 8))
        tk.Button(btn_frame, text="Refund Selected", font=("Segoe UI", 10, "bold"),
                  bg=T.ACCENT, fg=T.FG, cursor="hand2", relief="flat", padx=15, pady=5,
                  command=self._do_refund).pack(side="left")
                  
    def _load_data(self):
        self.tree.delete(*self.tree.get_children())
        self._sales_data = get_recent_sales_for_pos()
        for idx, s in enumerate(self._sales_data):
            tag = "refunded" if s["status"] == "refunded" else ""
            self.tree.insert("", "end", iid=str(idx), tags=(tag,), values=(
                s.get("txn_number", "") or f"#{s['id']}",
                s["sold_at"],
                s["product"],
                s["qty"],
                f"₱{s['total']:,.2f}",
                f"₱{s['tendered']:,.2f}",
                f"₱{s['change']:,.2f}",
                s["status"].upper(),
                s["username"]
            ))

    def _get_selected_txn(self):
        sel = self.tree.selection()
        if not sel:
            return None, None
        idx = int(sel[0])
        s = self._sales_data[idx]
        return s.get("txn_number"), s["id"]

    def _on_double_click(self, event):
        self._view_receipt()

    def _view_receipt(self):
        txn_number, sale_id = self._get_selected_txn()
        if txn_number is None and sale_id is None:
            messagebox.showwarning("Select Transaction", "Please select a transaction to view.", parent=self)
            return
        if txn_number:
            _ReceiptDialog(self, txn_number=txn_number)
        else:
            messagebox.showinfo("No Receipt", "This transaction was made before transaction numbers were added.", parent=self)

    def _do_refund(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Select Transaction", "Please select a transaction to refund.", parent=self)
            return

        idx = int(sel[0])
        s = self._sales_data[idx]
        sale_id = s["id"]
        status = s["status"]
        
        if status == "refunded":
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
