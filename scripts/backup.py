#!/usr/bin/env python3
"""Nightly SQLite backup (L6).

Takes a **consistent** snapshot of the live DB using SQLite's online backup API
(safe to run while the server is writing — no ``.db`` file copy race), writes it
to ``var/backups/ats-YYYYMMDD-HHMMSS.db``, and prunes to the most recent
``ATS_BACKUP_RETENTION`` snapshots (default 14).

Run manually:
    .venv/Scripts/python.exe scripts/backup.py

Schedule nightly on Windows (Task Scheduler), e.g. 21:00 IST:
    schtasks /Create /TN "ATS nightly backup" /SC DAILY /ST 21:00 ^
      /TR "\"%CD%\\.venv\\Scripts\\python.exe\" \"%CD%\\scripts\\backup.py\""

(macOS/Linux: a cron line ``0 21 * * *  cd <repo> && .venv/bin/python scripts/backup.py``.)
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime
from pathlib import Path

# Allow running as a file path or module.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _db_path(db_url: str) -> Path | None:
    prefix = "sqlite:///"
    return Path(db_url[len(prefix):]) if db_url.startswith(prefix) else None


def backup_once(db_path: Path, dest_dir: Path, retention: int) -> Path:
    """Snapshot ``db_path`` into ``dest_dir`` and prune to ``retention`` files.
    Returns the snapshot path."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    dest = dest_dir / f"{db_path.stem}-{stamp}.db"
    n = 1  # disambiguate multiple snapshots taken within the same second
    while dest.exists():
        dest = dest_dir / f"{db_path.stem}-{stamp}-{n}.db"
        n += 1

    src = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)   # atomic, WAL-consistent snapshot
        finally:
            dst.close()
    finally:
        src.close()

    _prune(dest_dir, db_path.stem, retention)
    return dest


def _prune(dest_dir: Path, stem: str, retention: int) -> None:
    if retention <= 0:
        return
    snaps = sorted(dest_dir.glob(f"{stem}-*.db"), key=lambda p: p.stat().st_mtime)
    for old in snaps[:-retention]:
        try:
            old.unlink()
        except OSError:
            pass


def main() -> int:
    from ats.core.config import get_settings

    settings = get_settings()
    db_path = _db_path(settings.db_url)
    if db_path is None:
        print(f"backup: only SQLite is supported (db_url={settings.db_url!r})", file=sys.stderr)
        return 2
    if not db_path.exists():
        print(f"backup: DB not found at {db_path}", file=sys.stderr)
        return 1

    dest_dir = db_path.parent / "backups"
    retention = int(getattr(settings, "backup_retention", 14))
    dest = backup_once(db_path, dest_dir, retention)
    size_mb = dest.stat().st_size / 1e6
    kept = len(list(dest_dir.glob(f"{db_path.stem}-*.db")))
    print(f"backup: wrote {dest}  ({size_mb:.1f} MB); {kept} snapshot(s) kept (retention {retention})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
