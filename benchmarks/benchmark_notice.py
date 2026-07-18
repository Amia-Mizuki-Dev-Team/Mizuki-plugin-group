"""Reproducible offline benchmark for the announcement storage boundaries."""

from __future__ import annotations

import json
import statistics
import sys
import tempfile
import time
from pathlib import Path
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from logic import get_content_hash  # noqa: E402
from storage import load_history, load_notices, save_json  # noqa: E402


def _measure(function: Callable[[], object], *, warmups: int = 2, runs: int = 5) -> dict[str, float]:
    for _ in range(warmups):
        function()
    samples = []
    for _ in range(runs):
        started = time.perf_counter()
        function()
        samples.append((time.perf_counter() - started) * 1000)
    return {
        "median_ms": statistics.median(samples),
        "min_ms": min(samples),
        "max_ms": max(samples),
    }


def benchmark_notice_file(count: int) -> dict[str, object]:
    notices = [f"notice-{index}" for index in range(count)]

    def save_and_load() -> int:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "notices.json"
            save_json(path, notices)
            return len(load_notices(path))

    result = _measure(save_and_load)
    result["count"] = count
    return result


def benchmark_history(count: int) -> dict[str, object]:
    def update_and_query() -> int:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "history.json"
            save_json(
                path,
                {
                    f"group:{index}": f"hash-{index % 3}"
                    for index in range(count)
                },
            )
            history = load_history(path)
            for index in range(count):
                history[f"group:{index}"] = f"hash-{(index + 1) % 3}"
            save_json(path, history)
            history = load_history(path)
            return len(history)

    result = _measure(update_and_query)
    result["count"] = count
    return result


def benchmark_pure_delivery(count: int) -> dict[str, object]:
    latest = get_content_hash("latest")
    history = {f"group:{index}": latest for index in range(count)}

    def pure_check() -> int:
        missing = 0
        for index in range(count):
            if history.get(f"group:{index}") != latest:
                missing += 1
        return missing

    result = _measure(pure_check)
    result["count"] = count
    return result


def main() -> None:
    report = {
        "python": sys.version.split()[0],
        "notice_save_load": [benchmark_notice_file(count) for count in (10, 100, 1000)],
        "history_update_query": [benchmark_history(count) for count in (100, 1000, 10000)],
        "pure_delivery_check": [benchmark_pure_delivery(count) for count in (100, 1000, 10000)],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
