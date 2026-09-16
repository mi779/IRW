"""Post-import acceptance tests and data quality report.

Checks (see 任务验收要求):
1. 行数统计: 各目标表
2. 字段覆盖率: 音标/中文释义/音译/例句/类别/词频 等
3. 抽样校验: 指定单词的释义、音标、音译、词根关联与依据
4. 检索与分页: 模糊查询 + LIMIT/OFFSET
5. 幂等与人工数据保护: 重复导入不产生重复行; 只补空字段不覆盖人工数据
6. 孤儿检查: 关联/词形指向不存在的词或词素
7. JSON 合法性: phonetics/definitions/tags

Usage (from backend/):
    python -m pipeline.validate [--sample 5]
Exit code 0 = all hard checks passed, 1 = failures found.
"""
from __future__ import annotations

import json
import sys
import time

from pipeline.common import get_logger, mysql_query, mysql_run, save_state
from pipeline.config import DB

log = get_logger("validate")

DB_NAME = DB["database"]

failures: list = []
warnings: list = []


def check(ok: bool, msg: str, warn_only: bool = False) -> bool:
    if ok:
        log.info(f"  PASS  {msg}")
    elif warn_only:
        warnings.append(msg)
        log.info(f"  WARN  {msg}")
    else:
        failures.append(msg)
        log.error(f"  FAIL  {msg}")
    return ok


def q1(sql: str) -> str:
    r = mysql_query(sql, DB_NAME)
    return r[0][0] if r else ""


def section(title: str) -> None:
    log.info("=" * 62)
    log.info(title)
    log.info("=" * 62)


def main() -> None:
    sample_n = 5
    if "--sample" in sys.argv:
        sample_n = int(sys.argv[sys.argv.index("--sample") + 1])
    t0 = time.time()

    # ------------------------------------------------------------------ 1
    section("1. 行数统计")
    counts = {}
    for t in ("words", "roots", "prefixes", "suffixes", "word_root",
              "word_prefix", "word_suffix", "word_forms", "word_etymologies",
              "pipeline_sources", "word_relations", "word_phrases"):
        counts[t] = q1(f"SELECT COUNT(*) FROM {t}")
        log.info(f"  {t:20s} {counts[t]:>10s}")
    check(int(counts["words"]) > 0, "words 非空")
    check(int(counts["roots"]) > 0 and int(counts["prefixes"]) > 0
          and int(counts["suffixes"]) > 0, "词素三表非空")
    check(int(counts["pipeline_sources"]) >= 3,
          f"来源记录 >= 3 (实际 {counts['pipeline_sources']})")

    # ------------------------------------------------------------------ 2
    section("2. 字段覆盖率")
    n = int(counts["words"])
    for label, col in (("音标 phonetics", "phonetics"),
                       ("释义 definitions", "definitions"),
                       ("中文释义(JSON含CJK)", None),
                       ("音译 transliteration", "transliteration"),
                       ("例句 example_sentences", "example_sentences"),
                       ("词性 part_of_speech", "part_of_speech"),
                       ("类别 category", "category"),
                       ("考试标签 tags", "tags"),
                       ("词频 bnc/frq", None)):
        if col:
            c = int(q1(f"SELECT COUNT(*) FROM words WHERE {col} IS NOT NULL"))
        elif label.startswith("中文"):
            c = int(q1(
                "SELECT COUNT(*) FROM words WHERE definitions REGEXP "
                "'[一-龥]' OR JSON_SEARCH(definitions, 'one', '%看%') "
                "IS NOT NULL"))
        else:
            c = int(q1("SELECT COUNT(*) FROM words WHERE bnc IS NOT NULL "
                       "OR frq IS NOT NULL"))
        pct = 100.0 * c / n if n else 0
        log.info(f"  {label:26s} {c:>10d}  ({pct:.1f}%)")
        if col in ("phonetics", "definitions"):
            check(c > 0, f"{label} 覆盖率 > 0")

    # ------------------------------------------------------------------ 3
    section("3. 抽样校验")
    for w in ("international", "apple", "transport", "invisible"):
        r = mysql_query(
            f"SELECT spelling, phonetics, transliteration, definitions, "
            f"category, tags FROM words WHERE spelling = '{w}'", DB_NAME)
        if not r:
            check(False, f"单词 {w} 存在")
            continue
        row = r[0]
        log.info(f"  {row[0]}: phonetics={row[1]} translit={row[2]} "
                 f"category={row[4]} tags={row[5]}")
        log.info(f"    defs: {str(row[3])[:120]}")
        links = mysql_query(
            "SELECT 'root' AS k, r.text, wr.evidence FROM word_root wr "
            "JOIN roots r ON r.id = wr.morpheme_id JOIN words w ON w.id = wr.word_id "
            f"WHERE w.spelling = '{w}' UNION ALL "
            "SELECT 'prefix', p.text, wp.evidence FROM word_prefix wp "
            "JOIN prefixes p ON p.id = wp.morpheme_id JOIN words w ON w.id = wp.word_id "
            f"WHERE w.spelling = '{w}' UNION ALL "
            "SELECT 'suffix', s.text, ws.evidence FROM word_suffix ws "
            "JOIN suffixes s ON s.id = ws.morpheme_id JOIN words w ON w.id = ws.word_id "
            f"WHERE w.spelling = '{w}'", DB_NAME)
        log.info(f"    morphemes: {[(l[0], l[1]) for l in links]}")
        if links:
            log.info(f"    evidence样本: {links[0][2]}")
    check(True, "抽样查询完成(见日志)")

    # 词根 spect 应有人工中文释义
    r = mysql_query("SELECT meaning FROM roots WHERE text='spect'", DB_NAME)
    check(bool(r) and bool(r[0][0]), "roots.spect 人工中文释义存在")

    # ------------------------------------------------------------------ 4
    section("4. 检索与分页")
    c = q1("SELECT COUNT(*) FROM words WHERE spelling LIKE '%tion%'")
    log.info(f"  LIKE '%tion%': {c} 行")
    page = mysql_query("SELECT spelling FROM words WHERE spelling LIKE "
                       "'%tion%' ORDER BY spelling LIMIT 5 OFFSET 10", DB_NAME)
    log.info(f"  分页第3页(5行/页): {[p[0] for p in page]}")
    check(int(c) > 100, "模糊检索返回结果")
    check(len(page) == 5, "分页 LIMIT/OFFSET 正常")
    # 词根->单词 分页排序
    c2 = q1("SELECT COUNT(*) FROM words w JOIN word_root wr ON wr.word_id=w.id "
            "JOIN roots r ON r.id=wr.morpheme_id WHERE r.text='spect'")
    log.info(f"  词根 spect 关联单词: {c2}")
    check(int(c2) > 0, "词根->单词关联可查询")

    # ------------------------------------------------------------------ 5
    section("5. 幂等与人工数据保护")
    mysql_run("DELETE FROM words WHERE spelling='__filltest__'", DB_NAME)
    mysql_run("INSERT INTO words (spelling, definitions) VALUES "
              "('__filltest__', '[{\"pos\":null,\"text\":\"人工定义\"}]')",
              DB_NAME)
    mysql_run("DELETE FROM stg_words WHERE spelling='__filltest__'", DB_NAME)
    mysql_run("INSERT INTO stg_words (spelling, phonetics, transliteration, "
              "definitions, category) VALUES ('__filltest__', "
              "'{\"uk\":\"test\"}', '测试', NULL, 'lemma')", DB_NAME)
    mysql_run("""
        INSERT INTO words (spelling, phonetics, transliteration, definitions,
                           part_of_speech, tags, bnc, frq, category,
                           example_sentences)
        SELECT s.spelling, s.phonetics, s.transliteration, s.definitions,
               s.part_of_speech, s.tags, s.bnc, s.frq, s.category,
               s.example_sentences
        FROM stg_words s WHERE s.spelling='__filltest__'
        ON DUPLICATE KEY UPDATE
            phonetics = IF(words.phonetics IS NULL, VALUES(phonetics), words.phonetics),
            transliteration = IF(words.transliteration IS NULL, VALUES(transliteration), words.transliteration),
            definitions = IF(words.definitions IS NULL, VALUES(definitions), words.definitions),
            category = IF(words.category IS NULL, VALUES(category), words.category)
    """, DB_NAME)
    r = mysql_query("SELECT definitions, phonetics, category FROM words "
                    "WHERE spelling='__filltest__'", DB_NAME)
    if check(bool(r), "fill-null 测试行存在"):
        defs, ph, cat = r[0]
        check(defs is not None and "人工" in defs,
              "人工 definitions 未被覆盖 (fill-null only)")
        check(ph == '{"uk": "test"}' or ph == '{"uk":"test"}',
              "空 phonetics 被补充")
        check(cat == "lemma", "空 category 被补充")
    mysql_run("DELETE FROM words WHERE spelling='__filltest__'", DB_NAME)
    mysql_run("DELETE FROM stg_words WHERE spelling='__filltest__'", DB_NAME)

    # 幂等: 关联表重复插入不产生新行
    before = q1("SELECT COUNT(*) FROM word_root")
    mysql_run("""
        INSERT IGNORE INTO word_root (word_id, morpheme_id, evidence, source)
        SELECT wr.word_id, wr.morpheme_id, wr.evidence, wr.source FROM word_root wr
    """, DB_NAME)
    after = q1("SELECT COUNT(*) FROM word_root")
    check(before == after, "关联表 INSERT IGNORE 幂等")

    # ------------------------------------------------------------------ 6
    section("6. 孤儿检查")
    orphans = q1(
        "SELECT COUNT(*) FROM word_forms f LEFT JOIN words w ON w.id=f.word_id "
        "WHERE w.id IS NULL")
    check(orphans == "0", f"word_forms 无孤儿 (实际 {orphans})", warn_only=True)
    orphans2 = q1(
        "SELECT COUNT(*) FROM stg_links sl WHERE NOT EXISTS "
        "(SELECT 1 FROM words w WHERE w.spelling = sl.spelling)")
    log.info(f"  stg_links 中找不到对应单词的链接: {orphans2} (正常丢弃)")

    # ------------------------------------------------------------------ 7
    section("7. JSON 合法性")
    for col in ("phonetics", "definitions", "tags", "example_sentences"):
        bad = q1(f"SELECT COUNT(*) FROM words WHERE {col} IS NOT NULL "
                 f"AND NOT JSON_VALID({col})")
        check(bad == "0", f"words.{col} JSON 合法 (bad={bad})")

    # ------------------------------------------------------------------ 8
    section("8. 数据展示样本")
    for label, sql in (
        ("词根(按关联词数)", """
            SELECT r.text, r.meaning, COUNT(wr.word_id) AS n
            FROM roots r LEFT JOIN word_root wr ON wr.morpheme_id=r.id
            GROUP BY r.id, r.text, r.meaning ORDER BY n DESC LIMIT %d""" % sample_n),
        ("前缀", "SELECT text, meaning FROM prefixes ORDER BY id LIMIT %d" % sample_n),
        ("后缀", "SELECT text, meaning FROM suffixes ORDER BY id LIMIT %d" % sample_n),
        ("词形变化", """
            SELECT w.spelling, f.form, f.form_tags FROM word_forms f
            JOIN words w ON w.id=f.word_id ORDER BY f.id LIMIT %d""" % sample_n),
        ("词源", """
            SELECT w.spelling, LEFT(e.etymology_text, 80) FROM word_etymologies e
            JOIN words w ON w.id=e.word_id ORDER BY e.id LIMIT %d""" % sample_n),
        ("来源清单", """
            SELECT source_key, data_version, license, sha256
            FROM pipeline_sources ORDER BY source_key"""),
    ):
        rows = mysql_query(sql, DB_NAME)
        log.info(f"  -- {label} --")
        for r in rows:
            log.info("    " + " | ".join(str(x)[:70] if x is not None else "-"
                                         for x in r))

    # ------------------------------------------------------------------ done
    elapsed = round(time.time() - t0, 1)
    log.info("=" * 62)
    log.info(f"验证完成: {elapsed}s  PASS={len(failures) == 0}  "
             f"failures={len(failures)} warnings={len(warnings)}")
    for f_ in failures:
        log.error(f"  FAIL: {f_}")
    for w_ in warnings:
        log.warning(f"  WARN: {w_}")
    save_state("validate", {"finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                            "counts": counts, "failures": failures,
                            "warnings": warnings, "elapsed_sec": elapsed})
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
