from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import sqlite3
from datetime import datetime, timedelta
import os
import jwt
import time
from functools import wraps
from werkzeug.security import generate_password_hash, check_password_hash

try:
    import psycopg2
except ImportError:
    psycopg2 = None

# Configure Flask to find templates in Frontend folder
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), "Frontend"),
    static_folder=os.path.join(os.path.dirname(__file__), "Frontend"),
    static_url_path="",
)
FLASK_ENV = os.environ.get("FLASK_ENV", "production" if os.environ.get("VERCEL") else "development").lower()
IS_PRODUCTION = FLASK_ENV == "production" or bool(os.environ.get("VERCEL"))
ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.environ.get(
        "ALLOWED_ORIGINS", "http://localhost:1000,http://127.0.0.1:1000"
    ).split(",")
    if origin.strip()
]
CORS(app, resources={r"/*": {"origins": ALLOWED_ORIGINS}})

# Secret key for JWT
DEFAULT_SECRET_KEY = "dev-secret-key-change-this"
SECRET_KEY = os.environ.get("SECRET_KEY", DEFAULT_SECRET_KEY)
JWT_EXPIRES_HOURS = int(os.environ.get("JWT_EXPIRES_HOURS", "24"))
RATE_LIMIT_WINDOW_SECONDS = int(os.environ.get("RATE_LIMIT_WINDOW_SECONDS", "60"))
RATE_LIMIT_MAX_ATTEMPTS = int(os.environ.get("RATE_LIMIT_MAX_ATTEMPTS", "10"))

if IS_PRODUCTION and SECRET_KEY == DEFAULT_SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set to a strong value in production")

DATABASE_URL = os.environ.get("DATABASE_URL")
USE_POSTGRES = bool(DATABASE_URL)
ON_VERCEL = bool(os.environ.get("VERCEL"))

if ON_VERCEL and not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is required on Vercel. Use a managed PostgreSQL database."
    )

if USE_POSTGRES and psycopg2 is None:
    raise RuntimeError(
        "DATABASE_URL is set but psycopg2 is not installed. Install dependencies from requirements.txt"
    )

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(BASE_DIR, "product_expiry.db")
LEGACY_DB_PATH = os.path.join(BASE_DIR, "medicine_expiry.db")
DB_PATH = DEFAULT_DB_PATH

if (
    not USE_POSTGRES
    and not os.path.exists(DEFAULT_DB_PATH)
    and os.path.exists(LEGACY_DB_PATH)
):
    DB_PATH = LEGACY_DB_PATH

RATE_LIMIT_STATE = {}


def _sql(query):
    """Translate sqlite style placeholders to postgres placeholders when needed."""
    if USE_POSTGRES:
        return query.replace("?", "%s")
    return query


def init_db():
    """Initialize database with users and medicines tables"""
    if USE_POSTGRES:
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS phone TEXT")

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS medicines (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                batch TEXT NOT NULL,
                expiry DATE NOT NULL,
                barcode TEXT NOT NULL,
                quantity INTEGER NOT NULL
            )
            """
        )

        conn.commit()
        conn.close()
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Create users table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cur.execute("PRAGMA table_info(users)")
    user_columns = [row[1] for row in cur.fetchall()]
    if "phone" not in user_columns:
        cur.execute("ALTER TABLE users ADD COLUMN phone TEXT")

    # Create medicines table with user_id
    cur.execute("""
        CREATE TABLE IF NOT EXISTS medicines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            batch TEXT NOT NULL,
            expiry TEXT NOT NULL,
            barcode TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)

    # Migrate legacy medicines table (without user_id) to the new schema.
    cur.execute("PRAGMA table_info(medicines)")
    medicine_columns = [row[1] for row in cur.fetchall()]
    if "user_id" not in medicine_columns:
        # Ensure a fallback user exists so old rows can be preserved.
        cur.execute(
            """
            INSERT OR IGNORE INTO users (id, email, password)
            VALUES (1, 'legacy@local', ?)
            """,
            (generate_password_hash("legacy-password"),),
        )

        cur.execute(
            """
            CREATE TABLE medicines_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                batch TEXT NOT NULL,
                expiry TEXT NOT NULL,
                barcode TEXT NOT NULL,
                quantity INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        cur.execute(
            """
            INSERT INTO medicines_new (id, user_id, name, batch, expiry, barcode, quantity)
            SELECT id, 1, name, batch, expiry, barcode, quantity
            FROM medicines
            """
        )
        cur.execute("DROP TABLE medicines")
        cur.execute("ALTER TABLE medicines_new RENAME TO medicines")

    conn.commit()
    conn.close()


# Initialize database on startup
init_db()


def get_db():
    if USE_POSTGRES:
        return psycopg2.connect(DATABASE_URL)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _normalize_phone(raw_phone):
    if raw_phone is None:
        return None

    cleaned = "".join(ch for ch in str(raw_phone).strip() if ch.isdigit() or ch == "+")
    if cleaned.startswith("+"):
        digits = "+" + "".join(ch for ch in cleaned[1:] if ch.isdigit())
    else:
        digits = "".join(ch for ch in cleaned if ch.isdigit())

    if len(digits.replace("+", "")) < 10:
        return None

    if not digits.startswith("+"):
        digits = "+" + digits

    return digits


def _get_client_ip():
    forwarded_for = request.headers.get("X-Forwarded-For", "")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.remote_addr or "unknown"


def _is_rate_limited(scope):
    now = time.time()
    key = f"{scope}:{_get_client_ip()}"
    state = RATE_LIMIT_STATE.get(key)

    if not state or now - state["window_start"] > RATE_LIMIT_WINDOW_SECONDS:
        RATE_LIMIT_STATE[key] = {"window_start": now, "count": 0}
        return False

    return state["count"] >= RATE_LIMIT_MAX_ATTEMPTS


def _record_rate_limit_attempt(scope):
    now = time.time()
    key = f"{scope}:{_get_client_ip()}"
    state = RATE_LIMIT_STATE.get(key)

    if not state or now - state["window_start"] > RATE_LIMIT_WINDOW_SECONDS:
        RATE_LIMIT_STATE[key] = {"window_start": now, "count": 1}
        return

    state["count"] += 1


def _clear_rate_limit(scope):
    key = f"{scope}:{_get_client_ip()}"
    RATE_LIMIT_STATE.pop(key, None)


def _is_valid_email(email):
    if not email or "@" not in email:
        return False
    local_part, domain_part = email.split("@", 1)
    return bool(local_part and domain_part and "." in domain_part)


def _is_strong_password(password):
    if len(password) < 8:
        return False
    has_alpha = any(ch.isalpha() for ch in password)
    has_digit = any(ch.isdigit() for ch in password)
    return has_alpha and has_digit


# JWT Token decorator
def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        auth_header = request.headers.get("Authorization", "")
        parts = auth_header.split(" ")
        if len(parts) == 2 and parts[0].lower() == "bearer":
            token = parts[1]

        if not token:
            return jsonify({"error": "Token is missing"}), 401

        try:
            data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            current_user_id = data["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token has expired"}), 401
        except Exception:
            return jsonify({"error": "Invalid token"}), 401

        return f(current_user_id, *args, **kwargs)

    return decorated


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com; script-src 'self' 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none';"
    )
    if request.is_secure:
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
    return response


@app.route("/")
def home():
    return render_template("intro.html")


@app.route("/auth")
def auth():
    return render_template("login.html")


@app.route("/dashboard")
def dashboard():
    return render_template("intra.html")


@app.route("/signup", methods=["POST"])
def signup():
    try:
        if _is_rate_limited("signup"):
            return jsonify({"error": "Too many requests. Try again later."}), 429

        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password")
        phone = _normalize_phone(data.get("phone")) if data.get("phone") else None

        if not email or not password:
            _record_rate_limit_attempt("signup")
            return jsonify({"error": "Email and password required"}), 400

        if not _is_valid_email(email):
            _record_rate_limit_attempt("signup")
            return jsonify({"error": "Invalid email format"}), 400

        if not _is_strong_password(password):
            _record_rate_limit_attempt("signup")
            return jsonify(
                {
                    "error": "Password must be at least 8 characters and include letters and numbers"
                }
            ), 400

        if data.get("phone") and not phone:
            _record_rate_limit_attempt("signup")
            return jsonify({"error": "Phone number is invalid"}), 400

        hashed_password = generate_password_hash(password)
        conn = get_db()
        cur = conn.cursor()

        try:
            cur.execute(
                _sql("INSERT INTO users (email, password, phone) VALUES (?, ?, ?)"),
                (email, hashed_password, phone),
            )
            conn.commit()
            conn.close()
            _clear_rate_limit("signup")
            return jsonify({"message": "User created successfully"}), 201
        except Exception as db_error:
            conn.close()
            if isinstance(db_error, sqlite3.IntegrityError) or (
                psycopg2 is not None and isinstance(db_error, psycopg2.IntegrityError)
            ):
                _record_rate_limit_attempt("signup")
                return jsonify({"error": "Email already exists"}), 400
            raise

    except Exception as e:
        _record_rate_limit_attempt("signup")
        return jsonify({"error": f"Signup failed: {str(e)}"}), 500


@app.route("/login", methods=["POST"])
def login():
    try:
        if _is_rate_limited("login"):
            return jsonify({"error": "Too many requests. Try again later."}), 429

        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        password = data.get("password")

        if not email or not password:
            _record_rate_limit_attempt("login")
            return jsonify({"error": "Email and password required"}), 400

        conn = get_db()
        cur = conn.cursor()
        cur.execute(_sql("SELECT id, password FROM users WHERE email = ?"), (email,))
        user = cur.fetchone()
        conn.close()

        if not user or not check_password_hash(user[1], password):
            _record_rate_limit_attempt("login")
            return jsonify({"error": "Invalid email or password"}), 401

        token = jwt.encode(
            {
                "user_id": user[0],
                "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRES_HOURS),
            },
            SECRET_KEY,
            algorithm="HS256",
        )

        _clear_rate_limit("login")
        return jsonify({"token": token}), 200

    except Exception as e:
        _record_rate_limit_attempt("login")
        return jsonify({"error": f"Login failed: {str(e)}"}), 500


@app.route("/add", methods=["POST"])
@app.route("/products/add", methods=["POST"])
@token_required
def add_medicine(current_user_id):
    try:
        data = request.get_json(silent=True) or {}

        if not data:
            return jsonify({"error": "No data provided"}), 400

        required_fields = ["name", "batch", "expiry", "barcode", "quantity"]
        missing_fields = [field for field in required_fields if field not in data]

        if missing_fields:
            return jsonify(
                {"error": f"Missing fields: {', '.join(missing_fields)}"}
            ), 400

        try:
            quantity = int(data["quantity"])
            if quantity < 0:
                return jsonify({"error": "Quantity must be positive"}), 400
        except ValueError:
            return jsonify({"error": "Quantity must be a number"}), 400

        try:
            datetime.strptime(data["expiry"], "%Y-%m-%d")
        except ValueError:
            return jsonify({"error": "Expiry date must be in YYYY-MM-DD format"}), 400

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            _sql(
                """
            INSERT INTO medicines (user_id, name, batch, expiry, barcode, quantity)
            VALUES (?, ?, ?, ?, ?, ?)
        """
            ),
            (
                current_user_id,
                data["name"],
                data["batch"],
                data["expiry"],
                data["barcode"],
                quantity,
            ),
        )

        conn.commit()
        conn.close()
        return jsonify({"message": "Product added successfully"}), 201

    except Exception as e:
        return jsonify({"error": f"Failed to add product: {str(e)}"}), 500


@app.route("/medicines", methods=["GET"])
@app.route("/products", methods=["GET"])
@token_required
def get_medicines(current_user_id):
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            _sql("SELECT * FROM medicines WHERE user_id = ?"), (current_user_id,)
        )
        rows = cur.fetchall()
        conn.close()

        medicines = []
        for r in rows:
            try:
                expiry_value = r[4]
                if hasattr(expiry_value, "strftime"):
                    expiry_text = expiry_value.strftime("%Y-%m-%d")
                else:
                    expiry_text = str(expiry_value)

                expiry_date = datetime.strptime(expiry_text, "%Y-%m-%d").date()
                days_left = (expiry_date - datetime.today().date()).days

                if days_left < 0:
                    status = "expired"
                elif days_left <= 30:
                    status = "warning"
                else:
                    status = "safe"

                medicines.append(
                    {
                        "id": r[0],
                        "name": r[2],
                        "batch": r[3],
                        "expiry": expiry_text,
                        "barcode": r[5],
                        "quantity": r[6],
                        "days_left": days_left,
                        "status": status,
                    }
                )
            except ValueError:
                continue

        return jsonify(medicines), 200
    except Exception as e:
        return jsonify({"error": f"Failed to fetch products: {str(e)}"}), 500


@app.route("/delete/<int:id>", methods=["DELETE"])
@app.route("/products/<int:id>", methods=["DELETE"])
@token_required
def delete_medicine(current_user_id, id):
    try:
        conn = get_db()
        cur = conn.cursor()
        # Ensure user can only delete their own medicines
        cur.execute(
            _sql("DELETE FROM medicines WHERE id=? AND user_id=?"),
            (id, current_user_id),
        )

        if cur.rowcount == 0:
            conn.close()
            return jsonify({"error": f"Product with id {id} not found"}), 404

        conn.commit()
        conn.close()
        return jsonify({"message": f"Product {id} deleted successfully"}), 200

    except Exception as e:
        return jsonify({"error": f"Failed to delete product: {str(e)}"}), 500


@app.route("/profile/phone", methods=["PUT"])
@token_required
def update_phone(current_user_id):
    try:
        data = request.get_json(silent=True) or {}
        phone = _normalize_phone(data.get("phone")) if data.get("phone") else None

        if not phone:
            return jsonify({"error": "Valid phone number is required"}), 400

        conn = get_db()
        cur = conn.cursor()
        cur.execute(
            _sql("UPDATE users SET phone=? WHERE id=?"), (phone, current_user_id)
        )
        conn.commit()
        conn.close()

        return jsonify({"message": "Phone number updated"}), 200
    except Exception as e:
        return jsonify({"error": f"Failed to update phone: {str(e)}"}), 500


if __name__ == "__main__":
    flask_debug = os.environ.get("FLASK_DEBUG", "0") == "1"
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 1000)),
        debug=flask_debug and not IS_PRODUCTION,
    )
