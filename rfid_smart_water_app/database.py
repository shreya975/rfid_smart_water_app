import sqlite3
from contextlib import closing
from pathlib import Path
from datetime import datetime, timedelta
import random

DB_PATH = Path("smart_water.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with closing(get_connection()) as conn:
        cur = conn.cursor()

        cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            household TEXT NOT NULL,
            connection_id TEXT UNIQUE NOT NULL,
            rfid_id TEXT UNIQUE NOT NULL,
            role TEXT NOT NULL DEFAULT 'user',
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            threshold_liters REAL NOT NULL DEFAULT 500,
            created_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            usage_liters REAL NOT NULL,
            source TEXT NOT NULL DEFAULT 'RFID Valve',
            logged_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS billing_rates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slab_start REAL NOT NULL,
            slab_end REAL,
            rate_per_liter REAL NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT NOT NULL
        )
        """)

        cur.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            period_month TEXT NOT NULL,
            total_liters REAL NOT NULL,
            total_amount REAL NOT NULL,
            bill_details TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
        """)

        conn.commit()

    seed_defaults()


def seed_defaults():
    with closing(get_connection()) as conn:
        cur = conn.cursor()

        # Seed rates once
        cur.execute("SELECT COUNT(*) as count FROM billing_rates")
        if cur.fetchone()["count"] == 0:
            now = datetime.now().isoformat()
            default_rates = [
                (0, 100, 2, 1, now),
                (100, 500, 5, 1, now),
                (500, None, 10, 1, now),
            ]
            cur.executemany("""
                INSERT INTO billing_rates (slab_start, slab_end, rate_per_liter, active, updated_at)
                VALUES (?, ?, ?, ?, ?)
            """, default_rates)

        # Seed users once
        cur.execute("SELECT COUNT(*) as count FROM users")
        if cur.fetchone()["count"] == 0:
            users = [
                ("Admin User", "Central Authority", "CONN-ADMIN", "RFID-ADMIN-001", "admin", "admin", "admin123", 1000, datetime.now().isoformat()),
                ("Shreya Mahajan", "Mahajan Residence", "CONN-1001", "RFID-1001", "user", "shreya", "user123", 450, datetime.now().isoformat()),
                ("Aarav Sharma", "Sharma Family", "CONN-1002", "RFID-1002", "user", "aarav", "user123", 550, datetime.now().isoformat()),
                ("Priya Deshmukh", "Deshmukh Home", "CONN-1003", "RFID-1003", "user", "priya", "user123", 400, datetime.now().isoformat()),
                ("Rohan Patil", "Patil Apartments", "CONN-1004", "RFID-1004", "user", "rohan", "user123", 650, datetime.now().isoformat()),
            ]
            cur.executemany("""
                INSERT INTO users (name, household, connection_id, rfid_id, role, username, password, threshold_liters, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, users)

        conn.commit()

        # Seed logs if empty
        cur.execute("SELECT COUNT(*) as count FROM usage_logs")
        if cur.fetchone()["count"] == 0:
            cur.execute("SELECT id FROM users WHERE role='user'")
            user_ids = [row["id"] for row in cur.fetchall()]
            now = datetime.now()

            logs = []
            for user_id in user_ids:
                for day_offset in range(120, -1, -1):
                    day = now - timedelta(days=day_offset)
                    # Base pattern with weekly seasonality
                    base_usage = random.randint(35, 120)
                    if day.weekday() in [5, 6]:
                        base_usage += random.randint(10, 40)

                    # Add a few anomalies
                    if random.random() < 0.04:
                        base_usage += random.randint(150, 300)

                    # Split into 1-3 sessions per day
                    sessions = random.randint(1, 3)
                    remaining = base_usage
                    for i in range(sessions):
                        if i == sessions - 1:
                            amount = remaining
                        else:
                            amount = round(remaining * random.uniform(0.25, 0.5), 2)
                            remaining -= amount

                        log_time = day.replace(
                            hour=random.randint(6, 22),
                            minute=random.randint(0, 59),
                            second=random.randint(0, 59),
                            microsecond=0,
                        )
                        logs.append((user_id, float(amount), "RFID Valve", log_time.isoformat()))

            cur.executemany("""
                INSERT INTO usage_logs (user_id, usage_liters, source, logged_at)
                VALUES (?, ?, ?, ?)
            """, logs)
            conn.commit()


def fetch_all(query, params=()):
    with closing(get_connection()) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        return [dict(row) for row in cur.fetchall()]


def fetch_one(query, params=()):
    with closing(get_connection()) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        row = cur.fetchone()
        return dict(row) if row else None


def execute_query(query, params=()):
    with closing(get_connection()) as conn:
        cur = conn.cursor()
        cur.execute(query, params)
        conn.commit()
        return cur.lastrowid


def execute_many(query, params_list):
    with closing(get_connection()) as conn:
        cur = conn.cursor()
        cur.executemany(query, params_list)
        conn.commit()


def get_users():
    return fetch_all("SELECT * FROM users ORDER BY role DESC, name ASC")


def get_user_by_username(username):
    return fetch_one("SELECT * FROM users WHERE username = ?", (username,))


def get_user_by_rfid(rfid_id):
    return fetch_one("SELECT * FROM users WHERE rfid_id = ?", (rfid_id,))


def get_user_by_id(user_id):
    return fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))


def add_user(name, household, connection_id, rfid_id, role, username, password, threshold_liters):
    return execute_query("""
        INSERT INTO users (name, household, connection_id, rfid_id, role, username, password, threshold_liters, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (name, household, connection_id, rfid_id, role, username, password, threshold_liters, datetime.now().isoformat()))


def update_user(user_id, name, household, connection_id, rfid_id, role, username, password, threshold_liters):
    return execute_query("""
        UPDATE users
        SET name = ?, household = ?, connection_id = ?, rfid_id = ?, role = ?, username = ?, password = ?, threshold_liters = ?
        WHERE id = ?
    """, (name, household, connection_id, rfid_id, role, username, password, threshold_liters, user_id))


def delete_user(user_id):
    execute_query("DELETE FROM usage_logs WHERE user_id = ?", (user_id,))
    execute_query("DELETE FROM bills WHERE user_id = ?", (user_id,))
    execute_query("DELETE FROM users WHERE id = ?", (user_id,))


def get_active_rates():
    return fetch_all("""
        SELECT slab_start, slab_end, rate_per_liter
        FROM billing_rates
        WHERE active = 1
        ORDER BY slab_start ASC
    """)


def replace_rates(rates):
    now = datetime.now().isoformat()
    with closing(get_connection()) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM billing_rates")
        cur.executemany("""
            INSERT INTO billing_rates (slab_start, slab_end, rate_per_liter, active, updated_at)
            VALUES (?, ?, ?, 1, ?)
        """, [(r["slab_start"], r["slab_end"], r["rate_per_liter"], now) for r in rates])
        conn.commit()


def add_usage_log(user_id, usage_liters, source="RFID Valve", logged_at=None):
    logged_at = logged_at or datetime.now().isoformat()
    return execute_query("""
        INSERT INTO usage_logs (user_id, usage_liters, source, logged_at)
        VALUES (?, ?, ?, ?)
    """, (user_id, usage_liters, source, logged_at))


def get_usage_logs(user_id=None, start_date=None, end_date=None):
    query = """
        SELECT ul.*, u.name, u.household, u.connection_id, u.rfid_id
        FROM usage_logs ul
        JOIN users u ON u.id = ul.user_id
        WHERE 1=1
    """
    params = []

    if user_id:
        query += " AND ul.user_id = ?"
        params.append(user_id)
    if start_date:
        query += " AND date(ul.logged_at) >= date(?)"
        params.append(start_date)
    if end_date:
        query += " AND date(ul.logged_at) <= date(?)"
        params.append(end_date)

    query += " ORDER BY ul.logged_at DESC"
    return fetch_all(query, tuple(params))


def save_bill(user_id, period_month, total_liters, total_amount, bill_details):
    existing = fetch_one("""
        SELECT id FROM bills
        WHERE user_id = ? AND period_month = ?
    """, (user_id, period_month))

    if existing:
        execute_query("""
            UPDATE bills
            SET total_liters = ?, total_amount = ?, bill_details = ?, generated_at = ?
            WHERE id = ?
        """, (total_liters, total_amount, bill_details, datetime.now().isoformat(), existing["id"]))
        return existing["id"]

    return execute_query("""
        INSERT INTO bills (user_id, period_month, total_liters, total_amount, bill_details, generated_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, period_month, total_liters, total_amount, bill_details, datetime.now().isoformat()))


def get_bills(user_id=None):
    query = """
        SELECT b.*, u.name, u.connection_id
        FROM bills b
        JOIN users u ON u.id = b.user_id
        WHERE 1=1
    """
    params = []
    if user_id:
        query += " AND b.user_id = ?"
        params.append(user_id)
    query += " ORDER BY b.generated_at DESC"
    return fetch_all(query, tuple(params))
