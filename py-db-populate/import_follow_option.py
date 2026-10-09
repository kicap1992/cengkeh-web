"""
Import records[].follow_ups[].options[] into tb_follow_option.

Since tb_follow_option.follow_up_id is a FK to tb_follow_up (which
has an auto-generated id), we first build a lookup map from
(pertanyaan_id, urutan) -> follow_up_id, then use it during insertion.

Usage:
    python import_follow_option.py <path-to-json>
    python import_follow_option.py <path-to-json> --rollback
"""

import sys

from db import get_connection, load_json, qa_id_to_int


def rollback(cursor):
    """Wipe tb_follow_option (cascades to next_qas)."""
    cursor.execute("DELETE FROM tb_follow_option")


def build_follow_up_map(cursor):
    """Return {(pertanyaan_id, urutan): follow_up_id}."""
    cursor.execute("SELECT id, pertanyaan_id, urutan FROM tb_follow_up")
    return {
        (row["pertanyaan_id"], row["urutan"]): row["id"]
        for row in cursor.fetchall()
    }


def import_follow_option(records, cursor, fu_map):
    """Insert options into tb_follow_option. Returns (inserted, skipped)."""
    count = 0
    skipped = 0
    for rec in records:
        follow_ups = rec.get("follow_ups", [])
        if not follow_ups:
            continue
        qa_id = qa_id_to_int(rec["id"])
        for i, fu in enumerate(follow_ups, start=1):
            follow_up_id = fu_map.get((qa_id, i))
            if follow_up_id is None:
                print(f"  ⚠  Missing follow_up for QA {qa_id} urutan {i}")
                skipped += len(fu.get("options", []))
                continue
            for opt in fu.get("options", []):
                cursor.execute(
                    """
                    INSERT INTO tb_follow_option (follow_up_id, label, value)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE value = VALUES(value)
                    """,
                    (follow_up_id, opt["label"], opt["value"]),
                )
                count += 1
    return count, skipped


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_follow_option.py <path-to-json> [--rollback]")
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
                print("🧹 Rolling back tb_follow_option (cascades to next_qas)...")
                rollback(cursor)
                print("   Cleared.")

            print("🔍 Loading follow_up map...")
            fu_map = build_follow_up_map(cursor)
            print(f"   Loaded {len(fu_map)} follow-ups")

            print("📝 Inserting into tb_follow_option...")
            inserted, skipped = import_follow_option(records, cursor, fu_map)
            conn.commit()

            print(f"✅ Inserted/updated {inserted} rows into tb_follow_option")
            if skipped:
                print(f"   ⚠  Skipped {skipped} rows")

            cursor.execute("SELECT COUNT(*) AS c FROM tb_follow_option")
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