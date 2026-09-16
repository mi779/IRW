"""Load merged TSVs into MySQL and merge into the target tables.

Usage (from backend/):
    python -m pipeline.import_db          # full import (idempotent)
    python -m pipeline.import_db --reset  # also rebuild scratch stg_* tables

Everything is idempotent:
- words / morphemes: INSERT ... ON DUPLICATE KEY UPDATE with fill-null-only
  semantics (人工维护的数据永不被覆盖, 只补空字段);
- links / forms / etymology: INSERT IGNORE (关联表以复合主键天然去重);
- pipeline_sources: upsert by source_key.

Prerequisites:
- load_*.tsv produced by pipeline.merge
- MySQL user needs SELECT/INSERT/UPDATE/ALTER/CREATE on the target DB
- PIPELINE_MYSQL_FILES_DIR must point at a dir allowed by secure_file_priv
  (default /var/lib/mysql-files; local validation: .local-mysql/files)

Schema changes applied to an existing DB (fresh DBs get them via
scripts/init_db.py; models/data_source.py is the authoritative definition):
- words.category, word_{root,prefix,suffix}.evidence/.source columns
- word_forms, word_etymologies, pipeline_sources tables
"""
from __future__ import annotations

import json
import sys
import time

from pipeline.common import get_logger, load_data_infile, mysql_query, mysql_run, save_state, tsv_row
from pipeline.config import DB, DOWNLOAD_DIR, STAGING_DIR

log = get_logger("import_db")

DB_NAME = DB["database"]

# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------
STG_DDL = [
    """CREATE TABLE IF NOT EXISTS stg_words (
        spelling VARCHAR(100) NOT NULL,
        phonetics JSON NULL,
        transliteration VARCHAR(64) NULL,
        definitions JSON NULL,
        part_of_speech VARCHAR(20) NULL,
        tags JSON NULL,
        bnc INT NULL, frq INT NULL,
        category VARCHAR(20) NULL,
        example_sentences JSON NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS stg_morphs (
        text VARCHAR(50) NOT NULL,
        kind VARCHAR(10) NOT NULL,
        meaning VARCHAR(200) NULL,
        description TEXT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS stg_links (
        spelling VARCHAR(100) NOT NULL,
        morph_text VARCHAR(50) NOT NULL,
        kind VARCHAR(10) NOT NULL,
        evidence VARCHAR(300) NULL,
        source VARCHAR(20) NOT NULL DEFAULT 'kaikki'
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS stg_forms (
        spelling VARCHAR(100) NOT NULL,
        form VARCHAR(150) NOT NULL,
        form_tags VARCHAR(190) NULL,
        source VARCHAR(20) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS stg_etym (
        spelling VARCHAR(100) NOT NULL,
        etymology_text MEDIUMTEXT NULL,
        source VARCHAR(20) NOT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
    """CREATE TABLE IF NOT EXISTS stg_sources (
        source_key VARCHAR(50) NOT NULL,
        name VARCHAR(200) NULL, page_url VARCHAR(500) NULL, url VARCHAR(500) NULL,
        file VARCHAR(200) NULL, size BIGINT NULL, sha256 CHAR(64) NULL,
        data_version VARCHAR(100) NULL, license VARCHAR(200) NULL,
        retrieved_at DATETIME NULL, notes TEXT NULL
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci""",
]

# DDL applied to an EXISTING installation (mirrors models/data_source.py).
NEW_TABLE_DDL = [
    """CREATE TABLE IF NOT EXISTS word_forms (
        id INT NOT NULL AUTO_INCREMENT,
        word_id INT NOT NULL,
        form VARCHAR(150) NOT NULL,
        form_tags VARCHAR(190) NULL,
        source VARCHAR(20) NOT NULL DEFAULT 'ecdict',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        KEY ix_word_forms_word_id (word_id),
        UNIQUE KEY uq_word_form (word_id, form),
        CONSTRAINT fk_word_forms_word FOREIGN KEY (word_id)
            REFERENCES words (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='词形变化(来自ECDICT exchange与Kaikki forms)'""",
    """CREATE TABLE IF NOT EXISTS word_etymologies (
        id INT NOT NULL AUTO_INCREMENT,
        word_id INT NOT NULL,
        etymology_text MEDIUMTEXT NULL,
        source VARCHAR(20) NOT NULL DEFAULT 'kaikki',
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY uq_word_etymology (word_id),
        CONSTRAINT fk_word_etym_word FOREIGN KEY (word_id)
            REFERENCES words (id) ON DELETE CASCADE
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='词源文本(来自Kaikki etymology_text)'""",
    """CREATE TABLE IF NOT EXISTS pipeline_sources (
        id INT NOT NULL AUTO_INCREMENT,
        source_key VARCHAR(50) NOT NULL,
        name VARCHAR(200) NULL, page_url VARCHAR(500) NULL, url VARCHAR(500) NULL,
        file VARCHAR(200) NULL, size BIGINT NULL, sha256 CHAR(64) NULL,
        data_version VARCHAR(100) NULL, license VARCHAR(200) NULL,
        retrieved_at DATETIME NULL, notes TEXT NULL,
        created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
            ON UPDATE CURRENT_TIMESTAMP,
        PRIMARY KEY (id),
        UNIQUE KEY source_key (source_key)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
      COMMENT='词库数据来源记录(manifest)'""",
]


def col_exists(table: str, column: str) -> bool:
    rows = mysql_query(
        "SELECT 1 FROM information_schema.columns "
        f"WHERE table_schema=DATABASE() AND table_name='{table}' "
        f"AND column_name='{column}'", DB_NAME)
    return bool(rows)


def ensure_schema() -> None:
    for ddl in NEW_TABLE_DDL:
        mysql_run(ddl, DB_NAME)
    alters = []
    if not col_exists("words", "category"):
        alters.append("ALTER TABLE words ADD COLUMN category VARCHAR(20) NULL")
    for t in ("word_root", "word_prefix", "word_suffix"):
        if not col_exists(t, "evidence"):
            alters.append(
                f"ALTER TABLE {t} ADD COLUMN evidence VARCHAR(300) NULL, "
                "ADD COLUMN source VARCHAR(20) NOT NULL DEFAULT 'manual'")
    for a in alters:
        log.info(f"schema: {a}")
        mysql_run(a, DB_NAME)


def reset_stg() -> None:
    for ddl in STG_DDL:
        mysql_run(ddl, DB_NAME)
    for t in ("stg_words", "stg_morphs", "stg_links", "stg_forms",
              "stg_etym", "stg_sources"):
        mysql_run(f"TRUNCATE TABLE {t}", DB_NAME)


# ---------------------------------------------------------------------------
# load
# ---------------------------------------------------------------------------
LOADS = [
    ("load_words.tsv", "stg_words",
     ["spelling", "phonetics", "transliteration", "definitions",
      "part_of_speech", "tags", "bnc", "frq", "category", "example_sentences"]),
    ("load_morphs.tsv", "stg_morphs",
     ["text", "kind", "meaning", "description"]),
    ("load_links.tsv", "stg_links",
     ["spelling", "morph_text", "kind", "evidence", "source"]),
    ("load_forms.tsv", "stg_forms", ["spelling", "form", "form_tags", "source"]),
    ("load_etym.tsv", "stg_etym", ["spelling", "etymology_text", "source"]),
]


def write_sources_tsv() -> None:
    from pipeline.common import sha256_file
    from pipeline.config import BACKEND_DIR, SOURCES

    manifest_path = DOWNLOAD_DIR / "manifest.json"
    rows = []
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        for key, m in sorted(manifest.items()):
            src = SOURCES.get(key, {})
            rows.append([
                key, m.get("name") or src.get("name"),
                m.get("page_url") or src.get("page_url"),
                m.get("url"), m.get("file"), m.get("size"), m.get("sha256"),
                m.get("data_version") or src.get("data_version"),
                m.get("license") or src.get("license"),
                m.get("retrieved_at"),
                m.get("notes") or src.get("notes"),
            ])
    else:
        log.warning("manifest.json missing - pipeline_sources stays as-is")
    # 仓库内维护、不经过下载器的来源(如 curated-zh)
    curated = BACKEND_DIR / "pipeline" / "data" / "curated_zh.tsv"
    if curated.exists():
        rows.append([
            "curated-zh", SOURCES["curated-zh"]["name"],
            SOURCES["curated-zh"]["page_url"], "", curated.name,
            curated.stat().st_size, sha256_file(curated),
            SOURCES["curated-zh"]["data_version"],
            SOURCES["curated-zh"]["license"],
            time.strftime("%Y-%m-%d %H:%M:%S"),
            SOURCES["curated-zh"]["notes"],
        ])
    with open(STAGING_DIR / "load_sources.tsv", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(tsv_row(r))


def load_stg() -> dict:
    stats = {}
    for fname, table, cols in LOADS:
        path = STAGING_DIR / fname
        if not path.exists():
            log.error(f"missing {fname} - run pipeline.merge first")
            sys.exit(1)
        n = load_data_infile(path, table, cols, DB_NAME)
        stats[table] = n
        log.info(f"loaded {n} rows -> {table}")
    write_sources_tsv()
    n = load_data_infile(STAGING_DIR / "load_sources.tsv", "stg_sources",
                          ["source_key", "name", "page_url", "url", "file", "size",
                           "sha256", "data_version", "license", "retrieved_at",
                           "notes"], DB_NAME)
    stats["stg_sources"] = n
    log.info(f"loaded {n} rows -> stg_sources")
    return stats


# ---------------------------------------------------------------------------
# merge into target tables
# ---------------------------------------------------------------------------
def merge_words() -> None:
    mysql_run("""
        INSERT INTO words (spelling, phonetics, transliteration, definitions,
                           part_of_speech, tags, bnc, frq, category,
                           example_sentences)
        SELECT s.spelling, s.phonetics, s.transliteration, s.definitions,
               s.part_of_speech, s.tags, s.bnc, s.frq, s.category,
               s.example_sentences
        FROM stg_words s
        ON DUPLICATE KEY UPDATE
            phonetics = IF(words.phonetics IS NULL, VALUES(phonetics), words.phonetics),
            transliteration = IF(words.transliteration IS NULL, VALUES(transliteration), words.transliteration),
            definitions = IF(words.definitions IS NULL, VALUES(definitions), words.definitions),
            part_of_speech = IF(words.part_of_speech IS NULL, VALUES(part_of_speech), words.part_of_speech),
            tags = IF(words.tags IS NULL, VALUES(tags), words.tags),
            bnc = IF(words.bnc IS NULL, VALUES(bnc), words.bnc),
            frq = IF(words.frq IS NULL, VALUES(frq), words.frq),
            category = IF(words.category IS NULL, VALUES(category), words.category),
            example_sentences = IF(words.example_sentences IS NULL, VALUES(example_sentences), words.example_sentences)
    """, DB_NAME)


def merge_morphemes() -> None:
    for kind, table in (("root", "roots"), ("prefix", "prefixes"),
                        ("suffix", "suffixes")):
        mysql_run(f"""
            INSERT INTO {table} (text, meaning, description)
            SELECT s.text, s.meaning, s.description
            FROM stg_morphs s WHERE s.kind = '{kind}'
            ON DUPLICATE KEY UPDATE
                meaning = IF({table}.meaning IS NULL OR {table}.meaning = '',
                              VALUES(meaning), {table}.meaning),
                description = IF({table}.description IS NULL,
                                 VALUES(description), {table}.description)
        """, DB_NAME)


def merge_links() -> None:
    for kind, table in (("root", "roots"), ("prefix", "prefixes"),
                        ("suffix", "suffixes")):
        mysql_run(f"""
            INSERT IGNORE INTO word_{kind} (word_id, morpheme_id, evidence, source)
            SELECT w.id, m.id, s.evidence, s.source
            FROM stg_links s
            JOIN words w ON w.spelling = s.spelling
            JOIN {table} m ON m.text = s.morph_text
            WHERE s.kind = '{kind}'
        """, DB_NAME)


def merge_extras() -> None:
    mysql_run("""
        INSERT IGNORE INTO word_forms (word_id, form, form_tags, source)
        SELECT w.id, s.form, s.form_tags, s.source
        FROM stg_forms s JOIN words w ON w.spelling = s.spelling
    """, DB_NAME)
    mysql_run("""
        INSERT IGNORE INTO word_etymologies (word_id, etymology_text, source)
        SELECT w.id, s.etymology_text, s.source
        FROM stg_etym s JOIN words w ON w.spelling = s.spelling
    """, DB_NAME)


def merge_sources() -> None:
    mysql_run("""
        INSERT INTO pipeline_sources (source_key, name, page_url, url, file,
                                      size, sha256, data_version, license,
                                      retrieved_at, notes)
        SELECT source_key, name, page_url, url, file, size, sha256,
               data_version, license, retrieved_at, notes
        FROM stg_sources
        ON DUPLICATE KEY UPDATE
            name=VALUES(name), page_url=VALUES(page_url), url=VALUES(url),
            file=VALUES(file), size=VALUES(size), sha256=VALUES(sha256),
            data_version=VALUES(data_version), license=VALUES(license),
            retrieved_at=VALUES(retrieved_at), notes=VALUES(notes)
    """, DB_NAME)


def counts() -> dict:
    out = {}
    for t in ("words", "roots", "prefixes", "suffixes",
              "word_root", "word_prefix", "word_suffix",
              "word_forms", "word_etymologies", "pipeline_sources"):
        r = mysql_query(f"SELECT COUNT(*) FROM {t}", DB_NAME)
        out[t] = r[0][0] if r else "?"
    return out


def main() -> None:
    t0 = time.time()
    log.info("step 1/6: ensure schema")
    ensure_schema()
    log.info("step 2/6: reset scratch tables")
    for t in ("stg_words", "stg_morphs", "stg_links", "stg_forms",
              "stg_etym", "stg_sources"):
        mysql_run(f"DROP TABLE IF EXISTS {t}", DB_NAME)
    reset_stg()
    log.info("step 3/6: LOAD DATA staging")
    stats = load_stg()
    log.info("step 4/6: merge words + morphemes (fill-null semantics)")
    merge_morphemes()
    merge_words()
    log.info("step 5/6: merge links / forms / etymology / sources")
    merge_links()
    merge_extras()
    merge_sources()
    log.info("step 6/6: final counts")
    c = counts()
    result = {"elapsed_sec": round(time.time() - t0, 1), "loaded": stats,
              "counts": c}
    save_state("import_db", {"finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                             **result})
    log.info(f"DONE {json.dumps(result, ensure_ascii=False)}")


if __name__ == "__main__":
    main()
