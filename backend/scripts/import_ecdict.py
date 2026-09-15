"""Import the open-source ECDICT dictionary (English->Chinese) into MySQL.

Downloads: https://github.com/skywind3000/ECDICT (ecdict.csv, ~770k entries)
Expected at: backend/data/ecdict.csv

Field mapping (ECDICT -> words table):
    word        -> spelling
    phonetic    -> phonetics {"uk": ...}
    translation -> definitions [{"pos": "n.", "text": "苹果；梨"}, ...]
    translation -> part_of_speech (first parsed pos)
    tag         -> tags JSON array (e.g. ["cet4","ky"])

Idempotent: INSERT IGNORE on the unique spelling key — existing words
(e.g. hand-curated seed data with morpheme links) are left untouched.
Re-running the script only fills in newly added dictionary entries.

Usage (from backend/):
    python scripts/import_ecdict.py
"""

import asyncio
import csv
import json
import re
import sys
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from core.database import engine

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "ecdict.csv"
BATCH_SIZE = 5000

# Matches a leading part-of-speech marker: "n. / vt. / suf." or "[网络] / [荷兰语]"
POS_RE = re.compile(r"^((?:[a-zA-Z]+\.)|\[[^\]]+\])\s*(.*)$")

# ECDICT stores multi-line translations with a LITERAL backslash-n (two
# chars), not real newlines. Handle both just in case.
LINE_SPLIT_RE = re.compile(r"\n|\\n")


def parse_translation(translation: str) -> list[dict]:
    """Split an ECDICT translation blob into structured definitions.

    Example input (literal \\n separators):
        "n. 罩；风帽\\nv. 覆盖\\n[网络] 胡德"
    Output:
        [{"pos": "n.", "text": "罩；风帽"},
         {"pos": "v.", "text": "覆盖"},
         {"pos": "[网络]", "text": "胡德"}]
    """
    defs = []
    for line in LINE_SPLIT_RE.split(translation or ""):
        line = line.strip()
        if not line:
            continue
        m = POS_RE.match(line)
        if m and m.group(2):
            defs.append({"pos": m.group(1), "text": m.group(2).strip()})
        else:
            defs.append({"pos": None, "text": line})
    return defs


def convert_row(row: dict) -> Optional[dict]:
    """Map one ECDICT CSV row to a words-table insert parameter dict."""
    spelling = (row.get("word") or "").strip()
    if not spelling or len(spelling) > 100:
        return None

    phonetic = (row.get("phonetic") or "").strip()
    phonetics = json.dumps({"uk": phonetic}, ensure_ascii=False) if phonetic else None

    definitions = parse_translation(row.get("translation") or "")
    definitions_json = (
        json.dumps(definitions, ensure_ascii=False) if definitions else None
    )

    pos = next((d["pos"] for d in definitions if d["pos"]), None)
    if pos and len(pos) > 20:
        pos = None

    tag_str = (row.get("tag") or "").strip()
    tags = json.dumps(tag_str.split()) if tag_str else None

    return {
        "spelling": spelling,
        "phonetics": phonetics,
        "definitions": definitions_json,
        "part_of_speech": pos,
        "tags": tags,
    }


async def main() -> None:
    if not CSV_PATH.exists():
        print(f"ERROR: {CSV_PATH} not found. Download it first from "
              "https://github.com/skywind3000/ECDICT")
        sys.exit(1)

    insert_sql = text(
        "INSERT IGNORE INTO words "
        "(spelling, phonetics, definitions, part_of_speech, tags) "
        "VALUES (:spelling, :phonetics, :definitions, :part_of_speech, :tags)"
    )

    total = inserted = skipped_bad = 0
    batch: list[dict] = []

    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total += 1
            params = convert_row(row)
            if params is None:
                skipped_bad += 1
                continue
            batch.append(params)
            if len(batch) >= BATCH_SIZE:
                # Commit per batch: a failure mid-import keeps finished
                # batches, and INSERT IGNORE makes a re-run idempotent.
                async with engine.begin() as conn:
                    result = await conn.execute(insert_sql, batch)
                inserted += result.rowcount
                batch = []
                if total % 50000 < BATCH_SIZE:
                    print(f"  ... {total} rows read, {inserted} inserted", flush=True)
        if batch:
            async with engine.begin() as conn:
                result = await conn.execute(insert_sql, batch)
            inserted += result.rowcount

    await engine.dispose()
    print(
        f"Import done: read={total}, inserted={inserted}, "
        f"skipped(duplicate/invalid)={total - inserted - skipped_bad}"
    )


if __name__ == "__main__":
    asyncio.run(main())
