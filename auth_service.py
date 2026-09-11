"""
auth_service.py - Authentication, Session & User Management System for E-Power (Online & Offline)
100% Dependency-Free (uses Python standard libraries: hashlib, secrets, sqlite3)
"""

import sqlite3
import hashlib
import secrets
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

from database import get_connection

DEFAULT_ADMIN_SALT = "epower_permanent_admin_salt_2026"
DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "admin123"

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Generates a salt and PBKDF2 HMAC-SHA256 password hash."""
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return pwd_hash, salt

def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    """Verifies a password against the stored salt and PBKDF2 hash."""
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000).hex()
    return secrets.compare_digest(pwd_hash, expected_hash)

def ensure_permanent_admin(conn: Optional[sqlite3.Connection] = None) -> None:
    """Ensures the permanent default admin account exists and is always Approved."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, status, role FROM Users WHERE username = ?", (DEFAULT_ADMIN_USERNAME,))
        row = cursor.fetchone()
        if not row:
            pwd_hash, salt = hash_password(DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_SALT)
            cursor.execute("""
            INSERT INTO Users (username, password_hash, salt, full_name, phone, role, status, is_permanent, approved_at, approved_by)
            VALUES (?, ?, ?, ?, ?, 'Admin', 'Approved', 1, CURRENT_TIMESTAMP, 'System');
            """, (DEFAULT_ADMIN_USERNAME, pwd_hash, salt, "អ្នកគ្រប់គ្រងប្រព័ន្ធ (Permanent Admin)", "012 888 999"))
            conn.commit()
        else:
            # Guarantee permanent admin can never lose Admin role or Approved status
            cursor.execute("""
            UPDATE Users SET is_permanent = 1, role = 'Admin', status = 'Approved' WHERE username = ?
            """, (DEFAULT_ADMIN_USERNAME,))
            conn.commit()
    finally:
        if close_conn:
            conn.close()

def register_user(
    username: str,
    password: str,
    full_name: str,
    phone: Optional[str] = None,
    role: str = "Staff",
    conn: Optional[sqlite3.Connection] = None
) -> Tuple[bool, str, Optional[int]]:
    """
    Registers a new user into the system.
    New users ALWAYS receive status = 'Pending' and require Permanent Admin approval.
    """
    username = username.strip().lower()
    full_name = full_name.strip()
    phone = (phone or "").strip()

    if not username:
        return False, "សូមបញ្ចូលឈ្មោះគណនី (Username)!", None
    if len(username) < 3:
        return False, "ឈ្មោះគណនីត្រូវមានយ៉ាងតិច ៣ តួអក្សរ!", None
    if not password or len(password) < 4:
        return False, "ពាក្យសម្ងាត់ត្រូវមានយ៉ាងតិច ៤ តួអក្សរ!", None
    if not full_name:
        return False, "សូមបញ្ចូលឈ្មោះពេញរបស់អ្នក!", None

    valid_roles = ["Staff", "Cashier", "Technician", "Admin"]
    if role not in valid_roles:
        role = "Staff"

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM Users WHERE username = ?", (username,))
        if cursor.fetchone():
            return False, f"ឈ្មោះគណនី '{username}' នេះមានក្នុងប្រព័ន្ធរួចហើយ! សូមជ្រើសរើសឈ្មោះផ្សេង។", None

        pwd_hash, salt = hash_password(password)
        cursor.execute("""
        INSERT INTO Users (username, password_hash, salt, full_name, phone, role, status, is_permanent, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'Pending', 0, CURRENT_TIMESTAMP);
        """, (username, pwd_hash, salt, full_name, phone, role))
        conn.commit()
        user_id = cursor.lastrowid
        return True, "ការចុះឈ្មោះបានជោគជ័យ! សូមរង់ចាំ Admin អចិន្ត្រៃយ៍អនុម័តគណនីជាមុនសិន ទើបអាចចូលប្រើប្រព័ន្ធបាន។", user_id
    finally:
        if close_conn:
            conn.close()

def authenticate_user(
    username: str,
    password: str,
    conn: Optional[sqlite3.Connection] = None
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validates username and password.
    Blocks login if the account is 'Pending' (waiting admin approval) or 'Rejected'.
    """
    username = username.strip().lower()
    if not username or not password:
        return False, "សូមបញ្ចូលឈ្មោះគណនី និងពាក្យសម្ងាត់!", None

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT user_id, username, password_hash, salt, full_name, phone, role, status, is_permanent, created_at, approved_at, approved_by
        FROM Users WHERE username = ?
        """, (username,))
        row = cursor.fetchone()

        if not row:
            return False, "ឈ្មោះគណនី ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវឡើយ!", None

        user = dict(row)
        if not verify_password(password, user["salt"], user["password_hash"]):
            return False, "ឈ្មោះគណនី ឬពាក្យសម្ងាត់មិនត្រឹមត្រូវឡើយ!", None

        # Check Account Status
        if user["status"] == "Pending":
            return False, "គណនីរបស់អ្នកកំពុងស្ថិតក្នុងស្ថានភាព «រង់ចាំការអនុម័ត» ពី Admin អចិន្ត្រៃយ៍។ សូមទាក់ទង Admin!", None

        if user["status"] == "Rejected":
            return False, "គណនីរបស់អ្នកត្រូវបានបដិសេធមិនអនុញ្ញាតឱ្យចូលប្រើឡើយ។ សូមទាក់ទង Admin!", None

        if user["status"] != "Approved":
            return False, f"គណនីរបស់អ្នកមិនទាន់ត្រូវបានអនុញ្ញាតឱ្យចូលប្រើទេ ({user['status']})!", None

        # Clean sensitive fields
        del user["password_hash"]
        del user["salt"]
        return True, "ចូលប្រើប្រព័ន្ធបានជោគជ័យ!", user
    finally:
        if close_conn:
            conn.close()

def create_session(user_id: int, days: int = 30, conn: Optional[sqlite3.Connection] = None) -> str:
    """Creates a persistent session token in SQLite, enabling 100% offline access."""
    session_id = secrets.token_urlsafe(36)
    expires_at = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT INTO User_Sessions (session_id, user_id, created_at, expires_at)
        VALUES (?, ?, CURRENT_TIMESTAMP, ?);
        """, (session_id, user_id, expires_at))
        conn.commit()
        return session_id
    finally:
        if close_conn:
            conn.close()

def get_user_by_session(session_id: str, conn: Optional[sqlite3.Connection] = None) -> Optional[Dict[str, Any]]:
    """Retrieves an active approved user associated with the given session ID."""
    if not session_id:
        return None

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
        SELECT u.user_id, u.username, u.full_name, u.phone, u.role, u.status, u.is_permanent,
               u.created_at, u.approved_at, u.approved_by, s.session_id, s.expires_at
        FROM User_Sessions s
        JOIN Users u ON s.user_id = u.user_id
        WHERE s.session_id = ? AND s.expires_at > ? AND u.status = 'Approved'
        """, (session_id, now_str))
        row = cursor.fetchone()
        return dict(row) if row else None
    finally:
        if close_conn:
            conn.close()

def destroy_session(session_id: str, conn: Optional[sqlite3.Connection] = None) -> None:
    """Invalidates and deletes a session token."""
    if not session_id:
        return

    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM User_Sessions WHERE session_id = ?", (session_id,))
        conn.commit()
    finally:
        if close_conn:
            conn.close()

def approve_user(
    user_id: int,
    admin_name: str,
    assigned_role: Optional[str] = None,
    conn: Optional[sqlite3.Connection] = None
) -> Tuple[bool, str]:
    """Approves a pending registered user."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username, status FROM Users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False, "រកមិនឃើញគណនីអ្នកប្រើប្រាស់នេះឡើយ!"

        if assigned_role:
            cursor.execute("""
            UPDATE Users
            SET status = 'Approved', role = ?, approved_at = CURRENT_TIMESTAMP, approved_by = ?
            WHERE user_id = ?
            """, (assigned_role, admin_name, user_id))
        else:
            cursor.execute("""
            UPDATE Users
            SET status = 'Approved', approved_at = CURRENT_TIMESTAMP, approved_by = ?
            WHERE user_id = ?
            """, (admin_name, user_id))

        conn.commit()
        return True, f"បានអនុម័តគណនី '{row['username']}' ឱ្យចូលប្រើប្រព័ន្ធបានជោគជ័យ!"
    finally:
        if close_conn:
            conn.close()

def reject_user(
    user_id: int,
    admin_name: str,
    conn: Optional[sqlite3.Connection] = None
) -> Tuple[bool, str]:
    """Rejects a user registration. Cannot reject permanent admin."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username, is_permanent FROM Users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False, "រកមិនឃើញគណនីអ្នកប្រើប្រាស់នេះឡើយ!"
        if row["is_permanent"] == 1:
            return False, "មិនអាចបដិសេធ Admin អចិន្ត្រៃយ៍បានជាដាច់ខាត!"

        cursor.execute("""
        UPDATE Users
        SET status = 'Rejected', approved_at = CURRENT_TIMESTAMP, approved_by = ?
        WHERE user_id = ?
        """, (admin_name, user_id))
        # Clear any active sessions
        cursor.execute("DELETE FROM User_Sessions WHERE user_id = ?", (user_id,))
        conn.commit()
        return True, f"បានបដិសេធគណនី '{row['username']}' រួចរាល់!"
    finally:
        if close_conn:
            conn.close()

def delete_user(user_id: int, conn: Optional[sqlite3.Connection] = None) -> Tuple[bool, str]:
    """Deletes a non-permanent user from the system."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT username, is_permanent FROM Users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if not row:
            return False, "រកមិនឃើញអ្នកប្រើប្រាស់នេះឡើយ!"
        if row["is_permanent"] == 1:
            return False, "មិនអាចលុបគណនី Admin អចិន្ត្រៃយ៍បានជាដាច់ខាត!"

        cursor.execute("DELETE FROM User_Sessions WHERE user_id = ?", (user_id,))
        cursor.execute("DELETE FROM Users WHERE user_id = ?", (user_id,))
        conn.commit()
        return True, f"បានលុបគណនី '{row['username']}' ចេញពីប្រព័ន្ធរួចរាល់!"
    finally:
        if close_conn:
            conn.close()

def list_all_users(conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Lists all users ordered by priority: Permanent Admin first, then pending requests, then recent users."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT user_id, username, full_name, phone, role, status, is_permanent,
               created_at, approved_at, approved_by
        FROM Users
        ORDER BY 
            is_permanent DESC,
            CASE status WHEN 'Pending' THEN 1 WHEN 'Approved' THEN 2 ELSE 3 END,
            created_at DESC
        """)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        if close_conn:
            conn.close()

def get_pending_users(conn: Optional[sqlite3.Connection] = None) -> List[Dict[str, Any]]:
    """Lists users waiting for approval."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT user_id, username, full_name, phone, role, status, created_at
        FROM Users
        WHERE status = 'Pending'
        ORDER BY created_at ASC
        """)
        return [dict(r) for r in cursor.fetchall()]
    finally:
        if close_conn:
            conn.close()

def get_pending_users_count(conn: Optional[sqlite3.Connection] = None) -> int:
    """Returns the count of users waiting for admin approval."""
    close_conn = False
    if conn is None:
        conn = get_connection()
        close_conn = True

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as cnt FROM Users WHERE status = 'Pending'")
        row = cursor.fetchone()
        return row["cnt"] if row else 0
    finally:
        if close_conn:
            conn.close()
