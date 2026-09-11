# ប្រព័ន្ធគ្រប់គ្រងការប្រើប្រាស់ និងចេញវិក្កយបត្រអគ្គិសនី (Electricity Consumption & Billing System)

ប្រព័ន្ធគ្រប់គ្រងការប្រើប្រាស់អគ្គិសនីនេះ ត្រូវបានរៀបចំឡើងជាភាសា **Python** ដោយប្រើប្រាស់ **SQLite Database** ដើម្បីធានានូវភាពត្រឹមត្រូវខ្ពស់ក្នុងការគណនាគីឡូវ៉ាត់ម៉ោង (kWh) ការចេញវិក្កយបត្រតាមកាំពន្ធុភាព (Tiered Tariffs) ប្រព័ន្ធផ្ទៀងផ្ទាត់និងព្រមានស្វ័យប្រវត្តិ (Alert System) ព្រមទាំងការគ្រប់គ្រងការបង់ប្រាក់ និងរបាយការណ៍បំណុល។

---

## ១. រចនាសម្ព័ន្ធឯកសារក្នុងគម្រោង (Project Architecture)

```
d:/IT/E-Power/
├── database.py         # ការតភ្ជាប់ SQLite & ការបង្កើតតារាងទាំង ៦ (Schema DDL)
├── models.py           # Dataclasses & Enums សម្រាប់អតិថិជន កុងទ័រ វិក្កយបត្រ ការទូទាត់
├── tariffs.py          # ម៉ាស៊ីនគណនាតម្លៃអគ្គិសនីតាមកម្រិតពន្ធុភាព (Tiered Tariffs Engine)
├── meter_service.py    # ការគ្រប់គ្រងអតិថិជន/កុងទ័រ, កត់ត្រា kWh, ប្រព័ន្ធព្រមាន (Alerts)
├── billing_service.py  # ការចេញវិក្កយបត្រ, ការគណនាថ្ងៃកំណត់, ពិន័យយឺតយ៉ាវ, ទម្រង់បោះពុម្ព
├── payment_service.py  # ការកត់ត្រាបង់ប្រាក់ (Cash, KHQR), តាមដានបំណុលមិនទាន់ទូទាត់
├── report_service.py   # របាយការណ៍ចំណូលប្រចាំខែ, ស្ថិតិបំណុល, ថាមពលបាត់បង់តាមតំបន់
├── test_system.py      # កញ្ចប់តេស្តស្វ័យប្រវត្តិ (Unit Tests 100% Passed)
├── main.py             # កម្មវិធីដំណើរការសាកល្បង + Interactive Console Menu ជាភាសាខ្មែរ
└── electricity_system.db # ឯកសារទិន្នន័យ SQLite
```

---

## ២. គ្រោងរចនាសម្ព័ន្ធទិន្នន័យ (Database Schema)

| តារាង (Table) | ជួរឈរសំខាន់ៗ (Fields) | ការពិពណ៌នា |
|---|---|---|
| **`Customers`** | `customer_id`, `name`, `phone`, `address`, `customer_type`, `created_at` | ព័ត៌មានអតិថិជន (លំនៅឋាន, អាជីវកម្ម, កសិកម្ម, ឧស្សាហកម្ម) |
| **`Meters`** | `meter_id`, `meter_number`, `customer_id`, `status`, `installation_date` | នាឡិកាស្ទង់អគ្គិសនី ភ្ជាប់ជាមួយអតិថិជន |
| **`Tariffs`** | `tariff_id`, `customer_type`, `min_kwh`, `max_kwh`, `price_per_kwh` | តារាងកាំតម្លៃពន្ធុភាពតាមប្រភេទអតិថិជន |
| **`Meter_Readings`** | `reading_id`, `meter_id`, `previous_reading`, `current_reading`, `total_kwh`, `reading_date`, `alert_notes` | កត់ត្រាលេខចាស់ លេខថ្មី ផលសង kWh និងកំណត់ចំណាំ Alert |
| **`Invoices`** | `invoice_id`, `reading_id`, `maintenance_fee`, `subsidy_amount`, `late_fee`, `total_amount`, `due_date`, `status`, `issue_date` | វិក្កយបត្រថ្លៃភ្លើង សេវាថែទាំ ឧបត្ថម្ភធន និងប្រាក់ពិន័យ |
| **`Payments`** | `payment_id`, `invoice_id`, `amount_paid`, `payment_method`, `payment_date`, `notes` | ប្រវត្តិការបង់ប្រាក់ (`Cash`, `KHQR`, `Bank_Transfer`) |

---

## ៣. ម៉ូឌុលចម្បងៗ និងរូបមន្តគណនា (Core Modules & Logic)

### ក. ការកត់ត្រានិងរូបមន្តគណនាការប្រើប្រាស់ (Meter Reading Formula)
$$\text{ការប្រើប្រាស់សរុប (kWh)} = \text{លេខកុងទ័រថ្មី (Current)} - \text{លេខកុងទ័រចាស់ (Previous)}$$

### ខ. ប្រព័ន្ធព្រមានស្វ័យប្រវត្តិ (Alert Anomaly Detection)
- **Negative Reading (`ValueError`)**៖ ព្រមាន និងទប់ស្កាត់ជាបន្ទាន់ប្រសិនបើលេខថ្មីតូចជាងលេខចាស់ (សង្ស័យកុងទ័រថយក្រោយ ឬបញ្ចូលច្រឡំ)។
- **High Usage Spike**៖ ព្រមានភ្លាមៗប្រសិនបើការប្រើប្រាស់កើនឡើងលើសពី ២.៥ ដង (២៥០%) ធៀបនឹងមធ្យមភាគប្រវត្តិប្រើប្រាស់របស់កុងទ័រនោះ។
- **Zero Consumption**៖ កត់សម្គាល់ករណីកុងទ័រកំពុងដំណើរការ តែមានការប្រើប្រាស់ 0 kWh។

### គ. តារាងពន្ធុភាពគំរូ EDC (Tiered Tariffs)
- **លំនៅឋាន (Residential)**:
  - 0 – 10 kWh: **380 ៛/kWh**
  - 10 – 50 kWh: **480 ៛/kWh**
  - 50 – 200 kWh: **610 ៛/kWh**
  - លើសពី 200 kWh: **730 ៛/kWh**
- គាំទ្រផងដែរនូវតម្លៃសម្រាប់ **អាជីវកម្ម (Commercial)**, **កសិកម្ម (Agricultural)**, និង **ឧស្សាហកម្ម (Industrial)**។

### ឃ. រូបមន្តគណនាទឹកប្រាក់វិក្កយបត្រ (Invoice Formula)
$$\text{Total Amount} = \text{Energy Cost} + \text{Maintenance Fee} - \text{State Subsidy} + \text{Late Fee}$$

### ង. ការវិភាគថាមពលបាត់បង់តាមតំបន់ (Energy Loss Formula)
$$\text{Energy Loss (kWh)} = \text{Supplied Energy} - \text{Total Billed kWh}$$
$$\text{Loss \%} = \left(\frac{\text{Energy Loss}}{\text{Supplied Energy}}\right) \times 100\%$$

---

## ៤. របៀបដំណើរការប្រព័ន្ធ (How to Run)

### ក. ដំណើរការកម្មវិធីពេញលេញ (Interactive Menu)
```powershell
python main.py
```
អ្នកនឹងឃើញម៉ឺនុយភាសាខ្មែរសម្រាប់៖
1. បង្ហាញបញ្ជីអតិថិជន និងកុងទ័រ
2. ចុះឈ្មោះអតិថិជន និងកុងទ័រថ្មី
3. កត់ត្រាលេខកុងទ័រប្រចាំខែ និងត្រួតពិនិត្យ Alert
4. ចេញវិក្កយបត្រ និងបោះពុម្ពវិក្កយបត្រជាទម្រង់បង្កាន់ដៃស្អាត
5. ទទួលការទូទាត់ប្រាក់ (Cash / KHQR / Bank Transfer)
6. តាមដានវិក្កយបត្រជំពាក់ & បំណុលយឺតយ៉ាវ
7. មើលតារាងតម្លៃពន្ធុភាព
8. របាយការណ៍ចំណូលប្រចាំខែ និងថាមពលបាត់បង់

### ខ. ដំណើរការ Demo Mode ដោយស្វ័យប្រវត្តិ
```powershell
python main.py --demo
```

### គ. ដំណើរការ Automated Unit Tests
```powershell
python test_system.py
```
