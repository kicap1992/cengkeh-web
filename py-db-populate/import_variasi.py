"""
Import records[].variations[] into tb_variasi.

Reads the knowledge base JSON and inserts each record's variation
strings into tb_variasi, linked to their parent question.

Usage:
    python import_variasi.py <path-to-json>
    python import_variasi.py <path-to-json> --rollback

--rollback wipes tb_variasi before importing, for a clean slate.

Design:
    - Runs inside a single transaction. All-or-nothing.
    - Uses INSERT ... ON DUPLICATE KEY UPDATE for idempotency.
    - Reads DB_PASS from environment (via db.py's .env loading).
"""

import sys

from db import get_connection, load_json, qa_id_to_int


def rollback(cursor):
    """Wipe tb_variasi."""
    cursor.execute("DELETE FROM tb_variasi")


def import_variasi(records, cursor):
    """Insert each variation string into tb_variasi.

    Returns the number of rows inserted/updated.
    """
    count = 0
    for rec in records:
        qa_id = qa_id_to_int(rec["id"])
        for text in rec.get("variations", []):
            cursor.execute(
                """
                INSERT INTO tb_variasi (pertanyaan_id, teks)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE id = id
                """,
                (qa_id, text),
            )
            count += 1
    return count


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_variasi.py <path-to-json> [--rollback]")
        sys.exit(1)

    json_path = sys.argv[1]
    do_rollback = "--rollback" in sys.argv

    print(f"📖 Reading {json_path}")
    data = load_json(json_path)
    records = data.get("records", [])
    print(f"   Found {len(records)} records")

    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            if do_rollback:
                print("🧹 Rolling back tb_variasi...")
                rollback(cursor)
                print("   Cleared.")

            print("📝 Inserting into tb_variasi...")
            inserted = import_variasi(records, cursor)
            conn.commit()

            print(f"✅ Inserted/updated {inserted} rows into tb_variasi")

            cursor.execute("SELECT COUNT(*) AS c FROM tb_variasi")
            print(f"   Table now has {cursor.fetchone()['c']} rows")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error: {e}", file=sys.stderr)
        print("   Rolled back — no changes were made.", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()


if __name__ == "__main__":
    main()