"""
main.py
-------
Entry point for the Rosemen Ukay-Ukay ArimaS application.
"""

import tkinter as tk
import sys
import os
import subprocess
import ctypes

def load_custom_fonts():
    if os.name == 'nt':
        font_dir = os.path.join(os.path.dirname(__file__), "font")
        for f in ["TrajanP3.otf", "ClashDisplay-Regular.otf", "Lato-Bold.ttf"]:
            fpath = os.path.join(font_dir, f)
            if os.path.exists(fpath):
                ctypes.windll.gdi32.AddFontResourceW(fpath)

load_custom_fonts()


def _ensure_dependencies():
    required = {
        "statsmodels": "statsmodels", 
        "matplotlib": "matplotlib", 
        "pandas": "pandas", 
        "sqlalchemy": "sqlalchemy",
        "sklearn": "scikit-learn"
    }
    missing = []
    for pkg, pip_name in required.items():
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pip_name)
    if missing:
        print(f"Installing missing dependencies: {', '.join(missing)}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        print("Dependencies installed successfully!")

_ensure_dependencies()

# Make sure imports resolve from the project root
sys.path.insert(0, os.path.dirname(__file__))

from database.db_setup import initialize_database
from ui.login_window import LoginWindow


def on_login_success(role: str):
    """Called after a successful login — routes to the correct window."""
    # Hide the login window
    root.withdraw()

    if role == "admin":
        from ui.admin.admin_dashboard import AdminDashboard
        dashboard = tk.Toplevel(root)
        AdminDashboard(dashboard, on_logout)
    else:
        from ui.user.user_window import UserWindow
        user_win = tk.Toplevel(root)
        UserWindow(user_win, on_logout)


def on_logout():
    """Called when a user logs out — returns to login screen."""
    from auth.auth_manager import logout
    logout()

    # Destroy all widgets in root to prevent stacking duplicate login screens
    for widget in root.winfo_children():
        widget.destroy()

    # Re-show and reset the login window
    root.deiconify()
    LoginWindow(root, on_login_success)


if __name__ == "__main__":
    # Phase 1: ensure database + tables + seed data exist
    initialize_database()

    root = tk.Tk()
    root.configure(bg="#1a1a2e")

    LoginWindow(root, on_login_success)
    root.mainloop()
