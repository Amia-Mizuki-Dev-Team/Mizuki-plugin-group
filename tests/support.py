"""Test import path setup for standalone and monorepo invocations."""

from __future__ import annotations

import sys
from pathlib import Path


def add_repo_paths() -> None:
    tests_root = Path(__file__).resolve().parent
    repo_root = tests_root.parent
    for path in (repo_root, tests_root):
        path_string = str(path)
        if path_string not in sys.path:
            sys.path.insert(0, path_string)
