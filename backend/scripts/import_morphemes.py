"""Seed a curated morpheme library (roots/prefixes/suffixes) and auto-link
dictionary words to them by spelling rules.

Also backfills word-frequency columns (bnc/frq) from the ECDICT csv so the
graph can show the most common words per morpheme first.

Idempotent: re-running inserts nothing new (INSERT IGNORE / ON DUPLICATE).

Usage (from backend/):
    python scripts/import_morphemes.py
"""

import asyncio
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import text

from core.database import engine

CSV_PATH = Path(__file__).resolve().parent.parent / "data" / "ecdict.csv"
BATCH_SIZE = 5000

# ---------------------------------------------------------------------------
# Curated morpheme dataset: (text, meaning)
# ---------------------------------------------------------------------------
ROOTS = [
    # 看与说
    ("spect", "看"), ("vis", "看"), ("vid", "看"), ("scop", "观察/仪器"),
    ("dict", "说"), ("log", "言语/学科"), ("loqu", "说"), ("voc", "声音/喊"),
    ("nounc", "讲述"), ("verb", "词语"), ("lingu", "语言"), ("liter", "文字"),
    ("graph", "书写"), ("gram", "书写/描绘"), ("scrib", "写"), ("script", "写"),
    ("bibli", "书"),
    # 听与感觉
    ("aud", "听"), ("son", "声音"), ("phon", "声音"), ("ton", "音调"),
    ("sens", "感觉"), ("sent", "感觉"), ("path", "感情/疾病"), ("pass", "感情/通过"),
    # 身体
    ("cord", "心"), ("cardi", "心"), ("psych", "心理"), ("neur", "神经"),
    ("man", "手"), ("ped", "足"), ("pod", "足"), ("ocul", "眼睛"),
    ("dent", "牙齿"), ("derm", "皮肤"), ("corp", "身体"),
    # 移动与引导
    ("mot", "移动"), ("mov", "移动"), ("mob", "移动"), ("it", "行走"),
    ("grad", "步/级"), ("gress", "行走"), ("curs", "跑"), ("migr", "迁移"),
    ("ven", "来"), ("vent", "来/风"), ("ced", "行走/让与"), ("cess", "行走/让与"),
    ("vad", "行走"), ("fug", "逃跑"),
    ("duc", "引导"), ("duct", "引导"), ("pel", "驱动"), ("puls", "驱动"),
    ("mit", "送/派出"), ("miss", "送/派出"), ("port", "搬运"), ("fer", "带来"),
    ("ger", "搬运"), ("veh", "运载"), ("vect", "运载"),
    # 放置与连接
    ("pos", "放置"), ("pon", "放置"), ("thes", "放置"), ("her", "粘附"),
    ("nect", "连结"), ("junct", "连接"), ("join", "连接"), ("apt", "适应/连接"),
    # 转与弯
    ("vert", "转"), ("vers", "转"), ("volv", "转/滚"), ("rot", "旋转"),
    ("tort", "扭曲"), ("tour", "转"), ("flect", "弯曲"), ("flex", "弯曲"),
    # 拉与持
    ("tract", "拉/拖"), ("strain", "拉紧"), ("strict", "拉紧"), ("string", "捆绑"),
    ("ten", "握持"), ("tain", "保持"), ("tin", "握持"), ("hab", "居住/持有"),
    # 建造与形态
    ("struct", "建造"), ("form", "形状"), ("morph", "形状"), ("fig", "塑造"),
    ("fac", "做"), ("fect", "做"), ("fact", "做"), ("fic", "做"),
    ("creat", "创造"), ("gener", "产生/种类"), ("gen", "出生/产生"), ("nat", "出生"),
    # 破裂与关闭
    ("rupt", "破裂"), ("fract", "破裂"), ("frag", "破裂"), ("clud", "关闭"),
    ("clos", "关闭"), ("clus", "关闭"), ("cover", "覆盖"), ("tect", "掩盖"),
    # 切割与分离
    ("cid", "切/落"), ("cis", "切"), ("sect", "切割"), ("tom", "切割"),
    ("divid", "分开"), ("divis", "分开"), ("part", "部分"),
    # 光与热
    ("phot", "光"), ("lumin", "光"), ("luc", "光"), ("splend", "发光"),
    ("clar", "清楚"), ("ign", "火"), ("therm", "热"), ("cry", "冷/隐藏"),
    # 自然界
    ("geo", "地球"), ("terr", "土地"), ("mar", "海洋"), ("aqu", "水"),
    ("hydr", "水"), ("sol", "太阳"), ("lun", "月亮"), ("stell", "星"),
    ("aer", "空气"), ("vac", "空"), ("flor", "花"), ("foli", "叶"),
    ("arbor", "树"), ("lith", "石头"), ("petr", "石头"),
    # 生命与死亡
    ("bio", "生命"), ("vit", "生命"), ("viv", "活"), ("anim", "生命/精神"),
    ("mort", "死亡"), ("necr", "死亡"), ("somn", "睡眠"), ("vigil", "清醒"),
    # 心智
    ("memor", "记忆"), ("cogn", "知道"), ("sci", "知道"), ("gnor", "不知道"),
    ("not", "标记"), ("sign", "标记"), ("soph", "智慧"), ("phil", "爱好"),
    ("math", "学习"), ("doc", "教导"), ("disc", "学习"), ("put", "思考/认为"),
    # 信任与价值
    ("cred", "相信"), ("fid", "信任"), ("val", "价值/强壮"), ("vail", "价值"),
    ("preci", "价值"), ("dur", "持久"), ("firm", "坚固"),
    # 意志与选择
    ("vol", "意志"), ("opt", "选择/眼睛"), ("pet", "寻求"), ("quest", "寻求"),
    ("quir", "寻求"), ("spir", "呼吸"), ("salut", "健康"), ("sanit", "健康"),
    ("medic", "治疗"), ("tox", "毒"), ("pest", "瘟疫"),
    # 社会与秩序
    ("dem", "人民"), ("popul", "人民"), ("ethn", "民族"), ("urb", "城市"),
    ("civ", "公民/城市"), ("polis", "城市"), ("equ", "相等"), ("just", "正义"),
    ("jur", "法律"), ("jud", "判断"), ("judic", "判断"), ("legis", "法律"),
    ("crim", "罪行"), ("culp", "罪责"), ("vinc", "征服"), ("vict", "征服"),
    ("pugn", "打斗"), ("bell", "战争"), ("milit", "士兵"), ("arm", "武器"),
    ("pac", "和平"), ("plac", "安抚/平静"), ("grat", "感激"), ("graci", "优雅"),
    ("lud", "玩耍"),
    # 给予与分配
    ("don", "给予"), ("dot", "给予"), ("trib", "给予/分配"), ("mun", "公共职责"),
    ("class", "等级/类别"),
    # 时间与顺序
    ("tempor", "时间"), ("chron", "时间"), ("ann", "年"), ("enni", "年"),
    ("noct", "夜"), ("diurn", "日"), ("prim", "第一"), ("ultim", "最后"),
    ("fin", "界限/结束"), ("termin", "界限"), ("nov", "新"), ("sen", "老的"),
    ("juven", "年轻"),
    # 数量与度量
    ("numer", "数字"), ("calcul", "计算"), ("rat", "计算/理性"), ("meas", "测量"),
    ("meter", "测量"), ("magn", "大"), ("maj", "大"), ("grand", "大"),
    ("mini", "小"), ("micro", "微小"), ("long", "长"), ("brev", "短"),
    ("alt", "高"), ("plen", "满"),
    # 水与流
    ("flu", "流动"), ("flux", "流动"), ("fus", "倾倒/熔"), ("fund", "倾倒/熔"),
    ("found", "底部/铸造"), ("solv", "松开"), ("solut", "松开"), ("lax", "松弛"),
    # 群体
    ("greg", "群体"), ("soci", "同伴/社会"), ("feder", "联盟"),
    # 劳作
    ("agri", "田地"), ("cult", "耕种/培养"), ("labor", "劳动"), ("oper", "工作"),
    ("erg", "工作/能量"), ("nav", "船"), ("naut", "水手/船"), ("avi", "鸟/飞行"),
    ("zoo", "动物"), ("hipp", "马"), ("bov", "牛"),
    # 高频补充
    ("ject", "扔/投掷"), ("jud", "判断"), ("merc", "贸易"), ("nomin", "名字"),
    ("onym", "名字"), ("press", "压"), ("punct", "刺/点"), ("rect", "正直"),
    ("reg", "统治/王"), ("rod", "咬/侵蚀"), ("sacr", "神圣"), ("scend", "攀爬"),
    ("sequ", "跟随"), ("sert", "插入/放置"), ("serv", "服务/保持"), ("sid", "坐"),
    ("spher", "球"), ("stabil", "稳定"), ("stat", "站立"), ("sum", "拿取"),
    ("tact", "接触"), ("techn", "技术"), ("tend", "伸展"), ("tens", "伸展"),
    ("tent", "伸展"), ("test", "测试/见证"), ("text", "编织"), ("tim", "害怕"),
    ("tors", "扭转"), ("tot", "全部"), ("turb", "搅乱"), ("umbr", "影子"),
    ("ust", "燃烧"), ("util", "使用"), ("vag", "漫游"), ("van", "空/前锋"),
    ("vari", "变化"), ("ver", "真实"), ("vest", "衣服"), ("viol", "力量"),
    ("vor", "吞吃"),
]
ROOTS = sorted(set(ROOTS))

PREFIXES = [
    ("anti", "反对"), ("auto", "自动/自己"), ("be", "使/加以"),
    ("bi", "双"), ("circum", "环绕"), ("co", "共同"),
    ("col", "共同"), ("com", "共同"), ("con", "共同"), ("cor", "共同"),
    ("contra", "相反"), ("counter", "反对"), ("de", "去除/向下"),
    ("dis", "分开/否定"), ("dif", "否定"), ("dys", "不良"),
    ("ex", "向外/前任"), ("extra", "超出"), ("fore", "预先"),
    ("hetero", "异"), ("homo", "同"), ("hyper", "过度"), ("hypo", "低于"),
    ("il", "否定"), ("im", "否定/进入"), ("in", "否定/进入"),
    ("ir", "否定"), ("inter", "之间"), ("intra", "之内"), ("intro", "向内"),
    ("macro", "巨大"), ("mal", "不良"), ("micro", "微小"),
    ("mid", "中间"), ("mini", "微小"), ("mis", "错误"), ("mono", "单一"),
    ("multi", "多"), ("neo", "新"), ("non", "否定"), ("ob", "逆/倒"),
    ("omni", "全"), ("out", "超过/向外"), ("over", "过度/在上"),
    ("pan", "全"), ("para", "旁/辅助"), ("pen", "几乎"),
    ("per", "透过/彻底"), ("peri", "周围"), ("poly", "多"), ("post", "之后"),
    ("pre", "预先"), ("pro", "向前/支持"), ("proto", "原始"),
    ("pseudo", "假"), ("re", "再次/返回"), ("retro", "向后"),
    ("semi", "半"), ("sub", "下面/次级"), ("suf", "下面"), ("sup", "下面"),
    ("super", "超越/在上"), ("sur", "在上/超过"), ("syn", "共同"),
    ("tele", "远"), ("trans", "横过/转移"), ("tri", "三"),
    ("ultra", "超出"), ("un", "否定"), ("under", "在下/不足"),
    ("uni", "单一"),
]
PREFIXES = sorted(set(PREFIXES))

SUFFIXES = [
    ("-able", "能够…的"), ("-ible", "能够…的"), ("-ation", "行为/结果"),
    ("-ition", "行为/结果"), ("-tion", "行为/结果"), ("-sion", "行为/结果"),
    ("-ion", "行为/状态"), ("-ment", "行为/结果"), ("-ness", "性质/状态"),
    ("-ity", "性质/状态"),
    ("-ist", "从事…的人"), ("-ism", "主义/学说"), ("-ology", "…学"),
    ("-ship", "身份/关系"), ("-hood", "身份/时期"), ("-dom", "状态/领域"),
    ("-ful", "充满…的"), ("-less", "没有…的"), ("-ous", "有…性质的"),
    ("-ious", "有…性质的"), ("-ive", "有…性质的"), ("-ative", "有…性质的"),
    ("-itive", "有…性质的"), ("-ly", "…地/…的"), ("-ward", "向…方向"),
    ("-wise", "以…方式"), ("-ure", "行为/结果"), ("-age", "行为/集合"),
    ("-ance", "状态/性质"), ("-ence", "状态/性质"), ("-ancy", "状态"),
    ("-ency", "状态"), ("-ary", "…的/场所"), ("-ory", "…的/场所"),
    ("-arium", "场所"), ("-orium", "场所"), ("-or", "…的人/物"),
    ("-er", "…的人/物"), ("-ee", "受动者"), ("-ese", "…语/人"),
    ("-ian", "…的人"), ("-an", "属于…的"), ("-ite", "…的/居民"),
    ("-ed", "…的/过去式"), ("-al", "…的/关于"), ("-ic", "…的/…学的"),
    ("-ine", "…的"), ("-oid", "像…的"), ("-ish", "稍…的"),
    ("-like", "像…的"), ("-most", "最…的"), ("-ize", "使…化"),
    ("-ise", "使…化"), ("-fy", "使…化"), ("-ate", "使/做"),
    ("-ify", "使…化"), ("-en", "使变得"),
]
SUFFIXES = sorted(set(SUFFIXES))

# Only morphemes at least this long are auto-linked (shorter ones match too
# many unrelated words to be useful).
MIN_ROOT_LEN = 3
MIN_PREFIX_LEN = 2
MIN_SUFFIX_LEN = 3  # suffix length without the leading '-'

# Common 2-letter inflection suffixes that are safe to auto-link despite the
# minimum-length rule. They only surface in word breakdowns for words that
# also carry a root/prefix link, so incidental matches stay invisible.
SHORT_SUFFIX_WHITELIST = {"ed", "er", "ly", "al", "ic", "en", "or", "an"}

# A morpheme must leave at least this many letters of "stem" in the word.
MIN_STEM_ROOT = 3
MIN_STEM_PREFIX = 3
MIN_STEM_SUFFIX = 3

# ---------------------------------------------------------------------------
# False-positive curation (spelling-rule matching is inherently fuzzy).
# ---------------------------------------------------------------------------

# Words CONTAINING any of these substrings are removed from the root's links;
# entries like "=word" match the whole spelling exactly. Curated for the most
# noise-prone short roots (etymologically unrelated look-alikes).
ROOT_STOPWORDS = {
    "sen": ["sens", "sent", "essen", "presen", "absen", "passen", "osen",
            "rsen", "seng", "senc", "send"],
    "man": ["human", "woman", "roman", "german", "talisman", "manor", "oman",
            "forman", "erman"],
    "ver": [  # however/very/cover/serv/receive/give families are NOT ver-"true"
        "very", "ever", "never", "every", "however", "whatever", "whenever",
        "wherever", "whoever", "whichever", "moreover", "nevertheless",
        "cover", "lover", "river", "liver", "fever", "clever", "several",
        "average", "deliver", "silver", "over", "serv", "receiv", "give",
        "live", "vers", "vert", "verb", "hiver", "=tavern", "=taverns",
        "waiv", "verg",
    ],
    "vid": ["vivid", "divid"],  # vivid=life, divide=division family
    "aud": ["fraud", "gaud"],
    "mar": ["mark", "marri", "marg", "marshal", "smart"],
    "arm": ["farm", "harm", "warm", "charm", "harmon", "alarm"],
    "alt": ["salt", "waltz", "alter", "halt", "assault", "ealth", "though",
            "nalt", "yalty", "togeth", "ualt", "ialt", "balt", "altr"],
    "min": ["examin", "determin", "domin", "femin", "omin"],
    "nov": ["novemb"],  # November = novem "nine"
    "tim": ["time", "estim", "intima", "centim", "millim"],
    "bell": ["=bell", "=bells", "belle", "bellies", "belly", "bellow"],
    "gen": ["agend"],  # agent/agenda = agere "do"
    "put": ["input", "output", "putt", "=put", "=puts"],
    "val": ["=valley", "=valleys", "=carnival", "avalanche"],
    "long": ["=belong", "=belongs", "=belonged", "=belongings", "=along"],
    "fin": ["fing"],  # finger is Germanic
    "cord": ["=cord", "=cords"],  # cord the rope
    "terr": ["terrib", "terro", "terrif", "nterr"],  # terrere "fright" / inter-
    "sol": ["consol", "solit", "isol", "solid", "soldi", "sole", "gasol",
            "solic", "obsole", "solac", "solemn", "desola", "solo", "erosol",
            "solub", "solv", "sold"],
}

# If a word links to both the key root AND one of its longer variants, keep
# only the longer one (e.g. "vers" beats "ver" in "conversation").
ROOT_PRECEDENCE = {
    "ver": ["vers", "vert", "verb"],
    "gen": ["gener"],
    "min": ["nomin"],
    "sol": ["solv", "solut"],
    "tim": ["ultim"],
}

# Prefixes matching far too many unrelated words to auto-link usefully.
NO_AUTO_LINK_PREFIXES = {"be"}

# Words STARTING WITH these substrings are removed from the prefix's links.
PREFIX_STOPWORDS = {
    "mis": ["miss", "mister", "miser"],  # mission/missile = miss "send"
    "pro": ["prob", "proper"],
    "per": ["person"],
    "re": ["read", "real", "reas", "rest"],
}

# A word starting with both the short prefix and the longer one keeps only
# the longer one (e.g. "under" beats "un" in "understand").
PREFIX_PRECEDENCE = {
    "un": ["under", "uni"],
    "ex": ["extra"],
    "per": ["peri"],
    "sup": ["super"],
}


async def get_or_create(conn, table: str, text_: str, meaning: str) -> int:
    row = (
        await conn.execute(text(f"SELECT id FROM {table} WHERE text = :t"), {"t": text_})
    ).first()
    if row:
        return row[0]
    await conn.execute(
        text(f"INSERT INTO {table} (text, meaning) VALUES (:t, :m)"),
        {"t": text_, "m": meaning},
    )
    row = (
        await conn.execute(text(f"SELECT id FROM {table} WHERE text = :t"), {"t": text_})
    ).first()
    return row[0]


async def backfill_frequency() -> None:
    """Backfill bnc/frq word-frequency columns from the ECDICT csv."""
    if not CSV_PATH.exists():
        print("WARN: ecdict.csv not found, skip frequency backfill")
        return
    upsert = text(
        "INSERT INTO words (spelling, bnc, frq) VALUES (:spelling, :bnc, :frq) "
        "AS new ON DUPLICATE KEY UPDATE bnc = new.bnc, frq = new.frq"
    )

    def to_int(v: str):
        v = (v or "").strip()
        return int(v) if v.isdigit() else None

    batch, total = [], 0
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        async with engine.begin() as conn:
            for row in reader:
                params = {
                    "spelling": (row.get("word") or "").strip(),
                    "bnc": to_int(row.get("bnc")),
                    "frq": to_int(row.get("frq")),
                }
                if not params["spelling"]:
                    continue
                batch.append(params)
                if len(batch) >= BATCH_SIZE:
                    await conn.execute(upsert, batch)
                    total += len(batch)
                    batch = []
            if batch:
                await conn.execute(upsert, batch)
                total += len(batch)
    print(f"Frequency backfill done: {total} rows", flush=True)


async def link_family(conn, table: str, link_table: str, morphemes, kind: str, min_stem: int) -> int:
    """Insert morphemes and link matching words. Returns links created."""
    if kind == "root":
        match = "LOWER(w.spelling) LIKE CONCAT('%', :t, '%')"
    elif kind == "prefix":
        match = "LOWER(w.spelling) LIKE CONCAT(:t, '%')"
    else:
        match = "LOWER(w.spelling) LIKE CONCAT('%', :t)"
    sql = text(
        f"INSERT IGNORE INTO {link_table} (word_id, morpheme_id) "
        f"SELECT w.id, :mid FROM words w "
        f"WHERE w.spelling REGEXP '^[a-zA-Z]+$' "
        f"AND {match} "
        f"AND CHAR_LENGTH(w.spelling) >= :minlen"
    )
    total = 0
    for text_, meaning in morphemes:
        mid = await get_or_create(conn, table, text_, meaning)
        res = await conn.execute(
            sql, {"mid": mid, "t": text_, "minlen": len(text_) + min_stem}
        )
        total += max(res.rowcount, 0)
    return total


async def _get_id(conn, table: str, text_: str):
    return (
        await conn.execute(text(f"SELECT id FROM {table} WHERE text = :t"), {"t": text_})
    ).scalar()


async def clean_false_positives() -> None:
    """Remove known false-positive links created by spelling-rule matching."""
    deleted = 0
    async with engine.begin() as conn:
        # 1) Root stopwords: substring / exact match on spelling.
        for root_text, stops in ROOT_STOPWORDS.items():
            rid = await _get_id(conn, "roots", root_text)
            if rid is None:
                continue
            for stop in stops:
                if stop.startswith("="):
                    sql, args = (
                        "DELETE wr FROM word_root wr JOIN words w ON w.id = wr.word_id "
                        "WHERE wr.morpheme_id = :rid AND LOWER(w.spelling) = :w",
                        {"rid": rid, "w": stop[1:]},
                    )
                else:
                    sql, args = (
                        "DELETE wr FROM word_root wr JOIN words w ON w.id = wr.word_id "
                        "WHERE wr.morpheme_id = :rid AND LOWER(w.spelling) LIKE :pat",
                        {"rid": rid, "pat": f"%{stop}%"},
                    )
                res = await conn.execute(text(sql), args)
                deleted += max(res.rowcount, 0)

        # 2) Root precedence: drop short-root link when a longer variant links too.
        for short, longs in ROOT_PRECEDENCE.items():
            sid = await _get_id(conn, "roots", short)
            if sid is None:
                continue
            for long_ in longs:
                lid = await _get_id(conn, "roots", long_)
                if lid is None:
                    continue
                res = await conn.execute(
                    text(
                        "DELETE wr FROM word_root wr "
                        "JOIN word_root wr2 ON wr2.word_id = wr.word_id "
                        "WHERE wr.morpheme_id = :sid AND wr2.morpheme_id = :lid"
                    ),
                    {"sid": sid, "lid": lid},
                )
                deleted += max(res.rowcount, 0)

        # 3) Prefix stopwords: starts-with match.
        for pfx, stops in PREFIX_STOPWORDS.items():
            pid = await _get_id(conn, "prefixes", pfx)
            if pid is None:
                continue
            for stop in stops:
                res = await conn.execute(
                    text(
                        "DELETE wp FROM word_prefix wp JOIN words w ON w.id = wp.word_id "
                        "WHERE wp.morpheme_id = :pid AND LOWER(w.spelling) LIKE :pat"
                    ),
                    {"pid": pid, "pat": f"{stop}%"},
                )
                deleted += max(res.rowcount, 0)

        # 4) Prefix precedence: word starts with the longer prefix -> drop short link.
        for short, longs in PREFIX_PRECEDENCE.items():
            sid = await _get_id(conn, "prefixes", short)
            if sid is None:
                continue
            for long_ in longs:
                res = await conn.execute(
                    text(
                        "DELETE wp FROM word_prefix wp JOIN words w ON w.id = wp.word_id "
                        "JOIN prefixes ps ON ps.id = wp.morpheme_id "
                        "WHERE ps.text = :short AND LOWER(w.spelling) LIKE :pat"
                    ),
                    {"short": short, "pat": f"{long_}%"},
                )
                deleted += max(res.rowcount, 0)

        # 5) Drop all links for prefixes excluded from auto-linking.
        for pfx in NO_AUTO_LINK_PREFIXES:
            pid = await _get_id(conn, "prefixes", pfx)
            if pid is None:
                continue
            res = await conn.execute(
                text("DELETE FROM word_prefix WHERE morpheme_id = :pid"), {"pid": pid}
            )
            deleted += max(res.rowcount, 0)

    print(f"Cleanup done: {deleted} false-positive links removed", flush=True)


async def main() -> None:
    phase = sys.argv[1] if len(sys.argv) > 1 else "all"
    if phase in ("all", "freq"):
        await backfill_frequency()
    if phase in ("all", "link"):
        roots = [(t, m) for t, m in ROOTS if len(t) >= MIN_ROOT_LEN]
        prefixes = [
            (t, m)
            for t, m in PREFIXES
            if len(t) >= MIN_PREFIX_LEN and t not in NO_AUTO_LINK_PREFIXES
        ]
        suffixes = [
            (t.lstrip("-"), m)
            for t, m in SUFFIXES
            if len(t.lstrip("-")) >= MIN_SUFFIX_LEN
            or t.lstrip("-") in SHORT_SUFFIX_WHITELIST
        ]

        async with engine.begin() as conn:
            n = await link_family(conn, "roots", "word_root", roots, "root", MIN_STEM_ROOT)
            print(f"roots: {len(roots)} morphemes, {n} links", flush=True)
        async with engine.begin() as conn:
            n = await link_family(
                conn, "prefixes", "word_prefix", prefixes, "prefix", MIN_STEM_PREFIX
            )
            print(f"prefixes: {len(prefixes)} morphemes, {n} links", flush=True)
        async with engine.begin() as conn:
            n = await link_family(
                conn, "suffixes", "word_suffix", suffixes, "suffix", MIN_STEM_SUFFIX
            )
            print(f"suffixes: {len(suffixes)} morphemes, {n} links", flush=True)
    if phase in ("all", "link", "clean"):
        await clean_false_positives()
    await engine.dispose()
    print("Morpheme import done.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
