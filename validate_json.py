#!/usr/bin/env python3
"""
validate_json.py — Validate the structure and integrity of cengkeh-data.json
before importing.

Checks:
    1. JSON parses
    2. Top-level keys exist
    3. Each record has all required fields
    4. IDs are unique and follow Q### pattern
    5. Type is one of the valid types
    6. Category is one of the valid categories
    7. Sources reference valid source codes
    8. related_qas reference existing QA IDs
    9. follow_ups[].options[].next_qas reference existing QA IDs
    10. No duplicate keywords within a record
"""

import json
import sys
from pathlib import Path
from collections import Counter


def main(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    errors = []
    warnings = []

    # ---------------------------------------------------------------
    # Top-level
    # ---------------------------------------------------------------
    for key in ["schema_version", "categories", "types", "source_catalog", "records"]:
        if key not in data:
            errors.append(f"Missing top-level key: {key}")

    if errors:
        report(errors, warnings)
        return

    categories = set(data["categories"])
    types = set(data["types"])
    source_codes = set(data["source_catalog"].keys())
    records = data["records"]

    print(f"📖 Loaded {len(records)} records")
    print(f"📁 Categories: {len(categories)}")
    print(f"🏷️  Types: {types}")
    print(f"📚 Sources: {source_codes}")
    print()

    # ---------------------------------------------------------------
    # Collect all QA IDs (first pass)
    # ---------------------------------------------------------------
    all_ids = [r.get("id") for r in records]
    id_set = set(all_ids)

    # Check for duplicates
    duplicates = [id_ for id_, count in Counter(all_ids).items() if count > 1]
    if duplicates:
        errors.append(f"Duplicate IDs: {duplicates}")

    # Check ID format
    for qa_id in all_ids:
        if not isinstance(qa_id, str) or not qa_id.startswith("Q") or not qa_id[1:].isdigit():
            errors.append(f"Invalid ID format: {qa_id!r}")

    # ---------------------------------------------------------------
    # Per-record validation (second pass)
    # ---------------------------------------------------------------
    required_fields = ["id", "category", "type", "question", "variations",
                       "keywords", "answer", "follow_ups", "related_qas", "sources"]

    for rec in records:
        qa_id = rec.get("id", "<no id>")

        # Required fields
        for field in required_fields:
            if field not in rec:
                errors.append(f"{qa_id}: missing field '{field}'")

        # Category
        cat = rec.get("category")
        if cat not in categories:
            errors.append(f"{qa_id}: unknown category '{cat}'")

        # Type
        t = rec.get("type")
        if t not in types:
            errors.append(f"{qa_id}: unknown type '{t}'")

        # Answer
        if not rec.get("answer", "").strip():
            warnings.append(f"{qa_id}: empty answer")

        # Sources
        for src in rec.get("sources", []):
            if src not in source_codes:
                errors.append(f"{qa_id}: source '{src}' not in source_catalog")

        # related_qas — must exist (skip self-references)
        for related in rec.get("related_qas", []):
            if related not in id_set:
                errors.append(f"{qa_id}: related_qas '{related}' not found")
            if related == qa_id:
                warnings.append(f"{qa_id}: self-reference in related_qas")

        # variations — should be non-empty list of strings
        variations = rec.get("variations", [])
        if not variations:
            warnings.append(f"{qa_id}: no variations")
        for v in variations:
            if not isinstance(v, str) or not v.strip():
                errors.append(f"{qa_id}: empty or non-string variation")

        # keywords — should be non-empty list of strings, no duplicates
        keywords = rec.get("keywords", [])
        if not keywords:
            warnings.append(f"{qa_id}: no keywords")
        if len(keywords) != len(set(keywords)):
            errors.append(f"{qa_id}: duplicate keywords {keywords}")

        # follow_ups — deep validation
        for fu in rec.get("follow_ups", []):
            fu_id = fu.get("id", "<no id>")
            if not fu.get("question"):
                errors.append(f"{qa_id}/{fu_id}: empty follow-up question")
            if not fu.get("options"):
                errors.append(f"{qa_id}/{fu_id}: no options")

            for opt in fu.get("options", []):
                if not opt.get("label"):
                    errors.append(f"{qa_id}/{fu_id}: option missing label")
                if not opt.get("value"):
                    errors.append(f"{qa_id}/{fu_id}: option missing value")
                for nxt in opt.get("next_qas", []):
                    if nxt not in id_set:
                        errors.append(f"{qa_id}/{fu_id}/{opt.get('value')}: "
                                      f"next_qas '{nxt}' not found")

    # ---------------------------------------------------------------
    # Report
    # ---------------------------------------------------------------
    report(errors, warnings)


def report(errors, warnings):
    if warnings:
        print(f"⚠️  {len(warnings)} warning(s):")
        for w in warnings[:20]:
            print(f"   • {w}")
        if len(warnings) > 20:
            print(f"   ... and {len(warnings) - 20} more")
        print()

    if errors:
        print(f"❌ {len(errors)} error(s):")
        for e in errors[:50]:
            print(f"   • {e}")
        if len(errors) > 50:
            print(f"   ... and {len(errors) - 50} more")
        print()
        print("❌ Validation FAILED")
        sys.exit(1)

    print("✅ Validation PASSED")


if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "cengkeh-data.json"
    main(path)