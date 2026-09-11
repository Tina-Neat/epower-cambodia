"""
tariffs.py - Tiered Tariff calculation engine and tariff management
"""

import sqlite3
from typing import List, Dict, Any, Optional, Tuple
from database import get_connection
from models import CustomerType, TariffTier

# Default standard tariffs (similar to EDC - Electricite du Cambodge structure)
DEFAULT_TARIFFS = [
    # Residential (លំនៅឋាន)
    {"customer_type": "Residential", "min_kwh": 0.0, "max_kwh": 10.0, "price_per_kwh": 380.0},
    {"customer_type": "Residential", "min_kwh": 10.0, "max_kwh": 50.0, "price_per_kwh": 480.0},
    {"customer_type": "Residential", "min_kwh": 50.0, "max_kwh": 200.0, "price_per_kwh": 610.0},
    {"customer_type": "Residential", "min_kwh": 200.0, "max_kwh": None, "price_per_kwh": 730.0},
    
    # Commercial (អាជីវកម្ម)
    {"customer_type": "Commercial", "min_kwh": 0.0, "max_kwh": 200.0, "price_per_kwh": 710.0},
    {"customer_type": "Commercial", "min_kwh": 200.0, "max_kwh": None, "price_per_kwh": 790.0},
    
    # Agricultural (កសិកម្ម)
    {"customer_type": "Agricultural", "min_kwh": 0.0, "max_kwh": 100.0, "price_per_kwh": 480.0},
    {"customer_type": "Agricultural", "min_kwh": 100.0, "max_kwh": None, "price_per_kwh": 600.0},
    
    # Industrial (ឧស្សាហកម្ម)
    {"customer_type": "Industrial", "min_kwh": 0.0, "max_kwh": 500.0, "price_per_kwh": 650.0},
    {"customer_type": "Industrial", "min_kwh": 500.0, "max_kwh": None, "price_per_kwh": 710.0},
]

def seed_default_tariffs(conn: Optional[sqlite3.Connection] = None) -> None:
    """Seeds default tiered tariffs if table is empty."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) AS count FROM Tariffs")
    count = cursor.fetchone()["count"]
    if count == 0:
        for t in DEFAULT_TARIFFS:
            cursor.execute(
                """
                INSERT INTO Tariffs (customer_type, min_kwh, max_kwh, price_per_kwh)
                VALUES (?, ?, ?, ?)
                """,
                (t["customer_type"], t["min_kwh"], t["max_kwh"], t["price_per_kwh"])
            )
        conn.commit()

    if should_close:
        conn.close()

def get_tariffs_by_customer_type(customer_type: str, conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Retrieves all sorted tariff tiers for a specific customer type."""
    should_close = False
    if conn is None:
        conn = get_connection()
        should_close = True

    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT tariff_id, customer_type, min_kwh, max_kwh, price_per_kwh
        FROM Tariffs
        WHERE customer_type = ?
        ORDER BY min_kwh ASC
        """,
        (customer_type,)
    )
    rows = cursor.fetchall()
    results = [dict(row) for row in rows]

    if should_close:
        conn.close()
    return results

def calculate_tiered_cost(
    customer_type: str,
    total_kwh: float,
    conn: Optional[sqlite3.Connection] = None
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Calculates total energy cost based on tiered tariffs.
    Returns:
      (total_energy_cost, breakdown_list)
      breakdown_list contains:
        - min_kwh, max_kwh, kwh_in_tier, rate, subtotal
    """
    if total_kwh < 0:
        raise ValueError("Total kWh cannot be negative.")
    if total_kwh == 0:
        return 0.0, []

    tiers = get_tariffs_by_customer_type(customer_type, conn)
    if not tiers:
        # Fallback if no database tariffs exist yet
        seed_default_tariffs(conn)
        tiers = get_tariffs_by_customer_type(customer_type, conn)

    total_cost = 0.0
    breakdown = []
    remaining_kwh = total_kwh

    for tier in tiers:
        min_kwh = tier["min_kwh"]
        max_kwh = tier["max_kwh"]
        rate = tier["price_per_kwh"]

        if remaining_kwh <= 0:
            break

        # Tier capacity
        if max_kwh is not None:
            tier_capacity = max_kwh - min_kwh
            kwh_in_tier = min(remaining_kwh, tier_capacity)
        else:
            kwh_in_tier = remaining_kwh

        if kwh_in_tier > 0:
            subtotal = kwh_in_tier * rate
            total_cost += subtotal
            breakdown.append({
                "tier_range": f"{min_kwh:g} - {max_kwh:g} kWh" if max_kwh else f"> {min_kwh:g} kWh",
                "kwh_used": round(kwh_in_tier, 2),
                "rate": rate,
                "subtotal": round(subtotal, 2)
            })
            remaining_kwh -= kwh_in_tier

    return round(total_cost, 2), breakdown
