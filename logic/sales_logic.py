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

def get_custom_report(start_date: str, end_date: str) -> dict:
    """Fetch sales report data for a specific date range (YYYY-MM-DD format)."""
    conn = get_connection()
    try:
        # Summary
        summary_row = conn.execute("""
            SELECT 
                COALESCE(SUM(CASE WHEN s.status='completed' THEN s.total_amount ELSE 0 END), 0) as total_revenue,
                COALESCE(SUM(CASE WHEN s.status='completed' THEN s.qty_sold ELSE 0 END), 0) as items_sold,
                SUM(CASE WHEN s.status='refunded' THEN 1 ELSE 0 END) as refund_count,
                COALESCE(SUM(CASE WHEN s.status='completed' THEN 
                    (p.buying_price / NULLIF(p.pieces_per_sack, 0)) * p.bundle_qty * s.qty_sold 
                ELSE 0 END), 0) as total_cost
            FROM sales s
            JOIN products p ON s.product_id = p.id
            WHERE date(s.sold_at) >= ? AND date(s.sold_at) <= ?
        """, (start_date, end_date)).fetchone()
        
        # Top Sellers (only completed sales)
        top_rows = conn.execute("""
            SELECT p.name, p.category, SUM(s.qty_sold) as total_qty, SUM(s.total_amount) as total_rev
            FROM sales s
            JOIN products p ON s.product_id = p.id
            WHERE s.status = 'completed' AND date(s.sold_at) >= ? AND date(s.sold_at) <= ?
            GROUP BY p.id
            ORDER BY total_qty DESC
            LIMIT 10
        """, (start_date, end_date)).fetchall()
        
        top_sellers = [
            {"name": r[0], "category": r[1], "qty": r[2], "revenue": r[3]} for r in top_rows
        ]
        
        # Chart Data (Daily or Hourly Revenue)
        if start_date == end_date:
            chart_rows = conn.execute("""
                SELECT strftime('%H:00', sold_at) as dt, SUM(total_amount) as daily_rev
                FROM sales
                WHERE status = 'completed' AND date(sold_at) = ?
                GROUP BY dt
                ORDER BY dt ASC
            """, (start_date,)).fetchall()
            
            # Pad 06:00 to 23:00
            hourly_dict = {r[0]: r[1] for r in chart_rows}
            chart_data = []
            for hour in range(6, 24):
                h_str = f"{hour:02d}:00"
                chart_data.append({"date": h_str, "revenue": hourly_dict.get(h_str, 0)})
        else:
            chart_rows = conn.execute("""
                SELECT date(sold_at) as dt, SUM(total_amount) as daily_rev
                FROM sales
                WHERE status = 'completed' AND date(sold_at) >= ? AND date(sold_at) <= ?
                GROUP BY dt
                ORDER BY dt ASC
            """, (start_date, end_date)).fetchall()
            chart_data = [{"date": r[0], "revenue": r[1]} for r in chart_rows]
        
        total_revenue = summary_row[0]
        total_cost = summary_row[3] or 0
        total_profit = total_revenue - total_cost

        return {
            "total_revenue": total_revenue,
            "items_sold": summary_row[1],
            "refund_count": summary_row[2] or 0,
            "total_cost": total_cost,
            "total_profit": total_profit,
            "top_sellers": top_sellers,
            "chart_data": chart_data
        }
    finally:
        conn.close()
