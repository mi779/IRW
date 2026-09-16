"""Merge staging TSVs into final load TSVs (no DB involved).

Inputs (produced by the parsers, sorted in place by this step):
  stg_ec_words   spelling, phonetic_uk, defs_json, pos, collins, oxford, tags_json, bnc, frq
  stg_ec_forms   spelling, form, form_tags
  stg_kw_words   spelling, spelling_norm, word_category, pos, defs_json, examples_json
  stg_kw_sounds  spelling, ipa, accent, note
  stg_kw_forms   spelling, form, form_tags
  stg_kw_etym    spelling, etymology_text
  stg_kw_morphs  text, kind, meaning_en, meaning_zh, source_lang, category
  stg_kw_links   spelling, morph_text, kind, relation_type, evidence, status
  stg_mf_morphs  text, kind, meaning_en, attach_to, category, examples_json, origin
  curated_zh.tsv (pipeline/data/) kind, text, meaning_zh

Outputs (ready for pipeline.import_db):
  load_words.tsv  spelling, phonetics_json, transliteration, definitions_json,
                  part_of_speech, tags_json, bnc, frq, category, examples_json
  load_morphs.tsv text, kind, meaning, description
  load_links.tsv  spelling, morph_text, kind, evidence
  load_forms.tsv  spelling, form, form_tags, source
  load_etym.tsv   spelling, etymology_text, source

Merge rules (see 任务规则):
- 词合并按 spelling 不区分大小写分组(MySQL 唯一键为 ci collation);
  展示拼写优先 ECDICT(小写规范), 其次 kaikki 全小写行。
- 中文释义/音标(uk)/tags/bnc/frq 来自 ECDICT; 例句/us音标/英文释义兜底/类别 来自 Kaikki。
- 词素 meaning 优先级: 人工 curated_zh > Wiktionary 中文 > Wiktionary 英文 > morphemes.json。
- 词形: ECDICT exchange(中文标签) 优先, Kaikki forms(英文标签) 补充, 按 (spelling, form) 去重。
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

from pipeline.common import get_logger, save_state, tsv_row
from pipeline.config import BACKEND_DIR, STAGING_DIR
from pipeline.parse_kaikki import CATEGORY_RANK
from pipeline.translit import transliterate

log = get_logger("merge")

CURATED_TSV = BACKEND_DIR / "pipeline" / "data" / "curated_zh.tsv"
MAX_MEANING = 200
MAX_DESC = 2000


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def tsv_field(v: str):
    """Inverse of common.tsv_escape for one raw field."""
    if v == r"\N":
        return None
    if "\\" not in v:
        return v
    out, i, n = [], 0, len(v)
    while i < n:
        c = v[i]
        if c == "\\" and i + 1 < n:
            nxt = v[i + 1]
            if nxt == "t":
                out.append("\t")
                i += 2
                continue
            if nxt == "n":
                out.append("\n")
                i += 2
                continue
            if nxt == "r":
                out.append("\r")
                i += 2
                continue
            if nxt == "\\":
                out.append("\\")
                i += 2
                continue
        out.append(c)
        i += 1
    return "".join(out)


def read_tsv_row(f):
    line = f.readline()
    if not line:
        return None
    return line.rstrip("\n").split("\t")


def sort_file(path: Path, extra_args=(), fold=False, unique=False) -> None:
    """In-place LC_ALL=C external sort of a TSV by column 1 (then 2)."""
    cmd = ["sort", "-t", "\t"]
    if fold:
        cmd.append("-f")
    if unique:
        cmd.append("-u")
    cmd += ["-k1,1", "-k2,2", "-o", str(path), str(path)]
    if extra_args:
        cmd = ["sort", "-t", "\t"] + list(extra_args) + ["-o", str(path), str(path)]
    env = dict(os.environ, LC_ALL="C")
    r = subprocess.run(cmd, env=env, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"sort failed for {path}: {r.stderr.decode()[:300]}")


class GroupReader:
    """Streaming grouped reader over a TSV sorted by its group key."""

    def __init__(self, path: Path):
        self.f = open(path, encoding="utf-8")
        self._next = read_tsv_row(self.f)

    def peek_key(self, key_of):
        return key_of(self._next) if self._next is not None else None

    def take_group(self, key, key_of):
        rows = []
        while self._next is not None and key_of(self._next) == key:
            rows.append(self._next)
            self._next = read_tsv_row(self.f)
        return rows

    def close(self):
        self.f.close()


def strip_slashes(ipa: str) -> str:
    s = (ipa or "").strip()
    if len(s) > 1 and s.startswith("/") and s.endswith("/"):
        return s[1:-1].strip()
    return s


# 与 LC_ALL=C sort -f 的折叠语义严格一致: 仅折叠 ASCII A-Z。
# Python str.lower() 还会映射非 ASCII(İ->i̇, K(U+212A)->k), 与 staging 文件
# 的 C 字节序排序冲突, 会打破多路归并的有序假设(曾导致 kw_rows 越界)。
_ASCII_FOLD = str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")


def fold_ascii(s: str) -> str:
    return s.translate(_ASCII_FOLD)


# ---------------------------------------------------------------------------
# words merge
# ---------------------------------------------------------------------------
def merge_words() -> dict:
    files = {name: STAGING_DIR / f"{name}.tsv"
             for name in ("stg_ec_words", "stg_kw_words", "stg_kw_sounds")}
    for name in ("stg_ec_words", "stg_kw_words", "stg_kw_sounds"):
        sort_file(files[name], fold=True)

    ec = GroupReader(files["stg_ec_words"])
    kw = GroupReader(files["stg_kw_words"])
    snd = GroupReader(files["stg_kw_sounds"])
    lower = lambda r: fold_ascii(r[0])  # noqa: E731

    out = open(STAGING_DIR / "load_words.tsv", "w", encoding="utf-8")
    stats = {"ec_only": 0, "kw_only": 0, "both": 0, "with_zh_defs": 0,
             "with_any_defs": 0, "with_phonetics": 0, "with_us": 0,
             "with_translit": 0, "with_examples": 0}

    while True:
        keys = [r.peek_key(lower) for r in (ec, kw, snd)]
        keys = [k for k in keys if k is not None]
        if not keys:
            break
        key = min(keys)
        ec_rows = ec.take_group(key, lower)
        kw_rows = kw.take_group(key, lower)
        snd_rows = snd.take_group(key, lower)

        ec_row = ec_rows[0] if ec_rows else None
        if ec_row and kw_rows:
            stats["both"] += 1
        elif ec_row:
            stats["ec_only"] += 1
        else:
            stats["kw_only"] += 1

        # canonical display spelling: ECDICT, else a fold-lowercase kaikki row
        if ec_row:
            spelling = ec_row[0]
        else:
            spelling = next((r[0] for r in kw_rows if r[0] == fold_ascii(r[0])),
                            kw_rows[0][0])

        # kaikki side: best-ranked entry supplies defs/examples/pos/category
        ranked = sorted(kw_rows, key=lambda r: CATEGORY_RANK.get(r[2], 99))
        kw_defs = next((v for v in (tsv_field(r[4]) for r in ranked)
                        if v is not None), None)
        kw_examples = next((v for v in (tsv_field(r[5]) for r in ranked)
                            if v is not None), None)
        kw_pos = next((v for v in (tsv_field(r[3]) for r in ranked)
                       if v is not None), None)
        category = ranked[0][2] if ranked else None

        uk_ipa = us_ipa = None
        for s in snd_rows:
            if s[2] == "uk" and not uk_ipa:
                uk_ipa = strip_slashes(tsv_field(s[1]) or "")
            elif s[2] == "us" and not us_ipa:
                us_ipa = strip_slashes(tsv_field(s[1]) or "")
        ec_uk = strip_slashes(tsv_field(ec_row[1]) or "") if ec_row else ""
        uk = ec_uk or uk_ipa or None

        phonetics = {}
        if uk:
            phonetics["uk"] = uk
        if us_ipa:
            phonetics["us"] = us_ipa
            stats["with_us"] += 1
        ph_json = json.dumps(phonetics, ensure_ascii=False) if phonetics else None
        if phonetics:
            stats["with_phonetics"] += 1

        defs = tsv_field(ec_row[2]) if ec_row else None
        if defs:
            stats["with_zh_defs"] += 1
        defs = defs or kw_defs
        if defs:
            stats["with_any_defs"] += 1

        pos = tsv_field(ec_row[3]) if ec_row else None
        pos = pos or kw_pos
        tags = tsv_field(ec_row[6]) if ec_row else None
        bnc = tsv_field(ec_row[7]) if ec_row else None
        frq = tsv_field(ec_row[8]) if ec_row else None

        translit = None
        if phonetics:
            t = transliterate(spelling, phonetics)
            if t:
                translit = t
                stats["with_translit"] += 1

        if kw_examples:
            stats["with_examples"] += 1

        out.write(tsv_row([spelling, ph_json, translit, defs, pos, tags,
                           bnc, frq, category, kw_examples]))

    out.close()
    for r in (ec, kw, snd):
        r.close()
    return stats


# ---------------------------------------------------------------------------
# morphemes merge
# ---------------------------------------------------------------------------
def merge_morphs() -> dict:
    kw_path = STAGING_DIR / "stg_kw_morphs.tsv"
    mf_path = STAGING_DIR / "stg_mf_morphs.tsv"
    sort_file(kw_path, unique=True)
    sort_file(mf_path)

    curated = {}
    if CURATED_TSV.exists():
        for line in CURATED_TSV.read_text(encoding="utf-8").splitlines():
            parts = line.split("\t")
            if len(parts) == 3 and parts[2].strip():
                curated[(parts[1].strip().lower(), parts[0].strip())] = \
                    parts[2].strip()
    else:
        log.warning(f"curated zh not found: {CURATED_TSV}")

    kw = GroupReader(kw_path)
    mf = GroupReader(mf_path)
    pair = lambda r: (r[0], r[1])  # noqa: E731

    out = open(STAGING_DIR / "load_morphs.tsv", "w", encoding="utf-8")
    stats = {"by_kind": {"root": 0, "prefix": 0, "suffix": 0},
             "meaning_curated": 0, "meaning_kw": 0, "meaning_mf": 0,
             "no_meaning": 0}

    while True:
        keys = [r.peek_key(pair) for r in (kw, mf)]
        keys = [k for k in keys if k is not None]
        if not keys:
            break
        key = min(keys)
        kw_rows = kw.take_group(key, pair)
        mf_rows = mf.take_group(key, pair)
        text, kind = key

        kw_en = next((tsv_field(r[2]) for r in kw_rows if r[2] != r"\N"), None)
        kw_zh = next((tsv_field(r[3]) for r in kw_rows if r[3] != r"\N"), None)
        kw_lang = next((tsv_field(r[4]) for r in kw_rows if r[4] != r"\N"), None)
        mf_en = next((tsv_field(r[2]) for r in mf_rows if r[2] != r"\N"), None)
        mf_attach = next((tsv_field(r[3]) for r in mf_rows if r[3] != r"\N"), None)
        mf_cat = next((tsv_field(r[4]) for r in mf_rows if r[4] != r"\N"), None)
        mf_ex = next((tsv_field(r[5]) for r in mf_rows if r[5] != r"\N"), None)
        mf_origin = next((tsv_field(r[6]) for r in mf_rows if r[6] != r"\N"), None)

        curated_zh = curated.pop((text, kind), None)

        meaning = (curated_zh or kw_zh or kw_en or mf_en or "")[:MAX_MEANING] or None
        if curated_zh:
            stats["meaning_curated"] += 1
        elif kw_zh or kw_en:
            stats["meaning_kw"] += 1
        elif mf_en:
            stats["meaning_mf"] += 1
        else:
            stats["no_meaning"] += 1

        desc_parts = []
        if curated_zh:
            desc_parts.append(f"[人工维护] {curated_zh}")
        if kw_zh or kw_en or kw_lang:
            p = "[Wiktionary] "
            p += f"en: {kw_en}" if kw_en else ""
            p += f" zh: {kw_zh}" if kw_zh else ""
            p += f" 来源语言: {kw_lang}" if kw_lang else ""
            desc_parts.append(p.strip())
        if mf_en or mf_cat or mf_attach or mf_ex or mf_origin:
            p = f"[morphemes.json] en: {mf_en}" if mf_en else "[morphemes.json]"
            if mf_cat:
                p += f"; 分类: {mf_cat}"
            if mf_attach:
                p += f"; 适用词性: {mf_attach}"
            if mf_origin:
                p += f"; 词源: {mf_origin}"
            if mf_ex:
                try:
                    words = json.loads(mf_ex)
                    if isinstance(words, list) and words:
                        p += "; 示例: " + ", ".join(str(w) for w in words[:8])
                except json.JSONDecodeError:
                    pass
            desc_parts.append(p)
        description = "；".join(desc_parts)[:MAX_DESC] or None

        out.write(tsv_row([text, kind, meaning, description]))
        stats["by_kind"][kind] = stats["by_kind"].get(kind, 0) + 1

    # curated entries with no counterpart in the other sources still get rows
    for (text, kind), zh in sorted(curated.items()):
        out.write(tsv_row([text, kind, zh[:MAX_MEANING],
                           f"[人工维护] {zh}"[:MAX_DESC]]))
        stats["by_kind"][kind] = stats["by_kind"].get(kind, 0) + 1
        stats["meaning_curated"] += 1

    out.close()
    kw.close()
    mf.close()
    return stats


# ---------------------------------------------------------------------------
# links merge (kaikki template links + morphemes.json example links)
# ---------------------------------------------------------------------------
def merge_links() -> dict:
    kw_path = STAGING_DIR / "stg_kw_links.tsv"
    mf_path = STAGING_DIR / "stg_mf_links.tsv"
    sort_file(kw_path, extra_args=["-u"])
    sort_file(mf_path, extra_args=["-u"])

    n_kw = n_mf = 0
    with open(STAGING_DIR / "load_links.tsv", "w", encoding="utf-8") as out:
        with open(kw_path, encoding="utf-8") as f:
            for line in f:
                cols = line.rstrip("\n").split("\t")
                if len(cols) < 6:
                    continue
                spelling, morph_text, kind, evidence = (tsv_field(c) for c in
                                                        (cols[0], cols[1], cols[2],
                                                         cols[4]))
                out.write(tsv_row([spelling, morph_text, kind, evidence, "kaikki"]))
                n_kw += 1
        with open(mf_path, encoding="utf-8") as f:
            for line in f:
                cols = line.rstrip("\n").split("\t")
                if len(cols) < 4:
                    continue
                spelling, morph_text, kind, evidence = (tsv_field(c) for c in
                                                        (cols[0], cols[1], cols[2],
                                                         cols[3]))
                out.write(tsv_row([spelling, morph_text, kind, evidence, "morphemes"]))
                n_mf += 1
    return {"links_kw": n_kw, "links_mf": n_mf}


# ---------------------------------------------------------------------------
# forms merge (ecdict exchange first, kaikki forms as supplement)
# ---------------------------------------------------------------------------
def merge_forms() -> dict:
    ec_path = STAGING_DIR / "stg_ec_forms.tsv"
    kw_path = STAGING_DIR / "stg_kw_forms.tsv"
    sort_file(ec_path, fold=True)
    sort_file(kw_path, fold=True)

    ec = GroupReader(ec_path)
    kw = GroupReader(kw_path)
    lower = lambda r: fold_ascii(r[0])  # noqa: E731

    out = open(STAGING_DIR / "load_forms.tsv", "w", encoding="utf-8")
    stats = {"ec": 0, "kw": 0}

    while True:
        keys = [r.peek_key(lower) for r in (ec, kw)]
        keys = [k for k in keys if k is not None]
        if not keys:
            break
        key = min(keys)
        ec_rows = ec.take_group(key, lower)
        kw_rows = kw.take_group(key, lower)
        seen = set()
        for r in ec_rows:
            if r[1] not in seen:
                out.write(tsv_row([r[0], r[1], tsv_field(r[2]), "ecdict"]))
                seen.add(r[1])
                stats["ec"] += 1
        for r in kw_rows:
            if r[1] not in seen:
                out.write(tsv_row([r[0], r[1], tsv_field(r[2]), "kaikki"]))
                seen.add(r[1])
                stats["kw"] += 1

    out.close()
    ec.close()
    kw.close()
    return stats


# ---------------------------------------------------------------------------
# etymology collapse (first non-empty per spelling)
# ---------------------------------------------------------------------------
def merge_etym() -> dict:
    src = STAGING_DIR / "stg_kw_etym.tsv"
    sort_file(src, fold=True)
    n = 0
    with open(STAGING_DIR / "load_etym.tsv", "w", encoding="utf-8") as out, \
            open(src, encoding="utf-8") as f:
        last_key = None
        for line in f:
            cols = line.rstrip("\n").split("\t", 1)
            if len(cols) < 2:
                continue
            key = fold_ascii(cols[0])
            if key == last_key:
                continue
            last_key = key
            out.write(tsv_row([cols[0], tsv_field(cols[1]), "kaikki"]))
            n += 1
    return {"etym": n}


def main() -> None:
    t0 = time.time()
    log.info("step 1/5: merge words (ecdict + kaikki + sounds)")
    w = merge_words()
    log.info(f"words: {json.dumps(w, ensure_ascii=False)}")
    log.info("step 2/5: merge morphemes (curated + kaikki + morphemes.json)")
    m = merge_morphs()
    log.info(f"morphs: {json.dumps(m, ensure_ascii=False)}")
    log.info("step 3/5: links passthrough")
    l = merge_links()
    log.info(f"links: {json.dumps(l, ensure_ascii=False)}")
    log.info("step 4/5: forms merge")
    fm = merge_forms()
    log.info(f"forms: {json.dumps(fm, ensure_ascii=False)}")
    log.info("step 5/5: etymology collapse")
    e = merge_etym()
    log.info(f"etym: {json.dumps(e, ensure_ascii=False)}")
    stats = {"elapsed_sec": round(time.time() - t0, 1), "words": w,
             "morphs": m, "links": l, "forms": fm, "etym": e}
    save_state("merge", {"finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                          **stats})
    log.info(f"DONE {json.dumps(stats, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
