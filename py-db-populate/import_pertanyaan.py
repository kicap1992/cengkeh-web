"""
Import records[].* into tb_pertanyaan.

Reads the knowledge base JSON and inserts each record's
core fields into tb_pertanyaan.

Usage:
    DB_PASS=xxx python import_pertanyaan.py <path-to-json>
    DB_PASS=xxx python import_pertanyaan.py <path-to-json> --rollback

--rollback wipes tb_pertanyaan before importing, so you get a clean slate.

Design:
    - Runs inside a single transaction. Fails cleanly if anything goes wrong.
    - Uses INSERT ... ON DUPLICATE KEY UPDATE so re-runs don't error.
    - Reads DB_PASS from environment (never hardcoded).
"""

import sys

from db import get_connection, load_json, qa_id_to_int


def build_kategori_map(cursor):
    """Return {nama_kategori: id} from tb_kategori."""
    cursor.execute("SELECT id, nama FROM tb_kategori")
    return {row["nama"]: row["id"] for row in cursor.fetchall()}


def import_pertanyaan(records, cursor, kategori_map):
    """Insert each record into tb_pertanyaan. Returns count inserted/updated."""
    count = 0
    for rec in records:
        qa_id = qa_id_to_int(rec["id"])
        kategori_nama = rec["category"]
        kategori_id = kategori_map.get(kategori_nama)

        if kategori_id is None:
            print(f"  ⚠  Skipping {rec['id']}: unknown category '{kategori_nama}'")
            continue

        cursor.execute(
            """
            INSERT INTO tb_pertanyaan (id, kategori_id, tipe, pertanyaan, jawaban)
            VALUES (%s, %s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE
                kategori_id = VALUES(kategori_id),
                tipe        = VALUES(tipe),
                pertanyaan  = VALUES(pertanyaan),
                jawaban     = VALUES(jawaban)
            """,
            (
                qa_id,
                kategori_id,
                rec["type"],
                rec["question"],
                rec.get("answer", ""),
            ),
        )
        count += 1

    return count


def rollback(cursor):
    """Wipe tb_pertanyaan (and reset AUTO_INCREMENT)."""
    cursor.execute("DELETE FROM tb_pertanyaan")


def main():
    if len(sys.argv) < 2:
        print("Usage: DB_PASS=xxx python import_pertanyaan.py <path-to-json> [--rollback]")
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
                print("🧹 Rolling back tb_pertanyaan...")
                rollback(cursor)
                print("   Cleared.")

            print("🔍 Loading kategori map...")
            kategori_map = build_kategori_map(cursor)
            print(f"   Loaded {len(kategori_map)} categories")

            print("📝 Inserting into tb_pertanyaan...")
            inserted = import_pertanyaan(records, cursor, kategori_map)
            conn.commit()

            print(f"✅ Inserted/updated {inserted} rows into tb_pertanyaan")

            # Print a quick verification
            cursor.execute("SELECT COUNT(*) AS c FROM tb_pertanyaan")
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