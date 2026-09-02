#!/usr/bin/env python3
"""Nightly WAL-safe snapshot of the new server's SQLite DB.

Uses the sqlite3 online backup API (consistent even while the server writes),
gzips the snapshot and keeps the last N days. Usage:
    python3 backup_db.py --db /var/lib/joinmultiplayer-new/contributions.sqlite3 \
        --out /var/backups/joinmultiplayer-new --keep 14
"""

import argparse
import gzip
import shutil
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--keep", type=int, default=14)
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    snapshot = out_dir / f"contributions_{stamp}.sqlite3"

    src = sqlite3.connect(f"file:{args.db}?mode=ro", uri=True)
    dst = sqlite3.connect(str(snapshot))
    with dst:
        src.backup(dst)
    src.close()
    dst.close()

    with open(snapshot, "rb") as raw, gzip.open(f"{snapshot}.gz", "wb") as packed:
        shutil.copyfileobj(raw, packed)
    snapshot.unlink()

    cutoff = time.time() - args.keep * 86400
    for old in out_dir.glob("contributions_*.sqlite3.gz"):
        if old.stat().st_mtime < cutoff:
            old.unlink()
    print(f"backup ok: {snapshot}.gz")


if __name__ == "__main__":
    main()
