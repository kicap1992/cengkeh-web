"""
Import records[].follow_ups[].options[].next_qas[] into tb_option_next_qa.

Since tb_option_next_qa.option_id is a FK to tb_follow_option (which
has an auto-generated id), we first build a lookup map from
(follow_up_id, label) -> option_id, then use it during insertion.

QA IDs are already numeric (via qa_id_to_int), so no QA lookup needed.

Usage:
    python import_option_next_qa.py <path-to-json>
    python import_option_next_qa.py <path-to-json> --rollback
"""

import sys

from db import get_connection, load_json, qa_id_to_int


def rollback(cursor):
    """Wipe tb_option_next_qa."""
    cursor.execute("DELETE FROM tb_option_next_qa")


def build_option_map(cursor):
    """Return {(follow_up_id, label): option_id}."""
    cursor.execute("SELECT id, follow_up_id, label FROM tb_follow_option")
    return {
        (row["follow_up_id"], row["label"]): row["id"]
        for row in cursor.fetchall()
    }


def build_follow_up_map(cursor):
    """Return {(pertanyaan_id, urutan): follow_up_id}."""
    cursor.execute("SELECT id, pertanyaan_id, urutan FROM tb_follow_up")
    return {
        (row["pertanyaan_id"], row["urutan"]): row["id"]
        for row in cursor.fetchall()
    }


def import_option_next_qa(records, cursor, fu_map, opt_map):
    """Insert option->next_qa pairs. Returns (inserted, skipped)."""
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
                skipped += sum(len(o.get("next_qas", [])) for o in fu.get("options", []))
                continue
            for opt in fu.get("options", []):
                option_id = opt_map.get((follow_up_id, opt["label"]))
                if option_id is None:
                    skipped += len(opt.get("next_qas", []))
                    continue
                for next_qa_str in opt.get("next_qas", []):
                    next_qa_id = qa_id_to_int(next_qa_str)
                    cursor.execute(
                        """
                        INSERT INTO tb_option_next_qa (option_id, next_qa_id)
                        VALUES (%s, %s)
                        ON DUPLICATE KEY UPDATE option_id = option_id
                        """,
                        (option_id, next_qa_id),
                    )
                    count += 1
    return count, skipped


def main():
    if len(sys.argv) < 2:
        print("Usage: python import_option_next_qa.py <path-to-json> [--rollback]")
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
                print("🧹 Rolling back tb_option_next_qa...")
                rollback(cursor)
                print("   Cleared.")

            print("🔍 Loading follow_up map...")
            fu_map = build_follow_up_map(cursor)
            print(f"   Loaded {len(fu_map)} follow-ups")

            print("🔍 Loading option map...")
            opt_map = build_option_map(cursor)
            print(f"   Loaded {len(opt_map)} options")

            print("📝 Inserting into tb_option_next_qa...")
            inserted, skipped = import_option_next_qa(records, cursor, fu_map, opt_map)
            conn.commit()

            print(f"✅ Inserted/updated {inserted} rows into tb_option_next_qa")
            if skipped:
                print(f"   ⚠  Skipped {skipped} rows")

            cursor.execute("SELECT COUNT(*) AS c FROM tb_option_next_qa")
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