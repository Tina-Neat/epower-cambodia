"""
report_service.py - Monthly/Yearly revenue reports, debtor statistics, and energy loss analysis
"""

import sqlite3
from typing import Optional, Dict, Any, List
from database import get_connection

def get_monthly_revenue_report(year: Optional[int] = None, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """
    Generates monthly revenue report:
    Total billed amount, total collected payments, collection rate %.
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    year_filter = f"WHERE strftime('%Y', issue_date) = '{year}'" if year else ""

    query = f"""
    SELECT 
        strftime('%Y-%m', i.issue_date) AS month,
        COUNT(DISTINCT i.invoice_id) AS total_invoices,
        SUM(i.total_amount) AS total_billed,
        COALESCE((
            SELECT SUM(p.amount_paid) 
            FROM Payments p 
            JOIN Invoices inv ON p.invoice_id = inv.invoice_id 
            WHERE strftime('%Y-%m', inv.issue_date) = strftime('%Y-%m', i.issue_date)
        ), 0) AS total_collected
    FROM Invoices i
    {year_filter}
    GROUP BY month
    ORDER BY month DESC;
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    results = []

    for r in rows:
        item = dict(r)
        billed = item["total_billed"] or 0.0
        collected = item["total_collected"] or 0.0
        rate = (collected / billed * 100) if billed > 0 else 0.0
        item["collection_rate_percent"] = round(rate, 2)
        results.append(item)

    if should_close:
        conn.close()
    return results

def get_revenue_by_customer_type(conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Generates revenue breakdown categorized by customer type (Residential, Commercial, etc.)."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            c.customer_type,
            COUNT(DISTINCT c.customer_id) as total_customers,
            SUM(r.total_kwh) as total_kwh_consumed,
            SUM(i.total_amount) as total_billed_amount,
            COALESCE(SUM(p.amount_paid), 0) as total_paid_amount
        FROM Customers c
        JOIN Meters m ON c.customer_id = m.customer_id
        JOIN Meter_Readings r ON m.meter_id = r.meter_id
        JOIN Invoices i ON r.reading_id = i.reading_id
        LEFT JOIN Payments p ON i.invoice_id = p.invoice_id
        GROUP BY c.customer_type
        ORDER BY total_billed_amount DESC;
        """
    )
    rows = [dict(r) for r in cursor.fetchall()]

    if should_close:
        conn.close()
    return rows

def get_outstanding_debt_summary(conn: Optional[sqlite3.Connection] = None) -> Dict[str, Any]:
    """Summarizes unpaid/overdue debt across the entire system."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT 
            COUNT(DISTINCT c.customer_id) as debtor_count,
            COUNT(i.invoice_id) as unpaid_invoice_count,
            SUM(i.total_amount) as total_unpaid_billed
        FROM Invoices i
        JOIN Meter_Readings r ON i.reading_id = r.reading_id
        JOIN Meters m ON r.meter_id = m.meter_id
        JOIN Customers c ON m.customer_id = c.customer_id
        WHERE i.status IN ('Unpaid', 'Partially Paid', 'Overdue');
        """
    )
    summary = dict(cursor.fetchone())

    # Get payments made toward these unpaid/partially paid invoices
    cursor.execute(
        """
        SELECT COALESCE(SUM(p.amount_paid), 0) as paid_part
        FROM Payments p
        JOIN Invoices i ON p.invoice_id = i.invoice_id
        WHERE i.status IN ('Unpaid', 'Partially Paid', 'Overdue');
        """
    )
    paid_part = cursor.fetchone()["paid_part"]

    total_billed = summary["total_unpaid_billed"] or 0.0
    summary["net_outstanding_debt"] = round(max(0.0, total_billed - paid_part), 2)

    if should_close:
        conn.close()
    return summary

def calculate_area_energy_loss(
    area_filter: Optional[str] = None,
    supplied_kwh: Optional[float] = None,
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """
    Calculates metered consumption by area/pole location and compares with supplied energy.
    Formula:
      Energy Loss (kWh) = Supplied Energy - Total Billed Metered Energy
      Loss Percentage = (Energy Loss / Supplied Energy) * 100
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    if area_filter:
        cursor.execute(
            """
            SELECT 
                c.address as area,
                COUNT(m.meter_id) as meter_count,
                COALESCE(SUM(r.total_kwh), 0) as billed_kwh
            FROM Customers c
            JOIN Meters m ON c.customer_id = m.customer_id
            JOIN Meter_Readings r ON m.meter_id = r.meter_id
            WHERE c.address LIKE ?
            GROUP BY c.address
            """,
            (f"%{area_filter}%",)
        )
    else:
        cursor.execute(
            """
            SELECT 
                c.address as area,
                COUNT(m.meter_id) as meter_count,
                COALESCE(SUM(r.total_kwh), 0) as billed_kwh
            FROM Customers c
            JOIN Meters m ON c.customer_id = m.customer_id
            JOIN Meter_Readings r ON m.meter_id = r.meter_id
            GROUP BY c.address
            """
        )

    rows = [dict(r) for r in cursor.fetchall()]
    total_billed_kwh = sum(r["billed_kwh"] for r in rows)

    result: Dict[str, Any] = {
        "areas": rows,
        "total_billed_kwh": round(total_billed_kwh, 2),
        "supplied_kwh": supplied_kwh,
        "loss_kwh": None,
        "loss_percentage": None
    }

    if supplied_kwh is not None and supplied_kwh > 0:
        loss = supplied_kwh - total_billed_kwh
        loss_pct = (loss / supplied_kwh) * 100.0
        result["loss_kwh"] = round(loss, 2)
        result["loss_percentage"] = round(loss_pct, 2)

    if should_close:
        conn.close()
    return result
