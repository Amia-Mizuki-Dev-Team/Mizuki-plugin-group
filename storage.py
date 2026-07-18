"""Small atomic JSON storage used by the notice plugin."""

from __future__ import annotations

import json
import os
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import Any


def load_json(file: Path, default: Any) -> Any:
    """Load JSON and return the caller's safe default for malformed files."""

    if not file.exists():
        return default
    try:
        return json.loads(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return default


def save_json(file: Path, data: Any) -> None:
    """Write JSON through a same-directory temporary file and atomic replace."""

    file.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{file.name}.",
        suffix=".tmp",
        dir=file.parent,
        text=True,
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        Path(temp_name).replace(file)
    except Exception:
        with suppress(OSError):
            Path(temp_name).unlink()
        raise


def load_notices(file: Path) -> list[str]:
    value = load_json(file, [])
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def load_history(file: Path) -> dict[str, str]:
    value = load_json(file, {})
    if not isinstance(value, dict):
        return {}
    return {
        str(key): item
        for key, item in value.items()
        if isinstance(item, str)
    }


def record_history(file: Path, target_id: str, notice_hash: str) -> None:
    """Merge one successful send into the latest history and save it.

    The read happens immediately before the atomic replacement so concurrent
    tasks in the same event loop do not overwrite each other's target entry
    with a stale snapshot.  This is still intentionally a single-process
    guarantee; multi-process deployments need a shared transactional store.
    """

    history = load_history(file)
    history[target_id] = notice_hash
    save_json(file, history)
