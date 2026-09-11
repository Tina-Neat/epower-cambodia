"""
payment_service.py - Payment processing, KHQR/Cash tracking, and debt management
"""

import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List
from database import get_connection

def record_payment(
    invoice_id: int,
    amount_paid: float,
    payment_method: str = "KHQR",
    notes: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> Dict[str, Any]:
    """
    Records a payment for an invoice.
    Updates invoice status to 'Paid' or 'Partially Paid'.
    Supports 'Cash', 'KHQR', 'Bank_Transfer'.
    """
    valid_methods = ('Cash', 'KHQR', 'Bank_Transfer')
    if payment_method not in valid_methods:
        raise ValueError(f"Invalid payment method: {payment_method}. Must be one of {valid_methods}")

    if amount_paid <= 0:
        raise ValueError("Payment amount must be greater than 0.")

    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()

    # Get invoice
    cursor.execute("SELECT invoice_id, total_amount, status FROM Invoices WHERE invoice_id = ?", (invoice_id,))
    inv = cursor.fetchone()
    if not inv:
        if should_close:
            conn.close()
        raise ValueError(f"Invoice ID {invoice_id} not found.")

    total_amount = inv["total_amount"]

    # Calculate existing payments
    cursor.execute("SELECT COALESCE(SUM(amount_paid), 0) as paid_sum FROM Payments WHERE invoice_id = ?", (invoice_id,))
    already_paid = cursor.fetchone()["paid_sum"]

    new_total_paid = already_paid + amount_paid

    # Insert payment record
    cursor.execute(
        """
        INSERT INTO Payments (invoice_id, amount_paid, payment_method, notes)
        VALUES (?, ?, ?, ?)
        """,
        (invoice_id, round(amount_paid, 2), payment_method, notes)
    )
    payment_id = cursor.lastrowid

    # Determine new invoice status
    if new_total_paid >= total_amount:
        new_status = "Paid"
    else:
        new_status = "Partially Paid"

    cursor.execute("UPDATE Invoices SET status = ? WHERE invoice_id = ?", (new_status, invoice_id))
    conn.commit()

    cursor.execute("SELECT * FROM Payments WHERE payment_id = ?", (payment_id,))
    payment_record = dict(cursor.fetchone())
    payment_record["new_invoice_status"] = new_status
    payment_record["balance_remaining"] = max(0.0, total_amount - new_total_paid)

    if should_close:
        conn.close()
    return payment_record

def get_unpaid_invoices(conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """
    Retrieves all invoices that are not fully paid ('Unpaid', 'Partially Paid', 'Overdue').
    Calculates the exact outstanding balance for each invoice.
    """
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT i.invoice_id, i.reading_id, i.total_amount, i.due_date, i.status, i.issue_date, i.late_fee,
               c.customer_id, c.name as customer_name, c.phone as customer_phone, c.address, c.customer_type,
               m.meter_number,
               COALESCE((SELECT SUM(p.amount_paid) FROM Payments p WHERE p.invoice_id = i.invoice_id), 0) as paid_amount
        FROM Invoices i
        JOIN Meter_Readings r ON i.reading_id = r.reading_id
        JOIN Meters m ON r.meter_id = m.meter_id
        JOIN Customers c ON m.customer_id = c.customer_id
        WHERE i.status IN ('Unpaid', 'Partially Paid', 'Overdue')
        ORDER BY i.due_date ASC
        """
    )
    rows = cursor.fetchall()
    results = []
    for r in rows:
        item = dict(r)
        item["outstanding_balance"] = round(max(0.0, item["total_amount"] - item["paid_amount"]), 2)
        results.append(item)

    if should_close:
        conn.close()
    return results

def get_customer_payment_history(customer_id: int, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Returns payment history for a specific customer."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT p.payment_id, p.invoice_id, p.amount_paid, p.payment_method, p.payment_date, p.notes,
               i.total_amount, i.status as invoice_status
        FROM Payments p
        JOIN Invoices i ON p.invoice_id = i.invoice_id
        JOIN Meter_Readings r ON i.reading_id = r.reading_id
        JOIN Meters m ON r.meter_id = m.meter_id
        WHERE m.customer_id = ?
        ORDER BY p.payment_date DESC
        """,
        (customer_id,)
    )
    rows = [dict(r) for r in cursor.fetchall()]

    if should_close:
        conn.close()
    return rows
