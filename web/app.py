"""
cengkeh-web — Flask app for the Cengkeh knowledge base chatbot.

Run locally (dev):
    source venv/bin/activate
    FLASK_DEBUG=1 python app.py
    # → http://localhost:5000
"""

import os
import sys
from contextlib import contextmanager
from pathlib import Path

import pymysql
from flask import Flask, render_template, jsonify, request, redirect, make_response, g

import re
from werkzeug.security import generate_password_hash, check_password_hash

import uuid
from datetime import datetime, timedelta
from functools import wraps
from flask import session, g

import os
import uuid
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta


# ---------------------------------------------------------------------------
# Upload config
# ---------------------------------------------------------------------------
UPLOAD_ROOT = os.path.join(os.path.dirname(__file__), "static", "uploads")
ALLOWED_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
MAX_PHOTO_SIZE_BYTES = 2 * 1024 * 1024   # 2 MB


def _save_uploaded_photo(file_storage, subfolder: str) -> str:
    """
    Save an uploaded file to static/uploads/<subfolder>/<uuid>.<ext>.
    Returns the path *relative to* /static/ (for use in <img src>).

    Raises ValueError on invalid input.
    """
    if not file_storage or not file_storage.filename:
        raise ValueError("File tidak ditemukan.")

    # Validate extension
    filename = secure_filename(file_storage.filename)
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext not in ALLOWED_PHOTO_EXTENSIONS:
        raise ValueError(
            f"Format file tidak didukung. Gunakan: "
            f"{', '.join(sorted(ALLOWED_PHOTO_EXTENSIONS))}."
        )

    # Ensure directory exists
    target_dir = os.path.join(UPLOAD_ROOT, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    # Generate a unique filename (so uploads never overwrite)
    unique_name = f"{uuid.uuid4().hex}{ext}"
    full_path = os.path.join(target_dir, unique_name)

    # Save
    file_storage.save(full_path)

    # Enforce max size *after* save (simplest)
    size = os.path.getsize(full_path)
    if size > MAX_PHOTO_SIZE_BYTES:
        os.remove(full_path)
        raise ValueError(
            f"Ukuran file maksimal {MAX_PHOTO_SIZE_BYTES // (1024*1024)} MB."
        )

    # Return path relative to /static/
    return f"uploads/{subfolder}/{unique_name}"


def _delete_uploaded_photo(rel_path: str):
    """
    Delete a photo from disk given its path relative to /static/.
    Silently ignores missing files.
    """
    if not rel_path:
        return
    # Only handle our uploads directory
    if not rel_path.startswith("uploads/"):
        return

    full_path = os.path.join(
        os.path.dirname(__file__), "static", rel_path
    )
    try:
        if os.path.isfile(full_path):
            os.remove(full_path)
    except OSError as e:
        # Log but don't crash — the DB is already updated
        print(f"⚠️  Could not delete photo {full_path}: {e}", file=sys.stderr)

# ---------------------------------------------------------------------------
# Session helpers
# ---------------------------------------------------------------------------
SESSION_COOKIE = "cengkeh_session"
SESSION_TTL_DAYS = 7        # sessions expire after 7 days


def create_session(user_id: int, ip: str, user_agent: str) -> str:
    """
    Create a new session for a user and return the session ID (UUID).
    """
    session_id = str(uuid.uuid4())
    expires_at = datetime.utcnow() + timedelta(days=SESSION_TTL_DAYS)

    with get_db() as cursor:
        cursor.execute(
            """
            INSERT INTO tb_session (id, user_id, expires_at, ip_address, user_agent)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (session_id, user_id, expires_at, ip, (user_agent or "")[:255]),
        )
        cursor.execute(
            "UPDATE tb_user SET last_login_at = NOW() WHERE id = %s",
            (user_id,),
        )

    return session_id


def get_session_user(session_id: str):
    """
    Look up the user for a given session ID.
    Returns a dict, or None if the session is invalid or expired.
    """
    if not session_id:
        return None

    with get_db() as cursor:
        cursor.execute(
            """
            SELECT u.id, u.nomor_telepon, u.nama, u.level, u.status,
                   s.id AS session_id, s.expires_at
            FROM tb_session s
            JOIN tb_user u ON u.id = s.user_id
            WHERE s.id = %s AND s.expires_at > NOW()
            """,
            (session_id,),
        )
        row = cursor.fetchone()

    if row is None:
        return None

    # Only active users
    if row["status"] != "active":
        return None

    return row


def delete_session(session_id: str):
    """Delete a session (logout)."""
    if not session_id:
        return
    with get_db() as cursor:
        cursor.execute("DELETE FROM tb_session WHERE id = %s", (session_id,))


def current_user():
    """
    Flask `g`-based helper. Returns the current user dict or None.
    Cached per-request.
    """
    if hasattr(g, "_current_user"):
        return g._current_user

    sid = request.cookies.get(SESSION_COOKIE)
    user = get_session_user(sid) if sid else None
    g._current_user = user
    return user


def login_required(f):
    """Decorator: route requires a logged-in user."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if current_user() is None:
            return jsonify({"error": "Login diperlukan."}), 401
        return f(*args, **kwargs)
    return wrapper


def admin_required(f):
    """Decorator: route requires an admin user."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return jsonify({"error": "Login diperlukan."}), 401
        if user["level"] != "admin":
            return jsonify({"error": "Hanya admin yang boleh mengakses."}), 403
        return f(*args, **kwargs)
    return wrapper



app = Flask(__name__)

# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
PHONE_RE = re.compile(r"^08\d{8,13}$")   # 08 + 8–13 digits (10–15 total)


def validate_phone(phone: str) -> str | None:
    """
    Return the normalized phone number, or None if invalid.
    Indonesian format: starts with 08, 10–15 digits total.
    """
    if not phone:
        return None
    phone = phone.strip().replace(" ", "").replace("-", "").replace("+62", "08")
    if not PHONE_RE.match(phone):
        return None
    return phone


def validate_password(password: str) -> str | None:
    """Return None if valid, or an error message if invalid."""
    if not password or len(password) < 8:
        return "Password minimal 8 karakter."
    if password.lower() in {"password", "12345678", "qwertyui"}:
        return "Password terlalu mudah ditebak."
    return None


def validate_name(name: str) -> str | None:
    """Return None if valid, or an error message."""
    if not name or len(name.strip()) < 2:
        return "Nama minimal 2 karakter."
    if len(name) > 100:
        return "Nama maksimal 100 karakter."
    return None

# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Tokenization
# ---------------------------------------------------------------------------
def tokenize(text: str, min_length: int = 3) -> list[str]:
    """
    Turn a raw user query into a list of clean tokens.

    Rules:
        - lowercase
        - split on whitespace
        - strip leading/trailing punctuation
        - drop tokens shorter than `min_length`
        - drop stopwords (from tb_stopwords)
        - deduplicate (preserve order)

    Example:
        "Bagaimana agar cengkeh dapat bertumbuh dengan baik"
        → ["cengkeh", "bertumbuh", "baik"]
    """
    tokens = []
    seen = set()

    for raw in text.lower().split():
        cleaned = raw.strip(".,!?;:()[]{}\"'")
        if len(cleaned) < min_length:
            continue
        if cleaned in STOPWORDS:
            continue
        if cleaned in seen:
            continue
        seen.add(cleaned)
        tokens.append(cleaned)

    return tokens

# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------
def _load_env():
    """Load the project's .env file from the parent directory.

    Real env vars take precedence — .env is only a fallback.
    """
    project_root = Path(__file__).resolve().parent.parent
    env_path = project_root / ".env"

    if not env_path.exists():
        print(f"⚠  No .env found at {env_path}", file=sys.stderr)
        return

    with env_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_env()


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("MYSQL_USER", "arham")
DB_PASS = os.getenv("DB_PASS") or os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE", "cengkeh_db")


# ---------------------------------------------------------------------------
# Database connection (context manager)
# ---------------------------------------------------------------------------
@contextmanager
def get_db():
    """Yield a cursor inside a managed transaction.

    Usage:
        with get_db() as cursor:
            cursor.execute(...)
            rows = cursor.fetchall()
    """
    if not DB_PASS:
        print("❌ No DB password found.", file=sys.stderr)
        print("   Set DB_PASS env var, or ensure MYSQL_PASSWORD is in .env", file=sys.stderr)
        sys.exit(1)

    conn = pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    try:
        with conn.cursor() as cursor:
            yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


STOPWORDS = set() 

def _load_stopwords():
    """Load stopwords from the DB into a module-level set."""
    global STOPWORDS
    try:
        with get_db() as cursor:
            cursor.execute("SELECT kata FROM tb_stopwords")
            STOPWORDS = {row["kata"].lower() for row in cursor.fetchall()}
        print(f"✅ Loaded {len(STOPWORDS)} stopwords")
    except Exception as e:
        print(f"⚠  Could not load stopwords: {e}", file=sys.stderr)
        print(f"   Continuing with empty stopword set", file=sys.stderr)
        STOPWORDS = set()

_load_stopwords()

# ---------------------------------------------------------------------------
# Error handlers
# ---------------------------------------------------------------------------
@app.errorhandler(404)
def not_found(e):
    if request.path.startswith("/api/"):
        return jsonify({"error": "not found", "path": request.path}), 404
    return e

# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Serve the chat UI."""
    return render_template("index.html")

# ---------------------------------------------------------------------------
# Page decorators (redirect instead of returning JSON errors)
# ---------------------------------------------------------------------------
def page_user_required(f):
    """
    Page decorator: requires login AND level='user'.
    Redirects:
      - to /login if not logged in
      - to /admin if logged in but level='admin'
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return redirect("/login")
        if user["level"] != "user":
            return redirect("/admin")
        return f(*args, **kwargs)
    return wrapper

def page_login_required(f):
    """
    Page decorator: redirects to /login if not logged in.
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper


def page_admin_required(f):
    """
    Page decorator: requires admin level. Redirects:
      - to /login if not logged in
      - to /user if logged in but not admin
    """
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = current_user()
        if user is None:
            return redirect("/login")
        if user["level"] != "admin":
            return redirect("/user")
        return f(*args, **kwargs)
    return wrapper

   
# ----------------------------------------------------------------------------
# Below are user-only routes. They require login AND level='user'.
# ----------------------------------------------------------------------------

@app.route("/user")
@page_user_required
def user_page():
    return render_template("user/index.html")


# create user_sewa_pemetik
@app.route("/user/sewa-pemetik")
@page_user_required
def user_sewa_pemetik():
    return render_template("user/sewa-pemetik.html")

@app.route("/user/booking/new")
@page_user_required
def user_booking_new():
    """Booking form page — creates an order with selected pemetik."""
    return render_template("user/booking-new.html")


@app.route("/api/user/pemetik")
@login_required
def api_user_pemetik_list():
    """
    List all ACTIVE pemetik + current daily price from tb_setting.
    For the user-facing browse page.
    """
    with get_db() as cursor:
        cursor.execute(
            """
            SELECT id, nama, deskripsi, foto_path
            FROM tb_pemetik
            WHERE is_active = 1
            ORDER BY nama ASC
            """
        )
        rows = cursor.fetchall()

        cursor.execute(
            "SELECT kunci, nilai FROM tb_setting "
            "WHERE kunci IN ('price_per_day', 'min_lead_days')"
        )
        settings = {r["kunci"]: int(r["nilai"]) for r in cursor.fetchall()}
        price_per_day = settings.get("price_per_day", 0)
        min_lead_days = settings.get("min_lead_days", 1)

    return jsonify({
        "status": "ok",
        "price_per_day": price_per_day,
        "min_lead_days": min_lead_days, 
        "pemetik": [
            {
                "id":        r["id"],
                "nama":      r["nama"],
                "deskripsi": r["deskripsi"] or "",
                "foto_path": r["foto_path"] or "",
            }
            for r in rows
        ],
    })


def _generate_order_code() -> str:
    """
    Generate a human-readable order code: ORD-YYYYMMDD-####
    The #### is sequential per day.
    """
    today = datetime.utcnow().strftime("%Y%m%d")
    prefix = f"ORD-{today}-"

    with get_db() as cursor:
        cursor.execute(
            """
            SELECT order_code FROM tb_order
            WHERE order_code LIKE %s
            ORDER BY order_code DESC
            LIMIT 1
            """,
            (prefix + "%",),
        )
        row = cursor.fetchone()

    if row:
        last_seq = int(row["order_code"].split("-")[-1])
        next_seq = last_seq + 1
    else:
        next_seq = 1

    return f"{prefix}{next_seq:04d}"


@app.route("/api/user/order", methods=["POST"])
@login_required
def api_user_order_create():
    """
    Create a new order (with N booking lines, one per selected pemetik).

    Request body (JSON):
        {
            "pemetik_ids": [1, 3, 7],
            "start_date": "2026-11-01",
            "end_date": "2026-11-05",
            "notes": "Optional notes"
        }

    Response:
        201 {
            "status": "ok",
            "order_id": N,
            "order_code": "ORD-20261015-0001",
            "total_amount": 1500000,
            "total_days": 5,
            "pemetik_count": 3,
        }
        400 { "error": "..." }
        404 { "error": "Pemetik X tidak ditemukan." }
    """
    user = current_user()
    data = request.get_json(silent=True) or {}

    pemetik_ids = data.get("pemetik_ids") or []
    start_date_str = (data.get("start_date") or "").strip()
    end_date_str = (data.get("end_date") or "").strip()
    notes = (data.get("notes") or "").strip() or None

    # -------------------------------------------------------------------
    # Validate pemetik_ids
    # -------------------------------------------------------------------
    if not isinstance(pemetik_ids, list) or len(pemetik_ids) == 0:
        return jsonify({"error": "Pilih minimal satu pemetik."}), 400

    # Deduplicate + force int
    try:
        pemetik_ids = list({int(x) for x in pemetik_ids})
    except (ValueError, TypeError):
        return jsonify({"error": "Format pemetik_ids tidak valid."}), 400

    # -------------------------------------------------------------------
    # Validate dates
    # -------------------------------------------------------------------
    try:
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date   = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({"error": "Format tanggal tidak valid (YYYY-MM-DD)."}), 400

    # Enforce minimum lead time
    with get_db() as cursor:
        cursor.execute("SELECT nilai FROM tb_setting WHERE kunci = 'min_lead_days'")
        row = cursor.fetchone()
        min_lead_days = int(row["nilai"]) if row else 1

    earliest_start = datetime.utcnow().date() + timedelta(days=min_lead_days)
    if start_date < earliest_start:
        return jsonify({
            "error": f"Tanggal mulai minimal {min_lead_days} hari dari sekarang "
                    f"(paling awal: {earliest_start.isoformat()})."
        }), 400


    total_days = (end_date - start_date).days + 1

    # Load min/max from settings
    with get_db() as cursor:
        cursor.execute(
            "SELECT kunci, nilai FROM tb_setting "
            "WHERE kunci IN ('min_booking_days', 'max_booking_days', 'price_per_day')"
        )
        settings = {r["kunci"]: int(r["nilai"]) for r in cursor.fetchall()}

    min_days = settings.get("min_booking_days", 1)
    max_days = settings.get("max_booking_days", 30)
    price_per_day = settings.get("price_per_day", 0)

    if total_days < min_days:
        return jsonify({"error": f"Minimum pemesanan {min_days} hari."}), 400
    if total_days > max_days:
        return jsonify({"error": f"Maksimum pemesanan {max_days} hari."}), 400

    # -------------------------------------------------------------------
    # Verify all pemetik exist and are active
    # -------------------------------------------------------------------
    with get_db() as cursor:
        placeholders = ",".join(["%s"] * len(pemetik_ids))
        cursor.execute(
            f"SELECT id FROM tb_pemetik WHERE id IN ({placeholders}) AND is_active = 1",
            pemetik_ids,
        )
        found_ids = {r["id"] for r in cursor.fetchall()}

    missing = set(pemetik_ids) - found_ids
    if missing:
        return jsonify({
            "error": f"Pemetik tidak ditemukan atau tidak aktif: {sorted(missing)}"
        }), 404

    # -------------------------------------------------------------------
    # Compute totals
    # -------------------------------------------------------------------
    subtotal_per_pemetik = total_days * price_per_day
    total_amount = subtotal_per_pemetik * len(pemetik_ids)

    # -------------------------------------------------------------------
    # Insert order + lines in a single transaction
    # -------------------------------------------------------------------
    try:
        with get_db() as cursor:
            order_code = _generate_order_code()

            cursor.execute(
                """
                INSERT INTO tb_order
                    (user_id, order_code, start_date, end_date, total_amount, status, notes)
                VALUES
                    (%s, %s, %s, %s, %s, 'pending_payment', %s)
                """,
                (user["id"], order_code, start_date, end_date, total_amount, notes),
            )
            order_id = cursor.lastrowid

            # Insert one line per pemetik
            for pid in pemetik_ids:
                cursor.execute(
                    """
                    INSERT INTO tb_booking_pemetik
                        (order_id, pemetik_id, price_per_day_at_booking, total_days, subtotal)
                    VALUES
                        (%s, %s, %s, %s, %s)
                    """,
                    (order_id, pid, price_per_day, total_days, subtotal_per_pemetik),
                )
    except Exception as e:
        # get_db() context manager rolls back automatically
        print(f"❌ Order creation failed: {e}", file=sys.stderr)
        return jsonify({"error": "Gagal membuat pesanan."}), 500

    return jsonify({
        "status": "ok",
        "order_id": order_id,
        "order_code": order_code,
        "total_amount": total_amount,
        "total_days": total_days,
        "pemetik_count": len(pemetik_ids),
        "message": f"Pesanan {order_code} berhasil dibuat. Menunggu pembayaran.",
    }), 201


@app.route("/api/user/current-order")
@login_required
def api_user_current_order():
    """
    Return the user's most relevant active order, if any.

    Priority:
        1. ongoing  — start_date <= today <= end_date, status paid/confirmed
        2. soon     — start_date > today, status paid/confirmed
        3. pending  — status pending_payment
        4. none

    Response:
        {
            "status": "ok",
            "state": "ongoing" | "soon" | "pending" | "none",
            "order": { ... } | null   (may include pemetik summary)
        }
    """
    user = current_user()

    with get_db() as cursor:
        # Ongoing first
        cursor.execute(
            """
            SELECT o.*, DATEDIFF(o.end_date, o.start_date) + 1 AS total_days
            FROM tb_order o
            WHERE o.user_id = %s
              AND o.status IN ('paid', 'confirmed')
              AND CURDATE() BETWEEN o.start_date AND o.end_date
            ORDER BY o.start_date ASC
            LIMIT 1
            """,
            (user["id"],),
        )
        order = cursor.fetchone()
        state = "ongoing" if order else None

        # Then soon
        if not order:
            cursor.execute(
                """
                SELECT o.*, DATEDIFF(o.end_date, o.start_date) + 1 AS total_days
                FROM tb_order o
                WHERE o.user_id = %s
                  AND o.status IN ('paid', 'confirmed')
                  AND o.start_date > CURDATE()
                ORDER BY o.start_date ASC
                LIMIT 1
                """,
                (user["id"],),
            )
            order = cursor.fetchone()
            if order:
                state = "soon"

        # Then pending payment
        if not order:
            cursor.execute(
                """
                SELECT o.*, DATEDIFF(o.end_date, o.start_date) + 1 AS total_days
                FROM tb_order o
                WHERE o.user_id = %s
                  AND o.status = 'pending_payment'
                ORDER BY o.created_at DESC
                LIMIT 1
                """,
                (user["id"],),
            )
            order = cursor.fetchone()
            if order:
                state = "pending"

    if not order:
        return jsonify({"status": "ok", "state": "none", "order": None})

    # Fetch the pemetik for this order (for a compact summary)
    with get_db() as cursor:
        cursor.execute(
            """
            SELECT p.id, p.nama, p.foto_path
            FROM tb_booking_pemetik bp
            JOIN tb_pemetik p ON p.id = bp.pemetik_id
            WHERE bp.order_id = %s
            ORDER BY p.nama ASC
            """,
            (order["id"],),
        )
        pemetik_rows = cursor.fetchall()

    return jsonify({
        "status": "ok",
        "state": state,
        "order": {
            "id":             order["id"],
            "order_code":     order["order_code"],
            "start_date":     order["start_date"].isoformat() if order["start_date"] else None,
            "end_date":       order["end_date"].isoformat() if order["end_date"] else None,
            "total_days":     order["total_days"],
            "total_amount":   float(order["total_amount"]),
            "status":         order["status"],
            "pemetik": [
                {
                    "id":        p["id"],
                    "nama":      p["nama"],
                    "foto_path": p["foto_path"] or "",
                }
                for p in pemetik_rows
            ],
        },
    })

# ----------------------------------------------------------------------------
# end of user-only routes
# ----------------------------------------------------------------------------


#  ----------------------------------------------------------------------------
# Below are admin-only routes. They require login AND level='admin'.
# ----------------------------------------------------------------------------
@app.route("/admin")
@page_admin_required
def admin_page():
    """ Admin page. Requires login AND level='admin'."""
    return render_template("admin/index.html", active_nav="dashboard")


# create a user_list route
@app.route("/user_list")
@page_admin_required
def user_list():
    """Admin page to list all users. Requires login AND level='admin'."""
    return render_template("admin/user-list.html", active_nav="user_list")


# create a pemetik_list route
@app.route("/pemetik_list")
@page_admin_required
def pemetik_list():
    """Admin page to list all pemetik. Requires login AND level='admin'."""
    return render_template("admin/pemetik.html", active_nav="pemetik_list")



# create a penyewaan_pemetik route
@app.route("/penyewaan_pemetik")
@page_admin_required
def penyewaan_pemetik():
    """Admin page to list all penyewaan pemetik. Requires login AND level='admin'."""
    return render_template("admin/penyewaan-pemetik.html" , active_nav="penyewaan_pemetik")


# ---------------------------------------------------------------------------
# Admin — penyewaan pemetik (booking orders)
# ---------------------------------------------------------------------------
def _serialize_order_row(row):
    """Shape a tb_order row (with joined user info) for the admin UI."""
    return {
        "id":             row["id"],
        "order_code":     row["order_code"],
        "user_id":        row["user_id"],
        "user_nama":      row.get("user_nama") or "",
        "user_telepon":   row.get("user_telepon") or "",
        "start_date":     row["start_date"].isoformat() if row["start_date"] else None,
        "end_date":       row["end_date"].isoformat() if row["end_date"] else None,
        "total_days":     row.get("total_days"),
        "total_amount":   float(row["total_amount"]) if row["total_amount"] is not None else 0,
        "status":         row["status"],
        "notes":          row.get("notes") or "",
        "cancel_reason":  row.get("cancel_reason") or "",
        "payment_reference": row.get("payment_reference") or "",
        "paid_at":        row["paid_at"].isoformat() if row.get("paid_at") else None,
        "created_at":     row["created_at"].isoformat() if row.get("created_at") else None,
        "updated_at":     row["updated_at"].isoformat() if row.get("updated_at") else None,
        "pemetik":        [],
    }


def _attach_pemetik_to_orders(cursor, orders):
    """Bulk-load the pemetik lines for a list of serialized orders."""
    if not orders:
        return orders

    order_ids = [o["id"] for o in orders]
    placeholders = ",".join(["%s"] * len(order_ids))
    cursor.execute(
        f"""
        SELECT bp.order_id, p.id, p.nama, p.foto_path,
               bp.price_per_day_at_booking, bp.total_days, bp.subtotal
        FROM tb_booking_pemetik bp
        JOIN tb_pemetik p ON p.id = bp.pemetik_id
        WHERE bp.order_id IN ({placeholders})
        ORDER BY p.nama ASC
        """,
        order_ids,
    )
    by_order = {}
    for r in cursor.fetchall():
        by_order.setdefault(r["order_id"], []).append({
            "id":            r["id"],
            "nama":          r["nama"],
            "foto_path":     r["foto_path"] or "",
            "price_per_day": float(r["price_per_day_at_booking"]),
            "total_days":    r["total_days"],
            "subtotal":      float(r["subtotal"]),
        })

    for o in orders:
        o["pemetik"] = by_order.get(o["id"], [])
    return orders


@app.route("/api/admin/penyewaan", methods=["GET"])
@admin_required
def api_admin_penyewaan_list():
    """
    List all booking orders for the admin panel.

    Query params (all optional):
        status — pending_payment | paid | confirmed | cancelled | completed
        q      — search on order_code / user nama / user telepon
    """
    status_filter = request.args.get("status")
    q = (request.args.get("q") or "").strip()

    where = []
    params = []

    if status_filter:
        where.append("o.status = %s")
        params.append(status_filter)

    if q:
        like = f"%{q}%"
        where.append(
            "(o.order_code LIKE %s OR u.nama LIKE %s OR u.nomor_telepon LIKE %s)"
        )
        params.extend([like, like, like])

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with get_db() as cursor:
        cursor.execute(
            f"""
            SELECT o.*,
                   DATEDIFF(o.end_date, o.start_date) + 1 AS total_days,
                   u.nama          AS user_nama,
                   u.nomor_telepon AS user_telepon
            FROM tb_order o
            JOIN tb_user u ON u.id = o.user_id
            {where_sql}
            ORDER BY
                FIELD(o.status, 'paid', 'pending_payment', 'confirmed', 'cancelled', 'completed'),
                o.created_at DESC
            """,
            params,
        )
        orders = [_serialize_order_row(r) for r in cursor.fetchall()]
        _attach_pemetik_to_orders(cursor, orders)

        cursor.execute("SELECT status, COUNT(*) AS cnt FROM tb_order GROUP BY status")
        counts = {r["status"]: r["cnt"] for r in cursor.fetchall()}
        counts["total"] = sum(counts.values())

    return jsonify({"status": "ok", "orders": orders, "counts": counts})


def _overlapping_confirmed_exists(cursor, pemetik_id, start_date, end_date,
                                  exclude_order_id=None):
    """
    Return True if any CONFIRMED order (other than exclude_order_id)
    for `pemetik_id` overlaps the [start_date, end_date] window.

    Overlap test: A.start <= B.end AND A.end >= B.start
    """
    sql = """
        SELECT o.id
        FROM tb_order o
        JOIN tb_booking_pemetik bp ON bp.order_id = o.id
        WHERE o.status = 'confirmed'
          AND bp.pemetik_id = %s
          AND o.start_date <= %s
          AND o.end_date   >= %s
    """
    params = [pemetik_id, end_date, start_date]

    if exclude_order_id is not None:
        sql += " AND o.id <> %s"
        params.append(exclude_order_id)

    sql += " LIMIT 1"
    cursor.execute(sql, params)
    return cursor.fetchone() is not None


def _overlapping_active_exists(cursor, pemetik_id, start_date, end_date, exclude_order_id=None):
    sql = """
        SELECT o.id FROM tb_order o 
        JOIN tb_booking_pemetik bp ON bp.order_id = o.id
        WHERE o.status IN ('confirmed', 'paid')
          AND bp.pemetik_id = %s 
          AND o.start_date <= %s 
          AND o.end_date >= %s
    """
    params = [pemetik_id, end_date, start_date]
    if exclude_order_id is not None:
        sql += " AND o.id <> %s"
        params.append(exclude_order_id)
    sql += " LIMIT 1"
    cursor.execute(sql, params)
    return cursor.fetchone() is not None


@app.route("/api/admin/penyewaan/<int:order_id>/mark-paid", methods=["POST"])
@admin_required
def api_admin_penyewaan_mark_paid(order_id):
    with get_db() as cursor:
        # 1. Check if the current order can be paid
        cursor.execute("SELECT id, order_code, status, start_date, end_date FROM tb_order WHERE id = %s", (order_id,))
        order = cursor.fetchone()
        if order is None: return jsonify({"error": f"Order {order_id} tidak ditemukan."}), 404
        if order["status"] != "pending_payment": return jsonify({"error": f"Hanya 'pending_payment' yang bisa jadi 'paid'."}), 400

        # 2. Check if THIS order is already blocked by someone else
        cursor.execute("SELECT pemetik_id FROM tb_booking_pemetik WHERE order_id = %s", (order_id,))
        pemetik_ids = [r["pemetik_id"] for r in cursor.fetchall()]

        for pid in pemetik_ids:
            if _overlapping_active_exists(cursor, pid, order["start_date"], order["end_date"], exclude_order_id=order_id):
                return jsonify({"error": "Gagal: Pemetik sudah dibayar/disewa oleh pengguna lain."}), 409

        # 3. Mark this order as PAID
        cursor.execute("UPDATE tb_order SET status='paid', paid_at=NOW() WHERE id = %s", (order_id,))

        # 4. Auto-cancel other PENDING orders that overlap, and list their conflicting pemetik names
        placeholders = ",".join(["%s"] * len(pemetik_ids))
        query_params = [order_id] + pemetik_ids + [order["end_date"], order["start_date"]]
        
        cursor.execute(
            f"""
            SELECT 
                o.id, 
                o.order_code, 
                GROUP_CONCAT(p.nama ORDER BY p.nama SEPARATOR ', ') AS pemetik_names
            FROM tb_order o 
            JOIN tb_booking_pemetik bp ON bp.order_id = o.id 
            JOIN tb_pemetik p ON p.id = bp.pemetik_id
            WHERE o.id <> %s 
              AND o.status = 'pending_payment' 
              AND bp.pemetik_id IN ({placeholders})
              AND o.start_date <= %s 
              AND o.end_date >= %s
            GROUP BY o.id, o.order_code
            """, 
            query_params
        )
        conflicting_pending = cursor.fetchall()

        if conflicting_pending:
            for conflict in conflicting_pending:
                # We now have the full list of pemetik names (e.g., "ARa1, aran2, aran3")
                p_names = conflict["pemetik_names"]
                reason = f"{p_names} sudah disewakan oleh pengguna lain."
                
                cursor.execute(
                    "UPDATE tb_order SET status='cancelled', cancel_reason = %s WHERE id = %s", 
                    (reason, conflict["id"])
                )

    return jsonify({
        "status": "ok", 
        "message": f"Order {order['order_code']} ditandai sudah dibayar. {len(conflicting_pending)} order bentrok otomatis dibatalkan."
    })


@app.route("/api/admin/penyewaan/<int:order_id>/approve", methods=["POST"])
@admin_required
def api_admin_penyewaan_approve(order_id):
    """
    Approve (confirm) a paid order.
    Auto-cancels overlapping pending/paid orders.
    """
    with get_db() as cursor:
        cursor.execute(
            "SELECT id, order_code, status, start_date, end_date "
            "FROM tb_order WHERE id = %s",
            (order_id,),
        )
        order = cursor.fetchone()
        if order is None:
            return jsonify({"error": f"Order {order_id} tidak ditemukan."}), 404

        if order["status"] != "paid":
            return jsonify({
                "error": f"Hanya order berstatus 'paid' yang bisa disetujui. "
                         f"Status sekarang: '{order['status']}'."
            }), 400

        cursor.execute(
            "SELECT pemetik_id FROM tb_booking_pemetik WHERE order_id = %s",
            (order_id,),
        )
        pemetik_ids = [r["pemetik_id"] for r in cursor.fetchall()]
        if not pemetik_ids:
            return jsonify({"error": "Order ini tidak punya pemetik."}), 400

        # Race-guard
        for pid in pemetik_ids:
            if _overlapping_confirmed_exists(
                cursor, pid, order["start_date"], order["end_date"],
                exclude_order_id=order_id,
            ):
                return jsonify({
                    "error": "Sudah ada order lain yang dikonfirmasi untuk "
                             "pemetik & tanggal ini. Tidak bisa disetujui."
                }), 409

        # 1. Confirm the current order
        cursor.execute(
            "UPDATE tb_order SET status='confirmed' WHERE id = %s",
            (order_id,),
        )

        # 2. Auto-cancel overlapping pending_payment / paid orders
        placeholders = ",".join(["%s"] * len(pemetik_ids))
        
        # We construct the params list carefully: order_id, then the pemetik_ids, then end_date, then start_date
        # (Because the WHERE clause goes in order of appearance)
        query_params = [order_id] + pemetik_ids + [order["end_date"], order["start_date"]]
        
        cursor.execute(
            f"""
            SELECT DISTINCT o.id, o.order_code, p.nama AS pemetik_nama
            FROM tb_order o
            JOIN tb_booking_pemetik bp ON bp.order_id = o.id
            JOIN tb_pemetik p ON p.id = bp.pemetik_id
            WHERE o.id <> %s
              AND o.status IN ('pending_payment', 'paid')
              AND bp.pemetik_id IN ({placeholders})
              AND o.start_date <= %s
              AND o.end_date   >= %s
            """,
            query_params,
        )
        conflicting = cursor.fetchall()

        cancelled = []
        if conflicting:
            conflict_ids = [c["id"] for c in conflicting]
            
            # Get the name of the pemetik causing the conflict
            pemetik_name = conflicting[0]["pemetik_nama"]
            reason = f"{pemetik_name} sudah disewakan oleh pengguna lain."
            
            id_ph = ",".join(["%s"] * len(conflict_ids))
            cursor.execute(
                f"""
                UPDATE tb_order
                SET status='cancelled', cancel_reason = %s
                WHERE id IN ({id_ph})
                """,
                [reason] + conflict_ids,
            )
            cancelled = [
                {"id": c["id"], "order_code": c["order_code"]}
                for c in conflicting
            ]

    msg = f"Order {order['order_code']} dikonfirmasi."
    if cancelled:
        msg += f" {len(cancelled)} order lain dibatalkan karena bentrok."

    return jsonify({
        "status": "ok",
        "message": msg,
        "cancelled": cancelled,
    })

@app.route("/api/admin/penyewaan/<int:order_id>/cancel", methods=["POST"])
@admin_required
def api_admin_penyewaan_cancel(order_id):
    """
    Manually cancel a booking order (admin action).

    Body (JSON, optional):
        { "reason": "..." }
    """
    data = request.get_json(silent=True) or {}
    reason = (data.get("reason") or "").strip() or "Dibatalkan oleh admin."

    with get_db() as cursor:
        cursor.execute(
            "SELECT id, order_code, status FROM tb_order WHERE id = %s",
            (order_id,),
        )
        order = cursor.fetchone()
        if order is None:
            return jsonify({"error": f"Order {order_id} tidak ditemukan."}), 404

        if order["status"] in ("cancelled", "completed"):
            return jsonify({
                "error": f"Order sudah '{order['status']}', tidak bisa dibatalkan."
            }), 400

        cursor.execute(
            "UPDATE tb_order SET status='cancelled', cancel_reason = %s WHERE id = %s",
            (reason, order_id),
        )

    return jsonify({
        "status": "ok",
        "message": f"Order {order['order_code']} dibatalkan.",
    })

@app.route("/api/admin/users")
@admin_required
def api_admin_users():
    """
    Return the full user list for the admin panel.

    Query params:
        status — optional filter: pending / active / rejected / suspended
        level  — optional filter: user / admin

    Response:
        {
            "status": "ok",
            "users": [
                { id, nomor_telepon, nama, level, status, created_at, last_login_at },
                ...
            ],
            "counts": {
                "pending":   N,
                "active":    N,
                "rejected":  N,
                "suspended": N,
                "total":     N,
            }
        }
    """
    status_filter = request.args.get("status")
    level_filter = request.args.get("level")

    # Build WHERE clause safely
    where = []
    params = []
    if status_filter:
        where.append("status = %s")
        params.append(status_filter)
    if level_filter:
        where.append("level = %s")
        params.append(level_filter)

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    with get_db() as cursor:
        # Fetch users
        cursor.execute(
            f"""
            SELECT id, nomor_telepon, nama, level, status,
                   created_at, updated_at, last_login_at
            FROM tb_user
            {where_sql}
            ORDER BY
                FIELD(status, 'pending', 'active', 'suspended', 'rejected'),
                created_at DESC
            """,
            params,
        )
        users = cursor.fetchall()

        # Counts per status (unfiltered — always the full picture)
        cursor.execute(
            """
            SELECT status, COUNT(*) AS cnt
            FROM tb_user
            GROUP BY status
            """
        )
        counts = {r["status"]: r["cnt"] for r in cursor.fetchall()}
        counts["total"] = sum(counts.values())

    return jsonify({
        "status": "ok",
        "users": [
            {
                "id":            u["id"],
                "nomor_telepon": u["nomor_telepon"],
                "nama":          u["nama"],
                "level":         u["level"],
                "status":        u["status"],
                "created_at":    u["created_at"].isoformat() if u["created_at"] else None,
                "updated_at":    u["updated_at"].isoformat() if u["updated_at"] else None,
                "last_login_at": u["last_login_at"].isoformat() if u["last_login_at"] else None,
            }
            for u in users
        ],
        "counts": counts,
    })

@app.route("/api/admin/approve/<int:user_id>", methods=["POST"])
@admin_required
def api_admin_approve(user_id):
    """
    Approve a user: set status='active'.

    Allowed source statuses:
        pending   → first-time approval
        rejected  → admin changed their mind
        suspended → reactivate
    """
    with get_db() as cursor:
        cursor.execute(
            "SELECT id, nama, status, level FROM tb_user WHERE id = %s",
            (user_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": f"User {user_id} tidak ditemukan."}), 404

        if row["status"] == "active":
            return jsonify({
                "status": "ok",
                "message": f"{row['nama']} sudah aktif.",
            })

        if row["status"] not in ("pending", "rejected", "suspended"):
            return jsonify({
                "error": f"Status '{row['status']}' tidak bisa disetujui."
            }), 400

        cursor.execute(
            "UPDATE tb_user SET status='active' WHERE id = %s",
            (user_id,),
        )

    return jsonify({
        "status": "ok",
        "message": f"{row['nama']} berhasil disetujui.",
    })


@app.route("/api/admin/reject/<int:user_id>", methods=["POST"])
@admin_required
def api_admin_reject(user_id):
    """
    Reject a user: set status='rejected'.

    Allowed source statuses:
        pending   → decline a new registration
    """
    with get_db() as cursor:
        cursor.execute(
            "SELECT id, nama, status, level FROM tb_user WHERE id = %s",
            (user_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": f"User {user_id} tidak ditemukan."}), 404

        if row["level"] == "admin":
            return jsonify({"error": "Akun admin tidak bisa ditolak."}), 400

        if row["status"] != "pending":
            return jsonify({
                "error": f"Hanya pendaftar 'pending' yang bisa ditolak. "
                         f"Status sekarang: '{row['status']}'."
            }), 400

        cursor.execute(
            "UPDATE tb_user SET status='rejected' WHERE id = %s",
            (user_id,),
        )

    return jsonify({
        "status": "ok",
        "message": f"{row['nama']} ditolak.",
    })

@app.route("/api/admin/suspend/<int:user_id>", methods=["POST"])
@admin_required
def api_admin_suspend(user_id):
    """Set a user's status to 'suspended'."""
    with get_db() as cursor:
        cursor.execute(
            "SELECT id, status, level FROM tb_user WHERE id = %s",
            (user_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": f"User {user_id} tidak ditemukan."}), 404
        if row["level"] == "admin":
            return jsonify({"error": "Admin tidak bisa ditangguhkan."}), 400
        if row["status"] != "active":
            return jsonify({
                "error": f"Hanya user aktif yang bisa ditangguhkan. Status sekarang: '{row['status']}'."
            }), 400

        cursor.execute(
            "UPDATE tb_user SET status='suspended' WHERE id = %s",
            (user_id,),
        )

    return jsonify({"status": "ok", "message": "User ditangguhkan."})


# ---------------------------------------------------------------------------
# Admin — pemetik (harvesters)
# ---------------------------------------------------------------------------
@app.route("/api/admin/pemetik", methods=["GET"])
@admin_required
def api_admin_pemetik_list():
    """
    Return all pemetik (both active and inactive) for the admin panel.

    Response:
        {
            "status": "ok",
            "pemetik": [
                { id, nama, deskripsi, foto_path, nomor_telepon,
                  is_active, created_at, updated_at },
                ...
            ]
        }
    """
    with get_db() as cursor:
        cursor.execute(
            """
            SELECT id, nama, deskripsi, foto_path, nomor_telepon,
                   is_active, created_at, updated_at
            FROM tb_pemetik
            ORDER BY is_active DESC, nama ASC
            """
        )
        rows = cursor.fetchall()

    return jsonify({
        "status": "ok",
        "pemetik": [
            {
                "id":            r["id"],
                "nama":          r["nama"],
                "deskripsi":     r["deskripsi"] or "",
                "foto_path":     r["foto_path"] or "",
                "nomor_telepon": r["nomor_telepon"] or "",
                "is_active":     bool(r["is_active"]),
                "created_at":    r["created_at"].isoformat() if r["created_at"] else None,
                "updated_at":    r["updated_at"].isoformat() if r["updated_at"] else None,
            }
            for r in rows
        ],
    })


@app.route("/api/admin/pemetik", methods=["POST"])
@admin_required
def api_admin_pemetik_create():
    """
    Create a new pemetik.

    Request body (JSON):
        {
            "nama": "Budi Santoso",
            "deskripsi": "Berpengalaman 10 tahun...",
            "foto_path": "pemetik/budi.jpg",   (optional)
            "nomor_telepon": "081111111111"    (optional)
        }

    Response:
        201 { "status": "ok", "id": N, "message": "..." }
        400 { "error": "..." }
    """
    data = request.get_json(silent=True) or {}

    nama = (data.get("nama") or "").strip()
    deskripsi = (data.get("deskripsi") or "").strip()
    foto_path = (data.get("foto_path") or "").strip() or None
    nomor_telepon = (data.get("nomor_telepon") or "").strip() or None

    # --- Validate ----------------------------------------------------------
    if len(nama) < 2:
        return jsonify({"error": "Nama pemetik minimal 2 karakter."}), 400
    if len(nama) > 100:
        return jsonify({"error": "Nama pemetik maksimal 100 karakter."}), 400

    if nomor_telepon:
        # Reuse our phone validator but make it optional
        normalized = validate_phone(nomor_telepon)
        if normalized is None:
            return jsonify({
                "error": "Nomor telepon tidak valid. Harus dimulai dengan 08."
            }), 400
        nomor_telepon = normalized

    # --- Insert ------------------------------------------------------------
    with get_db() as cursor:
        cursor.execute(
            """
            INSERT INTO tb_pemetik (nama, deskripsi, foto_path, nomor_telepon, is_active)
            VALUES (%s, %s, %s, %s, 1)
            """,
            (nama, deskripsi or None, foto_path, nomor_telepon),
        )
        new_id = cursor.lastrowid

    return jsonify({
        "status": "ok",
        "id": new_id,
        "message": f"Pemetik '{nama}' berhasil ditambahkan.",
    }), 201


# ---------------------------------------------------------------------------
# Admin — pemetik (single resource)
# ---------------------------------------------------------------------------
@app.route("/api/admin/pemetik/<int:pemetik_id>", methods=["GET"])
@admin_required
def api_admin_pemetik_get(pemetik_id):
    """Fetch a single pemetik."""
    with get_db() as cursor:
        cursor.execute(
            """
            SELECT id, nama, deskripsi, foto_path, nomor_telepon,
                   is_active, created_at, updated_at
            FROM tb_pemetik
            WHERE id = %s
            """,
            (pemetik_id,),
        )
        row = cursor.fetchone()

    if row is None:
        return jsonify({"error": f"Pemetik {pemetik_id} tidak ditemukan."}), 404

    return jsonify({
        "status": "ok",
        "pemetik": {
            "id":            row["id"],
            "nama":          row["nama"],
            "deskripsi":     row["deskripsi"] or "",
            "foto_path":     row["foto_path"] or "",
            "nomor_telepon": row["nomor_telepon"] or "",
            "is_active":     bool(row["is_active"]),
            "created_at":    row["created_at"].isoformat() if row["created_at"] else None,
            "updated_at":    row["updated_at"].isoformat() if row["updated_at"] else None,
        },
    })


@app.route("/api/admin/pemetik/<int:pemetik_id>", methods=["PUT"])
@admin_required
def api_admin_pemetik_update(pemetik_id):
    """
    Update a pemetik.

    Request body (JSON):
        {
            "nama": "...",
            "deskripsi": "...",
            "nomor_telepon": "...",
            "foto_path": "...",      (optional — only sent if user uploaded a new photo)
            "is_active": true/false  (optional)
        }
    """
    data = request.get_json(silent=True) or {}

    nama         = (data.get("nama") or "").strip()
    deskripsi    = (data.get("deskripsi") or "").strip()
    nomor_telepon = (data.get("nomor_telepon") or "").strip() or None
    foto_path    = (data.get("foto_path") or "").strip() or None
    is_active    = data.get("is_active")     # may be None → don't change

    # --- Validate ----------------------------------------------------------
    if len(nama) < 2:
        return jsonify({"error": "Nama pemetik minimal 2 karakter."}), 400
    if len(nama) > 100:
        return jsonify({"error": "Nama pemetik maksimal 100 karakter."}), 400

    if nomor_telepon:
        normalized = validate_phone(nomor_telepon)
        if normalized is None:
            return jsonify({
                "error": "Nomor telepon tidak valid. Harus dimulai dengan 08."
            }), 400
        nomor_telepon = normalized

    # --- Update ------------------------------------------------------------
    with get_db() as cursor:
        cursor.execute("SELECT id, foto_path FROM tb_pemetik WHERE id = %s", (pemetik_id,))
        existing = cursor.fetchone()
        if existing is None:
            return jsonify({"error": f"Pemetik {pemetik_id} tidak ditemukan."}), 404

        # Build the update dynamically — only include fields the client sent
        updates = ["nama = %s", "deskripsi = %s", "nomor_telepon = %s"]
        params  = [nama, deskripsi or None, nomor_telepon]

        if foto_path is not None:
            # User uploaded a new photo — update and delete the old file
            updates.append("foto_path = %s")
            params.append(foto_path)

            # Delete old photo from disk (if it existed and was different)
            old_path = existing["foto_path"]
            if old_path and old_path != foto_path:
                _delete_uploaded_photo(old_path)

        if is_active is not None:
            updates.append("is_active = %s")
            params.append(1 if is_active else 0)

        params.append(pemetik_id)

        cursor.execute(
            f"UPDATE tb_pemetik SET {', '.join(updates)} WHERE id = %s",
            params,
        )

    return jsonify({
        "status": "ok",
        "message": f"Pemetik '{nama}' berhasil diperbarui.",
    })


@app.route("/api/admin/pemetik/<int:pemetik_id>/toggle", methods=["POST"])
@admin_required
def api_admin_pemetik_toggle(pemetik_id):
    """
    Toggle a pemetik's is_active flag.

    - Active → deactivated (is_active=0). Keeps data + photo.
    - Inactive → reactivated (is_active=1).
    """
    with get_db() as cursor:
        cursor.execute(
            "SELECT id, nama, is_active FROM tb_pemetik WHERE id = %s",
            (pemetik_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return jsonify({"error": f"Pemetik {pemetik_id} tidak ditemukan."}), 404

        new_state = 0 if row["is_active"] else 1

        cursor.execute(
            "UPDATE tb_pemetik SET is_active = %s WHERE id = %s",
            (new_state, pemetik_id),
        )

    if new_state:
        msg = f"Pemetik '{row['nama']}' diaktifkan kembali."
    else:
        msg = f"Pemetik '{row['nama']}' dinonaktifkan (tidak muncul untuk pemesanan baru)."

    return jsonify({
        "status": "ok",
        "is_active": bool(new_state),
        "message": msg,
    })


@app.route("/api/admin/pemetik/upload", methods=["POST"])
@admin_required
def api_admin_pemetik_upload():
    """
    Upload a photo for a pemetik.
    Returns the relative path to use in the create/update endpoint.

    Form field:
        file — the image file (multipart)

    Response:
        200 { "status": "ok", "foto_path": "uploads/pemetik/abc123.jpg" }
        400 { "error": "..." }
    """
    if "file" not in request.files:
        return jsonify({"error": "Tidak ada file yang diunggah."}), 400

    try:
        path = _save_uploaded_photo(request.files["file"], "pemetik")
    except ValueError as e:
        return jsonify({"error": str(e)}), 400

    return jsonify({
        "status": "ok",
        "foto_path": path,
    })



# ---------------------------------------------------------------------------
# end of admin-only routes
# ---------------------------------------------------------------------------


# login route
@app.route("/login")
def login():
    """Serve the login page."""
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    """
    Log in a user.

    Request body (JSON):
        {
            "nomor_telepon": "081234567890",
            "password": "rahasia123"
        }

    Response:
        200 {
            "status": "ok",
            "user": { "id":..., "nama":..., "level":... }
        }
        400 { "error": "..." }
        401 { "error": "Nomor telepon atau password salah." }
        403 { "error": "..." }    (pending/rejected/suspended)
    """
    data = request.get_json(silent=True) or {}

    phone_raw = (data.get("nomor_telepon") or "").strip()
    password = data.get("password") or ""

    # Normalize phone (same helper as register)
    phone = validate_phone(phone_raw)
    if phone is None:
        # Don't reveal whether it's phone or password that's wrong
        return jsonify({"error": "Nomor telepon atau password salah."}), 401

    if not password:
        return jsonify({"error": "Nomor telepon atau password salah."}), 401

    # --- Lookup user -------------------------------------------------------
    with get_db() as cursor:
        cursor.execute(
            "SELECT id, nomor_telepon, nama, password_hash, level, status "
            "FROM tb_user WHERE nomor_telepon = %s",
            (phone,),
        )
        user = cursor.fetchone()

    # Generic error to avoid user enumeration
    GENERIC_ERROR = "Nomor telepon atau password salah."

    if user is None:
        return jsonify({"error": GENERIC_ERROR}), 401

    # --- Verify password ---------------------------------------------------
    if not check_password_hash(user["password_hash"], password):
        return jsonify({"error": GENERIC_ERROR}), 401

    # --- Check status ------------------------------------------------------
    status = user["status"]
    if status == "pending":
        return jsonify({
            "error": "Akun Anda masih menunggu persetujuan admin."
        }), 403
    if status == "rejected":
        return jsonify({
            "error": "Registrasi akun ini ditolak. Hubungi admin."
        }), 403
    if status == "suspended":
        return jsonify({
            "error": "Akun ini sedang ditangguhkan. Hubungi admin."
        }), 403
    if status != "active":
        return jsonify({"error": GENERIC_ERROR}), 401

    # --- Create session ----------------------------------------------------
    ip = request.remote_addr or ""
    ua = request.headers.get("User-Agent", "")
    session_id = create_session(user["id"], ip, ua)

    # --- Build response ----------------------------------------------------
    response = jsonify({
        "status": "ok",
        "user": {
            "id":             user["id"],
            "nomor_telepon":  user["nomor_telepon"],
            "nama":           user["nama"],
            "level":          user["level"],
        },
    })

    # Set the session cookie (HttpOnly, SameSite=Lax)
    response.set_cookie(
        SESSION_COOKIE,
        session_id,
        max_age=SESSION_TTL_DAYS * 24 * 3600,
        httponly=True,
        samesite="Lax",
        secure=False,   # ← set to True once we have HTTPS
        path="/",
    )

    return response, 200

# register route
@app.route("/register")
def register():
    """Serve the register page."""
    return render_template("register.html")


@app.route("/api/register", methods=["POST"])
def api_register():
    """
    Register a new user (status='pending', awaiting admin approval).

    Request body (JSON):
        {
            "nomor_telepon": "081234567890",
            "nama": "Budi",
            "password": "rahasia123"
        }

    Response:
        201 { "status": "ok", "message": "Registrasi berhasil. Menunggu persetujuan admin." }
        400 { "error": "..." }
        409 { "error": "Nomor telepon sudah terdaftar." }
    """
    data = request.get_json(silent=True) or {}

    phone = (data.get("nomor_telepon") or "").strip()
    name = (data.get("nama") or "").strip()
    password = data.get("password") or ""

    # --- Validate ----------------------------------------------------------
    normalized_phone = validate_phone(phone)
    if normalized_phone is None:
        return jsonify({
            "error": "Nomor telepon tidak valid. Harus dimulai dengan 08 dan 10–15 digit."
        }), 400

    name_err = validate_name(name)
    if name_err:
        return jsonify({"error": name_err}), 400

    pass_err = validate_password(password)
    if pass_err:
        return jsonify({"error": pass_err}), 400

    # --- Insert ------------------------------------------------------------
    with get_db() as cursor:
        # Check for existing phone (any status)
        cursor.execute(
            "SELECT id, status FROM tb_user WHERE nomor_telepon = %s",
            (normalized_phone,),
        )
        existing = cursor.fetchone()
        if existing:
            # Tailor the message based on status
            status = existing["status"]
            if status == "pending":
                msg = "Nomor ini sudah terdaftar dan sedang menunggu persetujuan admin."
            elif status == "active":
                msg = "Nomor ini sudah terdaftar. Silakan login."
            elif status == "rejected":
                msg = "Registrasi nomor ini sebelumnya ditolak. Hubungi admin."
            elif status == "suspended":
                msg = "Akun nomor ini sedang ditangguhkan. Hubungi admin."
            else:
                msg = "Nomor ini sudah terdaftar."
            return jsonify({"error": msg}), 409

        password_hash = generate_password_hash(password)

        cursor.execute(
            """
            INSERT INTO tb_user
                (nomor_telepon, nama, password_hash, level, status)
            VALUES
                (%s, %s, %s, 'user', 'pending')
            """,
            (normalized_phone, name, password_hash),
        )

    return jsonify({
        "status": "ok",
        "message": "Registrasi berhasil. Akun Anda menunggu persetujuan admin.",
    }), 201

@app.route("/api/logout", methods=["POST"])
def api_logout():
    sid = request.cookies.get(SESSION_COOKIE)
    if sid:
        delete_session(sid)
    response = jsonify({"status": "ok", "message": "Logout berhasil."})
    response.delete_cookie(SESSION_COOKIE, path="/")
    return response, 200


@app.route("/api/health")
def health():
    """A trivial endpoint to verify the API is reachable."""
    return jsonify({
        "status": "ok",
        "service": "cengkeh-web",
    })



@app.route("/api/chat", methods=["POST"])
def api_chat():
    """
    Receives the user's message and session id, tokenizes the message,
    prints to the server console, returns tokens as JSON.

    This is a stub. It will grow into the real search/matching logic.
    """
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()
    session_id = data.get("session_id") or "unknown"

    tokens = tokenize(message)

    # Print to the Flask console for verification
    print(f"📨 [{session_id}] {message}")
    print(f"   🔤 tokens: {tokens}")

    return jsonify({
        "status": "received",
        "session_id": session_id,
        "message": message,
        "tokens": tokens,
        "token_count": len(tokens),
    })



# ---------------------------------------------------------------------------
# QA search
# ---------------------------------------------------------------------------
KEYWORD_WEIGHT   = 3      # each keyword match adds this many points
VARIATION_WEIGHT = 1      # each variation match adds this many points


def search_qa(tokens):
    """
    Find QAs matching the given tokens.

    Scoring:
        - Each token matching a keyword in tb_keyword    → +KEYWORD_WEIGHT
        - Each token appearing in a variation in tb_variasi → +VARIATION_WEIGHT

    Returns a list of dicts (id, question, type, score), sorted by score desc.
    """
    if not tokens:
        return []

    scores = {}   # qa_id -> accumulated score

    with get_db() as cursor:
        # -------------------------------------------------------------------
        # 1. Keyword matches (weighted higher)
        # -------------------------------------------------------------------
        token_placeholders = ",".join(["%s"] * len(tokens))
        cursor.execute(
            f"""
            SELECT pertanyaan_id, COUNT(*) AS hits
            FROM tb_keyword
            WHERE kata IN ({token_placeholders})
            GROUP BY pertanyaan_id
            """,
            tokens,
        )
        for row in cursor.fetchall():
            qa_id = row["pertanyaan_id"]
            scores[qa_id] = scores.get(qa_id, 0) + row["hits"] * KEYWORD_WEIGHT

        # -------------------------------------------------------------------
        # 2. Variation matches (weighted lower, substring search)
        # -------------------------------------------------------------------
        for token in tokens:
            cursor.execute(
                """
                SELECT DISTINCT pertanyaan_id
                FROM tb_variasi
                WHERE teks LIKE %s
                """,
                (f"%{token}%",),
            )
            for row in cursor.fetchall():
                qa_id = row["pertanyaan_id"]
                scores[qa_id] = scores.get(qa_id, 0) + VARIATION_WEIGHT

        if not scores:
            return []

        # -------------------------------------------------------------------
        # 3. Fetch QA details for matched IDs
        # -------------------------------------------------------------------
        ranked_ids = sorted(scores.keys(), key=lambda qid: -scores[qid])
        id_placeholders = ",".join(["%s"] * len(ranked_ids))
        cursor.execute(
            f"""
            SELECT id, pertanyaan, tipe
            FROM tb_pertanyaan
            WHERE id IN ({id_placeholders})
            """,
            ranked_ids,
        )
        qa_by_id = {row["id"]: row for row in cursor.fetchall()}

    # -------------------------------------------------------------------
    # 4. Assemble the ranked list (full list — no limit)
    # -------------------------------------------------------------------
    matches = []
    for qa_id in ranked_ids:
        qa = qa_by_id.get(qa_id)
        if qa is None:
            continue
        matches.append({
            "id":       qa["id"],
            "question": qa["pertanyaan"],
            "type":     qa["tipe"],
            "score":    scores[qa_id],
        })

    return matches


@app.route("/api/search")
def api_search():
    q = request.args.get("q", "").strip()
    if not q:
        return jsonify({"error": "missing query parameter 'q'"}), 400

    try:
        limit = int(request.args.get("limit", "4"))
    except ValueError:
        limit = 3
    limit = max(1, min(limit, 50))

    tokens = tokenize(q)

    # ---- Case 1: no meaningful tokens ----
    if not tokens:
        return jsonify({
            "query":   q,
            "tokens":  [],
            "matches": [],
            "total":   0,
            "shown":   0,
            "message": (
                "Pertanyaan Anda terlalu umum. "
                "Coba tanyakan hal yang lebih spesifik, "
                "misalnya: 'Kapan waktu menanam cengkeh?' "
                "atau 'Kenapa daun cengkeh menguning?'"
            ),
        })

    all_matches = search_qa(tokens)
    shown       = all_matches[:limit]

    response = {
        "query":   q,
        "tokens":  tokens,
        "matches": shown,
        "total":   len(all_matches),
        "shown":   len(shown),
    }

    # ---- Case 2: tokens exist, but no matches found ----
    if not all_matches:
        response["message"] = (
            "Maaf, tidak ada pertanyaan yang cocok dengan kata kunci Anda. "
            "Coba gunakan kata kunci yang berbeda atau lebih umum."
        )

    # ---- Case 3: matches found — no message needed ----

    return jsonify(response)


# ---------------------------------------------------------------------------
# QA detail
# ---------------------------------------------------------------------------
def get_qa_detail(qa_id):
    """
    Fetch a QA with its sources, related QAs, and (if diagnostic)
    the first follow-up question with options.

    Returns a dict, or None if the QA doesn't exist.
    """
    with get_db() as cursor:
        # -------------------------------------------------------------------
        # 1. The QA itself
        # -------------------------------------------------------------------
        cursor.execute(
            """
            SELECT id, pertanyaan, jawaban, tipe
            FROM tb_pertanyaan
            WHERE id = %s
            """,
            (qa_id,),
        )
        qa = cursor.fetchone()
        if qa is None:
            return None

        # -------------------------------------------------------------------
        # 2. Sources
        # -------------------------------------------------------------------
        cursor.execute(
            """
            SELECT s.kode, s.judul
            FROM tb_pertanyaan_sumber ps
            JOIN tb_sumber s ON s.id = ps.sumber_id
            WHERE ps.pertanyaan_id = %s
            ORDER BY s.kode
            """,
            (qa_id,),
        )
        sources = cursor.fetchall()

        # -------------------------------------------------------------------
        # 3. Related QAs
        # -------------------------------------------------------------------
        cursor.execute(
            """
            SELECT r.related_id AS id, p.pertanyaan
            FROM tb_relasi r
            JOIN tb_pertanyaan p ON p.id = r.related_id
            WHERE r.pertanyaan_id = %s
            ORDER BY r.related_id
            """,
            (qa_id,),
        )
        related = cursor.fetchall()

        # -------------------------------------------------------------------
        # 4. First follow-up (if diagnostic)
        # -------------------------------------------------------------------
        follow_up = None
        cursor.execute(
            """
            SELECT id, urutan, pertanyaan
            FROM tb_follow_up
            WHERE pertanyaan_id = %s
            ORDER BY urutan
            LIMIT 1
            """,
            (qa_id,),
        )
        fu = cursor.fetchone()

        if fu:
            cursor.execute(
                """
                SELECT id, label
                FROM tb_follow_option
                WHERE follow_up_id = %s
                ORDER BY id
                """,
                (fu["id"],),
            )
            options = cursor.fetchall()

            follow_up = {
                "id":         fu["id"],
                "urutan":     fu["urutan"],
                "question":   fu["pertanyaan"],
                "options":    [
                    {"id": o["id"], "label": o["label"]}
                    for o in options
                ],
            }

    return {
        "id":        qa["id"],
        "question":  qa["pertanyaan"],
        "answer":    qa["jawaban"] or "",
        "type":      qa["tipe"],
        "sources":   [
            {"kode": s["kode"], "judul": s["judul"]}
            for s in sources
        ],
        "related":   [
            {"id": r["id"], "question": r["pertanyaan"]}
            for r in related
        ],
        "follow_up": follow_up,
    }


@app.route("/api/qa/<int:qa_id>")
def api_qa(qa_id):
    """Return the full QA detail: answer, sources, related QAs, first follow-up."""
    qa = get_qa_detail(qa_id)
    if qa is None:
        return jsonify({"error": f"QA {qa_id} not found"}), 404
    return jsonify(qa)


# ---------------------------------------------------------------------------
# Diagnostic flow
# ---------------------------------------------------------------------------
def get_next_step(option_id):
    """
    Given a chosen option, figure out the next step in the diagnostic flow.

    Returns a dict with a `type` field:
        - "follow_up" — there's another follow-up question to show
        - "matches"   — no more follow-ups; here are the resulting QAs
        - None        — option not found
    """
    with get_db() as cursor:
        # -------------------------------------------------------------------
        # 1. Find the option and its follow-up
        # -------------------------------------------------------------------
        cursor.execute(
            """
            SELECT fo.id AS option_id,
                   fo.follow_up_id,
                   fu.pertanyaan_id,
                   fu.urutan
            FROM tb_follow_option fo
            JOIN tb_follow_up fu ON fu.id = fo.follow_up_id
            WHERE fo.id = %s
            """,
            (option_id,),
        )
        opt = cursor.fetchone()
        if opt is None:
            return None

        qa_id = opt["pertanyaan_id"]
        current_urutan = opt["urutan"]

        # -------------------------------------------------------------------
        # 2. Is there a NEXT follow-up (urutan + 1) for this QA?
        # -------------------------------------------------------------------
        cursor.execute(
            """
            SELECT id, urutan, pertanyaan
            FROM tb_follow_up
            WHERE pertanyaan_id = %s AND urutan = %s
            """,
            (qa_id, current_urutan + 1),
        )
        next_fu = cursor.fetchone()

        if next_fu:
            # Fetch its options
            cursor.execute(
                """
                SELECT id, label
                FROM tb_follow_option
                WHERE follow_up_id = %s
                ORDER BY id
                """,
                (next_fu["id"],),
            )
            options = cursor.fetchall()

            return {
                "type": "follow_up",
                "follow_up": {
                    "id":       next_fu["id"],
                    "urutan":   next_fu["urutan"],
                    "question": next_fu["pertanyaan"],
                    "options":  [
                        {"id": o["id"], "label": o["label"]}
                        for o in options
                    ],
                },
            }

        # -------------------------------------------------------------------
        # 3. No more follow-ups — return the resulting QAs
        # -------------------------------------------------------------------
        cursor.execute(
            """
            SELECT q.next_qa_id AS id, p.pertanyaan, p.tipe
            FROM tb_option_next_qa q
            JOIN tb_pertanyaan p ON p.id = q.next_qa_id
            WHERE q.option_id = %s
            ORDER BY p.id
            """,
            (option_id,),
        )
        next_qas = cursor.fetchall()

        return {
            "type": "matches",
            "matches": [
                {
                    "id":       row["id"],
                    "question": row["pertanyaan"],
                    "type":     row["tipe"],
                }
                for row in next_qas
            ],
        }


@app.route("/api/next/<int:option_id>")
def api_next(option_id):
    """
    Given a chosen option, return the next step in the diagnostic flow:
    either another follow-up or a list of resulting QAs.
    """
    result = get_next_step(option_id)
    if result is None:
        return jsonify({"error": f"Option {option_id} not found"}), 404
    return jsonify(result)

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    port = int(os.getenv("PORT", "5000"))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"🍀 Starting cengkeh-web on http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug)