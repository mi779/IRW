"""Import WordNet 3.1 synonyms, antonyms and phrase collocations into MySQL.

Data source: wordnet-db 3.1.14 (Princeton WordNet 3.1 database files),
extracted to backend/data/wordnet/dict/. Download via npm mirror:
    https://registry.npmmirror.com/wordnet-db/-/wordnet-db-3.1.14.tgz

What gets imported:
    word_relations  synonyms: lemma's co-members of a synset (top senses only)
                    antonyms: WordNet "!" lexical pointers, stored both ways
    word_phrases    multi-word lemmas (look_after, take_care_of ...) attached
                    to each content-word component (look; take, care)

Chinese glosses for related words / phrases are backfilled from the words
table (ECDICT definitions) in a final UPDATE JOIN.

Idempotent: INSERT IGNORE on the unique keys; safe to re-run.

Usage (from backend/):
    python scripts/import_wordnet.py
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from core.database import engine

DICT_DIR = Path(__file__).resolve().parent.parent / "data" / "wordnet" / "dict"
BATCH_SIZE = 5000
POS_FILES = ["noun", "verb", "adj", "adv"]
# How many senses per lemma to harvest (WordNet lists senses roughly by
# frequency, so low ranks = most common meanings).
MAX_SENSES_SYNONYM = 5
MAX_SENSES_PHRASE = 3
# Function words never receive phrase attachments ("look after" -> look only).
FUNC_WORDS = {
    "a", "an", "the", "and", "or", "but", "of", "to", "in", "on", "at", "by",
    "for", "with", "from", "into", "onto", "up", "out", "off", "not", "no",
    "as", "is", "are", "be", "been", "was", "were", "am", "do", "does", "did",
    "it", "its", "he", "she", "they", "we", "you", "i", "one's", "ones",
}


def parse_data_file(path: Path) -> dict:
    """Parse data.* -> {offset: (pos, [words], gloss, [(tgt_offset, src_tgt)])}.

    Only "!" (antonym) pointers are kept; everything else is not needed.
    Header/license lines are indented with spaces; records start with a digit.
    """
    synsets = {}
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line[:1].isdigit():
                continue
            toks = line.split(" ")
            offset = toks[0]
            ss_type = toks[2]
            pos = "a" if ss_type == "s" else ss_type  # adjective satellite
            w_cnt = int(toks[3], 16)
            i = 4
            words = []
            for _ in range(w_cnt):
                words.append(toks[i])
                i += 2  # skip lex_id
            p_cnt = int(toks[i])
            i += 1
            antonyms = []
            for _ in range(p_cnt):
                sym, tgt, _tpos, src_tgt = toks[i], toks[i + 1], toks[i + 2], toks[i + 3]
                i += 4
                if sym == "!":
                    antonyms.append((tgt, src_tgt, len(words)))
            gloss = line.split(" | ", 1)[1].strip() if " | " in line else None
            synsets[offset] = (pos, words, gloss, antonyms)
    return synsets


def parse_index_file(path: Path) -> dict:
    """Parse index.* -> {lemma: [synset offsets in frequency rank order]}."""
    senses = {}
    with open(path, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if not line or line[0] in " \n":
                continue
            toks = line.split()
            lemma = toks[0]
            cnt = int(toks[2])
            senses[lemma] = toks[len(toks) - cnt :] if cnt else []
    return senses


async def load_word_ids() -> dict:
    """spelling -> id map from the words table (770k entries)."""
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT id, spelling FROM words"))
        return {spelling: wid for wid, spelling in rows.fetchall()}


async def insert_batches(conn, sql, rows, label: str) -> int:
    inserted = 0
    for start in range(0, len(rows), BATCH_SIZE):
        batch = rows[start : start + BATCH_SIZE]
        result = await conn.execute(sql, batch)
        inserted += result.rowcount
        print(f"  {label}: {min(start + BATCH_SIZE, len(rows))}/{len(rows)}", flush=True)
    return inserted


async def main() -> None:
    if not DICT_DIR.exists():
        print(f"ERROR: {DICT_DIR} not found. Extract wordnet-db first.")
        sys.exit(1)

    # ---- 1. Parse WordNet files -------------------------------------------
    synsets: dict = {}
    for name in POS_FILES:
        synsets.update(parse_data_file(DICT_DIR / f"data.{name}"))
    print(f"[1/5] Parsed {len(synsets)} synsets")

    lemma_senses: dict = {}
    for name in POS_FILES:
        lemma_senses.update(parse_index_file(DICT_DIR / f"index.{name}"))
    print(f"[1/5] Parsed {len(lemma_senses)} lemmas")

    word_ids = await load_word_ids()
    print(f"[1/5] Loaded {len(word_ids)} word ids from MySQL")

    # ---- 2. Synonyms + phrases from index order ---------------------------
    # (word_id, relation, related_word) -> (pos, sense_rank)
    relations: dict = {}
    # (word_id, phrase) -> (pos, gloss_en, sense_rank)
    phrases: dict = {}

    for lemma, offsets in lemma_senses.items():
        if "_" in lemma:
            parts = lemma.split("_")
            if not (2 <= len(parts) <= 4):
                continue
            comps = [p for p in parts if p not in FUNC_WORDS and len(p) >= 2]
            if not comps:
                continue
            phrase = lemma.replace("_", " ")
            for rank, off in enumerate(offsets[:MAX_SENSES_PHRASE]):
                entry = synsets.get(off)
                if entry is None:
                    continue
                pos, _words, gloss, _ants = entry
                for comp in comps:
                    wid = word_ids.get(comp)
                    if wid is None:
                        continue
                    key = (wid, phrase)
                    if key not in phrases or rank < phrases[key][2]:
                        phrases[key] = (pos, gloss, rank)
            continue

        wid = word_ids.get(lemma)
        if wid is None:
            continue
        for rank, off in enumerate(offsets[:MAX_SENSES_SYNONYM]):
            entry = synsets.get(off)
            if entry is None:
                continue
            pos, words, _gloss, _ants = entry
            singles = [w for w in words if "_" not in w]
            if len(singles) < 2:
                continue
            for other in singles:
                if other == lemma:
                    continue
                key = (wid, "synonym", other)
                if key not in relations or rank < relations[key][1]:
                    relations[key] = (pos, rank)

    # ---- 3. Antonyms from "!" lexical pointers ----------------------------
    for offset, (_pos, words, _gloss, ants) in synsets.items():
        for tgt_offset, src_tgt, _wcnt in ants:
            src_n = int(src_tgt[:2], 16)
            tgt_n = int(src_tgt[2:], 16)
            tgt_entry = synsets.get(tgt_offset)
            if tgt_entry is None:
                continue
            src_words = words if src_n == 0 else [words[src_n - 1]] if src_n <= len(words) else []
            tgt_words = (
                tgt_entry[1] if tgt_n == 0
                else [tgt_entry[1][tgt_n - 1]] if tgt_n <= len(tgt_entry[1])
                else []
            )
            for sw in src_words:
                sw_id = word_ids.get(sw)
                if sw_id is None:
                    continue
                for tw in tgt_words:
                    key = (sw_id, "antonym", tw)
                    if key not in relations:
                        relations[key] = (_pos, 0)

    print(f"[2/5] Built {len(relations)} relations, {len(phrases)} phrase links")

    # ---- 4. Insert ---------------------------------------------------------
    rel_sql = text(
        "INSERT IGNORE INTO word_relations "
        "(word_id, related_word, relation, pos, sense_rank) "
        "VALUES (:word_id, :related_word, :relation, :pos, :sense_rank)"
    )
    rel_rows = [
        {
            "word_id": wid, "related_word": rw, "relation": rel,
            "pos": pos, "sense_rank": rank,
        }
        for (wid, rel, rw), (pos, rank) in relations.items()
    ]
    phrase_sql = text(
        "INSERT IGNORE INTO word_phrases "
        "(word_id, phrase, pos, gloss_en, sense_rank) "
        "VALUES (:word_id, :phrase, :pos, :gloss_en, :sense_rank)"
    )
    phrase_rows = [
        {
            "word_id": wid, "phrase": ph, "pos": pos,
            "gloss_en": gloss, "sense_rank": rank,
        }
        for (wid, ph), (pos, gloss, rank) in phrases.items()
    ]

    async with engine.begin() as conn:
        n_rel = await insert_batches(conn, rel_sql, rel_rows, "relations")
        n_phr = await insert_batches(conn, phrase_sql, phrase_rows, "phrases")
    print(f"[3/5] Inserted {n_rel} relations, {n_phr} phrase links")

    # ---- 5. Backfill Chinese glosses from the words table ------------------
    async with engine.begin() as conn:
        r1 = await conn.execute(text(
            "UPDATE word_relations wr JOIN words w ON w.spelling = wr.related_word "
            "SET wr.gloss_cn = JSON_UNQUOTE(JSON_EXTRACT(w.definitions, '$[0].text')) "
            "WHERE wr.gloss_cn IS NULL"
        ))
        r2 = await conn.execute(text(
            "UPDATE word_phrases wp JOIN words w ON w.spelling = wp.phrase "
            "SET wp.gloss_cn = JSON_UNQUOTE(JSON_EXTRACT(w.definitions, '$[0].text')) "
            "WHERE wp.gloss_cn IS NULL"
        ))
    print(f"[4/5] Backfilled gloss_cn: {r1.rowcount} relations, {r2.rowcount} phrases")

    await engine.dispose()
    print("[5/5] WordNet import done.")


if __name__ == "__main__":
    asyncio.run(main())
