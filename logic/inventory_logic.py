"""
inventory_logic.py  –  CRUD for products and stock management.
"""

import sqlite3
from database.db_setup import get_connection
from utils.logger import log_action


def get_all_products(include_archived=True) -> list[dict]:
    conn = get_connection()
    cursor = conn.cursor()
    query = """
        SELECT id, name, category, buying_price, selling_price,
               bundle_qty, pieces_per_sack, stock_pieces, reorder_level, is_active
        FROM products 
    """
    if not include_archived:
        query += " WHERE is_active = 1 "
    query += " ORDER BY category, name"
    
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    cols = ["id","name","category","buying_price","selling_price",
            "bundle_qty","pieces_per_sack","stock_pieces","reorder_level","is_active"]
    return [dict(zip(cols, r)) for r in rows]


def get_product_by_id(product_id: int) -> dict | None:
    conn = get_connection()
    row = conn.execute(
        "SELECT id,name,category,buying_price,selling_price,bundle_qty,"
        "pieces_per_sack,stock_pieces,reorder_level,is_active FROM products WHERE id=?",
        (product_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None
    cols = ["id","name","category","buying_price","selling_price",
            "bundle_qty","pieces_per_sack","stock_pieces","reorder_level","is_active"]
    return dict(zip(cols, row))


def add_product(name, category, buying_price, selling_price,
                bundle_qty, reorder_level, user_id, username) -> tuple[bool, str]:
    try:
        conn = get_connection()
        conn.execute("""
            INSERT INTO products (name, category, buying_price, selling_price,
                                  bundle_qty, reorder_level)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (name, category, buying_price, selling_price, bundle_qty, reorder_level))
        conn.commit()
        conn.close()
        log_action(user_id, username, "ADD_PRODUCT", f"Added: {name}")
        return True, "Product added."
    except sqlite3.IntegrityError:
        return False, f"A product named '{name}' already exists."
    except sqlite3.Error as e:
        return False, str(e)


def update_product(product_id, name, category, buying_price, selling_price,
                   bundle_qty, reorder_level, user_id, username) -> tuple[bool, str]:
    try:
        conn = get_connection()
        conn.execute("""
            UPDATE products SET name=?, category=?, buying_price=?,
                selling_price=?, bundle_qty=?, reorder_level=?,
                updated_at=datetime('now','localtime')
            WHERE id=?
        """, (name, category, buying_price, selling_price, bundle_qty, reorder_level, product_id))
        conn.commit()
        conn.close()
        log_action(user_id, username, "UPDATE_PRODUCT", f"Updated ID {product_id}: {name}")
        return True, "Product updated."
    except sqlite3.IntegrityError:
        return False, f"A product named '{name}' already exists."
    except sqlite3.Error as e:
        return False, str(e)


def delete_product(product_id: int, user_id: int, username: str) -> tuple[bool, str]:
    try:
        conn = get_connection()
        row = conn.execute("SELECT name FROM products WHERE id=?", (product_id,)).fetchone()
        if not row:
            conn.close()
            return False, "Product not found."
        name = row[0]
        conn.execute("DELETE FROM products WHERE id=?", (product_id,))
        conn.commit()
        conn.close()
        log_action(user_id, username, "DELETE_PRODUCT", f"Deleted: {name}")
        return True, f"'{name}' deleted."
    except sqlite3.Error as e:
        return False, str(e)


def add_stock(product_id: int, sacks_bought: int, cost_per_sack: float,
              pieces_added: int, user_id: int, username: str) -> tuple[bool, str]:
    try:
        conn = get_connection()
        conn.execute("""
            INSERT INTO sack_purchases (product_id, sacks_bought, cost_per_sack,
                                        pieces_added, purchased_by)
            VALUES (?, ?, ?, ?, ?)
        """, (product_id, sacks_bought, cost_per_sack, pieces_added, user_id))
        conn.execute("""
            UPDATE products SET stock_pieces = stock_pieces + ?,
                updated_at = datetime('now','localtime')
            WHERE id=?
        """, (pieces_added, product_id))
        conn.commit()
        name = conn.execute("SELECT name FROM products WHERE id=?", (product_id,)).fetchone()[0]
        conn.close()
        log_action(user_id, username, "ADD_STOCK",
                   f"+{pieces_added} pcs ({sacks_bought} sack(s)) of {name}")
        return True, f"+{pieces_added} pieces added to stock."
    except sqlite3.Error as e:
        return False, str(e)


def get_low_stock() -> list[dict]:
    conn = get_connection()
    rows = conn.execute("""
        SELECT id, name, stock_pieces, reorder_level
        FROM products WHERE stock_pieces <= reorder_level
        ORDER BY stock_pieces ASC
    """).fetchall()
    conn.close()
    return [{"id": r[0], "name": r[1], "stock": r[2], "reorder": r[3]} for r in rows]


def get_dashboard_stats() -> dict:
    conn = get_connection()
    total_products   = conn.execute("SELECT COUNT(*) FROM products").fetchone()[0]
    low_stock        = conn.execute("SELECT COUNT(*) FROM products WHERE stock_pieces <= reorder_level").fetchone()[0]
    today_sales      = conn.execute("SELECT COUNT(*) FROM sales WHERE date(sold_at)=date('now','localtime')").fetchone()[0]
    today_revenue    = conn.execute("SELECT COALESCE(SUM(total_amount),0) FROM sales WHERE date(sold_at)=date('now','localtime')").fetchone()[0]
    total_stock      = conn.execute("SELECT COALESCE(SUM(stock_pieces),0) FROM products").fetchone()[0]
    conn.close()
    return {
        "total_products": total_products,
        "low_stock":      low_stock,
        "today_sales":    today_sales,
        "today_revenue":  today_revenue,
        "total_stock":    total_stock,
    }

def toggle_archive_product(product_id: int, user_id: int, username: str) -> tuple[bool, str]:
    try:
        conn = get_connection()
        row = conn.execute("SELECT name, is_active FROM products WHERE id=?", (product_id,)).fetchone()
        if not row:
            conn.close()
            return False, "Product not found."
            
        name, current_status = row
        new_status = 0 if current_status == 1 else 1
        
        conn.execute("UPDATE products SET is_active = ?, updated_at=datetime('now','localtime') WHERE id=?", (new_status, product_id))
        conn.commit()
        conn.close()
        
        action = "ARCHIVE_PRODUCT" if new_status == 0 else "UNARCHIVE_PRODUCT"
        status_str = "Archived" if new_status == 0 else "Restored"
        log_action(user_id, username, action, f"{status_str}: {name}")
        
        return True, f"'{name}' has been {status_str.lower()}."
    except sqlite3.Error as e:
        return False, str(e)

def get_restock_report() -> list[dict]:
    """Fetch all active products that are at or below their reorder level."""
    conn = get_connection()
    try:
        rows = conn.execute("""
            SELECT id, name, category, stock_pieces, reorder_level, buying_price, pieces_per_sack
            FROM products
            WHERE stock_pieces <= reorder_level AND is_active = 1
            ORDER BY stock_pieces ASC
        """).fetchall()
        
        report = []
        for r in rows:
            report.append({
                "id": r[0],
                "name": r[1],
                "category": r[2],
                "stock": r[3],
                "reorder_level": r[4],
                "buying_price": r[5],
                "pieces_per_sack": r[6]
            })
        return report
    finally:
        conn.close()
