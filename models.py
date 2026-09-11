"""
models.py - Data structures and dataclasses for Electricity Consumption Management System
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum

class CustomerType(str, Enum):
    RESIDENTIAL = "Residential"       # លំនៅឋាន
    COMMERCIAL = "Commercial"         # អាជីវកម្ម
    AGRICULTURAL = "Agricultural"     # កសិកម្ម
    INDUSTRIAL = "Industrial"         # ឧស្សាហកម្ម

class MeterStatus(str, Enum):
    ACTIVE = "Active"
    SUSPENDED = "Suspended"
    DISCONNECTED = "Disconnected"
    MAINTENANCE = "Maintenance"

class InvoiceStatus(str, Enum):
    UNPAID = "Unpaid"
    PAID = "Paid"
    PARTIALLY_PAID = "Partially Paid"
    OVERDUE = "Overdue"

class PaymentMethod(str, Enum):
    CASH = "Cash"
    KHQR = "KHQR"
    BANK_TRANSFER = "Bank_Transfer"

@dataclass
class Customer:
    customer_id: Optional[int]
    name: str
    phone: str
    address: str
    customer_type: CustomerType
    created_at: Optional[str] = None

@dataclass
class Meter:
    meter_id: Optional[int]
    meter_number: str
    customer_id: int
    status: MeterStatus = MeterStatus.ACTIVE
    installation_date: Optional[str] = None

@dataclass
class TariffTier:
    tariff_id: Optional[int]
    customer_type: CustomerType
    min_kwh: float
    max_kwh: Optional[float]  # None indicates upper open bound (infinity)
    price_per_kwh: float      # in KHR (Riels)

@dataclass
class MeterReading:
    reading_id: Optional[int]
    meter_id: int
    previous_reading: float
    current_reading: float
    total_kwh: float
    reading_date: str
    alert_notes: Optional[str] = None

@dataclass
class Invoice:
    invoice_id: Optional[int]
    reading_id: int
    maintenance_fee: float
    subsidy_amount: float
    late_fee: float
    total_amount: float
    due_date: str
    status: InvoiceStatus
    issue_date: str

@dataclass
class Payment:
    payment_id: Optional[int]
    invoice_id: int
    amount_paid: float
    payment_method: PaymentMethod
    payment_date: Optional[str] = None
    notes: Optional[str] = None

class UserRole(str, Enum):
    ADMIN = "Admin"
    STAFF = "Staff"
    CASHIER = "Cashier"
    TECHNICIAN = "Technician"

class UserStatus(str, Enum):
    PENDING = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"

@dataclass
class User:
    user_id: Optional[int]
    username: str
    password_hash: str
    salt: str
    full_name: str
    phone: Optional[str] = None
    role: UserRole = UserRole.STAFF
    status: UserStatus = UserStatus.PENDING
    is_permanent: int = 0
    created_at: Optional[str] = None
    approved_at: Optional[str] = None
    approved_by: Optional[str] = None

@dataclass
class UserSession:
    session_id: str
    user_id: int
    created_at: str
    expires_at: str
