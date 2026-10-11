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

# this is stopwords set, it will be populated from the database on app startup


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
        limit = int(request.args.get("limit", "3"))
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
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    debug = os.getenv("FLASK_DEBUG", "0") == "1"
    port = int(os.getenv("PORT", "5000"))
    host = os.getenv("HOST", "0.0.0.0")

    print(f"🍀 Starting cengkeh-web on http://{host}:{port}/")
    app.run(host=host, port=port, debug=debug)