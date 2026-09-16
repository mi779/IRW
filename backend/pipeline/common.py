"""Shared helpers: logging, mysql CLI runner, state files, TSV escaping."""
from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

from pipeline.config import DB, LOG_DIR, STATE_DIR


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    fh = logging.FileHandler(LOG_DIR / f"{name}.log", encoding="utf-8")
    fh.setFormatter(fmt)
    sh = logging.StreamHandler(sys.stdout)
    sh.setFormatter(fmt)
    logger.addHandler(fh)
    logger.addHandler(sh)
    return logger


def _mysql_cmd(database: str | None = None, skip_names: bool = False) -> list:
    cmd = [
        "mysql",
        "-h", DB["host"],
        "-P", str(DB["port"]),
        "-u", DB["user"],
        "--default-character-set=utf8mb4",
    ]
    if skip_names:
        cmd.append("--skip-column-names")
    if database:
        cmd.append(database)
    return cmd


def mysql_run(sql: str, database: str | None = None,
              skip_names: bool = False) -> str:
    """Execute a SQL string. Password passed via MYSQL_PWD env (not on cmdline)."""
    env = dict(os.environ)
    if DB["password"]:
        env["MYSQL_PWD"] = DB["password"]
    r = subprocess.run(_mysql_cmd(database, skip_names) + ["-e", sql], env=env,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"mysql failed: {r.stderr.strip()[:800]}")
    return r.stdout


def mysql_query(sql: str, database: str | None = None) -> list:
    """Run a query and return data rows (list of str lists, headers skipped)."""
    out = mysql_run(sql, database, skip_names=True)
    return [line.split("\t") for line in out.splitlines() if line]


def mysql_stream_file(sql_file: Path, database: str | None = None) -> None:
    """Stream a large .sql file into mysql via stdin (no full in-memory read)."""
    env = dict(os.environ)
    if DB["password"]:
        env["MYSQL_PWD"] = DB["password"]
    with open(sql_file, "rb") as f:
        r = subprocess.run(_mysql_cmd(database), stdin=f, env=env,
                           capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"mysql file failed: {r.stderr.decode()[:800]}")


def load_data_infile(tsv: Path, table: str, columns: list, database: str | None = None) -> int:
    """Server-side LOAD DATA INFILE. Copies the tsv into MYSQL_FILES_DIR first."""
    import shutil
    dest = Path(os.environ.get("PIPELINE_MYSQL_FILES_DIR", "/var/lib/mysql-files")) / tsv.name
    shutil.copy2(tsv, dest)
    os.chmod(dest, 0o644)
    cols = ",".join(columns)
    sql = (
        f"LOAD DATA INFILE '{dest}' INTO TABLE {table} "
        f"CHARACTER SET utf8mb4 "
        f"FIELDS TERMINATED BY '\\t' ESCAPED BY '\\\\' LINES TERMINATED BY '\\n' "
        f"({cols}); SELECT ROW_COUNT();"
    )
    out = mysql_run(sql, database, skip_names=True)
    try:
        n = int(out.strip().splitlines()[-1])
    except (ValueError, IndexError):
        n = 0
    return n


def tsv_escape(v) -> str:
    """Escape a value for LOAD DATA default escape syntax (backslash)."""
    if v is None:
        return r"\N"
    s = str(v)
    s = s.replace("\\", "\\\\")
    s = s.replace("\t", "\\t")
    s = s.replace("\n", "\\n")
    s = s.replace("\r", "\\r")
    return s


def tsv_row(values: list) -> str:
    return "\t".join(tsv_escape(v) for v in values) + "\n"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_state(name: str, default=None):
    p = STATE_DIR / f"{name}.json"
    if not p.exists():
        return default
    return json.loads(p.read_text(encoding="utf-8"))


def save_state(name: str, data) -> None:
    p = STATE_DIR / f"{name}.json"
    p.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


def dedup_tsv(path: Path, unique_cols: list | None = None) -> int:
    """LC_ALL=C sort -u a staging tsv (memory-safe external sort).
    If unique_cols given (1-based indices), only whole-line dedup still applies;
    column-subset dedup must be handled by the parser or import SQL."""
    env = dict(os.environ, LC_ALL="C")
    r = subprocess.run(["sort", "-u", "-o", str(path), str(path)],
                       env=env, capture_output=True)
    if r.returncode != 0:
        raise RuntimeError(f"sort failed: {r.stderr.decode()[:300]}")
    with open(path, "rb") as f:
        return sum(1 for _ in f)
