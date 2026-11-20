"""CLI entrypoint for launching the SYNAPSE isolated subprocess worker."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from synapse_api.config import Settings
from synapse_worker.executor import WorkerRunner


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="synapse-worker", description="SYNAPSE durable job worker"
    )
    parser.add_argument("--once", action="store_true", help="Claim/run at most one job and exit")
    parser.add_argument("--poll-interval", type=float, default=0.5)
    parser.add_argument("--timeout-seconds", type=float, default=None)
    parser.add_argument("--database-url", default=None)
    parser.add_argument("--runs-root", default=None)
    args = parser.parse_args()

    if args.database_url:
        os.environ["SYNAPSE_DATABASE_URL"] = args.database_url
    if args.runs_root:
        os.environ["SYNAPSE_RUNS_DIR"] = args.runs_root

    settings = Settings.from_env(repo_root=Path.cwd())
    runner = WorkerRunner(settings)
    try:
        if args.once:
            runner.run_once(timeout_s=args.timeout_seconds)
        else:
            runner.run_loop(
                poll_interval_s=args.poll_interval,
                timeout_s=args.timeout_seconds,
            )
    except KeyboardInterrupt:
        return 0
    finally:
        runner.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
