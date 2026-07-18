"""Load the hyphenated plugin package under a test-only import name."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from types import ModuleType

_MODULE_NAME = "amia_plugin_group_test"


def load_plugin() -> ModuleType:
    module = sys.modules.get(_MODULE_NAME)
    if module is not None:
        return module

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location(
        _MODULE_NAME,
        root / "__init__.py",
        submodule_search_locations=[str(root)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError
    module = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE_NAME] = module
    spec.loader.exec_module(module)
    return module
