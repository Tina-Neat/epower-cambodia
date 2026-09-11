"""
meter_service.py - Customer & Meter Management and Meter Reading recording with Anomaly Alerts
"""

import sqlite3
from datetime import datetime, date
from typing import Optional, Dict, Any, List, Tuple
from database import get_connection

def get_next_customer_code(conn: Optional[sqlite3.Connection] = None) -> str:
    """Generates the next sequential 6-digit customer code."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True
    cursor = conn.cursor()
    cursor.execute("SELECT MAX(customer_id) as max_id FROM Customers")
    row = cursor.fetchone()
    next_id = (row["max_id"] or 0) + 1
    if should_close:
        conn.close()
    return f"{next_id:06d}"

def add_customer(
    name: str,
    phone: str,
    address: str,
    customer_type: str,
    customer_code: Optional[str] = None,
    honorific: Optional[str] = None,
    last_name: Optional[str] = None,
    first_name: Optional[str] = None,
    last_name_en: Optional[str] = None,
    first_name_en: Optional[str] = None,
    dob: Optional[str] = None,
    pob: Optional[str] = None,
    gender: Optional[str] = None,
    id_type: Optional[str] = None,
    id_number: Optional[str] = None,
    occupation: Optional[str] = None,
    family_count: int = 1,
    customer_category: Optional[str] = None,
    is_poor_family: int = 0,
    representative: Optional[str] = None,
    account_number: Optional[str] = None,
    province: Optional[str] = None,
    district: Optional[str] = None,
    commune: Optional[str] = None,
    village: Optional[str] = None,
    area: Optional[str] = None,
    house_no: Optional[str] = None,
    street_no: Optional[str] = None,
    photo_url: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> int:
    """Registers a new electricity customer with detailed Khmer enterprise profile."""
    valid_types = ('Residential', 'Commercial', 'Agricultural', 'Industrial')
    if customer_type not in valid_types:
        # Fallback to Residential if non-standard string given
        customer_type = 'Residential'

    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    if not customer_code or not customer_code.strip():
        customer_code = get_next_customer_code(conn)

    # Automatically derive full name if last_name or first_name provided
    if (last_name or first_name) and (not name or not name.strip()):
        name = f"{last_name or ''} {first_name or ''}".strip()

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Customers (
            name, phone, address, customer_type, customer_code,
            honorific, last_name, first_name, last_name_en, first_name_en,
            dob, pob, gender, id_type, id_number,
            occupation, family_count, customer_category, is_poor_family,
            representative, account_number, province, district, commune,
            village, area, house_no, street_no, photo_url
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            name.strip() if name else "អតិថិជនថ្មី",
            phone.strip() if phone else "",
            address.strip() if address else "",
            customer_type,
            customer_code.strip() if customer_code else None,
            honorific, last_name, first_name, last_name_en, first_name_en,
            dob, pob, gender or 'ប្រុស', id_type or 'អត្តសញ្ញាណប័ណ្ណ', id_number,
            occupation, family_count or 1, customer_category, 1 if is_poor_family else 0,
            representative, account_number, province, district, commune,
            village, area, house_no, street_no, photo_url
        )
    )
    customer_id = cursor.lastrowid
    conn.commit()

    if should_close:
        conn.close()
    return customer_id

def get_customer(customer_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Fetches customer information by ID."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Customers WHERE customer_id = ?", (customer_id,))
    row = cursor.fetchone()
    res = dict(row) if row else None

    if should_close:
        conn.close()
    return res

def list_customers(conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Returns a list of all customers."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Customers ORDER BY customer_id ASC")
    rows = [dict(r) for r in cursor.fetchall()]

    if should_close:
        conn.close()
    return rows

def add_meter(
    meter_number: str,
    customer_id: int,
    status: str = "Active",
    installation_date: Optional[str] = None,
    location_code: Optional[str] = None,
    meter_size: Optional[str] = "15mm",
    phase: Optional[str] = "1 Phase 220V",
    initial_reading: float = 0.0,
    notes: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> int:
    """Registers and associates a meter with a customer."""
    if not installation_date:
        installation_date = date.today().isoformat()

    valid_statuses = ('Active', 'Suspended', 'Disconnected', 'Maintenance')
    if status not in valid_statuses:
        raise ValueError(f"Invalid status: {status}. Must be one of {valid_statuses}")

    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Meters (meter_number, customer_id, status, installation_date, location_code, meter_size, phase, initial_reading, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (meter_number.strip(), customer_id, status, installation_date, location_code, meter_size, phase, initial_reading, notes)
    )
    meter_id = cursor.lastrowid
    conn.commit()

    if should_close:
        conn.close()
    return meter_id

def get_meter(meter_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Gets meter details by meter_id."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT m.*, c.name as customer_name, c.phone, c.address, c.customer_type
        FROM Meters m
        JOIN Customers c ON m.customer_id = c.customer_id
        WHERE m.meter_id = ?
        """,
        (meter_id,)
    )
    row = cursor.fetchone()
    res = dict(row) if row else None

    if should_close:
        conn.close()
    return res

def get_meters_by_customer(customer_id: int, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Returns all meters owned by a specific customer."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Meters WHERE customer_id = ?", (customer_id,))
    rows = [dict(r) for r in cursor.fetchall()]

    if should_close:
        conn.close()
    return rows

def get_latest_reading(meter_id: int, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Returns the most recent meter reading for a given meter."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT * FROM Meter_Readings
        WHERE meter_id = ?
        ORDER BY reading_date DESC, reading_id DESC
        LIMIT 1
        """,
        (meter_id,)
    )
    row = cursor.fetchone()
    res = dict(row) if row else None

    if should_close:
        conn.close()
    return res

def check_reading_anomalies(
    meter_id: int,
    previous_reading: float,
    current_reading: float,
    conn: Optional[sqlite3.Connection] = None
) -> Tuple[float, Optional[str]]:
    """
    Validates meter reading and detects anomalies:
    1. Negative reading: current < previous (Meter rollback / typo)
    2. High usage spike: usage > 200% of previous usage average
    3. Zero consumption: usage == 0 on an active meter
    Returns (total_kwh, alert_message)
    """
    total_kwh = current_reading - previous_reading

    if total_kwh < 0:
        return total_kwh, f"ALERT: លេខថ្មី ({current_reading}) ទាបជាងលេខចាស់ ({previous_reading})! សង្ស័យកុងទ័រថយក្រោយ ឬបញ្ចូលលេខច្រឡំ។"

    # Check historical average usage for this meter
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT AVG(total_kwh) as avg_kwh, COUNT(*) as count
        FROM Meter_Readings
        WHERE meter_id = ?
        """,
        (meter_id,)
    )
    hist = cursor.fetchone()
    if should_close:
        conn.close()

    alert_notes = None
    if hist and hist["count"] > 0 and hist["avg_kwh"] is not None and hist["avg_kwh"] > 0:
        avg_usage = hist["avg_kwh"]
        if total_kwh > (avg_usage * 2.5):
            alert_notes = f"ALERT: ការប្រើប្រាស់កើនឡើងខ្ពស់ខុសប្រក្រតី ({total_kwh:.1f} kWh ធៀបនឹងមធ្យមភាគ {avg_usage:.1f} kWh, កើនឡើង {(total_kwh/avg_usage)*100:.0f}%)"
    elif total_kwh == 0:
        alert_notes = "ALERT: ការប្រើប្រាស់ 0 kWh សម្រាប់កុងទ័រដំណើរការ។"

    return total_kwh, alert_notes

def record_meter_reading(
    meter_id: int,
    current_reading: float,
    previous_reading: Optional[float] = None,
    reading_date: Optional[str] = None,
    force_negative: bool = False,
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """
    Records a new meter reading.
    Automatically retrieves previous_reading from the last record if not provided.
    Calculates total_kwh = current_reading - previous_reading.
    Raises ValueError if current_reading < previous_reading unless force_negative is set.
    """
    if not reading_date:
        reading_date = date.today().isoformat()

    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    # If previous_reading is not provided, fetch from last reading
    if previous_reading is None:
        last = get_latest_reading(meter_id, conn)
        previous_reading = last["current_reading"] if last else 0.0

    total_kwh, alert = check_reading_anomalies(meter_id, previous_reading, current_reading, conn)

    if total_kwh < 0 and not force_negative:
        if should_close:
            conn.close()
        raise ValueError(alert)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO Meter_Readings (meter_id, previous_reading, current_reading, total_kwh, reading_date, alert_notes)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (meter_id, previous_reading, current_reading, total_kwh, reading_date, alert)
    )
    reading_id = cursor.lastrowid
    conn.commit()

    cursor.execute("SELECT * FROM Meter_Readings WHERE reading_id = ?", (reading_id,))
    row = dict(cursor.fetchone())

    if should_close:
        conn.close()
    return row
