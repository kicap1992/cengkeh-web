"""
Import records[].related_qas[] into tb_relasi.

Usage:
    python import_relasi.py <path-to-json>
    python import_relasi.py <path-to-json> --rollback
"""

import sys

from db import get_connection, load_json, qa_id_to_int


def rollback(cursor):
    """Wipe tb_relasi."""
    cursor.execute("DELETE FROM tb_relasi")


def import_relasi(records, cursor):
    """Insert each related QA pair. Returns count."""
    count = 0
    for rec in records:
        qa_id = qa_id_to_int(rec["id"])
        for rel_id_str in rec.get("related_qas", []):
            rel_id = qa_id_to_int(rel_id_str)
            cursor.execute(
                """
                INSERT INTO tb_relasi (pertanyaan_id, related_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE pertanyaan_id = pertanyaan_id
                """,
                (qa_id, rel_id),
            )
            count += 1
    return count


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_relasi.py <path-to-json> [--rollback]")
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
                print("🧹 Rolling back tb_relasi...")
                rollback(cursor)
                print("   Cleared.")

            print("📝 Inserting into tb_relasi...")
            inserted = import_relasi(records, cursor)
            conn.commit()

            print(f"✅ Inserted/updated {inserted} rows into tb_relasi")

            cursor.execute("SELECT COUNT(*) AS c FROM tb_relasi")
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