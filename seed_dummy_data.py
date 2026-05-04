"""
seed_dummy_data.py
------------------
Seeds 60 days of realistic sales history, sack purchase records,
and sets current stock levels for all products.

Run ONCE from the project root:
  python seed_dummy_data.py
"""

import sys, os, random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from database.db_setup import get_connection

random.seed(42)  # reproducible

ADMIN_ID    = 1
CASHIER_ID  = 2
DAYS_BACK   = 60
TODAY       = datetime.now()

# ── Product config ─────────────────────────────────────────────────────
# name, product_id, weekday_avg_sales, weekend_boost, bundle_qty, sell_price, pcs_per_sack, target_stock
PRODUCTS = [
    {"id": 1, "name": "Men's Shirt",   "wd": 5, "we": 8,  "bundle": 1, "price": 50.0,  "pps": 110, "stock": 85},
    {"id": 2, "name": "Women's Shirt", "wd": 6, "we": 10, "bundle": 1, "price": 50.0,  "pps": 150, "stock": 120},
    {"id": 3, "name": "Shorts",        "wd": 3, "we": 5,  "bundle": 1, "price": 75.0,  "pps": 90,  "stock": 45},
    {"id": 4, "name": "Joggers",       "wd": 2, "we": 3,  "bundle": 1, "price": 100.0, "pps": 55,  "stock": 30},
    {"id": 5, "name": "Jackets",       "wd": 1, "we": 2,  "bundle": 1, "price": 100.0, "pps": 40,  "stock": 25},
    {"id": 6, "name": "Trousers",      "wd": 2, "we": 3,  "bundle": 1, "price": 100.0, "pps": 50,  "stock": 35},
    {"id": 7, "name": "Kids Wear",     "wd": 2, "we": 4,  "bundle": 4, "price": 100.0, "pps": 220, "stock": 152},
]


def generate_daily_qty(p: dict, day: datetime) -> int:
    """Random units sold for a product on a given day."""
    is_weekend = day.weekday() >= 5
    avg = p["we"] if is_weekend else p["wd"]
    # ±40% variance
    low  = max(0, int(avg * 0.6))
    high = int(avg * 1.4) + 1
    return random.randint(low, high)


def compute_sacks_needed(total_pcs_needed: int, pps: int) -> int:
    return (total_pcs_needed + pps - 1) // pps   # ceiling division


def main():
    conn = get_connection()

    # ── Clear old dummy data (sales + sack_purchases + logs) ──────────
    conn.execute("DELETE FROM sales")
    conn.execute("DELETE FROM sack_purchases")
    conn.execute("DELETE FROM activity_logs")
    conn.execute("DELETE FROM reorder_alerts")
    conn.commit()
    print("Cleared old sales/purchases/logs.")

    # ── Step 1: Generate sales day by day ─────────────────────────────
    all_sales: list[dict] = []  # will fill this first to know totals

    for d in range(DAYS_BACK, 0, -1):
        day = TODAY - timedelta(days=d)
        day_str = day.strftime("%Y-%m-%d %H:%M:%S")

        for p in PRODUCTS:
            qty = generate_daily_qty(p, day)
            if qty == 0:
                continue
            # Randomise hour between 8am and 7pm
            hour = random.randint(8, 19)
            ts = day.replace(hour=hour, minute=random.randint(0, 59), second=0)
            all_sales.append({
                "product_id":   p["id"],
                "qty_sold":     qty,
                "unit_price":   p["price"],
                "total_amount": qty * p["price"],
                "served_by":    CASHIER_ID if random.random() > 0.15 else ADMIN_ID,
                "sold_at":      ts.strftime("%Y-%m-%d %H:%M:%S"),
                "bundle":       p["bundle"],
            })

    # ── Step 2: Calculate total pieces sold per product ────────────────
    sold_totals: dict[int, int] = {p["id"]: 0 for p in PRODUCTS}
    for s in all_sales:
        sold_totals[s["product_id"]] += s["qty_sold"] * s["bundle"]

    # ── Step 3: Insert sack purchases (split across two dates) ─────────
    purchase_dates = [
        (TODAY - timedelta(days=58)).strftime("%Y-%m-%d 08:00:00"),
        (TODAY - timedelta(days=28)).strftime("%Y-%m-%d 09:00:00"),
    ]

    for p in PRODUCTS:
        total_needed = sold_totals[p["id"]] + p["stock"]
        sacks_total  = compute_sacks_needed(total_needed, p["pps"])
        pieces_total = sacks_total * p["pps"]

        # Split roughly 60/40 across two purchase dates
        sacks1  = max(1, int(sacks_total * 0.6))
        sacks2  = sacks_total - sacks1
        pieces1 = sacks1 * p["pps"]
        pieces2 = sacks2 * p["pps"]

        if sacks1 > 0:
            conn.execute("""
                INSERT INTO sack_purchases
                    (product_id, sacks_bought, cost_per_sack, pieces_added, purchased_by, purchased_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (p["id"], sacks1, 0, pieces1, ADMIN_ID, purchase_dates[0]))

        if sacks2 > 0:
            conn.execute("""
                INSERT INTO sack_purchases
                    (product_id, sacks_bought, cost_per_sack, pieces_added, purchased_by, purchased_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (p["id"], sacks2, 0, pieces2, ADMIN_ID, purchase_dates[1]))

        print(f"  {p['name']}: {sacks_total} sack(s) bought -> {pieces_total} pcs in, "
              f"{sold_totals[p['id']]} pcs sold, {p['stock']} pcs remaining")

    conn.commit()

    # ── Step 4: Insert sales records ───────────────────────────────────
    for s in all_sales:
        conn.execute("""
            INSERT INTO sales (product_id, qty_sold, unit_price, total_amount, served_by, sold_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (s["product_id"], s["qty_sold"], s["unit_price"],
              s["total_amount"], s["served_by"], s["sold_at"]))
    conn.commit()
    print(f"\nInserted {len(all_sales)} sales records across {DAYS_BACK} days.")

    # ── Step 5: Set current stock levels ──────────────────────────────
    for p in PRODUCTS:
        conn.execute(
            "UPDATE products SET stock_pieces=?, updated_at=datetime('now','localtime') WHERE id=?",
            (p["stock"], p["id"])
        )
    conn.commit()

    # ── Step 6: Seed activity logs for key events ─────────────────────
    log_entries = []
    for p in PRODUCTS:
        d1 = (TODAY - timedelta(days=58)).strftime("%Y-%m-%d 08:05:00")
        d2 = (TODAY - timedelta(days=28)).strftime("%Y-%m-%d 09:10:00")
        log_entries.append((ADMIN_ID, "admin", "ADD_STOCK",
                            f"Initial stock purchase for {p['name']}", d1))
        log_entries.append((ADMIN_ID, "admin", "ADD_STOCK",
                            f"Restocked {p['name']}", d2))

    log_entries.append((ADMIN_ID, "admin", "LOGIN",
                        "Admin initial setup",
                        (TODAY - timedelta(days=60)).strftime("%Y-%m-%d 07:55:00")))
    log_entries.append((CASHIER_ID, "cashier1", "LOGIN",
                        "First cashier login",
                        (TODAY - timedelta(days=59)).strftime("%Y-%m-%d 08:00:00")))

    for entry in log_entries:
        conn.execute("""
            INSERT INTO activity_logs (user_id, username, action, details, logged_at)
            VALUES (?, ?, ?, ?, ?)
        """, entry)
    conn.commit()

    # ── Summary ───────────────────────────────────────────────────────
    total_revenue = sum(s["total_amount"] for s in all_sales)
    total_units   = sum(s["qty_sold"] for s in all_sales)
    total_stock   = sum(p["stock"] for p in PRODUCTS)

    print(f"\n{'='*50}")
    print(f"  Total sales records : {len(all_sales)}")
    print(f"  Total units sold    : {total_units}")
    print(f"  Total revenue       : PHP {total_revenue:,.2f}")
    print(f"  Current total stock : {total_stock} pcs")
    print(f"{'='*50}")
    print("\nDummy data seeded successfully! Run main.py to see it in action.")
    conn.close()


if __name__ == "__main__":
    main()
