"""Parse colingoldberg/morphemes.json into a staging TSV.

Input shape (2435 groups keyed by group name):
  {"Afro": {"forms": [{"root": "Afro-", "form": "Afro", "loc": "prefix",
                       "attach_to": ["noun"], "category": "relating to"}],
            "meaning": ["relating to Africa"], "origin": "", "etymology": "",
            "examples": ["Afro-American", "Afro-Caribbean"]}}

loc mapping: prefix -> prefixes表, suffix -> suffixes表, embedded -> roots表.

Output:
  stg_mf_morphs  text, kind, meaning_en, attach_to, category, examples_json, origin
  stg_mf_links   example_word, text, kind, evidence   (来自组内 examples 列表,
                kind 取组内优先级 root > prefix/suffix 的形式)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from pipeline.common import get_logger, tsv_row
from pipeline.config import DOWNLOAD_DIR, STAGING_DIR

log = get_logger("parse_morphemes")

KIND_BY_LOC = {"prefix": "prefix", "suffix": "suffix", "embedded": "root"}

MAX_TEXT = 50


def normalize(text: str) -> str:
    return (text or "").strip().strip("-*").strip().lower()


def main() -> None:
    src = DOWNLOAD_DIR / "morphemes.json"
    if not src.exists():
        log.error(f"input not found: {src}")
        sys.exit(1)

    data = json.loads(src.read_text(encoding="utf-8"))
    stats = {"groups": 0, "morphs": 0, "skipped_loc": 0, "skipped_text": 0,
             "example_links": 0}
    t0 = time.time()

    with open(STAGING_DIR / "stg_mf_morphs.tsv", "w", encoding="utf-8") as out, \
            open(STAGING_DIR / "stg_mf_links.tsv", "w", encoding="utf-8") as lout:
        for group_key, g in sorted(data.items()):
            stats["groups"] += 1
            meaning_en = "; ".join(str(m) for m in (g.get("meaning") or []))[:500] or None
            examples = [str(e).strip() for e in (g.get("examples") or [])
                        if str(e).strip() and len(str(e)) <= 100]
            origin_parts = [p for p in (g.get("origin") or "", g.get("etymology") or "") if p]
            origin = "; ".join(origin_parts)[:500] or None
            ex_json = json.dumps(examples[:20], ensure_ascii=False) if examples else None

            texts_kinds = []  # [(text, kind)] 有效形式, 供示例链接选目标
            for f in g.get("forms") or []:
                loc = f.get("loc") or ""
                kind = KIND_BY_LOC.get(loc)
                if not kind:
                    stats["skipped_loc"] += 1
                    continue
                text = normalize(f.get("form") or f.get("root") or "")
                if not text or len(text) > MAX_TEXT:
                    stats["skipped_text"] += 1
                    continue
                attach = f.get("attach_to") or ([f["pos"]] if f.get("pos") else [])
                out.write(tsv_row([
                    text,
                    kind,
                    meaning_en,
                    ";".join(str(a) for a in attach)[:100] or None,
                    (f.get("category") or "")[:100] or None,
                    ex_json,
                    origin,
                ]))
                stats["morphs"] += 1
                if (text, kind) not in texts_kinds:
                    texts_kinds.append((text, kind))

            # 组的示例词 -> 词素关联(kind 优先 root), 服务词根分组检索
            if examples and texts_kinds:
                prefer_root = [(t, k) for t, k in texts_kinds if k == "root"]
                targets = prefer_root or texts_kinds
                ev = ("morphemes.json examples: "
                      + ", ".join(examples[:4]))[:300]
                for word in examples:
                    for text, kind in targets:
                        if word.lower() == text:
                            continue
                        lout.write(tsv_row([word, text, kind, ev]))
                        stats["example_links"] += 1

    stats["elapsed_sec"] = round(time.time() - t0, 1)
    log.info(f"DONE {json.dumps(stats, ensure_ascii=False)}")
    from pipeline.common import save_state
    save_state("parse_morphemes", {"finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                   "input": str(src), **stats})


if __name__ == "__main__":
    main()
