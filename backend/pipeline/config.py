"""Pipeline configuration: paths, database access, data source registry."""
import os
from pathlib import Path
from urllib.parse import unquote, urlparse

BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("PIPELINE_DATA_DIR", BACKEND_DIR / "data" / "pipeline"))
DOWNLOAD_DIR = DATA_DIR / "downloads"
STAGING_DIR = DATA_DIR / "staging"
STATE_DIR = DATA_DIR / "state"
LOG_DIR = DATA_DIR / "logs"
for _d in (DOWNLOAD_DIR, STAGING_DIR, STATE_DIR, LOG_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# MySQL LOAD DATA INFILE requires files inside secure_file_priv dir.
MYSQL_FILES_DIR = os.environ.get("PIPELINE_MYSQL_FILES_DIR", "/var/lib/mysql-files")

# ---------------------------------------------------------------------------
# Data source registry. data_version = 源数据日期(以来源页面声明为准, 非抓取时间).
# 核实时间: 2026-09-16
# ---------------------------------------------------------------------------
SOURCES = {
    "kaikki-en": {
        "name": "Kaikki English (Wiktionary wiktextract postprocessed)",
        "page_url": "https://kaikki.org/dictionary/English/index.html",
        "url": "https://kaikki.org/dictionary/English/kaikki.org-dictionary-English.jsonl.gz",
        "file": "kaikki-en.jsonl.gz",
        "data_version": "enwiktionary dump 2026-09-02",
        "license": "CC BY-SA 4.0 (Wiktionary text)",
        "notes": (
            "仅英语词条(lang_code=en)。rawdata页声明当前版本出自2026-09-02的"
            "enwiktionary dump, 文件Last-Modified 2026-09-09; English索引页脚注"
            "显示较旧的2026-07-06日期, 已如实记录。未压缩约3GB, 流式解析。"
        ),
    },
    "ecdict": {
        "name": "ECDICT (ecdict.csv, 76万词条基础版)",
        "page_url": "https://github.com/skywind3000/ECDICT",
        "url": "https://raw.githubusercontent.com/skywind3000/ECDICT/master/ecdict.csv",
        "file": "ecdict.csv",
        "data_version": "repo最后提交 2026-09-16",
        "license": "MIT",
        "notes": (
            "选repo根目录ecdict.csv(76万条)而非releases的stardict/增强版"
            "(340万条, 为mdx等词典应用格式且体积大)。提供中文释义/英式音标/"
            "词频/考试标签/词形变化。考试标签为历史语料标注, 不代表最新考试大纲。"
        ),
    },
    "morphemes": {
        "name": "colingoldberg/morphemes",
        "page_url": "https://github.com/colingoldberg/morphemes",
        "url": "https://raw.githubusercontent.com/colingoldberg/morphemes/master/data/morphemes.json",
        "file": "morphemes.json",
        "data_version": "repo最后提交 2026-07-09",
        "license": "MIT",
        "notes": "2435个词素组(按含义分组), 含变体形式/英文含义/适用词性/示例词。",
    },
    "curated-zh": {
        "name": "本项目人工维护词素中文释义",
        "page_url": "https://github.com/mi779/IRW",
        "url": "",
        "file": "curated_zh.tsv",
        "data_version": "随仓库维护",
        "license": "项目自有数据",
        "notes": (
            "从 scripts/import_morphemes.py 人工词素表迁移(仅取 text/中文含义, "
            "不迁移其子串自动链接逻辑)。"
        ),
    },
}

# ---------------------------------------------------------------------------
# Database access for the mysql CLI. Credentials come from DATABASE_URL
# (env var or backend/.env) - never hard-coded, never logged.
# ---------------------------------------------------------------------------


def load_db_config() -> dict:
    url = os.environ.get("DATABASE_URL")
    if not url:
        env_file = BACKEND_DIR / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line.startswith("DATABASE_URL="):
                    url = line.split("=", 1)[1].strip()
                    break
    if not url:
        raise RuntimeError("DATABASE_URL not found in env or backend/.env")
    if url.startswith("mysql+"):  # mysql+asyncmy://...
        url = url[len("mysql+"):]
    p = urlparse(url)
    return {
        "host": p.hostname or "127.0.0.1",
        "port": p.port or 3306,
        "user": unquote(p.username or "root"),
        "password": unquote(p.password or ""),
        "database": p.path.lstrip("/").split("?")[0] or "vocab_app",
    }


DB = load_db_config()
