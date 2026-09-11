"""
main.py - Interactive CLI and Demonstration for Electricity Consumption Management System (ប្រព័ន្ធគ្រប់គ្រងការប្រើប្រាស់អគ្គិសនី)
"""

import sys
import os
from datetime import date

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
        sys.stdin.reconfigure(encoding='utf-8')
    except Exception:
        pass
from database import init_db, get_connection
from tariffs import seed_default_tariffs, get_tariffs_by_customer_type, calculate_tiered_cost
import meter_service
import billing_service
import payment_service
import report_service

def seed_demo_data():
    """Seeds rich, realistic Cambodian sample data for quick demonstration."""
    init_db()
    conn = get_connection()
    seed_default_tariffs(conn)

    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM Customers")
    if cursor.fetchone()["count"] > 0:
        conn.close()
        return

    print("កំពុងបញ្ចូលទិន្នន័យគំរូ (Seeding sample data)...")

    # 1. Add Customers
    sample_customers = [
        ("សុខ ចាន់ដារា", "012 889 901", "បង្គោលលេខ P-014, ភូមិទួលគោក, រាជធានីភ្នំពេញ", "Residential"),
        ("ហេង ស្រីពៅ", "098 776 554", "ផ្ទះលេខ 25, ផ្លូវ 271, សង្កាត់បឹងទំពុន", "Residential"),
        ("កាហ្វេ អាម៉ាហ្សូន សាខាផ្សារថ្មី", "077 334 455", "មហាវិថីព្រះមុនីវង្ស, ខណ្ឌដូនពេញ", "Commercial"),
        ("កសិដ្ឋានបន្លែធម្មជាតិ បាត់ដំបង", "088 554 332", "ភូមិស្វាយប៉ោ, ស្រុកបាណន់, ខេត្តបាត់ដំបង", "Agricultural"),
        ("រោងចក្រកាត់ដេរ ជ័យជំនះ", "011 223 344", "តំបន់សេដ្ឋកិច្ចពិសេស ភ្នំពេញ (PPSEZ)", "Industrial")
    ]

    cust_ids = []
    for name, phone, addr, c_type in sample_customers:
        cid = meter_service.add_customer(name, phone, addr, c_type, conn)
        cust_ids.append(cid)

    # 2. Add Meters
    meter_ids = []
    for i, cid in enumerate(cust_ids, start=1):
        mid = meter_service.add_meter(f"EDC-2026-M{i:04d}", cid, "Active", "2026-01-01", conn)
        meter_ids.append(mid)

    # 3. Add Readings (Month 1 - January 2026)
    r1 = meter_service.record_meter_reading(meter_ids[0], current_reading=85.0, previous_reading=0.0, reading_date="2026-01-31", conn=conn)
    r2 = meter_service.record_meter_reading(meter_ids[1], current_reading=45.0, previous_reading=0.0, reading_date="2026-01-31", conn=conn)
    r3 = meter_service.record_meter_reading(meter_ids[2], current_reading=380.0, previous_reading=0.0, reading_date="2026-01-31", conn=conn)
    r4 = meter_service.record_meter_reading(meter_ids[3], current_reading=220.0, previous_reading=0.0, reading_date="2026-01-31", conn=conn)
    r5 = meter_service.record_meter_reading(meter_ids[4], current_reading=1850.0, previous_reading=0.0, reading_date="2026-01-31", conn=conn)

    # 4. Generate Invoices
    inv1 = billing_service.generate_invoice(r1["reading_id"], maintenance_fee=2000, subsidy_amount=0, issue_date="2026-02-01", conn=conn)
    inv2 = billing_service.generate_invoice(r2["reading_id"], maintenance_fee=2000, subsidy_amount=0, issue_date="2026-02-01", conn=conn)
    inv3 = billing_service.generate_invoice(r3["reading_id"], maintenance_fee=3000, subsidy_amount=0, issue_date="2026-02-01", conn=conn)
    inv4 = billing_service.generate_invoice(r4["reading_id"], maintenance_fee=2500, subsidy_amount=0, issue_date="2026-02-01", conn=conn)
    inv5 = billing_service.generate_invoice(r5["reading_id"], maintenance_fee=5000, subsidy_amount=0, issue_date="2026-02-01", conn=conn)

    # 5. Process Some Payments
    payment_service.record_payment(inv1["invoice_id"], inv1["total_amount"], "KHQR", "បង់តាម Bakong KHQR", conn=conn)
    payment_service.record_payment(inv3["invoice_id"], 100000.0, "Bank_Transfer", "បង់មួយចំណែក", conn=conn)

    conn.close()
    print("ទិន្នន័យគំរូត្រូវបានបង្កើតរួចរាល់ដោយជោគជ័យ!\n")

def print_banner():
    banner = """
================================================================================
          ប្រព័ន្ធគ្រប់គ្រងការប្រើប្រាស់ និងចេញវិក្កយបត្រអគ្គិសនី
                (Electricity Consumption & Billing System)
================================================================================
"""
    print(banner)

def display_menu():
    print("""
[១]. បង្ហាញបញ្ជីអតិថិជន និងកុងទ័រ (List Customers & Meters)
[២]. ចុះឈ្មោះអតិថិជន និងកុងទ័រថ្មី (Register Customer & Meter)
[៣]. កត់ត្រាលេខកុងទ័រប្រចាំខែ និងត្រួតពិនិត្យ (Record Meter Reading)
[៤]. ចេញវិក្កយបត្រ និងបោះពុម្ពវិក្កយបត្រ (Generate & Print Invoice)
[៥]. ទទួលការទូទាត់ប្រាក់ - Cash / KHQR (Record Payment)
[៦]. តាមដានវិក្កយបត្រមិនទាន់ទូទាត់ & បំណុល (Outstanding Debt)
[៧]. តារាងតម្លៃពន្ធុភាព (Tariff Rates Breakdown)
[៨]. របាយការណ៍ចំណូល និងថាមពលបាត់បង់តាមតំបន់ (Reports & Energy Loss)
[៩]. បង្កើតឡើងវិញនូវទិន្នន័យគំរូ (Reset & Reseed Demo Data)
[០]. ចាកចេញ (Exit)
--------------------------------------------------------------------------------
""")

def handle_list_customers():
    customers = meter_service.list_customers()
    print("\n--- បញ្ជីអតិថិជន និងកុងទ័រក្នុងប្រព័ន្ធ ---")
    print(f"{'ID':<4} | {'ឈ្មោះអតិថិជន':<25} | {'ទូរស័ព្ទ':<13} | {'ប្រភេទ':<14} | {'កុងទ័រ':<15}")
    print("-" * 80)
    for c in customers:
        meters = meter_service.get_meters_by_customer(c["customer_id"])
        meter_nums = ", ".join([m["meter_number"] for m in meters]) if meters else "គ្មានកុងទ័រ"
        print(f"{c['customer_id']:<4} | {c['name']:<25} | {c['phone']:<13} | {c['customer_type']:<14} | {meter_nums:<15}")
    print("-" * 80)

def handle_register_customer():
    print("\n--- ចុះឈ្មោះអតិថិជនថ្មី ---")
    name = input("បញ្ចូលឈ្មោះអតិថិជន: ").strip()
    if not name:
        print("ឈ្មោះមិនអាចទទេបានទេ!")
        return
    phone = input("លេខទូរស័ព្ទ: ").strip()
    address = input("អាសយដ្ឋាន/ទីតាំងបង្គោលភ្លើង: ").strip()
    print("ជ្រើសរើសប្រភេទអតិថិជន:")
    print("1. Residential (លំនៅឋាន)\n2. Commercial (អាជីវកម្ម)\n3. Agricultural (កសិកម្ម)\n4. Industrial (ឧស្សាហកម្ម)")
    type_choice = input("ជម្រើស (1-4) [default: 1]: ").strip()
    types_map = {"1": "Residential", "2": "Commercial", "3": "Agricultural", "4": "Industrial"}
    c_type = types_map.get(type_choice, "Residential")

    cust_id = meter_service.add_customer(name, phone, address, c_type)
    print(f"✓ បានចុះឈ្មោះអតិថិជនជោគជ័យ! (Customer ID: {cust_id})")

    add_m = input("តើចង់ភ្ជាប់កុងទ័រភ្លាមៗទេ? (y/n): ").strip().lower()
    if add_m == "y":
        meter_num = input("បញ្ចូលលេខកូដកុងទ័រ (Meter Number): ").strip()
        if not meter_num:
            meter_num = f"EDC-M-{cust_id:05d}"
        meter_id = meter_service.add_meter(meter_num, cust_id)
        print(f"✓ បានភ្ជាប់កុងទ័រ {meter_num} (Meter ID: {meter_id}) ជោគជ័យ!")

def handle_record_reading():
    print("\n--- កត់ត្រាលេខកុងទ័រប្រចាំខែ (Meter Reading) ---")
    meter_id_str = input("បញ្ចូល Meter ID: ").strip()
    if not meter_id_str.isdigit():
        print("សូមបញ្ចូលលេខសម្គាល់ Meter ID ឱ្យបានត្រឹមត្រូវ!")
        return
    meter_id = int(meter_id_str)
    meter = meter_service.get_meter(meter_id)
    if not meter:
        print("រកមិនឃើញកុងទ័រនេះទេ!")
        return

    latest = meter_service.get_latest_reading(meter_id)
    prev_val = latest["current_reading"] if latest else 0.0
    print(f"ព័ត៌មានកុងទ័រ: {meter['meter_number']} | អតិថិជន: {meter['customer_name']}")
    print(f"លេខកុងទ័រចាស់ (Previous Reading): {prev_val:.2f} kWh")

    curr_val_str = input(f"បញ្ចូលលេខកុងទ័រថ្មី (Current Reading) [> {prev_val}]: ").strip()
    try:
        curr_val = float(curr_val_str)
    except ValueError:
        print("តម្លៃបញ្ចូលមិនត្រឹមត្រូវ!")
        return

    r_date = input(f"កាលបរិច្ឆេទកត់ត្រា (YYYY-MM-DD) [default: {date.today()}]: ").strip()
    if not r_date:
        r_date = date.today().isoformat()

    try:
        record = meter_service.record_meter_reading(
            meter_id=meter_id,
            current_reading=curr_val,
            previous_reading=prev_val,
            reading_date=r_date
        )
        print(f"✓ កត់ត្រាជោគជ័យ! ការប្រើប្រាស់ខែនេះ: {record['total_kwh']:.2f} kWh (Reading ID: {record['reading_id']})")
        if record["alert_notes"]:
            print(f"⚠️ {record['alert_notes']}")
        
        gen_inv = input("តើចង់ចេញវិក្កយបត្រភ្លាមៗដែរឬទេ? (y/n): ").strip().lower()
        if gen_inv == "y":
            inv = billing_service.generate_invoice(record["reading_id"])
            print(f"✓ ចេញវិក្កយបត្រជោគជ័យ! Invoice ID: {inv['invoice_id']} | ទឹកប្រាក់: {inv['total_amount']:,.0f} ៛")
    except ValueError as e:
        print(f"❌ កំហុស៖ {e}")

def handle_print_invoice():
    print("\n--- ចេញវិក្កយបត្រ និងបោះពុម្ព ---")
    inv_id_str = input("បញ្ចូលលេខវិក្កយបត្រ (Invoice ID): ").strip()
    if not inv_id_str.isdigit():
        print("សូមបញ្ចូលលេខ Invoice ID ត្រឹមត្រូវ!")
        return
    inv_id = int(inv_id_str)
    output = billing_service.format_invoice_printable(inv_id)
    print("\n" + output + "\n")

def handle_record_payment():
    print("\n--- ទទួលការទូទាត់ប្រាក់ (Process Payment) ---")
    inv_id_str = input("បញ្ចូលលេខវិក្កយបត្រ (Invoice ID): ").strip()
    if not inv_id_str.isdigit():
        print("សូមបញ្ចូលលេខ Invoice ID ត្រឹមត្រូវ!")
        return
    inv_id = int(inv_id_str)
    inv = billing_service.get_invoice_details(inv_id)
    if not inv:
        print(f"រកមិនឃើញវិក្កយបត្រ #{inv_id} ទេ!")
        return

    print(f"វិក្កយបត្រ #{inv_id} | អតិថិជន: {inv['customer_name']} | សរុប: {inv['total_amount']:,.0f} ៛ | នៅខ្វះ: {inv['balance_due']:,.0f} ៛")
    if inv["balance_due"] <= 0:
        print("វិក្កយបត្រនេះបានទូទាត់រួចរាល់ហើយ!")
        return

    amount_str = input(f"បញ្ចូលចំនួនទឹកប្រាក់ត្រូវបង់ [default: {inv['balance_due']:.0f}]: ").strip()
    amount = float(amount_str) if amount_str else inv["balance_due"]

    print("វិធីសាស្ត្រទូទាត់:\n1. KHQR\n2. Cash (សាច់ប្រាក់)\n3. Bank_Transfer (ផ្ទេរតាមធនាគារ)")
    m_choice = input("ជម្រើស (1-3) [default: 1]: ").strip()
    m_map = {"1": "KHQR", "2": "Cash", "3": "Bank_Transfer"}
    method = m_map.get(m_choice, "KHQR")
    notes = input("កំណត់ចំណាំ (បើសិនមាន): ").strip()

    res = payment_service.record_payment(inv_id, amount, method, notes)
    print(f"✓ ទូទាត់ជោគជ័យ! បង់ប្រាក់: {res['amount_paid']:,.0f} ៛ តាម {method} | ស្ថានភាពវិក្កយបត្រថ្មី: {res['new_invoice_status']} | នៅសល់: {res['balance_remaining']:,.0f} ៛")

def handle_unpaid_invoices():
    print("\n--- បញ្ជីវិក្កយបត្រមិនទាន់ទូទាត់ & បំណុល (Outstanding Invoices) ---")
    billing_service.update_overdue_invoices()
    unpaid = payment_service.get_unpaid_invoices()
    if not unpaid:
        print("ពុំមានវិក្កយបត្រជំពាក់ទេ! អតិថិជនទាំងអស់បានទូទាត់រួចរាល់។")
        return

    print(f"{'Inv ID':<7} | {'អតិថិជន':<22} | {'ទូរស័ព្ទ':<12} | {'ថ្ងៃផុតកំណត់':<11} | {'ទឹកប្រាក់សរុប':<14} | {'នៅខ្វះ (KHR)':<14} | {'ស្ថានភាព'}")
    print("-" * 95)
    for u in unpaid:
        print(f"INV-{u['invoice_id']:<3} | {u['customer_name']:<22} | {u['customer_phone']:<12} | {u['due_date']:<11} | {u['total_amount']:>10,.0f} ៛ | {u['outstanding_balance']:>10,.0f} ៛ | {u['status']}")
    print("-" * 95)

    summary = report_service.get_outstanding_debt_summary()
    print(f"សរុបអតិថិជនជំពាក់: {summary['debtor_count']} នាក់ | វិក្កយបត្រមិនទាន់បង់: {summary['unpaid_invoice_count']} | ទឹកប្រាក់បំណុលសរុប: {summary['net_outstanding_debt']:,.0f} ៛\n")

def handle_show_tariffs():
    print("\n--- តារាងតម្លៃពន្ធុភាពតាមប្រភេទអតិថិជន (Tiered Tariffs) ---")
    types = ["Residential", "Commercial", "Agricultural", "Industrial"]
    for t in types:
        tiers = get_tariffs_by_customer_type(t)
        print(f"\n[ប្រភេទ: {t}]")
        print(f"{'កម្រិតប្រើប្រាស់ (kWh)':<25} | {'តម្លៃក្នុង 1 kWh (KHR)':<20}")
        print("-" * 50)
        for tr in tiers:
            rn = f"{tr['min_kwh']:g} - {tr['max_kwh']:g} kWh" if tr['max_kwh'] else f"> {tr['min_kwh']:g} kWh"
            print(f"{rn:<25} | {tr['price_per_kwh']:>12,.0f} ៛")

def handle_reports():
    print("\n--- របាយការណ៍ និងស្ថិតិ (Reports & Analytics) ---")
    print("1. របាយការណ៍ចំណូលប្រចាំខែ (Monthly Revenue)")
    print("2. របាយការណ៍តាមប្រភេទអតិថិជន (Revenue by Customer Type)")
    print("3. របាយការណ៍ថាមពលបាត់បង់តាមតំបន់ (Area Energy Loss)")
    choice = input("ជ្រើសរើសរបាយការណ៍ (1-3): ").strip()

    if choice == "1":
        rev = report_service.get_monthly_revenue_report()
        print("\n--- របាយការណ៍ចំណូលប្រចាំខែ ---")
        print(f"{'ខែ':<10} | {'ចំនួនវិក្កយបត្រ':<15} | {'ប្រាក់ចេញវិក្កយបត្រ':<18} | {'ប្រាក់ប្រមូលបាន':<18} | {'អត្រាប្រមូល (%)'}")
        print("-" * 80)
        for r in rev:
            print(f"{r['month']:<10} | {r['total_invoices']:<15} | {r['total_billed']:>14,.0f} ៛ | {r['total_collected']:>14,.0f} ៛ | {r['collection_rate_percent']:>10.1f} %")
        print("-" * 80)
    elif choice == "2":
        by_type = report_service.get_revenue_by_customer_type()
        print("\n--- ស្ថិតិតាមប្រភេទអតិថិជន ---")
        print(f"{'ប្រភេទ':<14} | {'អតិថិជន':<8} | {'ថាមពល (kWh)':<14} | {'ប្រាក់ចេញវិក្កយបត្រ':<18} | {'ប្រាក់បានបង់'}")
        print("-" * 75)
        for bt in by_type:
            print(f"{bt['customer_type']:<14} | {bt['total_customers']:<8} | {bt['total_kwh_consumed']:>10.1f} kWh | {bt['total_billed_amount']:>14,.0f} ៛ | {bt['total_paid_amount']:>14,.0f} ៛")
        print("-" * 75)
    elif choice == "3":
        sup_str = input("បញ្ចូលថាមពលសរុបផ្គត់ផ្គង់ពីស្ថានីយ (Supplied kWh) [default: 3000]: ").strip()
        sup = float(sup_str) if sup_str else 3000.0
        loss = report_service.calculate_area_energy_loss(supplied_kwh=sup)
        print("\n--- ការវិភាគថាមពល និងការបាត់បង់ (Energy Loss Report) ---")
        print(f"ថាមពលផ្គត់ផ្គង់សរុប (Total Supplied) : {loss['supplied_kwh']:>12,.2f} kWh")
        print(f"ថាមពលលក់បានតាមកុងទ័រ (Total Billed): {loss['total_billed_kwh']:>12,.2f} kWh")
        print(f"ថាមពលបាត់បង់ (Energy Loss)         : {loss['loss_kwh']:>12,.2f} kWh ({loss['loss_percentage']} %)")
        print("\nលម្អិតតាមទីតាំង/តំបន់:")
        for a in loss["areas"]:
            print(f"  • {a['area']}: {a['billed_kwh']:,.1f} kWh ({a['meter_count']} កុងទ័រ)")

def main():
    seed_demo_data()
    print_banner()

    # If non-interactive demo is triggered or arguments passed
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        print("\n[DEMO RUN AUTOMATION] កំពុងបង្ហាញមុខងារចម្បងៗដោយស្វ័យប្រវត្តិ:\n")
        handle_list_customers()
        print("\n[Demo Invoice Print Sample]:")
        sample_inv = billing_service.format_invoice_printable(1)
        print(sample_inv)
        handle_unpaid_invoices()
        return

    while True:
        display_menu()
        choice = input("សូមជ្រើសរើសមុខងារ (0-9): ").strip()
        if choice == "1":
            handle_list_customers()
        elif choice == "2":
            handle_register_customer()
        elif choice == "3":
            handle_record_reading()
        elif choice == "4":
            handle_print_invoice()
        elif choice == "5":
            handle_record_payment()
        elif choice == "6":
            handle_unpaid_invoices()
        elif choice == "7":
            handle_show_tariffs()
        elif choice == "8":
            handle_reports()
        elif choice == "9":
            if os.path.exists("electricity_system.db"):
                os.remove("electricity_system.db")
            seed_demo_data()
            print("✓ បានរៀបចំ Database ឡើងវិញរួចរាល់!")
        elif choice == "0":
            print("\nសូមអរគុណ! សូមជម្រាបលា។ (Thank you!)")
            break
        else:
            print("ជម្រើសមិនត្រឹមត្រូវ សូមព្យាយាមម្តងទៀត!")

if __name__ == "__main__":
    main()
