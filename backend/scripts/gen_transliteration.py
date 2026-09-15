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
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from core.database import engine

# --------------------------------------------------------------------------
# Established loanword transliterations (override the generated form)
# --------------------------------------------------------------------------
LOANWORDS = {
    "aspirin": "阿司匹林", "brandy": "白兰地", "blog": "博客", "bus": "巴士",
    "cacao": "可可", "caffeine": "咖啡因", "champagne": "香槟", "cheese": "芝士",
    "chocolate": "巧克力", "cigar": "雪茄", "clone": "克隆", "cocoa": "可可",
    "cocaine": "可卡因", "coffee": "咖啡", "copy": "拷贝", "disco": "迪斯科",
    "engine": "引擎", "gene": "基因", "golf": "高尔夫", "guitar": "吉他",
    "hacker": "黑客", "hamburger": "汉堡", "hysteria": "歇斯底里", "humor": "幽默",
    "jeep": "吉普", "jazz": "爵士", "karaoke": "卡拉OK", "lemon": "柠檬",
    "logic": "逻辑", "laser": "镭射", "marathon": "马拉松", "modern": "摩登",
    "morphine": "吗啡", "motor": "马达", "nicotine": "尼古丁", "nylon": "尼龙",
    "olympic": "奥林匹克", "party": "派对", "pizza": "披萨", "poker": "扑克",
    "pudding": "布丁", "radar": "雷达", "romance": "罗曼史", "salad": "沙拉",
    "sandwich": "三明治", "shampoo": "香波", "sofa": "沙发", "sonar": "声呐",
    "tank": "坦克", "taxi": "的士", "toast": "吐司", "utopia": "乌托邦",
    "vodka": "伏特加", "whisky": "威士忌", "bowling": "保龄球",
}

# --------------------------------------------------------------------------
# IPA -> 汉字 mapping tables
# --------------------------------------------------------------------------
# multi-char tokens, longest first
DIPHTHONGS = {
    "aɪ": "艾", "ai": "艾", "eɪ": "埃", "ei": "埃", "ɔɪ": "哦伊", "oi": "哦伊",
    "əʊ": "欧", "ou": "欧", "aʊ": "奥", "au": "奥", "ɪə": "伊尔", "iə": "伊尔",
    "eə": "艾尔", "ɛə": "艾尔", "ʊə": "乌尔", "uə": "乌尔",
}
LONG_VOWELS = {"iː": "伊", "ɑː": "阿", "ɔː": "奥", "uː": "乌", "ɜː": "厄", "ɜ": "厄"}

CONSONANTS = set("bdfghklmnprstvwzʒŋʃ")

# consonant (incl. digraphs/ascii) -> column: A  O  I  U  E  SCHWA
CV_TABLE = {
    "b":  ["班", "波", "比", "布", "贝", "布"],
    "d":  ["丹", "多", "迪", "杜", "德", "德"],
    "f":  ["凡", "福", "菲", "夫", "费", "夫"],
    "g":  ["甘", "果", "吉", "古", "格", "格"],
    "h":  ["汉", "豪", "希", "胡", "赫", "赫"],
    "k":  ["坎", "科", "基", "库", "克", "克"],
    "l":  ["兰", "罗", "里", "卢", "勒", "勒"],
    "m":  ["曼", "莫", "米", "姆", "默", "姆"],
    "n":  ["南", "诺", "尼", "努", "内", "内"],
    "p":  ["潘", "坡", "皮", "普", "佩", "普"],
    "r":  ["兰", "若", "瑞", "鲁", "勒", "若"],
    "s":  ["桑", "索", "西", "苏", "瑟", "斯"],
    "t":  ["坦", "托", "提", "图", "特", "特"],
    "v":  ["凡", "沃", "维", "武", "维", "维"],
    "w":  ["万", "沃", "威", "乌", "韦", "伍"],
    "z":  ["赞", "佐", "兹", "祖", "泽", "兹"],
    "j":  [None, None, "叶", None, None, "伊"],
    "ʃ":  ["山", "肖", "希", "舒", "谢", "什"],
    "sh": ["山", "肖", "希", "舒", "谢", "什"],
    "tʃ": ["钱", "乔", "奇", "楚", "切", "切"],
    "ch": ["钱", "乔", "奇", "楚", "切", "切"],
    "dʒ": ["詹", "乔", "吉", "朱", "杰", "杰"],
    "ʒ":  [None, None, None, "儒", None, "热"],
    "θ":  ["桑", None, "西", None, "瑟", "斯"],
    "th": ["桑", None, "西", None, "瑟", "斯"],
    "ð":  ["赞", None, None, None, "泽", "泽"],
}
VOWEL_COL = {
    "A": "æaɑʌ", "O": "ɒɔo", "I": "ɪiey", "U": "ʊu", "E": "eɜɛ", "SCH": "ə",
}
STANDALONE_VOWELS = {
    "æ": "艾", "a": "阿", "ɑ": "阿", "ʌ": "阿", "ɒ": "奥", "ɔ": "奥", "o": "欧",
    "ɪ": "伊", "i": "伊", "y": "伊", "ʊ": "乌", "u": "乌", "e": "艾", "ɛ": "艾",
    "ɜ": "厄", "ə": "额",
}
# consonant with no following vowel (coda)
CODA = {
    "b": "布", "d": "德", "f": "夫", "g": "格", "h": "赫", "k": "克", "l": "勒",
    "m": "姆", "n": "恩", "ŋ": "昂", "ng": "昂", "p": "普", "r": "尔", "s": "斯",
    "t": "特", "v": "夫", "w": "伍", "z": "斯", "ʃ": "什", "sh": "什",
    "tʃ": "切", "ch": "切", "dʒ": "杰", "ʒ": "日", "θ": "斯", "th": "斯",
    "ð": "泽", "j": "伊",
}
CLEAN_RE = re.compile(r"[^a-zɑɒɔʊəɜɪæðθʃʒŋː]")

# coda-n absorption: table chars already ending in -n make a following n redundant
_N_FINAL = set("安班丹凡甘汉坎兰曼南潘桑坦詹钱山赞瑟")

VOWEL_KEY_COL = {
    "aɪ": "A", "ai": "A", "aʊ": "A", "au": "A", "ɑː": "A", "æ": "A",
    "a": "A", "ʌ": "A", "ɑ": "A",
    "eɪ": "E", "ei": "E", "eə": "E", "ɛə": "E", "ɜː": "E", "ɜ": "E", "e": "E", "ɛ": "E",
    "ɔɪ": "O", "oi": "O", "əʊ": "O", "ou": "O", "ɔː": "O", "ɒ": "O", "ɔ": "O", "o": "O",
    "ɪə": "I", "iə": "I", "iː": "I", "ɪ": "I", "i": "I", "y": "I",
    "ʊə": "U", "uə": "U", "uː": "U", "ʊ": "U", "u": "U",
    "ə": "SCH",
}
COL_ORDER = ["A", "O", "I", "U", "E", "SCH"]


def _column_of(vtok: str) -> str:
    if vtok in VOWEL_KEY_COL:
        return VOWEL_KEY_COL[vtok]
    return _column_of(vtok[0]) if vtok else ""


def _tokenize(ph: str):
    """Greedy longest-match tokenization of a normalized phonetic string."""
    tokens = []
    i = 0
    n = len(ph)
    while i < n:
        two = ph[i:i + 2]
        one = ph[i]
        if two in DIPHTHONGS:
            tokens.append(("V", two))
            i += 2
        elif two in LONG_VOWELS:
            tokens.append(("V", two))
            i += 2
        elif two in ("tʃ", "dʒ", "sh", "ch", "th", "ng"):
            tokens.append(("C", two))
            i += 2
        elif one in CONSONANTS or one in "jθð":
            tokens.append(("C", one))
            i += 1
        elif one in STANDALONE_VOWELS:
            tokens.append(("V", one))
            i += 1
        else:
            i += 1  # skip unknown symbol
    return tokens


def phonetic_to_chinese(ph: str) -> str:
    if not ph:
        return ""
    ph = ph.strip().lower()
    # normalize ECDICT quirks: Cyrillic schwa, brackets/slashes/stress marks
    ph = ph.replace("ә", "ə").replace("ɵ", "ə")
    ph = re.sub(r"[/\[\](){}|:;,.!ˈˌ'`]", "", ph)
    ph = CLEAN_RE.sub("", ph)
    if not ph:
        return ""

    tokens = _tokenize(ph)
    out = []
    i = 0
    while i < len(tokens):
        kind, tok = tokens[i]
        if kind == "V":
            if tok in DIPHTHONGS:
                out.append(DIPHTHONGS[tok])
            elif tok in LONG_VOWELS:
                out.append(LONG_VOWELS[tok])
            else:
                out.append(STANDALONE_VOWELS.get(tok, ""))
            i += 1
        else:  # consonant
            row = CV_TABLE.get(tok)
            if row and i + 1 < len(tokens) and tokens[i + 1][0] == "V":
                col = _column_of(tokens[i + 1][1])
                if col:
                    merged = row[COL_ORDER.index(col)] or CODA.get(tok, "")
                    out.append(merged)
                    # absorb a redundant coda n after a -n final char
                    if merged in _N_FINAL and i + 2 < len(tokens) and \
                            tokens[i + 2] == ("C", "n"):
                        i += 3
                        continue
                    i += 2
                    continue
            out.append(CODA.get(tok, ""))
            i += 1

    # post-process: collapse repeats, drop trailing 额, cap length
    s = "".join(out)
    s = re.sub(r"(.)\1+", r"\1", s)
    s = s.rstrip("额")
    return s[:16]


def transliterate(spelling: str, phonetics: dict) -> str:
    if spelling.lower() in LOANWORDS:
        return LOANWORDS[spelling.lower()]
    if not phonetics:
        return ""
    ph = phonetics.get("uk") or phonetics.get("us") or ""
    result = phonetic_to_chinese(ph)
    return result


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
