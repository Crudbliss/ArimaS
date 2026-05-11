"""
login_window.py
---------------
The login screen for Rosemen Ukay-Ukay.
"""

import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk
import os
from auth.auth_manager import login
import utils.theme as T


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
        # You can resize the login window by changing the numbers below (Width, Height):
        self._center_window(600, 660)

        self._build_ui()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------
    def _build_ui(self):
        # ── Outer frame ─────────────────────────────────────────────
        outer = tk.Frame(self.root, bg=T.BG)
        outer.pack(fill="both", expand=True)

        # ── Header / Banner ─────────────────────────────────────────
        header = tk.Frame(outer, bg=T.CARD, pady=20)
        header.pack(fill="x")

        # Theme toggle button in header
        mode_text = "🌙" if T.is_dark() else "☀"
        self.theme_btn = tk.Button(
            header, text=mode_text, font=("Segoe UI", 12),
            bg=T.CARD, fg=T.FG_DIM, relief="flat", cursor="hand2", bd=0,
            activebackground=T.SECONDARY, activeforeground=T.FG,
            command=self._toggle_theme
        )
        self.theme_btn.place(relx=0.95, rely=0.1, anchor="ne")

        # Load and display the logo
        try:
            logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "RosemenLOGO.png")
            if os.path.exists(logo_path):
                img = Image.open(logo_path)
                # Resize the image to look good in the header
                img.thumbnail((120, 120), Image.Resampling.LANCZOS)
                self._logo_photo = ImageTk.PhotoImage(img)
                tk.Label(header, image=self._logo_photo, bg=T.CARD).pack(pady=(0, 5))
        except Exception as e:
            print("Failed to load logo:", e)

        tk.Label(
            header,
            text="Rosemen Ukay-Ukay",
            font=("Trajan Pro 3", 20, "bold"),
            bg=T.CARD,
            fg=T.ACCENT,
        ).pack()

        tk.Label(
            header,
            text="Inventory & Sales Management System",
            font=("Segoe UI", 9),
            bg=T.CARD,
            fg=T.FG_DIM,
        ).pack(pady=(2, 0))

        # ── Card ────────────────────────────────────────────────────
        card = tk.Frame(outer, bg=T.CARD, padx=40, pady=30)
        card.pack(fill="both", expand=True, padx=30, pady=20)

        tk.Label(
            card,
            text="Sign In",
            font=("Segoe UI", 14, "bold"),
            bg=T.CARD,
            fg=T.FG,
        ).pack(anchor="w", pady=(0, 20))

        # Username
        tk.Label(card, text="Username", font=("Segoe UI", 9),
                 bg=T.CARD, fg=T.FG_DIM).pack(anchor="w")
        self.username_var = tk.StringVar()
        username_entry = tk.Entry(
            card, textvariable=self.username_var,
            font=("Segoe UI", 11), bg=T.SECONDARY, fg=T.FG,
            insertbackground=T.FG, relief="flat",
            highlightthickness=1, highlightbackground=T.ACCENT,
        )
        username_entry.pack(fill="x", pady=(4, 16), ipady=6)

        # Password
        tk.Label(card, text="Password", font=("Segoe UI", 9),
                 bg=T.CARD, fg=T.FG_DIM).pack(anchor="w")

        pw_frame = tk.Frame(card, bg=T.SECONDARY,
                            highlightthickness=1, highlightbackground=T.ACCENT)
        pw_frame.pack(fill="x", pady=(4, 4))

        self.password_var = tk.StringVar()
        self.show_pw = False

        self.pw_entry = tk.Entry(
            pw_frame, textvariable=self.password_var,
            font=("Segoe UI", 11), bg=T.SECONDARY, fg=T.FG,
            insertbackground=T.FG, relief="flat", show="●",
        )
        self.pw_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(6, 0))

        self.toggle_btn = tk.Button(
            pw_frame, text="👁", bg=T.SECONDARY, fg=T.FG_DIM,
            relief="flat", cursor="hand2",
            command=self._toggle_password,
        )
        self.toggle_btn.pack(side="right", padx=4)

        # Error label (hidden until needed)
        self.error_var = tk.StringVar()
        self.error_label = tk.Label(
            card, textvariable=self.error_var,
            font=("Segoe UI", 9), bg=T.CARD, fg=T.ACCENT,
            wraplength=300,
        )
        self.error_label.pack(anchor="w", pady=(0, 8))

        # Login button
        self.login_btn = tk.Button(
            card,
            text="Login",
            font=("Segoe UI", 11, "bold"),
            bg=T.ACCENT, fg=T.BG,  # Usually background of button is ACCENT, text is BG
            activebackground=T.SECONDARY, activeforeground=T.FG,
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
            bg=T.BG, fg=T.FG_DIM,
        ).pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _do_toggle_theme(self):
        T.toggle_theme()
        for w in self.root.winfo_children():
            w.destroy()
        self._build_ui()

    def _toggle_theme(self):
        self.root.after(10, self._do_toggle_theme)

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
