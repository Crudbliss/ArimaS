"""
login_window.py
---------------
The login screen for Rosemen Ukay-Ukay.
"""

import tkinter as tk
from tkinter import messagebox
from auth.auth_manager import login


class LoginWindow:
    def __init__(self, root: tk.Tk, on_success):
        """
        Args:
            root:       The root Tk window.
            on_success: Callback(role: str) called after a successful login.
        """
        self.root = root
        self.on_success = on_success

        self.root.title("Rosemen Ukay-Ukay")
        self.root.resizable(False, False)
        self._center_window(420, 480)

        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Outer frame ─────────────────────────────────────────────
        outer = tk.Frame(self.root, bg="#1a1a2e")
        outer.pack(fill="both", expand=True)

        # ── Header / Banner ─────────────────────────────────────────
        header = tk.Frame(outer, bg="#16213e", pady=20)
        header.pack(fill="x")

        tk.Label(
            header,
            text="👗 Rosemen Ukay-Ukay",
            font=("Segoe UI", 18, "bold"),
            bg="#16213e",
            fg="#e94560",
        ).pack()

        tk.Label(
            header,
            text="Inventory & Sales Management System",
            font=("Segoe UI", 9),
            bg="#16213e",
            fg="#a8a8b3",
        ).pack(pady=(2, 0))

        # ── Card ────────────────────────────────────────────────────
        card = tk.Frame(outer, bg="#16213e", padx=40, pady=30)
        card.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(
            card,
            text="Sign In",
            font=("Segoe UI", 14, "bold"),
            bg="#16213e",
            fg="#ffffff",
        ).pack(anchor="w", pady=(0, 20))

        # Username
        tk.Label(card, text="Username", font=("Segoe UI", 9),
                 bg="#16213e", fg="#a8a8b3").pack(anchor="w")
        self.username_var = tk.StringVar()
        username_entry = tk.Entry(
            card, textvariable=self.username_var,
            font=("Segoe UI", 11), bg="#0f3460", fg="#ffffff",
            insertbackground="#ffffff", relief="flat",
            highlightthickness=1, highlightbackground="#e94560",
        )
        username_entry.pack(fill="x", pady=(4, 16), ipady=6)

        # Password
        tk.Label(card, text="Password", font=("Segoe UI", 9),
                 bg="#16213e", fg="#a8a8b3").pack(anchor="w")

        pw_frame = tk.Frame(card, bg="#0f3460",
                            highlightthickness=1, highlightbackground="#e94560")
        pw_frame.pack(fill="x", pady=(4, 4))

        self.password_var = tk.StringVar()
        self.show_pw = False

        self.pw_entry = tk.Entry(
            pw_frame, textvariable=self.password_var,
            font=("Segoe UI", 11), bg="#0f3460", fg="#ffffff",
            insertbackground="#ffffff", relief="flat", show="●",
        )
        self.pw_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(6, 0))

        self.toggle_btn = tk.Button(
            pw_frame, text="👁", bg="#0f3460", fg="#a8a8b3",
            relief="flat", cursor="hand2",
            command=self._toggle_password,
        )
        self.toggle_btn.pack(side="right", padx=4)

        # Error label (hidden until needed)
        self.error_var = tk.StringVar()
        self.error_label = tk.Label(
            card, textvariable=self.error_var,
            font=("Segoe UI", 9), bg="#16213e", fg="#e94560",
            wraplength=300,
        )
        self.error_label.pack(anchor="w", pady=(0, 8))

        # Login button
        self.login_btn = tk.Button(
            card,
            text="Login",
            font=("Segoe UI", 11, "bold"),
            bg="#e94560", fg="#ffffff",
            activebackground="#c73652", activeforeground="#ffffff",
            relief="flat", cursor="hand2", pady=8,
            command=self._on_login,
        )
        self.login_btn.pack(fill="x", pady=(4, 0))

        # Bind Enter key
        self.root.bind("<Return>", lambda e: self._on_login())

        # Focus username field
        username_entry.focus()

        # ── Footer ──────────────────────────────────────────────────
        tk.Label(
            outer,
            text="© 2025 Rosemen Ukay-Ukay · ArimaS v1.0",
            font=("Segoe UI", 8),
            bg="#1a1a2e", fg="#555577",
        ).pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _toggle_password(self):
        self.show_pw = not self.show_pw
        self.pw_entry.config(show="" if self.show_pw else "●")
        self.toggle_btn.config(text="🙈" if self.show_pw else "👁")

    def _on_login(self):
        username = self.username_var.get().strip()
        password = self.password_var.get()

        if not username or not password:
            self.error_var.set("Please enter both username and password.")
            return

        self.login_btn.config(state="disabled", text="Signing in…")
        self.root.update()

        success, result = login(username, password)

        self.login_btn.config(state="normal", text="Login")

        if success:
            self.error_var.set("")
            self.on_success(result)   # result = "admin" or "user"
        else:
            self.error_var.set(result)
            self.password_var.set("")
            self.pw_entry.focus()

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------
    def _center_window(self, width: int, height: int):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = (sw - width) // 2
        y = (sh - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")
