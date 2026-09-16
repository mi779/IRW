"""Resumable downloader with timeout, retry, progress and SHA-256 verification.

Usage (from backend/):
    python -m pipeline.download kaikki-en ecdict morphemes
    python -m pipeline.download --check     # verify sha256 of finished files
"""
import json
import sys
import time
import urllib.request
from pathlib import Path

from pipeline.common import get_logger, sha256_file
from pipeline.config import DOWNLOAD_DIR, SOURCES

log = get_logger("download")

CHUNK = 1 << 20          # 1MB read chunks
READ_TIMEOUT = 60        # socket timeout per read
MAX_RETRIES = 10
PROGRESS_EVERY = 50       # log every 50MB


def _download_one(key: str) -> None:
    src = SOURCES[key]
    dest = DOWNLOAD_DIR / src["file"]
    part = Path(str(dest) + ".part")
    expected_size = None

    if dest.exists():
        log.info(f"[{key}] already downloaded: {dest.name}")
        return

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            existing = part.stat().st_size if part.exists() else 0
            headers = {"User-Agent": "irw-pipeline/1.0"}
            if existing:
                headers["Range"] = f"bytes={existing}-"
            req = urllib.request.Request(src["url"], headers=headers)
            with urllib.request.urlopen(req, timeout=READ_TIMEOUT) as resp, \
                    open(part, "ab") as f:
                if existing and resp.status != 206:
                    # server ignored the range: restart from zero
                    log.info(f"[{key}] server ignored Range, restarting")
                    f.truncate(0)
                    existing = 0
                clen = resp.headers.get("Content-Length")
                expected_size = existing + int(clen) if clen else None
                since_log = 0
                while True:
                    chunk = resp.read(CHUNK)
                    if not chunk:
                        break
                    f.write(chunk)
                    since_log += len(chunk)
                    if since_log >= PROGRESS_EVERY * CHUNK:
                        done = f.tell()
                        pct = (f"{100 * done / expected_size:.1f}%" if expected_size
                               else "?")
                        log.info(f"[{key}] {done >> 20}MB / "
                                 f"{expected_size >> 20 if expected_size else '?'}MB ({pct})")
                        since_log = 0
            if expected_size is not None and part.stat().st_size != expected_size:
                raise IOError(f"size mismatch: got {part.stat().st_size}, "
                              f"expected {expected_size}")
            part.rename(dest)
            log.info(f"[{key}] download complete: {dest.name} "
                     f"({dest.stat().st_size} bytes)")
            return
        except Exception as e:
            wait = min(2 ** attempt, 60)
            log.warning(f"[{key}] attempt {attempt} failed: {e}; "
                        f"retrying in {wait}s (resume supported)")
            time.sleep(wait)
    raise RuntimeError(f"[{key}] download failed after {MAX_RETRIES} attempts")


def verify_manifest() -> dict:
    """Compute/refresh SHA-256 of each finished download, save manifest.json."""
    manifest = {}
    for key, src in SOURCES.items():
        f = DOWNLOAD_DIR / src["file"]
        if not f.exists():
            log.info(f"[{key}] not downloaded yet")
            continue
        digest = sha256_file(f)
        manifest[key] = {
            "source": key,
            "name": src["name"],
            "page_url": src["page_url"],
            "url": src["url"],
            "file": f.name,
            "size": f.stat().st_size,
            "sha256": digest,
            "data_version": src["data_version"],
            "license": src["license"],
            "retrieved_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "notes": src.get("notes"),
        }
        log.info(f"[{key}] sha256={digest} size={f.stat().st_size}")
    (DOWNLOAD_DIR / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=1), encoding="utf-8")
    return manifest


def main() -> None:
    args = sys.argv[1:]
    if args == ["--check"]:
        verify_manifest()
        return
    keys = args or ["kaikki-en", "ecdict", "morphemes"]
    for k in keys:
        _download_one(k)
    verify_manifest()


if __name__ == "__main__":
    main()
