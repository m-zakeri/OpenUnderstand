"""
Shared test-isolation machinery for the OpenUnderstand test suite.

Why this module exists
----------------------
Importing ``openunderstand.oudb.api`` transitively imports the whole metric
engine (``openunderstand.metrics.*``) and the ANTLR/Java parsing stack
(``openunderstand.ounderstand.*``).  Several metric modules also use absolute
``from gen.javaLabeled... import ...`` imports that only resolve in the original
run layout.  None of that machinery is needed to exercise the database-backed
``Db``/``Ent``/``Kind``/``Ref`` classes.

``install_stub_finder()`` registers a :pep:`302` meta-path finder that
synthesises a harmless stub module for ANY import under those prefixes.  This is
the textbook "test in isolation" technique: the unit under test (the api layer)
is decoupled from its heavy collaborators (the parser/metric layers).

Two consumers share this module:

* ``tests/conftest.py`` -- for the pytest unit suite.
* ``tests/_pynguin_support/sitecustomize.py`` -- for Pynguin, which runs in a
  separate process **and** a separate virtualenv, so it cannot import a pytest
  conftest.  It bootstraps this module by path instead.

Keeping one implementation means the pytest suite and the Pynguin run always
isolate exactly the same surface.
"""

from __future__ import annotations

import importlib.abc
import importlib.machinery
import sys
import types

__all__ = ["STUBBED_PREFIXES", "StubFinder", "install_stub_finder"]

#: Import prefixes replaced by synthetic stub modules during isolated testing.
#:
#: ``openunderstand.metrics`` / ``openunderstand.ounderstand`` / ``gen``
#:     the metric engine and the ANTLR parser stack.
#:
#: ``git``
#:     GitPython is imported at ``api.py`` module level but used by exactly one
#:     function, ``update_db()``, which needs a real repository and is therefore
#:     outside the unit under test (it is marked ``# pragma: no cover``).
#:
#:     Stubbing it is not merely tidy -- it is required for Pynguin.  Pynguin
#:     runs its search in a ``multiprocess`` worker and ships module state there
#:     with ``dill``.  While reconstructing types, ``dill._create_type`` calls
#:     the metaclass of ``git.util.Iterable``, and that metaclass' ``__init__``
#:     refers to its own name as a module global::
#:
#:         class IterableClassWatcher(type):
#:             def __init__(cls, name, bases, clsdict):
#:                 for base in bases:
#:                     if type(base) == IterableClassWatcher:   # global lookup
#:
#:     During reconstruction that global is not yet bound, so the worker dies
#:     with ``NameError: name 'IterableClassWatcher' is not defined``.  The
#:     class is GitPython's deprecated ``Iterable`` shim (removed upstream after
#:     3.1.x), so keeping it out of the module graph avoids the whole problem.
STUBBED_PREFIXES: tuple[str, ...] = (
    "openunderstand.metrics",
    "openunderstand.ounderstand",
    "gen",
    "git",
)


class _Dummy:
    """A do-nothing stand-in for any class/function pulled from a stub module."""

    def __init__(self, *args, **kwargs):
        pass

    def __call__(self, *args, **kwargs):
        return None


def _stub_getattr(name):
    """
    PEP 562 module ``__getattr__``: synthesise any requested symbol.

    Dunder names are deliberately **not** synthesised.  Introspection tools walk
    ``sys.modules`` and probe attributes such as ``__file__``, ``__all__`` or
    ``__wrapped__``, expecting either a real value or ``AttributeError``.
    Handing them a class instead makes them fail in confusing ways -- Hypothesis'
    constant-collection pass, for instance, crashes with
    ``TypeError: argument of type 'type' is not iterable`` when ``__file__``
    turns out not to be a string.  Raising ``AttributeError`` is the honest
    answer: a stub module genuinely has no such attribute.
    """
    if name.startswith("__") and name.endswith("__"):
        raise AttributeError(name)
    return _Dummy


class StubFinder(importlib.abc.MetaPathFinder, importlib.abc.Loader):
    """Meta-path finder that loads synthetic packages for stubbed prefixes."""

    def __init__(self, prefixes: tuple[str, ...] = STUBBED_PREFIXES):
        self.prefixes = prefixes

    def _matches(self, fullname: str) -> bool:
        return any(
            fullname == prefix or fullname.startswith(prefix + ".")
            for prefix in self.prefixes
        )

    def find_spec(self, fullname, path=None, target=None):
        if self._matches(fullname):
            return importlib.machinery.ModuleSpec(fullname, self)
        return None

    def create_module(self, spec):
        module = types.ModuleType(spec.name)
        module.__path__ = []  # treat as a package so submodule imports resolve
        module.__getattr__ = _stub_getattr  # PEP 562: synthesise any name
        return module

    def exec_module(self, module):
        """Stub modules have no body to execute."""


def install_stub_finder(prefixes: tuple[str, ...] = STUBBED_PREFIXES) -> bool:
    """
    Install the stub finder at the front of ``sys.meta_path``.

    Idempotent: repeated calls (e.g. under ``pytest-xdist`` or a re-imported
    conftest) will not stack duplicate finders.

    Returns ``True`` if a finder was installed, ``False`` if one was already
    present.
    """
    if any(isinstance(finder, StubFinder) for finder in sys.meta_path):
        return False
    sys.meta_path.insert(0, StubFinder(prefixes))
    return True
