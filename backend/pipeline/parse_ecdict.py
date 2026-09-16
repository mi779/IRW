"""Stream-parse ECDICT csv into staging TSVs.

ECDICT columns: word,phonetic,definition,translation,pos,collins,oxford,tag,
                bnc,frq,exchange,detail,audio

Output staging files:
  stg_ec_words  spelling, phonetic_uk, defs_json, pos, collins, oxford, tags_json, bnc, frq
  stg_ec_forms  spelling, form, form_tags   (from the exchange field)

Mapping follows the project's existing convention (scripts/import_ecdict.py):
  translation -> definitions [{"pos": "n.", "text": "..."}] (literal \\n splits)
  phonetic    -> phonetics {"uk": ...}
  tag         -> tags JSON array
  bnc/frq     -> word frequency columns
audio/detail are dropped (URL pattern / bulky, out of scope).
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
from pathlib import Path

from pipeline.common import get_logger, tsv_row
from pipeline.config import DOWNLOAD_DIR, STAGING_DIR

log = get_logger("parse_ecdict")

MAX_SPELLING = 100

# Matches a leading part-of-speech marker: "n. / vt. / suf." or "[网络] / [荷兰语]"
POS_RE = re.compile(r"^((?:[a-zA-Z]+\.)|\[[^\]]+\])\s*(.*)$")

# ECDICT stores multi-line translations with a LITERAL backslash-n
LINE_SPLIT_RE = re.compile(r"\n|\\n")

EXCHANGE_TAGS = {
    "p": "过去式", "d": "过去分词", "i": "现在分词",
    "3": "第三人称单数", "r": "比较级", "t": "最高级",
    "s": "复数形式", "0": "原形", "1": "原形",
}


def parse_translation(translation: str) -> list:
    """Split an ECDICT translation blob into structured definitions."""
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


def parse_exchange(exchange: str, word: str) -> list:
    """Parse 'p:did/d:done/i:doing/3:does' into [(form, tag), ...]."""
    out = []
    for part in (exchange or "").split("/"):
        if ":" not in part:
            continue
        code, form = part.split(":", 1)
        code, form = code.strip(), form.strip()
        if not form or form == word or len(form) > 150:
            continue
        tag = EXCHANGE_TAGS.get(code, code)
        out.append((form, tag))
    return out


def to_int(v) -> int | None:
    v = (v or "").strip()
    if not v:
        return None
    try:
        return int(v)
    except ValueError:
        return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="只处理前N行(小批量贯通验证用)")
    args = ap.parse_args()

    src = DOWNLOAD_DIR / "ecdict.csv"
    if not src.exists():
        log.error(f"input not found: {src}")
        sys.exit(1)

    f_words = open(STAGING_DIR / "stg_ec_words.tsv", "w", encoding="utf-8")
    f_forms = open(STAGING_DIR / "stg_ec_forms.tsv", "w", encoding="utf-8")
    stats = {"rows": 0, "words": 0, "skipped": 0, "forms": 0,
             "with_translation": 0, "with_phonetic": 0, "with_freq": 0}
    t0 = time.time()

    with open(src, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            stats["rows"] += 1
            if args.limit and stats["rows"] > args.limit:
                break
            spelling = (row.get("word") or "").strip()
            if not spelling or len(spelling) > MAX_SPELLING:
                stats["skipped"] += 1
                continue

            phonetic = (row.get("phonetic") or "").strip()
            defs = parse_translation(row.get("translation") or "")
            if defs:
                stats["with_translation"] += 1
            if phonetic:
                stats["with_phonetic"] += 1
            pos = next((d["pos"] for d in defs if d["pos"]), None)
            if pos and len(pos) > 20:
                pos = None

            tag_str = (row.get("tag") or "").strip()
            bnc = to_int(row.get("bnc"))
            frq = to_int(row.get("frq"))
            if bnc or frq:
                stats["with_freq"] += 1

            f_words.write(tsv_row([
                spelling,
                phonetic or None,
                json.dumps(defs, ensure_ascii=False) if defs else None,
                pos,
                to_int(row.get("collins")),
                to_int(row.get("oxford")),
                json.dumps(tag_str.split(), ensure_ascii=False) if tag_str else None,
                bnc,
                frq,
            ]))
            stats["words"] += 1

            for form, tag in parse_exchange(row.get("exchange") or "", spelling):
                f_forms.write(tsv_row([spelling, form, tag]))
                stats["forms"] += 1

            if stats["rows"] % 100000 == 0:
                rate = stats["rows"] / max(time.time() - t0, 1)
                log.info(f"rows={stats['rows']} words={stats['words']} "
                         f"({rate:.0f} rows/s)")

    f_words.close()
    f_forms.close()
    stats["elapsed_sec"] = round(time.time() - t0, 1)
    log.info(f"DONE {json.dumps(stats, ensure_ascii=False)}")

    from pipeline.common import save_state
    save_state("parse_ecdict", {"finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "input": str(src), "limit": args.limit, **stats})


if __name__ == "__main__":
    main()
