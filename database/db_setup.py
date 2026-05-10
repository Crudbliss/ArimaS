"""
db_setup.py
-----------
Creates all SQLite tables and seeds default data for Rosemen Ukay-Ukay.
Run this once before launching the app for the first time.
"""

import sqlite3
import hashlib
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "arimas.db")


def get_connection():
    """Return a connection to the SQLite database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def hash_password(password: str) -> str:
    """SHA-256 hash a password string."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_tables(conn: sqlite3.Connection):
    """Create all application tables if they don't already exist."""
    cursor = conn.cursor()

    # ------------------------------------------------------------------
    # USERS
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT    NOT NULL UNIQUE,
            password    TEXT    NOT NULL,
            role        TEXT    NOT NULL CHECK(role IN ('admin', 'user')),
            is_active   INTEGER NOT NULL DEFAULT 1,
            created_at  TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # ------------------------------------------------------------------
    # PRODUCTS  (Clothing catalog)
    # buying_price  = cost per sack (bulk purchase)
    # selling_price = price per piece (or per bundle for kids wear)
    # bundle_qty    = pieces per selling unit (1 for most, 4 for kids wear)
    # pieces_per_sack = estimated/actual pieces extracted from one sack
    # stock_pieces  = current available pieces in store
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL UNIQUE,
            category         TEXT    NOT NULL,
            buying_price     REAL    NOT NULL,
            selling_price    REAL    NOT NULL,
            bundle_qty       INTEGER NOT NULL DEFAULT 1,
            pieces_per_sack  INTEGER NOT NULL DEFAULT 0,
            stock_pieces     INTEGER NOT NULL DEFAULT 0,
            reorder_level    INTEGER NOT NULL DEFAULT 10,
            created_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime')),
            updated_at       TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # ------------------------------------------------------------------
    # SACK PURCHASES  (records every bulk sack bought)
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sack_purchases (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id   INTEGER NOT NULL REFERENCES products(id),
            sacks_bought INTEGER NOT NULL DEFAULT 1,
            cost_per_sack REAL   NOT NULL,
            pieces_added INTEGER NOT NULL,
            purchased_by INTEGER NOT NULL REFERENCES users(id),
            purchased_at TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # ------------------------------------------------------------------
    # SALES  (individual POS transactions)
    # qty_sold = number of pieces (or bundles for kids wear)
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id   INTEGER NOT NULL REFERENCES products(id),
            qty_sold     INTEGER NOT NULL,
            unit_price   REAL    NOT NULL,
            total_amount REAL    NOT NULL,
            tendered     REAL    NOT NULL DEFAULT 0,
            change       REAL    NOT NULL DEFAULT 0,
            status       TEXT    NOT NULL DEFAULT 'completed',
            served_by    INTEGER NOT NULL REFERENCES users(id),
            sold_at      TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # --- Migration: add columns to existing sales table if they don't exist ---
    try:
        cursor.execute("ALTER TABLE sales ADD COLUMN tendered REAL NOT NULL DEFAULT 0")
        cursor.execute("ALTER TABLE sales ADD COLUMN change REAL NOT NULL DEFAULT 0")
        cursor.execute("ALTER TABLE sales ADD COLUMN status TEXT NOT NULL DEFAULT 'completed'")
    except sqlite3.OperationalError:
        pass  # Columns already exist

    # ------------------------------------------------------------------
    # ACTIVITY LOGS  (audit trail for every significant action)
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS activity_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id     INTEGER REFERENCES users(id),
            username    TEXT    NOT NULL,
            action      TEXT    NOT NULL,
            details     TEXT,
            logged_at   TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    # ------------------------------------------------------------------
    # REORDER ALERTS  (generated by forecast/recommendation logic)
    # ------------------------------------------------------------------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reorder_alerts (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id      INTEGER NOT NULL REFERENCES products(id),
            current_stock   INTEGER NOT NULL,
            predicted_demand INTEGER NOT NULL,
            suggested_sacks INTEGER NOT NULL,
            status          TEXT    NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','acknowledged','ordered')),
            generated_at    TEXT    NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)

    conn.commit()
    print("[db_setup] Tables created successfully.")


def seed_default_users(conn: sqlite3.Connection):
    """Insert default admin and user accounts (skips if already present)."""
    cursor = conn.cursor()

    defaults = [
        ("admin",    hash_password("Admin@1234"), "admin"),
        ("cashier1", hash_password("User@1234"),  "user"),
    ]

    for username, pwd_hash, role in defaults:
        cursor.execute(
            "INSERT OR IGNORE INTO users (username, password, role) VALUES (?, ?, ?)",
            (username, pwd_hash, role)
        )

    conn.commit()
    print("[db_setup] Default users seeded (admin / cashier1).")


def seed_products(conn: sqlite3.Connection):
    """
    Seed the clothing catalog with real store data.

    Kids Wear note:
      - Sold as 4-piece bundles at 100 pesos per bundle (25 pesos each)
      - bundle_qty = 4, selling_price = 100
    """
    cursor = conn.cursor()

    # (name, category, buying_price, selling_price, bundle_qty, pieces_per_sack, reorder_level)
    products = [
        ("Men's Shirt",   "Tops",      2800.0,  50.0,  1, 110, 15),
        ("Women's Shirt", "Tops",      3500.0,  50.0,  1, 150, 15),
        ("Shorts",        "Bottoms",   2499.0,  75.0,  1,  90, 10),
        ("Joggers",       "Bottoms",   2800.0, 100.0,  1,  55, 10),
        ("Jackets",       "Outerwear", 2600.0, 100.0,  1,  40,  8),
        ("Trousers",      "Bottoms",   3500.0, 100.0,  1,  50, 10),
        ("Kids Wear",     "Kids",      5000.0, 100.0,  4, 220, 12),
    ]

    for p in products:
        cursor.execute("""
            INSERT OR IGNORE INTO products
                (name, category, buying_price, selling_price, bundle_qty, pieces_per_sack, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, p)

    conn.commit()
    print("[db_setup] Clothing products seeded.")


def initialize_database():
    """Full setup: connect → create tables → seed data."""
    conn = get_connection()
    try:
        create_tables(conn)
        seed_default_users(conn)
        seed_products(conn)
        print(f"[db_setup] Database ready at: {DB_PATH}")
    finally:
        conn.close()


if __name__ == "__main__":
    initialize_database()
