"""
Interpreter-startup shim for running Pynguin against ``openunderstand.oudb.api``
in isolation.  Python auto-imports ``sitecustomize`` at startup if it is on
``sys.path``; the Pynguin run scripts put this directory on ``PYTHONPATH`` so the
heavy ANTLR/metric stack is stubbed (the same meta-path finder used by the
pytest ``conftest.py``) before Pynguin imports the target module.
"""

import importlib.abc
import importlib.machinery
import sys
import types

# Pynguin snapshots module state with ``dill``, which recursively pickles the
# peewee ORM objects reachable from ``openunderstand.oudb.api``.  Those object
# graphs are deep, so the default limit (1000) overflows with a
# ``RecursionError`` before generation even starts.  Raise it well above the
# ORM graph depth so serialization can complete.
sys.setrecursionlimit(30000)


class _Dummy:
    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return None


def _stub_getattr(_name):
    return _Dummy


class _StubFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    _PREFIXES = ("openunderstand.metrics", "openunderstand.ounderstand", "gen")

    def _matches(self, fullname):
        return any(
            fullname == prefix or fullname.startswith(prefix + ".")
            for prefix in self._PREFIXES
        )

    def find_spec(self, fullname, path=None, target=None):
        if self._matches(fullname):
            return importlib.machinery.ModuleSpec(fullname, self)
        return None

    def create_module(self, spec):
        module = types.ModuleType(spec.name)
        module.__path__ = []
        module.__getattr__ = _stub_getattr
        return module

    def exec_module(self, module):
        pass


if not any(isinstance(f, _StubFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _StubFinder())
