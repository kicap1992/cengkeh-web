"""
Import records[].sources[] into tb_pertanyaan_sumber.

The JSON contains source CODES (e.g., "S1", "S2"), but the DB
uses numeric IDs (tb_sumber.id). So we build a kode -> id map
first, then insert.

Usage:
    python import_pertanyaan_sumber.py <path-to-json>
    python import_pertanyaan_sumber.py <path-to-json> --rollback
"""

import sys

from db import get_connection, load_json, qa_id_to_int


def rollback(cursor):
    """Wipe tb_pertanyaan_sumber."""
    cursor.execute("DELETE FROM tb_pertanyaan_sumber")


def build_sumber_map(cursor):
    """Return {kode: id} from tb_sumber."""
    cursor.execute("SELECT id, kode FROM tb_sumber")
    return {row["kode"]: row["id"] for row in cursor.fetchall()}


def import_pertanyaan_sumber(records, cursor, sumber_map):
    """Insert each (pertanyaan_id, sumber_id) pair. Returns count."""
    count = 0
    skipped = 0
    for rec in records:
        qa_id = qa_id_to_int(rec["id"])
        for kode in rec.get("sources", []):
            sumber_id = sumber_map.get(kode)
            if sumber_id is None:
                print(f"  ⚠  Skipping unknown source code '{kode}' in {rec['id']}")
                skipped += 1
                continue
            cursor.execute(
                """
                INSERT INTO tb_pertanyaan_sumber (pertanyaan_id, sumber_id)
                VALUES (%s, %s)
                ON DUPLICATE KEY UPDATE pertanyaan_id = pertanyaan_id
                """,
                (qa_id, sumber_id),
            )
            count += 1
    return count, skipped


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_pertanyaan_sumber.py <path-to-json> [--rollback]")
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
                print("🧹 Rolling back tb_pertanyaan_sumber...")
                rollback(cursor)
                print("   Cleared.")

            print("🔍 Loading sumber map...")
            sumber_map = build_sumber_map(cursor)
            print(f"   Loaded {len(sumber_map)} sources")

            print("📝 Inserting into tb_pertanyaan_sumber...")
            inserted, skipped = import_pertanyaan_sumber(records, cursor, sumber_map)
            conn.commit()

            print(f"✅ Inserted/updated {inserted} rows into tb_pertanyaan_sumber")
            if skipped:
                print(f"   ⚠  Skipped {skipped} rows with unknown source codes")

            cursor.execute("SELECT COUNT(*) AS c FROM tb_pertanyaan_sumber")
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