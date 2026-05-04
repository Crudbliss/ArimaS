"""
logger.py
---------
Writes entries to the activity_logs table.
"""

import sqlite3
from database.db_setup import get_connection


def log_action(user_id: int | None, username: str, action: str, details: str = ""):
    """
    Insert an audit log entry.

    Args:
        user_id:  ID from the users table (None for system actions)
        username: Display name for the log entry
        action:   Short action label (e.g. "LOGIN", "ADD_PRODUCT", "SALE")
        details:  Optional longer description
    """
    try:
        conn = get_connection()
        conn.execute(
            """
            INSERT INTO activity_logs (user_id, username, action, details)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, username, action, details)
        )
        conn.commit()
        conn.close()
    except sqlite3.Error as e:
        print(f"[logger] Failed to write log: {e}")
