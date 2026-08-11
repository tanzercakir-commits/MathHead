"""Load the stdlib-only legacy kernel without executing discovery package exports."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType


def load_legacy_kernel(root: Path) -> ModuleType:
    name = "mathhead.discovery.kernel"
    existing = sys.modules.get(name)
    if existing is not None:
        return existing
    source = root / "src/mathhead/discovery/kernel.py"
    spec = importlib.util.spec_from_file_location(name, source)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load frozen legacy kernel fixture")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except BaseException:
        del sys.modules[name]
        raise
    return module
