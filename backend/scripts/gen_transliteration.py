"""Generate Chinese transliterations (中文音译/拟音) for the ECDICT words.

The phonetic (IPA) data is already in `words.phonetics` (uk/us variants).
This script converts each phonetic spelling into a Chinese-character
approximation of the pronunciation, e.g.:

    abandon     /əˈbændən/   -> 额班德恩
    coffee      /ˈkɒfi/      -> 咖啡     (loanword override)
    perspective /pəˈspektɪv/ -> 佩斯佩克提夫

Well-established loanword transliterations (coffee->咖啡, sofa->沙发 ...)
are kept in a small override table; everything else is generated with an
IPA -> 汉字 syllable mapper (onset-consonant + vowel merged into one
natural char, e.g. k+ɒ->科, f+i->菲).

Result is stored in `words.transliteration` (added by this script if the
column is missing). Idempotent: re-running regenerates all values.

Usage (from backend/):
    python scripts/gen_transliteration.py [--limit N] [--dry-run]
"""

import asyncio
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from core.database import engine
from pipeline.translit import transliterate  # noqa: E402 (single source of truth)


async def ensure_column():
    async with engine.begin() as conn:
        await conn.execute(text(
            "ALTER TABLE words ADD COLUMN transliteration VARCHAR(64) NULL"
        ))


async def main():
    dry_run = "--dry-run" in sys.argv
    limit = None
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    async with engine.begin() as conn:
        cols = (await conn.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_schema=DATABASE() AND table_name='words' "
            "AND column_name='transliteration'"
        ))).scalar_one()
        if not cols:
            await conn.execute(text(
                "ALTER TABLE words ADD COLUMN transliteration VARCHAR(64) NULL"
            ))
            print("added column words.transliteration")

    # demo output first
    demo = {"abandon": {"uk": "ә'bændәn"}, "coffee": {"uk": "'kɒfi"},
            "perspective": {"uk": "/pəˈspektɪv/"}, "hello": {"uk": "hə'ləʊ"},
            "water": {"uk": "'wɔːtə"}, "sofa": {"uk": "'səʊfə"}}
    for w, ph in demo.items():
        print(f"  demo {w:14s} -> {transliterate(w, ph)}")

    async with engine.begin() as conn:
        q = "SELECT id, spelling, phonetics FROM words"
        if limit:
            q += f" LIMIT {limit}"
        rows = (await conn.execute(text(q))).fetchall()

    print(f"loaded {len(rows)} words")
    updates = []
    skipped = 0
    for rid, spelling, phonetics in rows:
        try:
            ph = json.loads(phonetics) if isinstance(phonetics, str) else phonetics
        except (json.JSONDecodeError, TypeError):
            ph = None
        val = transliterate(spelling, ph) if ph else ""
        if val:
            updates.append({"id": rid, "t": val})
        else:
            skipped += 1
    print(f"generated {len(updates)}, no-phonetic/empty {skipped}")

    if dry_run:
        return

    stmt = text("UPDATE words SET transliteration=:t WHERE id=:id")
    batch = 2000
    done = 0
    for i in range(0, len(updates), batch):
        # one short transaction per batch: no long row locks
        async with engine.begin() as conn:
            await conn.execute(stmt, updates[i:i + batch])
        done = min(i + batch, len(updates))
        if done % 50000 == 0 or done == len(updates):
            print(f"  updated {done}/{len(updates)}")
    await engine.dispose()
    print(f"done: {len(updates)} transliterations written "
          f"({math.ceil(len(updates)/batch)} batches)")


if __name__ == "__main__":
    asyncio.run(main())
