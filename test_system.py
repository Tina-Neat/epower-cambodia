"""
test_system.py - Unit and Integration Tests for Electricity Consumption & Billing System
"""

import unittest
import os
import sqlite3
from database import init_db, get_connection
from tariffs import seed_default_tariffs, calculate_tiered_cost, get_tariffs_by_customer_type
import meter_service
import billing_service
import payment_service
import report_service

TEST_DB = "test_electricity.db"

class TestElectricitySystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)
        init_db(TEST_DB)
        cls.conn = get_connection(TEST_DB)
        seed_default_tariffs(cls.conn)

    @classmethod
    def tearDownClass(cls):
        cls.conn.close()
        if os.path.exists(TEST_DB):
            os.remove(TEST_DB)

    def test_01_tariff_calculation(self):
        """Verify tiered tariff calculation with residential tiers."""
        # Residential tiers:
        # 0-10: 380, 10-50: 480, 50-200: 610, >200: 730
        # Case 1: 5 kWh => 5 * 380 = 1900
        cost, breakdown = calculate_tiered_cost("Residential", 5.0, self.conn)
        self.assertEqual(cost, 1900.0)
        self.assertEqual(len(breakdown), 1)

        # Case 2: 25 kWh => (10 * 380) + (15 * 480) = 3800 + 7200 = 11000
        cost, breakdown = calculate_tiered_cost("Residential", 25.0, self.conn)
        self.assertEqual(cost, 11000.0)
        self.assertEqual(len(breakdown), 2)

        # Case 3: 75 kWh => (10 * 380) + (40 * 480) + (25 * 610) = 3800 + 19200 + 15250 = 38250
        cost, breakdown = calculate_tiered_cost("Residential", 75.0, self.conn)
        self.assertEqual(cost, 38250.0)
        self.assertEqual(len(breakdown), 3)

        # Case 4: 250 kWh => (10*380) + (40*480) + (150*610) + (50*730)
        # 3800 + 19200 + 91500 + 36500 = 151000
        cost, breakdown = calculate_tiered_cost("Residential", 250.0, self.conn)
        self.assertEqual(cost, 151000.0)
        self.assertEqual(len(breakdown), 4)

    def test_02_customer_and_meter_management(self):
        """Test registering customer and linking meter."""
        cust_id = meter_service.add_customer(
            name="សុខ ចាន់ដារា",
            phone="012 345 678",
            address="បង្គោលលេខ P-045, ភូមិ១, សង្កាត់ទួលសង្កែ",
            customer_type="Residential",
            conn=self.conn
        )
        self.assertIsNotNone(cust_id)

        customer = meter_service.get_customer(cust_id, self.conn)
        self.assertEqual(customer["name"], "សុខ ចាន់ដារា")

        # Add meter
        meter_id = meter_service.add_meter(
            meter_number="EDC-M-100234",
            customer_id=cust_id,
            status="Active",
            installation_date="2026-01-01",
            conn=self.conn
        )
        self.assertIsNotNone(meter_id)

        meter = meter_service.get_meter(meter_id, self.conn)
        self.assertEqual(meter["meter_number"], "EDC-M-100234")
        self.assertEqual(meter["customer_name"], "សុខ ចាន់ដារា")

    def test_03_meter_reading_and_formula(self):
        """Verify meter reading formula: total_kwh = current - previous."""
        # Find meter
        cursor = self.conn.cursor()
        cursor.execute("SELECT meter_id FROM Meters WHERE meter_number = 'EDC-M-100234'")
        meter_id = cursor.fetchone()["meter_id"]

        # Month 1: previous 0, current 80 => total = 80
        reading1 = meter_service.record_meter_reading(
            meter_id=meter_id,
            current_reading=80.0,
            previous_reading=0.0,
            reading_date="2026-01-31",
            conn=self.conn
        )
        self.assertEqual(reading1["total_kwh"], 80.0)

        # Month 2: previous auto-detected (80), current 175 => total = 95
        reading2 = meter_service.record_meter_reading(
            meter_id=meter_id,
            current_reading=175.0,
            reading_date="2026-02-28",
            conn=self.conn
        )
        self.assertEqual(reading2["previous_reading"], 80.0)
        self.assertEqual(reading2["total_kwh"], 95.0)

    def test_04_reading_anomaly_alerts(self):
        """Test abnormal reading alerts (negative reading & high usage spike)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT meter_id FROM Meters WHERE meter_number = 'EDC-M-100234'")
        meter_id = cursor.fetchone()["meter_id"]

        # Negative reading should raise ValueError
        with self.assertRaises(ValueError):
            meter_service.record_meter_reading(
                meter_id=meter_id,
                current_reading=150.0, # Previous was 175, so 150 < 175!
                reading_date="2026-03-31",
                conn=self.conn
            )

        # High usage spike (> 250% average)
        # Average previous is (80 + 95)/2 = 87.5. Let's record current = 500 (total = 325 kWh)
        reading_spike = meter_service.record_meter_reading(
            meter_id=meter_id,
            current_reading=500.0,
            reading_date="2026-03-31",
            conn=self.conn
        )
        self.assertIsNotNone(reading_spike["alert_notes"])
        self.assertIn("ALERT: ការប្រើប្រាស់កើនឡើងខ្ពស់ខុសប្រក្រតី", reading_spike["alert_notes"])

    def test_05_billing_and_invoicing(self):
        """Test invoice generation, maintenance fee, subsidy, and printable text."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT reading_id FROM Meter_Readings ORDER BY reading_id ASC LIMIT 1")
        reading_id = cursor.fetchone()["reading_id"]

        invoice = billing_service.generate_invoice(
            reading_id=reading_id,
            maintenance_fee=2000.0,
            subsidy_amount=0.0,
            due_days=15,
            issue_date="2026-02-01",
            conn=self.conn
        )
        self.assertIsNotNone(invoice["invoice_id"])
        self.assertEqual(invoice["status"], "Unpaid")

        # 80 kWh Residential:
        # (10*380) + (40*480) + (30*610) = 3800 + 19200 + 18300 = 41300 + 2000 fee = 43300
        self.assertEqual(invoice["total_amount"], 43300.0)

        # Printable layout test
        bill_text = billing_service.format_invoice_printable(invoice["invoice_id"], self.conn)
        self.assertIn("វិក្កយបត្រអគ្គិសនី", bill_text)
        self.assertIn("43,300 ៛", bill_text)

    def test_06_payments_and_outstanding(self):
        """Test recording payments (KHQR, Cash) and updating invoice status."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT invoice_id, total_amount FROM Invoices LIMIT 1")
        inv = cursor.fetchone()
        invoice_id = inv["invoice_id"]
        total_amount = inv["total_amount"]

        # Partial payment: pay 20,000 KHR via KHQR
        p1 = payment_service.record_payment(
            invoice_id=invoice_id,
            amount_paid=20000.0,
            payment_method="KHQR",
            notes="Paid via Bakong KHQR",
            conn=self.conn
        )
        self.assertEqual(p1["new_invoice_status"], "Partially Paid")
        self.assertEqual(p1["balance_remaining"], total_amount - 20000.0)

        # Remaining payment: pay the rest via Cash
        remaining = total_amount - 20000.0
        p2 = payment_service.record_payment(
            invoice_id=invoice_id,
            amount_paid=remaining,
            payment_method="Cash",
            notes="Paid remaining in cash",
            conn=self.conn
        )
        self.assertEqual(p2["new_invoice_status"], "Paid")
        self.assertEqual(p2["balance_remaining"], 0.0)

    def test_07_reports_and_loss_calculation(self):
        """Test reporting: monthly revenue, unpaid debt, area energy loss."""
        # Check area energy loss
        loss_data = report_service.calculate_area_energy_loss(
            supplied_kwh=1000.0,
            conn=self.conn
        )
        self.assertIsNotNone(loss_data["loss_kwh"])
        self.assertGreater(loss_data["loss_kwh"], 0)
        self.assertGreater(loss_data["loss_percentage"], 0)

        # Revenue report
        rev = report_service.get_monthly_revenue_report(conn=self.conn)
        self.assertTrue(len(rev) > 0)

    def test_08_authentication_and_admin_approval(self):
        """Test user registration, pending approval state, permanent admin protection, and admin approval."""
        import auth_service
        auth_service.ensure_permanent_admin(self.conn)

        # 1. Verify Permanent Admin login
        ok, msg, admin_user = auth_service.authenticate_user("admin", "admin123", conn=self.conn)
        self.assertTrue(ok, f"Admin login failed: {msg}")
        self.assertEqual(admin_user["username"], "admin")
        self.assertEqual(admin_user["role"], "Admin")
        self.assertEqual(admin_user["status"], "Approved")
        self.assertEqual(admin_user["is_permanent"], 1)

        # 2. Register a new staff user
        ok, msg, new_id = auth_service.register_user(
            username="sok_assistant",
            password="password123",
            full_name="សុខ ជំនួយការ",
            phone="012 345 678",
            role="Staff",
            conn=self.conn
        )
        self.assertTrue(ok, f"Registration failed: {msg}")
        self.assertIsNotNone(new_id)

        # 3. New user must be 'Pending' and CANNOT login yet
        ok_login, msg_login, _ = auth_service.authenticate_user("sok_assistant", "password123", conn=self.conn)
        self.assertFalse(ok_login)
        self.assertIn("រង់ចាំការអនុម័ត", msg_login)

        # 4. Check pending count
        pending_cnt = auth_service.get_pending_users_count(self.conn)
        self.assertGreaterEqual(pending_cnt, 1)

        # 5. Permanent Admin CANNOT be rejected or deleted
        ok_rej, msg_rej = auth_service.reject_user(admin_user["user_id"], "admin", conn=self.conn)
        self.assertFalse(ok_rej)
        self.assertIn("មិនអាចបដិសេធ Admin អចិន្ត្រៃយ៍", msg_rej)

        ok_del, msg_del = auth_service.delete_user(admin_user["user_id"], conn=self.conn)
        self.assertFalse(ok_del)
        self.assertIn("មិនអាចលុបគណនី Admin អចិន្ត្រៃយ៍", msg_del)

        # 6. Admin approves new user
        ok_app, msg_app = auth_service.approve_user(new_id, "admin", assigned_role="Cashier", conn=self.conn)
        self.assertTrue(ok_app, f"Approval failed: {msg_app}")

        # 7. Now approved user CAN login successfully
        ok_login2, msg_login2, staff_user = auth_service.authenticate_user("sok_assistant", "password123", conn=self.conn)
        self.assertTrue(ok_login2, f"Login after approval failed: {msg_login2}")
        self.assertEqual(staff_user["role"], "Cashier")
        self.assertEqual(staff_user["status"], "Approved")

        # 8. Test offline session creation and retrieval
        session_id = auth_service.create_session(staff_user["user_id"], days=30, conn=self.conn)
        self.assertIsNotNone(session_id)
        session_user = auth_service.get_user_by_session(session_id, conn=self.conn)
        self.assertIsNotNone(session_user)
        self.assertEqual(session_user["username"], "sok_assistant")

        # 9. Test session destruction (logout)
        auth_service.destroy_session(session_id, conn=self.conn)
        logged_out = auth_service.get_user_by_session(session_id, conn=self.conn)
        self.assertIsNone(logged_out)

if __name__ == "__main__":
    unittest.main()
