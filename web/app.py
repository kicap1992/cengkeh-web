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
from flask import Flask, render_template, jsonify, request


app = Flask(__name__)


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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    """Serve the chat UI."""
    return render_template("index.html")


@app.route("/api/health")
def health():
    """A trivial endpoint to verify the API is reachable."""
    return jsonify({
        "status": "ok",
        "service": "cengkeh-web",
    })


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    port = int(os.getenv("PORT", "5000"))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"🍀 Starting cengkeh-web on http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug)