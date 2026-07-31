"""
Interpreter-startup shim for running Pynguin against ``openunderstand.oudb.api``
in isolation.

Python auto-imports ``sitecustomize`` at startup if it is on ``sys.path``; the
Pynguin run scripts put this directory on ``PYTHONPATH`` so the heavy
ANTLR/metric stack is stubbed *before* Pynguin imports the target module.

Pynguin runs in its own process **and** its own virtualenv, so it cannot import
the pytest ``conftest.py``.  It therefore loads ``tests/_isolation.py`` directly
by path -- the same implementation the pytest suite uses, so both isolate
exactly the same surface.
"""

import importlib.util
import sys
from pathlib import Path

# Pynguin snapshots module state with ``dill``, which recursively pickles the
# peewee ORM objects reachable from ``openunderstand.oudb.api``.  Those object
# graphs are deep, so the default limit (1000) overflows with a
# ``RecursionError`` before generation even starts.  Raise it well above the
# ORM graph depth so serialization can complete.
sys.setrecursionlimit(30000)

# Load tests/_isolation.py by path (this file lives in tests/_pynguin_support/).
_MODULE_NAME = "_ou_test_isolation"
_ISOLATION_PATH = Path(__file__).resolve().parent.parent / "_isolation.py"
_spec = importlib.util.spec_from_file_location(_MODULE_NAME, _ISOLATION_PATH)
if _spec is None or _spec.loader is None:  # pragma: no cover - defensive
    raise ImportError(f"cannot load isolation shim from {_ISOLATION_PATH}")
_isolation = importlib.util.module_from_spec(_spec)

# Register before exec_module.  Pynguin inspects `__module__` on everything it
# reaches and then re-imports that module to parse its syntax tree; the stub
# classes live here, so this name has to resolve through the normal import
# system or Pynguin dies with `ModuleNotFoundError: _ou_test_isolation`.
sys.modules[_MODULE_NAME] = _isolation
_spec.loader.exec_module(_isolation)

_isolation.install_stub_finder()
