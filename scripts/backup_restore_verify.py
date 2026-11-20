"""Verify backup & restore integrity for SQLite metadata DB and immutable run artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sqlite3
from pathlib import Path
from typing import Any


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(65536):
            h.update(chunk)
    return h.hexdigest()


def _snapshot_tree_hashes(root: Path) -> dict[str, str]:
    if not root.is_dir():
        return {}
    return {
        p.relative_to(root).as_posix(): _sha256_file(p)
        for p in sorted(root.rglob("*"))
        if p.is_file()
    }


def _db_table_counts(db_path: Path) -> dict[str, int]:
    conn = sqlite3.connect(str(db_path))
    try:
        tables = [
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
            ).fetchall()
        ]
        counts: dict[str, int] = {}
        for tbl in tables:
            val = conn.execute(f'SELECT COUNT(*) FROM "{tbl}"').fetchone()
            counts[tbl] = int(val[0]) if val else 0
        return counts
    finally:
        conn.close()


def verify_sqlite_and_runs_backup_restore(
    *,
    db_path: Path,
    runs_dir: Path,
    backup_work_dir: Path,
) -> dict[str, Any]:
    """Perform online SQLite backup + runs artifact snapshot, restore to fresh location, verify."""
    if not db_path.is_file():
        raise FileNotFoundError(f"SQLite metadata DB not found: {db_path}")

    snapshot_dir = backup_work_dir / "backup_snapshot"
    restore_dir = backup_work_dir / "restored"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    restore_dir.mkdir(parents=True, exist_ok=True)

    backup_db = snapshot_dir / "metadata_backup.sqlite3"
    src_conn = sqlite3.connect(str(db_path))
    dst_conn = sqlite3.connect(str(backup_db))
    try:
        src_conn.backup(dst_conn)
    finally:
        dst_conn.close()
        src_conn.close()

    backup_runs = snapshot_dir / "runs"
    if runs_dir.is_dir():
        shutil.copytree(runs_dir, backup_runs, dirs_exist_ok=True)
    else:
        backup_runs.mkdir(parents=True, exist_ok=True)

    restored_db = restore_dir / "restored.sqlite3"
    b_conn = sqlite3.connect(str(backup_db))
    r_conn = sqlite3.connect(str(restored_db))
    try:
        b_conn.backup(r_conn)
    finally:
        r_conn.close()
        b_conn.close()

    restored_runs = restore_dir / "runs"
    shutil.copytree(backup_runs, restored_runs, dirs_exist_ok=True)

    orig_counts = _db_table_counts(db_path)
    restored_counts = _db_table_counts(restored_db)
    if orig_counts != restored_counts:
        raise AssertionError(
            f"Database restore table count mismatch: {orig_counts} vs {restored_counts}"
        )

    orig_hashes = _snapshot_tree_hashes(runs_dir)
    restored_hashes = _snapshot_tree_hashes(restored_runs)
    if orig_hashes != restored_hashes:
        raise AssertionError("Restored run artifact hashes differ from source runs_dir")

    return {
        "verified": True,
        "table_counts": restored_counts,
        "artifact_file_count": len(restored_hashes),
        "backup_db_sha256": _sha256_file(backup_db),
        "restored_db_sha256": _sha256_file(restored_db),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify SYNAPSE backup & restore round-trip")
    parser.add_argument("--db-path", required=True)
    parser.add_argument("--runs-dir", required=True)
    parser.add_argument("--work-dir", required=True)
    args = parser.parse_args()

    result = verify_sqlite_and_runs_backup_restore(
        db_path=Path(args.db_path),
        runs_dir=Path(args.runs_dir),
        backup_work_dir=Path(args.work_dir),
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
