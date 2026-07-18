"""Small reproducible benchmark for the notice history write path.

This benchmark uses a temporary directory and never touches the bot's runtime
data.  It measures the atomic JSON merge used after a successful notice send;
the result is a local comparison signal, not a deployment SLA.
"""

# ruff: noqa: T201 - this file is a command-line benchmark.

from __future__ import annotations

import argparse
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from storage import load_history, record_history


def run(iterations: int, targets: int) -> tuple[float, int]:
    if iterations < 1 or targets < 1:
        raise ValueError

    with tempfile.TemporaryDirectory() as temp_dir:
        history_file = Path(temp_dir) / "sent_history.json"
        started = time.perf_counter()
        for index in range(iterations):
            target_id = f"group:{index % targets}"
            record_history(history_file, target_id, f"hash-{index % 7}")
        elapsed = time.perf_counter() - started
        entries = len(load_history(history_file))
    return elapsed, entries


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=100)
    parser.add_argument("--targets", type=int, default=32)
    args = parser.parse_args()

    elapsed, entries = run(args.iterations, args.targets)
    rate = args.iterations / elapsed if elapsed else float("inf")
    print(f"iterations={args.iterations}")
    print(f"targets={args.targets}")
    print(f"elapsed_seconds={elapsed:.6f}")
    print(f"records_per_second={rate:.2f}")
    print(f"final_history_entries={entries}")


if __name__ == "__main__":
    main()
