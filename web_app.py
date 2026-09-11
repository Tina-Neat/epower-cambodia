"""
web_app.py - FastAPI Web Application for Electricity Consumption & Billing Management System
"""

import os
import io
import base64
import socket
from datetime import date
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, Request, Form, Query
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import qrcode

from database import init_db, get_connection, DB_FILE
import auth_service
from tariffs import seed_default_tariffs, get_tariffs_by_customer_type, calculate_tiered_cost
import meter_service
import billing_service
import payment_service
import report_service
from main import seed_demo_data

app = FastAPI(title="E-Power Cambodia - Electricity Management System (Online & Offline)")

def get_local_ip() -> str:
    """Detects local LAN/WiFi IP address for network devices."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

# Mount Static Files, Image Directory and Templates
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
STATIC_IMG_DIR = os.path.join(STATIC_DIR, "img")
IMG_DIR = os.path.join(BASE_DIR, "img")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(STATIC_IMG_DIR, exist_ok=True)
os.makedirs(IMG_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Synchronize logos between img and static/img
import shutil
for _d1, _d2 in [(STATIC_IMG_DIR, IMG_DIR), (IMG_DIR, STATIC_IMG_DIR)]:
    if os.path.exists(_d1):
        for _f in os.listdir(_d1):
            _s = os.path.join(_d1, _f)
            _t = os.path.join(_d2, _f)
            if os.path.isfile(_s) and not os.path.exists(_t):
                try:
                    shutil.copy2(_s, _t)
                except Exception:
                    pass

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/img", StaticFiles(directory=IMG_DIR), name="img")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Automatic Context Injector for all Templates
_orig_template_response = templates.TemplateResponse

def _safe_template_response(request: Request, name: str, context: Optional[dict] = None, *args, **kwargs):
    ctx = context.copy() if context is not None else {}
    if "current_user" not in ctx and request:
        ctx["current_user"] = getattr(request.state, "current_user", None)
    if "pending_users_count" not in ctx:
        u = ctx.get("current_user")
        ctx["pending_users_count"] = auth_service.get_pending_users_count() if (u and u.get("role") == "Admin") else 0
    return _orig_template_response(request, name, ctx, *args, **kwargs)

templates.TemplateResponse = _safe_template_response

# --------------------------------------------------------------------------
# Authentication Middleware (Offline & Online Login Wall)
# --------------------------------------------------------------------------
@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path

    # Publicly accessible routes
    public_paths = {"/login", "/register", "/favicon.ico"}
    if (
        path in public_paths
        or path.startswith("/static/")
        or path.startswith("/img/")
        or path.endswith(".png")
        or path.endswith(".ico")
        or path.endswith(".json")
    ):
        return await call_next(request)

    # Check session
    session_id = request.cookies.get("epower_session")
    current_user = auth_service.get_user_by_session(session_id)

    if not current_user:
        if path.startswith("/api/"):
            return JSONResponse({"error": "Unauthorized", "message": "សូមចូលប្រើប្រព័ន្ធជាមុនសិន"}, status_code=401)
        return RedirectResponse(url="/login", status_code=303)

    request.state.current_user = current_user
    response = await call_next(request)
    return response


@app.get("/favicon.ico", include_in_schema=False)
async def get_favicon():
    fav_path = os.path.join(STATIC_DIR, "icons", "favicon.png")
    if os.path.exists(fav_path):
        return FileResponse(fav_path, media_type="image/png")
    return FileResponse(os.path.join(IMG_DIR, "E-power-logo.png"), media_type="image/png")


@app.get("/img/E-power-logo.png", include_in_schema=False)
@app.get("/static/img/E-power-logo.png", include_in_schema=False)
async def get_epower_logo():
    """Guarantees official E-Power logo is returned regardless of route or mount."""
    candidates = [
        os.path.join(STATIC_IMG_DIR, "E-power-logo.png"),
        os.path.join(IMG_DIR, "E-power-logo.png"),
        os.path.join(STATIC_DIR, "E-power-logo.png"),
        os.path.join(STATIC_IMG_DIR, "E-power-logo-clean.png"),
        os.path.join(IMG_DIR, "E-power-logo-clean.png"),
    ]
    for c in candidates:
        if os.path.isfile(c):
            return FileResponse(c, media_type="image/png")
    return HTMLResponse("Logo not found", status_code=404)


@app.get("/img/{filename:path}", include_in_schema=False)
async def get_img_file(filename: str):
    """Fallback handler for any file requested under /img/."""
    candidates = [
        os.path.join(IMG_DIR, filename),
        os.path.join(STATIC_IMG_DIR, filename),
        os.path.join(STATIC_DIR, filename),
    ]
    for c in candidates:
        if os.path.isfile(c):
            media_type = "image/png" if c.endswith(".png") else None
            return FileResponse(c, media_type=media_type)
    return HTMLResponse("Image not found", status_code=404)



def generate_qr_base64(data: str) -> str:
    """Generates a base64 encoded PNG QR code image."""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=6,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0f172a", back_color="#ffffff")
    
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
    return f"data:image/png;base64,{img_str}"

@app.on_event("startup")
def on_startup():
    """Ensures database, permanent admin and demo data are initialized on startup."""
    init_db()
    auth_service.ensure_permanent_admin()
    seed_demo_data()

# --------------------------------------------------------------------------
# Auth & User Routes
# --------------------------------------------------------------------------
@app.get("/login", response_class=HTMLResponse)
async def login_page(
    request: Request,
    msg: Optional[str] = None,
    msg_type: Optional[str] = "info",
    tab: Optional[str] = "login"
):
    session_id = request.cookies.get("epower_session")
    if session_id:
        user = auth_service.get_user_by_session(session_id)
        if user:
            return RedirectResponse(url="/", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"msg": msg, "msg_type": msg_type, "active_tab": tab}
    )

@app.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    remember_me: Optional[str] = Form(None)
):
    ok, msg, user = auth_service.authenticate_user(username, password)
    if not ok:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"msg": msg, "msg_type": "error", "active_tab": "login"}
        )

    days = 30 if remember_me else 7
    session_id = auth_service.create_session(user["user_id"], days=days)
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key="epower_session",
        value=session_id,
        max_age=days * 86400,
        httponly=True,
        samesite="lax"
    )
    return response

@app.post("/register")
async def register_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    confirm_password: str = Form(...),
    full_name: str = Form(...),
    phone: Optional[str] = Form(None),
    role: str = Form("Staff")
):
    if password != confirm_password:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={
                "msg": "ពាក្យសម្ងាត់ទាំងពីរមិនត្រូវគ្នាឡើយ! សូមពិនិត្យឡើងវិញ។",
                "msg_type": "error",
                "active_tab": "register"
            }
        )

    ok, msg, user_id = auth_service.register_user(
        username=username,
        password=password,
        full_name=full_name,
        phone=phone,
        role=role
    )

    if not ok:
        return templates.TemplateResponse(
            request=request,
            name="login.html",
            context={"msg": msg, "msg_type": "error", "active_tab": "register"}
        )

    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={"msg": msg, "msg_type": "success", "active_tab": "login"}
    )

@app.get("/logout")
async def logout(request: Request):
    session_id = request.cookies.get("epower_session")
    if session_id:
        auth_service.destroy_session(session_id)
    response = RedirectResponse(url="/login?msg=បានចាកចេញពីប្រព័ន្ធដោយជោគជ័យ&msg_type=info", status_code=303)
    response.delete_cookie("epower_session")
    return response

@app.get("/users", response_class=HTMLResponse)
async def list_users(
    request: Request,
    msg: Optional[str] = None,
    msg_type: Optional[str] = "info"
):
    current_user = getattr(request.state, "current_user", None)
    if not current_user or current_user.get("role") != "Admin":
        return RedirectResponse(url="/?msg=អ្នកមិនមានសិទ្ធិចូលទំព័រគ្រប់គ្រងអ្នកប្រើឡើយ!&msg_type=danger", status_code=303)

    pending_users = auth_service.get_pending_users()
    all_users = auth_service.list_all_users()
    return templates.TemplateResponse(
        request=request,
        name="users.html",
        context={
            "active_page": "users",
            "pending_users": pending_users,
            "all_users": all_users,
            "msg": msg,
            "msg_type": msg_type
        }
    )

@app.post("/users/{user_id}/approve")
async def approve_user_route(
    request: Request,
    user_id: int,
    assigned_role: Optional[str] = Form(None)
):
    current_user = getattr(request.state, "current_user", None)
    if not current_user or current_user.get("role") != "Admin":
        return RedirectResponse(url="/?msg=គ្មានសិទ្ធិអនុម័តឡើយ!&msg_type=danger", status_code=303)

    ok, msg = auth_service.approve_user(
        user_id=user_id,
        admin_name=current_user.get("username", "admin"),
        assigned_role=assigned_role
    )
    return RedirectResponse(url=f"/users?msg={msg}&msg_type={'success' if ok else 'danger'}", status_code=303)

@app.post("/users/{user_id}/reject")
async def reject_user_route(
    request: Request,
    user_id: int
):
    current_user = getattr(request.state, "current_user", None)
    if not current_user or current_user.get("role") != "Admin":
        return RedirectResponse(url="/?msg=គ្មានសិទ្ធិបដិសេធឡើយ!&msg_type=danger", status_code=303)

    ok, msg = auth_service.reject_user(
        user_id=user_id,
        admin_name=current_user.get("username", "admin")
    )
    return RedirectResponse(url=f"/users?msg={msg}&msg_type={'warning' if ok else 'danger'}", status_code=303)

@app.post("/users/{user_id}/delete")
async def delete_user_route(
    request: Request,
    user_id: int
):
    current_user = getattr(request.state, "current_user", None)
    if not current_user or current_user.get("role") != "Admin":
        return RedirectResponse(url="/?msg=គ្មានសិទ្ធិលុបឡើយ!&msg_type=danger", status_code=303)

    ok, msg = auth_service.delete_user(user_id=user_id)
    return RedirectResponse(url=f"/users?msg={msg}&msg_type={'info' if ok else 'danger'}", status_code=303)

# --------------------------------------------------------------------------
# 1. Dashboard
# --------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, msg: Optional[str] = None, msg_type: Optional[str] = "info"):
    billing_service.update_overdue_invoices()
    conn = get_connection()
    cursor = conn.cursor()

    # Aggregate Statistics
    cursor.execute("SELECT COALESCE(SUM(total_amount), 0) as total_billed, COUNT(*) as total_invoices FROM Invoices")
    inv_stat = cursor.fetchone()

    cursor.execute("SELECT COALESCE(SUM(amount_paid), 0) as total_collected FROM Payments")
    pay_stat = cursor.fetchone()

    cursor.execute("SELECT COALESCE(SUM(total_kwh), 0) as total_kwh FROM Meter_Readings")
    kwh_stat = cursor.fetchone()

    cursor.execute("SELECT COUNT(*) as active_meters FROM Meters WHERE status = 'Active'")
    meter_stat = cursor.fetchone()

    debt_summary = report_service.get_outstanding_debt_summary(conn)
    revenue_by_type = report_service.get_revenue_by_customer_type(conn)

    # Recent Invoices
    cursor.execute("""
        SELECT i.invoice_id, i.total_amount, i.due_date, i.status, i.issue_date,
               r.total_kwh, m.meter_number, c.name as customer_name
        FROM Invoices i
        JOIN Meter_Readings r ON i.reading_id = r.reading_id
        JOIN Meters m ON r.meter_id = m.meter_id
        JOIN Customers c ON m.customer_id = c.customer_id
        ORDER BY i.invoice_id DESC
        LIMIT 6
    """)
    recent_invoices = [dict(r) for r in cursor.fetchall()]

    total_billed = inv_stat["total_billed"]
    total_collected = pay_stat["total_collected"]
    col_rate = round((total_collected / total_billed * 100), 1) if total_billed > 0 else 0.0
    active_m = meter_stat["active_meters"] or 1
    avg_kwh = round((kwh_stat["total_kwh"] / active_m), 1)

    stats = {
        "total_billed": total_billed,
        "total_invoices": inv_stat["total_invoices"],
        "total_collected": total_collected,
        "collection_rate": col_rate,
        "net_debt": debt_summary["net_outstanding_debt"],
        "debtor_count": debt_summary["debtor_count"],
        "total_kwh": kwh_stat["total_kwh"],
        "avg_kwh_per_meter": avg_kwh
    }

    local_ip = get_local_ip()
    host_header = request.headers.get("host", f"{local_ip}:8000")
    proto = request.headers.get("x-forwarded-proto", "https" if "https" in str(request.url) else "http")
    is_cloud = not any(h in host_header for h in ["localhost", "127.0.0.1", local_ip])

    conn.close()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={
            "request": request,
            "active_page": "dashboard",
            "stats": stats,
            "recent_invoices": recent_invoices,
            "revenue_by_type": revenue_by_type,
            "local_ip": local_ip,
            "host_header": host_header,
            "proto": proto,
            "is_cloud": is_cloud,
            "msg": msg,
            "msg_type": msg_type
        }
    )

# --------------------------------------------------------------------------
# 2. Customers & Meters
# --------------------------------------------------------------------------
@app.get("/customers", response_class=HTMLResponse)
async def customers_page(request: Request, msg: Optional[str] = None, msg_type: Optional[str] = "info"):
    conn = get_connection()
    customers_raw = meter_service.list_customers(conn)
    customers = []
    for c in customers_raw:
        meters = meter_service.get_meters_by_customer(c["customer_id"], conn)
        c["meters"] = meters
        customers.append(c)
    next_code = meter_service.get_next_customer_code(conn)
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="customers.html",
        context={
            "request": request,
            "active_page": "customers",
            "customers": customers,
            "next_code": next_code,
            "msg": msg,
            "msg_type": msg_type
        }
    )

@app.post("/customers/add")
async def add_customer(
    # Personal & Identity Info
    customer_code: Optional[str] = Form(None),
    honorific: Optional[str] = Form(None),
    last_name: Optional[str] = Form(None),
    first_name: Optional[str] = Form(None),
    last_name_en: Optional[str] = Form(None),
    first_name_en: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    has_dob: Optional[str] = Form(None),
    dob: Optional[str] = Form(None),
    pob: Optional[str] = Form(None),
    gender: Optional[str] = Form("ប្រុស"),
    id_type: Optional[str] = Form("អត្តសញ្ញាណប័ណ្ណ"),
    id_number: Optional[str] = Form(None),
    occupation: Optional[str] = Form(None),
    family_count: Optional[int] = Form(1),
    customer_type: Optional[str] = Form("Residential"),
    customer_category: Optional[str] = Form("បុគ្គលមិនជាប់អាករ"),
    is_poor_family: Optional[str] = Form(None),
    representative: Optional[str] = Form(None),
    photo_url: Optional[str] = Form(None),
    # Contact & Address Info
    phone: Optional[str] = Form(""),
    account_number: Optional[str] = Form(None),
    province: Optional[str] = Form("កណ្តាល"),
    district: Optional[str] = Form("មុខកំពូល"),
    commune: Optional[str] = Form("ឫស្សីជ្រោយ"),
    village: Optional[str] = Form("ឫស្សីជ្រោយ"),
    area: Optional[str] = Form("ឫស្សីជ្រោយ"),
    house_no: Optional[str] = Form(None),
    street_no: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    # Meter Info from Tab 2
    meter_number: Optional[str] = Form(None),
    location_code: Optional[str] = Form(None),
    meter_size: Optional[str] = Form("15mm"),
    phase: Optional[str] = Form("1 Phase 220V"),
    installation_date: Optional[str] = Form(None),
    initial_reading: Optional[float] = Form(0.0),
    meter_notes: Optional[str] = Form(None)
):
    try:
        conn = get_connection()
        # Compute display name
        full_name = (name or "").strip()
        if not full_name:
            full_name = f"{last_name or ''} {first_name or ''}".strip() or "អតិថិជនថ្មី"
        
        # Compute display address
        full_address = (address or "").strip()
        if not full_address:
            addr_parts = []
            if house_no and house_no.strip(): addr_parts.append(f"ផ្ទះលេខ {house_no.strip()}")
            if street_no and street_no.strip(): addr_parts.append(f"ផ្លូវ {street_no.strip()}")
            if village and village.strip(): addr_parts.append(f"ភូមិ{village.strip()}")
            if commune and commune.strip(): addr_parts.append(f"ឃុំ{commune.strip()}")
            if district and district.strip(): addr_parts.append(f"ស្រុក{district.strip()}")
            if province and province.strip(): addr_parts.append(f"ខេត្ត{province.strip()}")
            full_address = " ".join(addr_parts) if addr_parts else "ភូមិឫស្សីជ្រោយ ឃុំឫស្សីជ្រោយ ស្រុកមុខកំពូល ខេត្តកណ្តាល"
        
        # Map customer_type for billing/tariff compatibility
        ctype = customer_type or "Residential"
        if customer_category == "អាជីវកម្ម" or ctype == "Commercial":
            ctype = "Commercial"
        elif customer_category == "កសិកម្ម" or ctype == "Agricultural":
            ctype = "Agricultural"
        elif customer_category == "ឧស្សាហកម្ម" or ctype == "Industrial":
            ctype = "Industrial"
        else:
            ctype = "Residential"
            
        poor_val = 1 if (is_poor_family in ("1", "on", "true", True)) else 0
        actual_dob = dob if (has_dob or dob) else None

        cid = meter_service.add_customer(
            name=full_name,
            phone=(phone or "").strip(),
            address=full_address,
            customer_type=ctype,
            customer_code=customer_code,
            honorific=honorific,
            last_name=last_name,
            first_name=first_name,
            last_name_en=last_name_en,
            first_name_en=first_name_en,
            dob=actual_dob,
            pob=pob,
            gender=gender,
            id_type=id_type,
            id_number=id_number,
            occupation=occupation,
            family_count=family_count or 1,
            customer_category=customer_category,
            is_poor_family=poor_val,
            representative=representative,
            account_number=account_number,
            province=province,
            district=district,
            commune=commune,
            village=village,
            area=area,
            house_no=house_no,
            street_no=street_no,
            photo_url=photo_url,
            conn=conn
        )
        
        if meter_number and meter_number.strip():
            meter_service.add_meter(
                meter_number=meter_number.strip(),
                customer_id=cid,
                status="Active",
                installation_date=installation_date,
                location_code=location_code,
                meter_size=meter_size or "15mm",
                phase=phase or "1 Phase 220V",
                initial_reading=initial_reading or 0.0,
                notes=meter_notes,
                conn=conn
            )
            
        conn.close()
        return RedirectResponse(
            url=f"/customers?msg=បានចុះឈ្មោះអតិថិជន {full_name} ជោគជ័យ!&msg_type=success",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/customers?msg=កំហុស៖ {str(e)}&msg_type=danger",
            status_code=303
        )

@app.post("/meters/add")
async def add_meter(customer_id: int = Form(...), meter_number: str = Form(...)):
    try:
        meter_service.add_meter(meter_number.strip(), customer_id)
        return RedirectResponse(
            url=f"/customers?msg=បានភ្ជាប់កុងទ័រ {meter_number} ជោគជ័យ!&msg_type=success",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/customers?msg=កំហុស៖ {str(e)}&msg_type=danger",
            status_code=303
        )

# --------------------------------------------------------------------------
# 3. Meter Readings & Usage
# --------------------------------------------------------------------------
@app.get("/readings", response_class=HTMLResponse)
async def readings_page(request: Request, msg: Optional[str] = None, msg_type: Optional[str] = "info"):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT m.meter_id, m.meter_number, c.name as customer_name, c.customer_type,
               COALESCE((SELECT current_reading FROM Meter_Readings WHERE meter_id = m.meter_id ORDER BY reading_date DESC, reading_id DESC LIMIT 1), 0.0) as latest_reading
        FROM Meters m
        JOIN Customers c ON m.customer_id = c.customer_id
        WHERE m.status = 'Active'
    """)
    meters = [dict(r) for r in cursor.fetchall()]

    cursor.execute("""
        SELECT r.*, m.meter_number, c.name as customer_name
        FROM Meter_Readings r
        JOIN Meters m ON r.meter_id = m.meter_id
        JOIN Customers c ON m.customer_id = c.customer_id
        ORDER BY r.reading_date DESC, r.reading_id DESC
        LIMIT 20
    """)
    readings = [dict(r) for r in cursor.fetchall()]

    conn.close()
    return templates.TemplateResponse(
        request=request,
        name="meter_readings.html",
        context={
            "request": request,
            "active_page": "readings",
            "meters": meters,
            "readings": readings,
            "today": date.today().isoformat(),
            "current_month": date.today().strftime("%Y-%m"),
            "msg": msg,
            "msg_type": msg_type
        }
    )

@app.post("/readings/record")
async def record_reading(
    meter_id: int = Form(...),
    current_reading: float = Form(...),
    previous_reading: float = Form(0.0),
    reading_date: Optional[str] = Form(None),
    billing_month: Optional[str] = Form(None),
    pricing_policy: Optional[str] = Form("tiered"),
    flat_rate: Optional[float] = Form(800.0),
    tier1_rate: Optional[float] = Form(400.0),
    tier2_rate: Optional[float] = Form(600.0),
    auto_generate_invoice: bool = Form(True)
):
    try:
        conn = get_connection()
        actual_date = reading_date
        if not actual_date:
            if billing_month:
                actual_date = f"{billing_month}-15"
            else:
                actual_date = date.today().isoformat()

        record = meter_service.record_meter_reading(
            meter_id=meter_id,
            current_reading=current_reading,
            previous_reading=previous_reading,
            reading_date=actual_date,
            conn=conn
        )
        if billing_month:
            conn.execute("UPDATE Meter_Readings SET billing_month = ? WHERE reading_id = ?", (billing_month, record["reading_id"]))
            conn.commit()

        inv_msg = ""
        if auto_generate_invoice:
            inv = billing_service.generate_invoice(
                reading_id=record["reading_id"],
                maintenance_fee=0.0,
                pricing_policy=pricing_policy or "tiered",
                flat_rate=flat_rate or 800.0,
                tier1_rate=tier1_rate or 400.0,
                tier2_rate=tier2_rate or 600.0,
                conn=conn
            )
            inv_msg = f" និងបានចេញវិក្កយបត្រ INV-{inv['invoice_id']:05d} ({inv['total_amount']:,.0f} ៛)"

        conn.close()
        alert_text = f" (ព្រមាន៖ {record['alert_notes']})" if record["alert_notes"] else ""
        return RedirectResponse(
            url=f"/readings?msg=បានកត់ត្រាការប្រើប្រាស់ {record['total_kwh']:.2f} kWh ជោគជ័យ{inv_msg}!{alert_text}&msg_type=success",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/readings?msg=កំហុសក្នុងការកត់ត្រា៖ {str(e)}&msg_type=danger",
            status_code=303
        )

# --------------------------------------------------------------------------
# 4. Invoices & Billing
# --------------------------------------------------------------------------
@app.get("/invoices", response_class=HTMLResponse)
async def invoices_page(request: Request, msg: Optional[str] = None, msg_type: Optional[str] = "info"):
    billing_service.update_overdue_invoices()
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT i.*, r.total_kwh, m.meter_number, c.name as customer_name, c.phone as customer_phone
        FROM Invoices i
        JOIN Meter_Readings r ON i.reading_id = r.reading_id
        JOIN Meters m ON r.meter_id = m.meter_id
        JOIN Customers c ON m.customer_id = c.customer_id
        ORDER BY i.invoice_id DESC
    """)
    invoices = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="invoices.html",
        context={
            "request": request,
            "active_page": "invoices",
            "invoices": invoices,
            "msg": msg,
            "msg_type": msg_type
        }
    )

@app.get("/invoices/{invoice_id}", response_class=HTMLResponse)
async def invoice_view(invoice_id: int, request: Request, msg: Optional[str] = None, msg_type: Optional[str] = "info"):
    conn = get_connection()
    billing_service.update_overdue_invoices(conn=conn)
    inv = billing_service.get_invoice_details(invoice_id, conn)
    conn.close()

    if not inv:
        return RedirectResponse(url="/invoices?msg=រកមិនឃើញវិក្កយបត្រ&msg_type=danger", status_code=303)

    # KHQR generation string
    khqr_raw = f"00020101021229370016cambodia.epower540{inv['total_amount']:.0f}53031165802KH5911E-Power KH6010Phnom Penh62210717INV-{inv['invoice_id']:06d}6304"
    qr_code_url = generate_qr_base64(khqr_raw)

    return templates.TemplateResponse(
        request=request,
        name="invoice_view.html",
        context={
            "request": request,
            "active_page": "invoices",
            "inv": inv,
            "qr_code_url": qr_code_url,
            "current_date": date.today().isoformat(),
            "msg": msg,
            "msg_type": msg_type
        }
    )

@app.post("/invoices/{invoice_id}/mark-overdue")
async def invoice_mark_overdue(invoice_id: int):
    try:
        inv = billing_service.mark_invoice_overdue(invoice_id)
        return RedirectResponse(
            url=f"/invoices/{invoice_id}?msg=បានកំណត់វិក្កយបត្រជា 'ហួសកំណត់' និងគណនាប្រាក់ពិន័យ 5% (+{inv['late_fee']:,.0f} ៛) រួចរាល់!&msg_type=danger",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(url=f"/invoices/{invoice_id}?msg=កំហុស៖ {str(e)}&msg_type=danger", status_code=303)

@app.post("/invoices/{invoice_id}/mark-paid")
async def invoice_mark_paid(invoice_id: int):
    try:
        billing_service.mark_invoice_paid(invoice_id, payment_method="Cash")
        return RedirectResponse(
            url=f"/invoices/{invoice_id}?msg=បានបោះត្រា 'បង់រួច' និងកត់ត្រាការទូទាត់ជោគជ័យ!&msg_type=success",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(url=f"/invoices/{invoice_id}?msg=កំហុស៖ {str(e)}&msg_type=danger", status_code=303)

@app.post("/invoices/{invoice_id}/mark-unpaid")
async def invoice_mark_unpaid(invoice_id: int):
    try:
        billing_service.mark_invoice_unpaid(invoice_id)
        return RedirectResponse(
            url=f"/invoices/{invoice_id}?msg=បានកំណត់ឡើងវិញជា 'មិនទាន់បង់' និងលុបប្រាក់ពិន័យរួចរាល់!&msg_type=info",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(url=f"/invoices/{invoice_id}?msg=កំហុស៖ {str(e)}&msg_type=danger", status_code=303)

# --------------------------------------------------------------------------
# 5. Payments & Debt
# --------------------------------------------------------------------------
@app.get("/payments", response_class=HTMLResponse)
async def payments_page(
    request: Request,
    invoice_id: Optional[int] = None,
    msg: Optional[str] = None,
    msg_type: Optional[str] = "info"
):
    conn = get_connection()
    unpaid = payment_service.get_unpaid_invoices(conn)

    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, i.invoice_id, c.name as customer_name
        FROM Payments p
        JOIN Invoices i ON p.invoice_id = i.invoice_id
        JOIN Meter_Readings r ON i.reading_id = r.reading_id
        JOIN Meters m ON r.meter_id = m.meter_id
        JOIN Customers c ON m.customer_id = c.customer_id
        ORDER BY p.payment_id DESC
        LIMIT 25
    """)
    payments = [dict(r) for r in cursor.fetchall()]
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="payments.html",
        context={
            "request": request,
            "active_page": "payments",
            "unpaid_invoices": unpaid,
            "payments": payments,
            "selected_invoice_id": invoice_id,
            "msg": msg,
            "msg_type": msg_type
        }
    )

@app.post("/payments/process")
async def process_payment(
    invoice_id: int = Form(...),
    amount_paid: float = Form(...),
    payment_method: str = Form("KHQR"),
    notes: Optional[str] = Form(None)
):
    try:
        res = payment_service.record_payment(
            invoice_id=invoice_id,
            amount_paid=amount_paid,
            payment_method=payment_method,
            notes=notes
        )
        return RedirectResponse(
            url=f"/payments?msg=បានទទួលការបង់ប្រាក់ {res['amount_paid']:,.0f} ៛ តាម {payment_method} ជោគជ័យ! (ស្ថានភាពថ្មី: {res['new_invoice_status']})&msg_type=success",
            status_code=303
        )
    except Exception as e:
        return RedirectResponse(
            url=f"/payments?msg=កំហុសក្នុងការទូទាត់៖ {str(e)}&msg_type=danger",
            status_code=303
        )

# --------------------------------------------------------------------------
# 6. Reports & Energy Loss
# --------------------------------------------------------------------------
@app.get("/reports", response_class=HTMLResponse)
async def reports_page(request: Request, supplied_kwh: float = Query(3500.0)):
    billing_service.update_overdue_invoices()
    conn = get_connection()
    monthly_rev = report_service.get_monthly_revenue_report(conn=conn)
    debtors = payment_service.get_unpaid_invoices(conn=conn)
    loss_data = report_service.calculate_area_energy_loss(supplied_kwh=supplied_kwh, conn=conn)
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="reports.html",
        context={
            "request": request,
            "active_page": "reports",
            "monthly_rev": monthly_rev,
            "debtors": debtors,
            "loss_data": loss_data
        }
    )

# --------------------------------------------------------------------------
# 7. Tiered Tariffs & Simulation API
# --------------------------------------------------------------------------
@app.get("/tariffs", response_class=HTMLResponse)
async def tariffs_page(request: Request):
    conn = get_connection()
    types = ["Residential", "Commercial", "Agricultural", "Industrial"]
    tariffs_by_type = {}
    for t in types:
        tariffs_by_type[t] = get_tariffs_by_customer_type(t, conn)
    conn.close()

    return templates.TemplateResponse(
        request=request,
        name="tariffs.html",
        context={
            "request": request,
            "active_page": "tariffs",
            "tariffs_by_type": tariffs_by_type
        }
    )

@app.get("/api/calculate")
async def calculate_api(customer_type: str = "Residential", kwh: float = 0.0):
    try:
        cost, breakdown = calculate_tiered_cost(customer_type, max(0.0, kwh))
        return JSONResponse({"customer_type": customer_type, "kwh": kwh, "total_cost": cost, "breakdown": breakdown})
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)

# --------------------------------------------------------------------------
# 8. Offline Database Backup & Bulk Sync Endpoints
# --------------------------------------------------------------------------
@app.get("/api/backup/download")
async def download_backup():
    """Provides direct download of SQLite database for offline backup."""
    if os.path.exists(DB_FILE):
        return FileResponse(
            path=DB_FILE,
            filename=f"epower_backup_{date.today().isoformat()}.db",
            media_type="application/x-sqlite3"
        )
    return JSONResponse({"error": "Database file not found"}, status_code=404)

@app.post("/api/readings/bulk_sync")
async def bulk_sync_readings(readings: List[Dict[str, Any]]):
    """Syncs readings collected in offline queue to SQLite database."""
    conn = get_connection()
    synced = 0
    errors = []

    for r in readings:
        try:
            rec = meter_service.record_meter_reading(
                meter_id=int(r["meter_id"]),
                current_reading=float(r["current_reading"]),
                previous_reading=float(r.get("previous_reading", 0)),
                reading_date=r.get("reading_date"),
                conn=conn
            )
            if r.get("auto_generate_invoice"):
                billing_service.generate_invoice(
                    reading_id=rec["reading_id"],
                    maintenance_fee=0.0,
                    pricing_policy=r.get("pricing_policy", "tiered"),
                    flat_rate=float(r.get("flat_rate", 800.0)),
                    tier1_rate=float(r.get("tier1_rate", 400.0)),
                    tier2_rate=float(r.get("tier2_rate", 600.0)),
                    conn=conn
                )
            synced += 1
        except Exception as e:
            errors.append({"meter_id": r.get("meter_id"), "error": str(e)})

    conn.close()
    return JSONResponse({"synced_count": synced, "errors": errors})

if __name__ == "__main__":
    import uvicorn
    # Support dynamic PORT and HOST from cloud environments (Render, Railway, Heroku, Docker)
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"[*] Starting E-Power Cambodia on http://{host}:{port}")
    uvicorn.run("web_app:app", host=host, port=port, reload=False)


