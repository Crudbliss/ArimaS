"""
user_manager.py  –  Admin panel to create and manage user accounts.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import hashlib
from database.db_setup import get_connection
from auth.auth_manager import get_current_user
from utils.validators import validate_password, validate_username
from utils.logger import log_action
import utils.theme as T


def _get_all_users() -> list[tuple]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, username, role,
               CASE is_active WHEN 1 THEN 'Active' ELSE 'Inactive' END,
               created_at
        FROM users ORDER BY id
    """).fetchall()
    conn.close()
    return rows


def _toggle_active(user_id: int, current_label: str) -> tuple[bool, str]:
    new_val = 0 if current_label == "Active" else 1
    try:
        conn = get_connection()
        conn.execute("UPDATE users SET is_active=? WHERE id=?", (new_val, user_id))
        conn.commit()
        conn.close()
        return True, "Active" if new_val else "Inactive"
    except Exception as e:
        return False, str(e)


def _create_user(username: str, password: str, role: str) -> tuple[bool, str]:
    ok, msg = validate_username(username)
    if not ok:
        return False, msg
    ok, msg = validate_password(password)
    if not ok:
        return False, msg
    try:
        conn = get_connection()
        hashed = hashlib.sha256(password.encode()).hexdigest()
        conn.execute(
            "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, hashed, role)
        )
        conn.commit()
        conn.close()
        return True, f"User '{username}' created."
    except Exception as e:
        return False, f"Username already exists." if "UNIQUE" in str(e) else str(e)


class UserManagerPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=T.BG)
        self._build()

    def _build(self):
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=24, pady=(20, 6))

        tk.Label(bar, text="User Manager",
                 font=("Segoe UI", 16, "bold"), bg=T.BG, fg=T.FG).pack(side="left")

        for label, cmd in [("⟳ Refresh", self.refresh),
                           ("+ Add User", self._open_add),
                           ("⏻ Toggle Active", self._toggle)]:
            tk.Button(bar, text=label, font=("Segoe UI", 9),
                      bg=T.SECONDARY, fg=T.FG, relief="flat", cursor="hand2",
                      padx=10, pady=4, command=cmd).pack(side="right", padx=3)

        # Treeview
        frame = tk.Frame(self, bg=T.CARD)
        frame.pack(fill="both", expand=True, padx=24, pady=(8, 20))

        style = T.apply_treeview_style("User.Treeview")
        cols = ("id", "username", "role", "status", "created")
        self._tree = ttk.Treeview(frame, columns=cols,
                                  show="headings", style=style)

        for col, text, w in [("id","ID",50),("username","Username",180),
                               ("role","Role",100),("status","Status",100),
                               ("created","Created At",180)]:
            self._tree.heading(col, text=text)
            self._tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        self._tree.pack(fill="both", expand=True)

        self.refresh()

    def refresh(self):
        rows = _get_all_users()
        self._tree.delete(*self._tree.get_children())
        for r in rows:
            tag = "inactive" if r[3] == "Inactive" else ""
            self._tree.insert("", "end", iid=str(r[0]), values=r, tags=(tag,))
        self._tree.tag_configure("inactive", foreground=T.FG_DIM)

    def _selected(self):
        sel = self._tree.selection()
        if not sel:
            messagebox.showwarning("No Selection", "Select a user first.")
            return None
        return self._tree.item(sel[0])["values"]  # (id, username, role, status, created)

    def _toggle(self):
        row = self._selected()
        if not row:
            return
        uid, uname, _, status, _ = row
        caller = get_current_user()
        if uid == caller["id"]:
            messagebox.showwarning("Not Allowed",
                                   "You cannot deactivate your own account.")
            return
        ok, result = _toggle_active(int(uid), status)
        if ok:
            log_action(caller["id"], caller["username"],
                       "TOGGLE_USER", f"{uname} → {result}")
            self.refresh()
        else:
            messagebox.showerror("Error", result)

    def _open_add(self):
        _AddUserDialog(self, on_save=self.refresh)


class _AddUserDialog(tk.Toplevel):
    def __init__(self, parent, on_save):
        super().__init__(parent)
        self.on_save = on_save
        self.title("Create New User")
        self.configure(bg=T.CARD)
        self.resizable(False, False)
        self.grab_set()
        self._build()
        self.update_idletasks()
        sw, sh = self.winfo_screenwidth(), self.winfo_screenheight()
        self.geometry(f"400x380+{(sw-400)//2}+{(sh-380)//2}")

    def _build(self):
        f = tk.Frame(self, bg=T.CARD, padx=30, pady=24)
        f.pack(fill="both", expand=True)

        tk.Label(f, text="New User Account",
                 font=("Segoe UI", 13, "bold"), bg=T.CARD, fg=T.FG).pack(anchor="w", pady=(0,16))

        self.v_user = tk.StringVar()
        self.v_pass = tk.StringVar()
        self.v_role = tk.StringVar(value="user")
        self.v_err  = tk.StringVar()

        for label, var, show in [("Username", self.v_user, False),
                                  ("Password", self.v_pass, True)]:
            tk.Label(f, text=label, font=("Segoe UI", 9),
                     bg=T.CARD, fg=T.FG_DIM).pack(anchor="w")
            tk.Entry(f, textvariable=var, font=("Segoe UI", 10),
                     bg=T.SECONDARY, fg=T.FG, insertbackground=T.FG,
                     relief="flat", show="●" if show else ""
                     ).pack(fill="x", pady=(3, 12), ipady=5)

        tk.Label(f, text="Role", font=("Segoe UI", 9),
                 bg=T.CARD, fg=T.FG_DIM).pack(anchor="w")
        role_frame = tk.Frame(f, bg=T.CARD)
        role_frame.pack(anchor="w", pady=(3, 12))
        for val, lbl in [("user","Cashier / User"), ("admin","Admin")]:
            tk.Radiobutton(role_frame, text=lbl, variable=self.v_role,
                           value=val, bg=T.CARD, fg=T.FG, selectcolor=T.SECONDARY,
                           activebackground=T.CARD, font=("Segoe UI", 9)
                           ).pack(side="left", padx=(0, 16))

        tk.Label(f, textvariable=self.v_err, font=("Segoe UI", 8),
                 bg=T.CARD, fg=T.ACCENT, wraplength=320).pack(anchor="w")

        tk.Button(f, text="Create User", font=("Segoe UI", 10, "bold"),
                  bg=T.ACCENT, fg=T.FG, relief="flat", cursor="hand2",
                  pady=8, command=self._save).pack(fill="x", pady=(12, 0))

    def _save(self):
        username = self.v_user.get().strip()
        password = self.v_pass.get()
        role     = self.v_role.get()

        ok, msg = _create_user(username, password, role)
        if ok:
            caller = get_current_user()
            log_action(caller["id"], caller["username"],
                       "CREATE_USER", f"Created {role} account: {username}")
            messagebox.showinfo("Created", msg, parent=self)
            self.on_save()
            self.destroy()
        else:
            self.v_err.set(msg)
