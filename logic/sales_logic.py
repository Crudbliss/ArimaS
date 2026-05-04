"""
sales_logic.py  –  POS transaction processing and sales retrieval.
"""

import sqlite3
from database.db_setup import get_connection
from utils.logger import log_action


def process_sale(cart: list[dict], user_id: int, username: str) -> tuple[bool, str]:
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
                INSERT INTO sales (product_id, qty_sold, unit_price, total_amount, served_by)
                VALUES (?, ?, ?, ?, ?)
            """, (pid, qty, unit_price, total, user_id))
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
        SELECT s.id, p.name, s.qty_sold, s.unit_price, s.total_amount, s.sold_at
        FROM sales s
        JOIN products p ON s.product_id = p.id
        WHERE s.served_by = ?
        ORDER BY s.sold_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    cols = ["id","product","qty","unit_price","total","sold_at"]
    return [dict(zip(cols, r)) for r in rows]
