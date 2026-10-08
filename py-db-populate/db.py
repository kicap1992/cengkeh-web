"""
Shared database helpers for the py-db-populate scripts.

All import scripts use this module to connect to the dev/prod DB.
Connection settings come from (in order of precedence):
    1. Environment variables (e.g., DB_PASS=xxx python script.py)
    2. .env file in the project root (~/cengkeh/.env)
    3. Sane defaults for dev-host
"""

import os
import sys
from pathlib import Path

import pymysql


# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------
def _load_env():
    """Load the project's .env file (from the parent directory).

    Values are set as environment variables only if not already set.
    This means real env vars (e.g., in CI) take precedence over .env.
    """
    # py-db-populate/ -> project root
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
            key = key.strip()
            value = value.strip()
            # Don't overwrite existing env vars
            os.environ.setdefault(key, value)


# Load .env as soon as this module is imported
_load_env()


# ---------------------------------------------------------------------------
# Config — read from environment (which is now populated by .env if present)
# ---------------------------------------------------------------------------
DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "3306"))
DB_USER = os.getenv("MYSQL_USER", "arham")
# Note: We need to map from the .env's MYSQL_PASSWORD to DB_PASS
DB_PASS = os.getenv("DB_PASS") or os.getenv("MYSQL_PASSWORD", "")
DB_NAME = os.getenv("DB_NAME") or os.getenv("MYSQL_DATABASE", "cengkeh_db")


# ---------------------------------------------------------------------------
# Connection
# ---------------------------------------------------------------------------
def get_connection():
    """Open a new connection to MariaDB."""
    if not DB_PASS:
        print("❌ No DB password found.", file=sys.stderr)
        print("   Set DB_PASS env var, or ensure MYSQL_PASSWORD is in .env", file=sys.stderr)
        sys.exit(1)

    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASS,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_json(path):
    """Load a JSON file and return the parsed dict."""
    import json
    p = Path(path)
    if not p.exists():
        print(f"❌ JSON file not found: {path}", file=sys.stderr)
        sys.exit(1)
    with p.open("r", encoding="utf-8") as f:
        return json.load(f)


def qa_id_to_int(qa_id):
    """Convert 'Q001' -> 1, 'Q100' -> 100."""
    return int(qa_id.lstrip("Q"))