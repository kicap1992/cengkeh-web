"""
Import records[].keywords[] into tb_keyword.

Usage:
    python import_keyword.py <path-to-json>
    python import_keyword.py <path-to-json> --rollback
"""

import sys

from db import get_connection, load_json, qa_id_to_int


def rollback(cursor):
    """Wipe tb_keyword."""
    cursor.execute("DELETE FROM tb_keyword")


def import_keyword(records, cursor):
    """Insert each keyword into tb_keyword. Returns count."""
    count = 0
    for rec in records:
        qa_id = qa_id_to_int(rec["id"])
        for kata in rec.get("keywords", []):
            cursor.execute(
                """
                INSERT INTO tb_keyword (pertanyaan_id, kata)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE id = id
                """,
                (qa_id, kata),
            )
            count += 1
    return count


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_keyword.py <path-to-json> [--rollback]")
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
                print("🧹 Rolling back tb_keyword...")
                rollback(cursor)
                print("   Cleared.")

            print("📝 Inserting into tb_keyword...")
            inserted = import_keyword(records, cursor)
            conn.commit()

            print(f"✅ Inserted/updated {inserted} rows into tb_keyword")

            cursor.execute("SELECT COUNT(*) AS c FROM tb_keyword")
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