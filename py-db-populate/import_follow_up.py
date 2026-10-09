"""
Import records[].follow_ups[] into tb_follow_up.

For each QA record, iterate its follow_ups array and insert one row
per follow-up into tb_follow_up. The 'urutan' column stores the
position of the follow-up within its parent (1-based).

Usage:
    python import_follow_up.py <path-to-json>
    python import_follow_up.py <path-to-json> --rollback
"""

import sys

from db import get_connection, load_json, qa_id_to_int


def rollback(cursor):
    """Wipe tb_follow_up (cascades to options and next_qas)."""
    cursor.execute("DELETE FROM tb_follow_up")


def import_follow_up(records, cursor):
    """Insert follow-ups. Returns (inserted, qa_with_followups)."""
    count = 0
    qa_count = 0
    for rec in records:
        follow_ups = rec.get("follow_ups", [])
        if not follow_ups:
            continue
        qa_id = qa_id_to_int(rec["id"])
        qa_count += 1
        for i, fu in enumerate(follow_ups, start=1):
            cursor.execute(
                """
                INSERT INTO tb_follow_up (pertanyaan_id, urutan, pertanyaan)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE pertanyaan = VALUES(pertanyaan)
                """,
                (qa_id, i, fu["question"]),
            )
            count += 1
    return count, qa_count


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_follow_up.py <path-to-json> [--rollback]")
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
                print("🧹 Rolling back tb_follow_up (cascades down)...")
                rollback(cursor)
                print("   Cleared.")

            print("📝 Inserting into tb_follow_up...")
            inserted, qa_count = import_follow_up(records, cursor)
            conn.commit()

            print(f"✅ Inserted/updated {inserted} follow-ups "
                  f"(across {qa_count} diagnostic QAs)")

            cursor.execute("SELECT COUNT(*) AS c FROM tb_follow_up")
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