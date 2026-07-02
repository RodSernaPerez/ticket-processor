#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ticket_processor.infrastructure.config.container import get_container  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll Gmail and process supermarket receipts.")
    parser.add_argument("--once", action="store_true", help="Process one polling cycle and exit.")
    args = parser.parse_args()

    container = get_container()
    logger = container.logger.bind(script="run_processor")

    def run_cycle() -> None:
        results = container.sync_purchases_use_case.execute()
        logger.info(
            "poll_cycle_completed",
            processed=len(results),
            successes=sum(1 for result in results if result.success),
            skipped=sum(1 for result in results if result.skipped),
        )

    if args.once:
        run_cycle()
        return 0

    logger.info("polling_started", interval_seconds=container.settings.gmail_poll_interval_seconds)
    while True:
        try:
            run_cycle()
        except Exception:
            logger.exception("poll_cycle_failed")
        time.sleep(container.settings.gmail_poll_interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
