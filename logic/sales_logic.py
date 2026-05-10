"""
sales_logic.py  –  POS transaction processing and sales retrieval.
"""

import sqlite3
from database.db_setup import get_connection
from utils.logger import log_action


def process_sale(cart: list[dict], user_id: int, username: str, tendered: float = 0.0, change: float = 0.0) -> tuple[bool, str]:
    """
    cart items: {"product_id", "name", "qty", "unit_price", "bundle_qty"}
    """
    if not cart:
        return False, "Cart is empty."

    conn = get_connection()
    try:
        for item in cart:
            pid        = item["product_id"]
            qty        = item["qty"]
            unit_price = item["unit_price"]
            bundle_qty = item["bundle_qty"]
            total      = qty * unit_price
            pieces_needed = qty * bundle_qty

            row = conn.execute(
                "SELECT stock_pieces FROM products WHERE id=?", (pid,)
            ).fetchone()
            if not row:
                raise ValueError(f"Product '{item['name']}' not found.")
            if row[0] < pieces_needed:
                raise ValueError(
                    f"Not enough stock for '{item['name']}'. "
                    f"Have {row[0]} pcs, need {pieces_needed}."
                )

            conn.execute("""
                INSERT INTO sales (product_id, qty_sold, unit_price, total_amount, tendered, change, status, served_by)
                VALUES (?, ?, ?, ?, ?, ?, 'completed', ?)
            """, (pid, qty, unit_price, total, tendered, change, user_id))
            conn.execute("""
                UPDATE products SET stock_pieces = stock_pieces - ?,
                    updated_at = datetime('now','localtime')
                WHERE id = ?
            """, (pieces_needed, pid))

        conn.commit()
        grand_total = sum(i["qty"] * i["unit_price"] for i in cart)
        summary = ", ".join(f"{i['name']} x{i['qty']}" for i in cart)
        log_action(user_id, username, "SALE", f"₱{grand_total:.2f} — {summary}")
        return True, f"Sale complete! Total: ₱{grand_total:.2f}"

    except ValueError as e:
        conn.rollback()
        return False, str(e)
    except sqlite3.Error as e:
        conn.rollback()
        return False, f"Database error: {e}"
    finally:
        conn.close()


def get_all_sales() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.id, p.name, s.qty_sold, s.unit_price, s.total_amount,
               u.username, s.sold_at
        FROM sales s
        JOIN products p ON s.product_id = p.id
        JOIN users u ON s.served_by = u.id
        ORDER BY s.sold_at DESC
    """).fetchall()
    conn.close()
    cols = ["id","product","qty","unit_price","total","served_by","sold_at"]
    return [dict(zip(cols, r)) for r in rows]


def get_my_sales(user_id: int) -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.id, p.name, s.qty_sold, s.unit_price, s.total_amount, s.sold_at, s.status, s.tendered, s.change
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE s.served_by = ?
        ORDER BY s.sold_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    cols = ["id","product","qty","unit_price","total","sold_at","status","tendered","change"]
    return [dict(zip(cols, r)) for r in rows]

def get_recent_sales_for_pos() -> list[dict]:
    """Fetch the latest sales for the POS 'Transactions' popup."""
    conn = get_connection()
    rows = conn.execute("""
        SELECT s.id, p.name, s.qty_sold, s.total_amount, s.status, u.username, s.sold_at, s.tendered, s.change
        FROM sales s
        JOIN products p ON s.product_id = p.id
        JOIN users u ON s.served_by = u.id
        WHERE date(s.sold_at) = date('now', 'localtime')
        ORDER BY s.sold_at DESC LIMIT 100
    """).fetchall()
    conn.close()
    cols = ["id","product","qty","total","status","username","sold_at","tendered","change"]
    return [dict(zip(cols, r)) for r in rows]

def refund_sale(sale_id: int, user_id: int, username: str) -> tuple[bool, str]:
    conn = get_connection()
    try:
        # Check if sale exists and is completed
        row = conn.execute(
            "SELECT product_id, qty_sold, status FROM sales WHERE id=?", (sale_id,)
        ).fetchone()
        if not row:
            return False, "Transaction not found."
        
        pid, qty_sold, status = row
        if status == 'refunded':
            return False, "This transaction is already refunded."
        
        # We need bundle_qty to restore the exact pieces
        p_row = conn.execute("SELECT bundle_qty, name FROM products WHERE id=?", (pid,)).fetchone()
        if not p_row:
            bundle_qty = 1
            pname = f"Unknown Product (ID {pid})"
        else:
            bundle_qty, pname = p_row

        pieces_to_restore = qty_sold * bundle_qty

        # 1. Update sale status
        conn.execute("UPDATE sales SET status='refunded' WHERE id=?", (sale_id,))
        
        # 2. Restore stock
        conn.execute("""
            UPDATE products SET stock_pieces = stock_pieces + ?, updated_at = datetime('now','localtime')
            WHERE id=?
        """, (pieces_to_restore, pid))
        
        conn.commit()
        log_action(user_id, username, "REFUND", f"Refunded sale #{sale_id} - restored {pieces_to_restore} pcs of {pname}")
        return True, "Transaction successfully refunded. Stock has been restored."
    except sqlite3.Error as e:
        conn.rollback()
        return False, str(e)
    finally:
        conn.close()

