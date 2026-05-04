"""
auth_manager.py
---------------
Handles login authentication and session state.
"""

import hashlib
import sqlite3
from database.db_setup import get_connection
from utils.logger import log_action

# Tracks the currently logged-in user for the session
_current_user: dict | None = None

# Failed login attempt counter per username
_failed_attempts: dict[str, int] = {}
MAX_ATTEMPTS = 5


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()


def login(username: str, password: str) -> tuple[bool, str]:
    """
    Attempt to log in with username and password.

    Returns:
        (True,  "admin" | "user") on success
        (False, "reason message") on failure
    """
    global _current_user

    # Check lockout
    attempts = _failed_attempts.get(username, 0)
    if attempts >= MAX_ATTEMPTS:
        return False, f"Account locked after {MAX_ATTEMPTS} failed attempts. Contact an admin."

    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, username, password, role, is_active FROM users WHERE username = ?",
            (username,)
        )
        row = cursor.fetchone()
        conn.close()
    except sqlite3.Error as e:
        return False, f"Database error: {e}"

    if row is None:
        _record_failure(username)
        return False, "Invalid username or password."

    user_id, db_username, db_password, role, is_active = row

    if not is_active:
        return False, "This account has been deactivated. Contact an admin."

    if hash_password(password) != db_password:
        _record_failure(username)
        remaining = MAX_ATTEMPTS - _failed_attempts.get(username, 0)
        return False, f"Invalid username or password. {remaining} attempt(s) remaining."

    # Success — clear failure count and set session
    _failed_attempts.pop(username, None)
    _current_user = {
        "id":       user_id,
        "username": db_username,
        "role":     role,
    }

    log_action(user_id, db_username, "LOGIN", f"Logged in as {role}")
    return True, role


def logout():
    """Clear the current session."""
    global _current_user
    if _current_user:
        log_action(
            _current_user["id"],
            _current_user["username"],
            "LOGOUT",
            "User logged out"
        )
    _current_user = None


def get_current_user() -> dict | None:
    """Return the active session user dict, or None if not logged in."""
    return _current_user


def is_admin() -> bool:
    return _current_user is not None and _current_user["role"] == "admin"


def _record_failure(username: str):
    _failed_attempts[username] = _failed_attempts.get(username, 0) + 1
