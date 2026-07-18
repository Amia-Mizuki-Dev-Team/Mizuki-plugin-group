"""Pure helpers for the notice plugin.

The helpers in this module deliberately do not import NoneBot.  Keeping the
validation and coverage calculations here makes the important behavior easy
to test offline and keeps the runtime matcher focused on message I/O.
"""

from __future__ import annotations

import hashlib
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

MAX_NOTICES = 5
MAX_NOTICE_LENGTH = 2000


@dataclass(frozen=True, slots=True)
class NoticeCommand:
    """The small command grammar used by the announcement matcher."""

    operation: str
    argument: str | None = None


def get_content_hash(content: str) -> str:
    """Return the stable version identifier used in send history."""

    return hashlib.md5(content.encode("utf-8")).hexdigest()


def target_key(*, group_id: object | None = None, user_id: object | None = None) -> str:
    """Return a namespace-safe history key for one delivery target."""

    if group_id is not None:
        return f"group:{group_id}"
    if user_id is not None:
        return f"private:{user_id}"
    raise ValueError("a group_id or user_id is required")


def parse_notice_command(text: str) -> NoticeCommand | None:
    """Parse the public announcement command without importing NoneBot."""

    if not isinstance(text, str):
        return None
    parts = text.strip().split(maxsplit=2)
    if not parts or parts[0] != "公告":
        return None
    operation = parts[1] if len(parts) > 1 else "查看"
    argument = parts[2] if len(parts) > 2 else None
    return NoticeCommand(operation=operation, argument=argument)


def valid_notice_content(content: str | None) -> bool:
    return bool(
        isinstance(content, str)
        and content.strip()
        and len(content) <= MAX_NOTICE_LENGTH
    )


def parse_notice_index(value: str | None, notice_count: int) -> int | None:
    """Convert a one-based user index to a zero-based list index.

    ``None`` is returned for non-decimal input and for indexes outside the
    current notice list.  The explicit decimal check avoids surprising
    ``int`` behavior for values such as underscores or superscript digits.
    """

    if not isinstance(value, str) or not value or not value.isdecimal():
        return None
    try:
        number = int(value)
    except ValueError:
        return None
    if not 1 <= number <= notice_count:
        return None
    return number - 1


def group_coverage(
    group_list: Iterable[Any],
    history: Mapping[str, str],
    latest_hash: str,
) -> tuple[int, int]:
    """Return ``(sent_groups, total_groups)`` for the current bot groups.

    Only group IDs returned by the current bot are counted.  Stale history
    entries and private targets therefore cannot inflate the denominator or
    numerator.
    """

    target_ids: set[str] = set()
    for group in group_list:
        if not isinstance(group, Mapping):
            continue
        group_id = group.get("group_id")
        if group_id is not None:
            target_ids.add(f"group:{group_id}")

    sent_count = sum(
        1 for target_id in target_ids if history.get(target_id) == latest_hash
    )
    return sent_count, len(target_ids)
