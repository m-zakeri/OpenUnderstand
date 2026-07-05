"""
Shared pytest fixtures and test-isolation bootstrap for the OpenUnderstand
unit-test suite.

The module under test is ``openunderstand.oudb.api`` -- the public, Understand-
compatible Python API (``Db``, ``Ent``, ``Kind``, ``Ref``).

Why the stub bootstrap below exists
-----------------------------------
Importing ``openunderstand.oudb.api`` transitively imports the whole metric
engine (``openunderstand.metrics.*``) and the ANTLR/Java parsing stack
(``openunderstand.ounderstand.*``).  The metric modules also use absolute
``from gen.javaLabeled... import ...`` imports that only resolve in the original
run layout.  None of that machinery is needed to exercise the database-backed
``Db``/``Ent``/``Kind``/``Ref`` classes.

So, before importing the api, we install a meta-path finder that synthesises a
harmless stub for ANY import under those prefixes.  This is the textbook "test
in isolation" technique: the unit under test (the api layer) is decoupled from
its heavy collaborators (the parser/metric layers).

Every test runs against a fresh in-memory SQLite database, so tests never touch
the developer's real ``.oudb`` files and cannot interfere with one another.
"""

import importlib.abc
import importlib.machinery
import sys
import types

import pytest
from peewee import SqliteDatabase


# ---------------------------------------------------------------------------
# 1. Isolation bootstrap: stub the heavy parser/metric stack before importing api
# ---------------------------------------------------------------------------
class _Dummy:
    """A do-nothing stand-in for any class/function pulled from a stub module."""

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
        module.__path__ = []  # treat as a package so submodule imports resolve
        module.__getattr__ = _stub_getattr  # PEP 562: synthesise any name
        return module

    def exec_module(self, module):
        pass


if not any(isinstance(f, _StubFinder) for f in sys.meta_path):
    sys.meta_path.insert(0, _StubFinder())

# Now it is safe to import the unit under test and the ORM models.
from openunderstand.oudb import api  # noqa: E402
from openunderstand.oudb.models import (  # noqa: E402
    EntityModel,
    KindModel,
    ProjectModel,
    ReferenceModel,
)

MODELS = [KindModel, EntityModel, ReferenceModel, ProjectModel]


@pytest.fixture()
def db():
    """Bind all models to a throw-away in-memory SQLite database."""
    database = SqliteDatabase(":memory:")
    database.bind(MODELS, bind_refs=False, bind_backrefs=False)
    database.connect()
    database.create_tables(MODELS)
    try:
        yield database
    finally:
        database.drop_tables(MODELS)
        database.close()


@pytest.fixture()
def kinds(db):
    """
    Create a realistic slice of the Java kind table.

    Reference kinds follow the same convention as ``oudb/fill.py``: the inverse
    ("...by") kind carries an ``_inv`` foreign key pointing back at the forward
    kind.  Entity kinds have ``_inv = None``.
    """
    cls = KindModel.create(_name="Java Class", is_ent_kind=True, _inv=None)
    method = KindModel.create(
        _name="Java Method Public Member", is_ent_kind=True, _inv=None
    )
    parameter = KindModel.create(_name="Java Parameter", is_ent_kind=True, _inv=None)
    file_kind = KindModel.create(_name="Java File", is_ent_kind=True, _inv=None)

    call = KindModel.create(_name="Java Call", is_ent_kind=False, _inv=None)
    callby = KindModel.create(_name="Java Callby", is_ent_kind=False, _inv=call)

    define = KindModel.create(_name="Java Define", is_ent_kind=False, _inv=None)
    definein = KindModel.create(_name="Java Definein", is_ent_kind=False, _inv=define)

    contain = KindModel.create(_name="Java Contain", is_ent_kind=False, _inv=None)
    containin = KindModel.create(_name="Java Containin", is_ent_kind=False, _inv=contain)

    return {
        "class": cls,
        "method": method,
        "parameter": parameter,
        "file": file_kind,
        "call": call,
        "callby": callby,
        "define": define,
        "definein": definein,
        "contain": contain,
        "containin": containin,
    }


@pytest.fixture()
def entities(db, kinds):
    """Build a parent-child entity tree: File -> Class -> Method -> Parameter."""
    file_ent = EntityModel.create(
        _kind=kinds["file"], _parent=None, _name="Main.java",
        _longname="com/example/Main.java", _value="", _type="",
        _contents="class Main {}",
    )
    class_ent = EntityModel.create(
        _kind=kinds["class"], _parent=file_ent, _name="Main",
        _longname="com.example.Main", _value="", _type="",
        _contents="class Main {}",
    )
    method_ent = EntityModel.create(
        _kind=kinds["method"], _parent=class_ent, _name="run",
        _longname="com.example.Main.run", _value="", _type="void",
        _contents="void run(int x) {}",
    )
    param_ent = EntityModel.create(
        _kind=kinds["parameter"], _parent=method_ent, _name="x",
        _longname="com.example.Main.run.x", _value="", _type="int",
        _contents="",
    )
    return {
        "file": file_ent,
        "class": class_ent,
        "method": method_ent,
        "parameter": param_ent,
    }


@pytest.fixture()
def references(db, kinds, entities):
    """Create one Java Call reference: run (scope) calls run (ent) in Main.java."""
    call_ref = ReferenceModel.create(
        _kind=kinds["call"], _file=entities["file"], _line=3, _column=5,
        _ent=entities["method"], _scope=entities["method"],
    )
    return {"call": call_ref}


@pytest.fixture()
def open_db(db, entities, references):
    """Return an api.Db instance wired to the in-memory database."""
    project = ProjectModel.create(
        name="example", language="Java", root="com/example", db_path=":memory:",
    )
    return api.Db(db_obj=project)


# peewee's Model.create() only stores explicitly-set columns in __data__; the api
# dataclasses need every field, so we re-fetch each row by primary key (loading
# all columns), exactly mirroring how api.py builds objects from select() results.
@pytest.fixture()
def make_kind():
    """Factory: wrap a KindModel row in an api.Kind dataclass instance."""

    def _make(kind_model):
        fresh = KindModel.get_by_id(kind_model.get_id())
        return api.Kind(**fresh.__dict__.get("__data__"))

    return _make


@pytest.fixture()
def make_ent():
    """Factory: wrap an EntityModel row in an api.Ent dataclass instance."""

    def _make(entity_model):
        fresh = EntityModel.get_by_id(entity_model.get_id())
        return api.Ent(**fresh.__dict__.get("__data__"))

    return _make


@pytest.fixture()
def make_ref():
    """Factory: wrap a ReferenceModel row in an api.Ref dataclass instance."""

    def _make(reference_model):
        fresh = ReferenceModel.get_by_id(reference_model.get_id())
        return api.Ref(**fresh.__dict__.get("__data__"))

    return _make
