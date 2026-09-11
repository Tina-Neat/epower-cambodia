"""
database.py - Database connection and schema definitions for Electricity Consumption Management System
"""

import sqlite3
import os
from typing import Optional

DB_FILE = os.environ.get("DATABASE_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "electricity_system.db"))

def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Returns a SQLite connection with foreign keys enabled and row factory set to Row."""
    path = db_path if db_path else DB_FILE
    # Ensure parent directory exists (critical for Docker /data/ or cloud persistent volumes)
    db_dir = os.path.dirname(os.path.abspath(path))
    if db_dir and not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.row_factory = sqlite3.Row
    return conn

def migrate_columns(conn: sqlite3.Connection) -> None:
    """Migrates the Customers and Meters tables with all extended customer form fields."""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(Customers)")
    existing_cols = {r[1] for r in cursor.fetchall()}

    new_cols = [
        ("customer_code", "TEXT"),
        ("honorific", "TEXT"),
        ("last_name", "TEXT"),
        ("first_name", "TEXT"),
        ("last_name_en", "TEXT"),
        ("first_name_en", "TEXT"),
        ("dob", "DATE"),
        ("pob", "TEXT"),
        ("gender", "TEXT"),
        ("id_type", "TEXT"),
        ("id_number", "TEXT"),
        ("occupation", "TEXT"),
        ("family_count", "INTEGER DEFAULT 1"),
        ("customer_category", "TEXT"),
        ("is_poor_family", "INTEGER DEFAULT 0"),
        ("representative", "TEXT"),
        ("account_number", "TEXT"),
        ("province", "TEXT"),
        ("district", "TEXT"),
        ("commune", "TEXT"),
        ("village", "TEXT"),
        ("area", "TEXT"),
        ("house_no", "TEXT"),
        ("street_no", "TEXT"),
        ("photo_url", "TEXT")
    ]
    for col, col_type in new_cols:
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE Customers ADD COLUMN {col} {col_type};")

    cursor.execute("PRAGMA table_info(Meters)")
    existing_meter_cols = {r[1] for r in cursor.fetchall()}
    meter_new_cols = [
        ("location_code", "TEXT"),
        ("meter_size", "TEXT DEFAULT '15mm'"),
        ("phase", "TEXT DEFAULT '1 Phase 220V'"),
        ("initial_reading", "REAL DEFAULT 0"),
        ("notes", "TEXT")
    ]
    for col, col_type in meter_new_cols:
        if col not in existing_meter_cols:
            cursor.execute(f"ALTER TABLE Meters ADD COLUMN {col} {col_type};")

    cursor.execute("PRAGMA table_info(Invoices)")
    existing_inv_cols = {r[1] for r in cursor.fetchall()}
    inv_new_cols = [
        ("pricing_policy", "TEXT DEFAULT 'standard'"),
        ("flat_rate", "REAL DEFAULT NULL"),
        ("tier1_rate", "REAL DEFAULT 400.0"),
        ("tier2_rate", "REAL DEFAULT 600.0")
    ]
    for col, col_type in inv_new_cols:
        if col not in existing_inv_cols:
            cursor.execute(f"ALTER TABLE Invoices ADD COLUMN {col} {col_type};")

    cursor.execute("PRAGMA table_info(Meter_Readings)")
    existing_mr_cols = {r[1] for r in cursor.fetchall()}
    mr_new_cols = [
        ("billing_month", "TEXT DEFAULT NULL")
    ]
    for col, col_type in mr_new_cols:
        if col not in existing_mr_cols:
            cursor.execute(f"ALTER TABLE Meter_Readings ADD COLUMN {col} {col_type};")

    # Backfill customer_code for existing records
    cursor.execute("SELECT customer_id, customer_code FROM Customers WHERE customer_code IS NULL OR customer_code = ''")
    for row in cursor.fetchall():
        cid = row["customer_id"]
        code = f"{cid:06d}"
        cursor.execute("UPDATE Customers SET customer_code = ? WHERE customer_id = ?", (code, cid))

    conn.commit()

def init_db(db_path: Optional[str] = None) -> None:
    """Initializes all 6 database tables according to the system schema."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    # 1. Customers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Customers (
        customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        address TEXT NOT NULL,
        customer_type TEXT NOT NULL CHECK(customer_type IN ('Residential', 'Commercial', 'Agricultural', 'Industrial')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Meters Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Meters (
        meter_id INTEGER PRIMARY KEY AUTOINCREMENT,
        meter_number TEXT NOT NULL UNIQUE,
        customer_id INTEGER NOT NULL,
        status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Suspended', 'Disconnected', 'Maintenance')),
        installation_date DATE NOT NULL,
        FOREIGN KEY (customer_id) REFERENCES Customers(customer_id) ON DELETE CASCADE
    );
    """)

    # 3. Tariffs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Tariffs (
        tariff_id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_type TEXT NOT NULL CHECK(customer_type IN ('Residential', 'Commercial', 'Agricultural', 'Industrial')),
        min_kwh REAL NOT NULL,
        max_kwh REAL, -- NULL means infinity (no upper limit)
        price_per_kwh REAL NOT NULL
    );
    """)

    # 4. Meter_Readings Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Meter_Readings (
        reading_id INTEGER PRIMARY KEY AUTOINCREMENT,
        meter_id INTEGER NOT NULL,
        previous_reading REAL NOT NULL,
        current_reading REAL NOT NULL,
        total_kwh REAL NOT NULL,
        reading_date DATE NOT NULL,
        alert_notes TEXT,
        FOREIGN KEY (meter_id) REFERENCES Meters(meter_id) ON DELETE CASCADE
    );
    """)

    # 5. Invoices Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Invoices (
        invoice_id INTEGER PRIMARY KEY AUTOINCREMENT,
        reading_id INTEGER NOT NULL UNIQUE,
        maintenance_fee REAL DEFAULT 0.0,
        subsidy_amount REAL DEFAULT 0.0,
        late_fee REAL DEFAULT 0.0,
        total_amount REAL NOT NULL,
        due_date DATE NOT NULL,
        status TEXT NOT NULL DEFAULT 'Unpaid' CHECK(status IN ('Unpaid', 'Paid', 'Partially Paid', 'Overdue')),
        issue_date DATE NOT NULL,
        FOREIGN KEY (reading_id) REFERENCES Meter_Readings(reading_id) ON DELETE CASCADE
    );
    """)

    # 6. Payments Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Payments (
        payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        amount_paid REAL NOT NULL,
        payment_method TEXT NOT NULL CHECK(payment_method IN ('Cash', 'KHQR', 'Bank_Transfer')),
        payment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        notes TEXT,
        FOREIGN KEY (invoice_id) REFERENCES Invoices(invoice_id) ON DELETE CASCADE
    );
    """)

    # 7. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        salt TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT,
        role TEXT NOT NULL DEFAULT 'Staff' CHECK(role IN ('Admin', 'Staff', 'Cashier', 'Technician')),
        status TEXT NOT NULL DEFAULT 'Pending' CHECK(status IN ('Pending', 'Approved', 'Rejected')),
        is_permanent INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        approved_at TIMESTAMP,
        approved_by TEXT
    );
    """)

    # 8. User_Sessions Table (100% Offline Session Store)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS User_Sessions (
        session_id TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    );
    """)

    migrate_columns(conn)

    # Ensure Permanent Default Admin exists
    import hashlib
    cursor.execute("SELECT user_id, is_permanent, status FROM Users WHERE username = 'admin'")
    existing_admin = cursor.fetchone()
    if not existing_admin:
        salt = "epower_permanent_admin_salt_2026"
        pwd_hash = hashlib.pbkdf2_hmac('sha256', "admin123".encode('utf-8'), salt.encode('utf-8'), 100000).hex()
        cursor.execute("""
        INSERT INTO Users (username, password_hash, salt, full_name, phone, role, status, is_permanent, approved_at, approved_by)
        VALUES (?, ?, ?, ?, ?, 'Admin', 'Approved', 1, CURRENT_TIMESTAMP, 'System');
        """, ("admin", pwd_hash, salt, "អ្នកគ្រប់គ្រងប្រព័ន្ធ (Permanent Admin)", "012 888 999"))
    else:
        # Guarantee permanent admin is always Admin and Approved
        cursor.execute("UPDATE Users SET is_permanent = 1, role = 'Admin', status = 'Approved' WHERE username = 'admin'")

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully with 8 tables (including Users & Sessions).")
