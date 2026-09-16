"""Stream-parse the kaikki English JSONL.gz into staging TSVs.

Output staging files (all under data/pipeline/staging/):
  stg_kw_words   spelling, spelling_norm, word_category, pos, defs_json, examples_json
  stg_kw_defs    spelling, pos, order_idx, text, tags
  stg_kw_sounds  spelling, ipa, accent, note
  stg_kw_forms   spelling, form, form_tags
  stg_kw_etym    spelling, etymology_text
  stg_kw_morphs  text, kind, meaning_en, meaning_zh, source_lang, category
  stg_kw_links   spelling, morph_text, kind, relation_type, evidence, status

Design notes (see 任务规则):
- 流式逐行解析, 不把数据集载入内存; 同一拼写多行(多词性/多词源)由导入SQL去重。
- 只导入英语词条(lang_code=en); 区分基础词/屈折/短语/专名/缩写/古语/罕见词。
- IPA 仅取 sounds[].ipa 字段(来源规范为IPA); 地区标签缺失时 accent='unknown',
  不自行猜测; "both"标签会同时落uk和us两行。
- 词根/词缀关联只来自 Wiktionary root/prefix/suffix/affix/confix 模板(有依据),
  不做子串匹配。模板中的裸词干部分不生成关联, 只保留在依据文本里。
"""
import argparse
import gzip
import json
import re
import sys
import time
from pathlib import Path

from pipeline.common import get_logger, tsv_row
from pipeline.config import DOWNLOAD_DIR, STAGING_DIR

log = get_logger("parse_kaikki")

# ---------------------------------------------------------------------------
# 常量与映射
# ---------------------------------------------------------------------------
MAX_SPELLING = 100
MAX_TEXT = 2000
MAX_ETYM = 60000

# 词条类别优先级: 选定合并词的展示 category 时, 普通词义(lemma)最优先,
# 其次词素页/专名/缩写等, 罕见义最后。
CATEGORY_RANK = {
    "lemma": 1, "morpheme": 2, "abbreviation": 3, "inflection": 4,
    "phrase": 5, "proper_noun": 6, "symbol": 7, "rare": 8, "archaic": 9,
}

PHRASE_POS = {"phrase", "prep_phrase", "adv_phrase", "proverb"}
SYMBOL_POS = {"punct", "symbol", "character", "letter"}
MORPHEME_POS = {"prefix", "suffix", "circumfix", "infix", "interfix",
                "combining form"}
ABBREV_POS = {"abbrev", "contraction"}

UK_TAGS = {"uk", "britain", "british", "england", "gb", "rp",
           "received pronunciation"}
US_TAGS = {"us", "united states", "american", "ga", "general american"}
OTHER_REGIONS = {
    "australia", "canada", "ireland", "scotland", "wales", "new zealand",
    "nz", "south africa", "india", "singapore", "caribbean", "liverpool",
    "cockney", "boston", "new york", "philadelphia", "southern us",
    "midland us", "canadian", "australian", "irish", "scottish",
}

IPA_CHARS = set("əɪʊæɑɒθðʃʒŋʌɜɔɛːˈˌˑː:.")

LANG_NAMES = {
    "la": "Latin", "grc": "Ancient Greek", "el": "Greek",
    "enm": "Middle English", "ang": "Old English", "frm": "Middle French",
    "fro": "Old French", "LL.": "Late Latin", "LL": "Late Latin",
    "ML.": "Medieval Latin", "NL.": "New Latin", "gem-pro": "Proto-Germanic",
    "ine-pro": "Proto-Indo-European", "itc-pro": "Proto-Italic",
    "cel-pro": "Proto-Celtic", "sla-pro": "Proto-Slavic", "gmw-pro": "Proto-West Germanic",
    "odt": "Old Dutch", "osx": "Old Saxon", "non": "Old Norse",
    "gml": "Middle Low German", "dum": "Middle Dutch", "pro": "Old Occitan",
    "osp": "Old Spanish", "it": "Italian", "es": "Spanish", "fr": "French",
    "de": "German", "nl": "Dutch", "pt": "Portuguese", "ru": "Russian",
    "ar": "Arabic", "he": "Hebrew", "fa": "Persian", "hi": "Hindi",
    "sa": "Sanskrit", "tpi": "Tok Pisin", "mis": "Uncoded",
}

RESPPELLING_RE = re.compile(r"[A-Za-z]-[A-Za-z]")


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------
def clean_gloss(sense: dict) -> str:
    g = sense.get("glosses") or []
    if not g:
        g = sense.get("raw_glosses") or []
    if not g:
        return ""
    text = g[0] if isinstance(g, list) else str(g)
    return text.strip()[:MAX_TEXT]


def map_accent(tags: list):
    """返回 [(accent, note), ...]; 无地区标注返回 [('unknown','')].
    UK+US 同行会返回两行。"""
    low = {str(t).lower() for t in (tags or [])}
    out = []
    if low & UK_TAGS:
        out.append(("uk", ""))
    if low & US_TAGS:
        out.append(("us", ""))
    if out:
        return out
    regions = low & OTHER_REGIONS
    if regions:
        return [("other", sorted(regions)[0][:100])]
    return [("unknown", "")]


def looks_like_ipa(ipa: str) -> bool:
    if any(ch in IPA_CHARS for ch in ipa):
        return True
    # 纯ASCII重拼形式(如 dik-shuh-ner-ee)不算IPA
    if RESPPELLING_RE.search(ipa):
        return False
    return bool(re.fullmatch(r"[A-Za-z'ʼ ˈˌ.:]+", ipa))


def normalize_morpheme(text: str) -> str:
    # Wiktionary 模板参数常带 <id:...>/<t:...> 内联注记(如 "in<id:inverse>")
    # 和 #锚点后缀(如 "a-#etymology_6")
    text = re.sub(r"<[a-z]+:[^>]*>", "", text)
    text = text.split("#", 1)[0]
    return text.strip().strip("-*").strip().lower()


def numbered_args(args: dict) -> list:
    """按 1,2,3... 顺序取出编号参数(跳过空缺)。"""
    out = []
    nums = sorted(int(k) for k in args if str(k).isdigit())
    for n in nums:
        v = str(args.get(str(n), "")).strip()
        if v:
            out.append(v)
    return out


def extract_template_morphemes(entry: dict, word: str):
    """从 head_templates / etymology_templates 提取有依据的词素关联。
    返回 [(morph_text, kind, relation_type, source_lang, evidence)]。"""
    results = []
    for container in ("etymology_templates", "head_templates"):
        for t in entry.get(container) or []:
            name = t.get("name", "")
            args = t.get("args") or {}
            if not isinstance(args, dict):
                continue
            parts = numbered_args(args)
            if len(parts) < 2:
                continue
            # parts[0] 通常是语言代码(en)
            payload = parts[1:]
            if name == "root":
                # {{root|en|<源语言>|<词根>...}}: 第2个参数是源语言,其后都是词根
                if len(payload) < 2:
                    continue
                lang_code = payload[0]
                lang = LANG_NAMES.get(lang_code, lang_code)
                for rt in payload[1:]:
                    m = normalize_morpheme(rt)
                    if m and len(m) <= 50:
                        ev = f"{{{{root|en|{lang_code}|{rt}}}}}"
                        results.append((m, "root", "etymology", lang, ev))
            elif name == "suffix":
                # {{suffix|en|<词基>|<后缀>...}}: 首个是词基,其余是后缀
                for sf in payload[1:]:
                    m = normalize_morpheme(sf)
                    if m and len(m) <= 50:
                        ev = f"{{{{{name}|en|{'|'.join(payload)}}}}}"[:300]
                        results.append((m, "suffix", "surface", None, ev))
            elif name == "prefix":
                # {{prefix|en|<前缀>...|<词基>}}: 末尾是词基,其余是前缀
                for pf in payload[:-1]:
                    m = normalize_morpheme(pf)
                    if m and len(m) <= 50:
                        ev = f"{{{{{name}|en|{'|'.join(payload)}}}}}"[:300]
                        results.append((m, "prefix", "surface", None, ev))
            elif name in ("affix", "confix"):
                # 现代写法: 前缀带尾连字符(pre-), 后缀带首连字符(-ment); 裸词干不关联
                for p in payload:
                    p = p.strip()
                    m = normalize_morpheme(p)
                    if not m or len(m) > 50:
                        continue
                    ev = f"{{{{{name}|en|{'|'.join(payload)}}}}}"[:300]
                    if p.startswith("-") and p.endswith("-"):
                        continue  # circumfix整体, 跳过
                    if p.startswith("-"):
                        results.append((m, "suffix", "surface", None, ev))
                    elif p.endswith("-"):
                        results.append((m, "prefix", "surface", None, ev))
            # compound/circumfix/infix/interfix: 不生成词素关联(整词或跨词),
            # 词源文本已保留依据
    return results


def extract_affix_entry_morpheme(entry: dict, pos: str):
    """pos 为 prefix/suffix/combining form 的词条本身是词素释义条目,
    提取 meaning_en(义项) 和 meaning_zh(翻译)。"""
    word = entry.get("word", "")
    m = normalize_morpheme(word)
    if not m or len(m) > 50:
        return None
    kind = None
    category = pos
    if pos == "prefix":
        kind = "prefix"
    elif pos == "suffix":
        kind = "suffix"
    elif pos == "combining form":
        kind = "root"  # 组合形式按词根表记录, morpheme_category 保留原始分类
    else:
        return None
    meaning_en = ""
    for sense in entry.get("senses") or []:
        meaning_en = clean_gloss(sense)
        if meaning_en:
            break
    meaning_zh = ""
    trans = entry.get("translations") or {}
    if isinstance(trans, list):
        # wiktextract format: [{"code": "zh", "lang": "Chinese", "word": "意义"}, ...]
        words = [str(t.get("word", "")).strip() for t in trans
                 if isinstance(t, dict) and t.get("word")
                 and str(t.get("lang", t.get("code", ""))).lower()
                 in ("chinese", "zh", "mandarin", "cmn")]
        meaning_zh = "; ".join(w for w in words if w)[:200]
    else:
        for key in ("Chinese", "zh", "Mandarin"):
            lst = trans.get(key) if isinstance(trans.get(key), list) else []
            words = [str(x.get("word", "")).strip() for x in lst
                     if isinstance(x, dict) and x.get("word")]
            words = [w for w in words if w]
            if words:
                meaning_zh = "; ".join(words[:2])[:200]
                break
    return (m, kind, meaning_en[:500] or None, meaning_zh or None, None, category)


def classify(entry: dict, word: str, pos: str) -> str:
    if pos in MORPHEME_POS:
        return "morpheme" if pos in ("prefix", "suffix") else "morpheme"
    if "form_of" in entry and entry.get("form_of"):
        return "inflection"
    if pos == "name":
        return "proper_noun"
    if pos in ABBREV_POS:
        return "abbreviation"
    if pos in PHRASE_POS or " " in word.strip():
        return "phrase"
    if pos in SYMBOL_POS:
        return "symbol"
    tags = [str(t).lower() for t in (entry.get("tags") or [])]
    for sense in entry.get("senses") or []:
        tags += [str(t).lower() for t in (sense.get("tags") or [])]
    if "archaic" in tags or "obsolete" in tags:
        return "archaic"
    if "rare" in tags:
        return "rare"
    return "lemma"


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0,
                    help="只处理前N行(小批量贯通验证用)")
    ap.add_argument("--input", default="", help="覆盖默认输入文件路径")
    args = ap.parse_args()

    src = Path(args.input) if args.input else DOWNLOAD_DIR / "kaikki-en.jsonl.gz"
    if not src.exists():
        log.error(f"input not found: {src}")
        sys.exit(1)

    outs = {name: open(STAGING_DIR / f"{name}.tsv", "w", encoding="utf-8")
            for name in ("stg_kw_words", "stg_kw_defs", "stg_kw_sounds",
                         "stg_kw_forms", "stg_kw_etym", "stg_kw_morphs",
                         "stg_kw_links")}
    stats = {
        "lines": 0, "entries": 0, "skipped_non_en": 0, "skipped_long": 0,
        "defs": 0, "sounds": 0, "forms": 0, "etym": 0, "morphs": 0,
        "links": 0, "examples_words": 0,
        "categories": {},
    }

    def w(name, row):
        outs[name].write(tsv_row(row))

    t0 = time.time()
    last_word = None
    def_counter = 0

    with gzip.open(src, "rt", encoding="utf-8", errors="replace") as f:
        for line in f:
            stats["lines"] += 1
            if args.limit and stats["lines"] > args.limit:
                break
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                stats["skipped_non_en"] += 0  # 计入parse错误
                continue
            lang_code = entry.get("lang_code")
            if lang_code not in (None, "en"):
                stats["skipped_non_en"] += 1
                continue
            word = (entry.get("word") or "").strip()
            pos = entry.get("pos") or ""
            if not word or len(word) > MAX_SPELLING:
                stats["skipped_long"] += 1
                continue
            stats["entries"] += 1

            if word != last_word:
                last_word = word
                def_counter = 0

            category = classify(entry, word, pos)
            stats["categories"][category] = stats["categories"].get(category, 0) + 1

            # -- 词条主行(投影列也在这里组装) --
            proj_defs = []
            proj_examples = []
            for sense in entry.get("senses") or []:
                g = clean_gloss(sense)
                if g:
                    def_counter += 1
                    sense_tags = ";".join(str(t) for t in (sense.get("tags") or []))[:190]
                    w("stg_kw_defs", [word, pos, def_counter, g, sense_tags or None])
                    stats["defs"] += 1
                    if len(proj_defs) < 3:
                        proj_defs.append({"pos": pos, "text": g[:300]})
                for ex in (sense.get("examples") or [])[:2]:
                    t = str(ex.get("text", "")).strip() if isinstance(ex, dict) else ""
                    if t and len(proj_examples) < 3:
                        proj_examples.append(t[:400])
            defs_json = json.dumps(proj_defs, ensure_ascii=False) if proj_defs else None
            ex_json = json.dumps(proj_examples, ensure_ascii=False) if proj_examples else None
            stats["examples_words"] += 1 if proj_examples else 0
            w("stg_kw_words", [word, word.lower(), category, pos or None,
                               defs_json, ex_json])

            # -- 音标 --
            for snd in entry.get("sounds") or []:
                ipa = str(snd.get("ipa", "")).strip() if isinstance(snd, dict) else ""
                if not ipa or len(ipa) > 200:
                    continue
                is_ipa = looks_like_ipa(ipa)
                for accent, note in map_accent(snd.get("tags") or []):
                    full_note = note
                    if not is_ipa:
                        full_note = (note + ";" if note else "") + "格式存疑,未按IPA收录"
                    w("stg_kw_sounds", [word, ipa, accent, full_note or None])
                    stats["sounds"] += 1

            # -- 词形 --
            for fm in entry.get("forms") or []:
                form = str(fm.get("form", "")).strip() if isinstance(fm, dict) else ""
                if not form or len(form) > 150 or form == word:
                    continue
                ftags = ";".join(str(t) for t in (fm.get("tags") or []))[:190]
                w("stg_kw_forms", [word, form, ftags or None])
                stats["forms"] += 1

            # -- 词源文本 --
            ety = (entry.get("etymology_text") or "").strip()
            if ety:
                w("stg_kw_etym", [word, ety[:MAX_ETYM]])
                stats["etym"] += 1

            # -- 词素与关联(模板依据) --
            affix_entry = extract_affix_entry_morpheme(entry, pos)
            if affix_entry:
                w("stg_kw_morphs", list(affix_entry))
                stats["morphs"] += 1
            for m_text, kind, rel, lang, ev in extract_template_morphemes(entry, word):
                w("stg_kw_morphs", [m_text, kind, None, None, lang, None])
                w("stg_kw_links", [word, m_text, kind, rel, ev, "verified"])
                stats["morphs"] += 1
                stats["links"] += 1

            if stats["lines"] % 200000 == 0:
                rate = stats["lines"] / max(time.time() - t0, 1)
                log.info(f"lines={stats['lines']} entries={stats['entries']} "
                         f"defs={stats['defs']} links={stats['links']} "
                         f"({rate:.0f} lines/s)")

    for f_ in outs.values():
        f_.close()
    stats["elapsed_sec"] = round(time.time() - t0, 1)
    log.info(f"DONE {json.dumps(stats, ensure_ascii=False)}")

    from pipeline.common import save_state
    save_state("parse_kaikki", {"finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                                "input": str(src), "limit": args.limit, **stats})


if __name__ == "__main__":
    main()
