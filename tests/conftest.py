"""
Shared pytest fixtures and test-isolation bootstrap for the OpenUnderstand
test suite.

The module under test is ``openunderstand.oudb.api`` -- the public, Understand-
compatible Python API (``Db``, ``Ent``, ``Kind``, ``Ref``).

Test tiers
----------
``tests/unit/``         isolated unit tests for the api/db layer (stubbed parser)
``tests/integration/``  tests that drive the *real* ANTLR Java parser
``tests/property/``     Hypothesis property-based tests

Fixtures defined here are visible to all three tiers.

Why the stub bootstrap below exists
-----------------------------------
Importing ``openunderstand.oudb.api`` transitively imports the whole metric
engine and the ANTLR/Java parsing stack.  None of that machinery is needed to
exercise the database-backed ``Db``/``Ent``/``Kind``/``Ref`` classes, so before
importing the api we install a meta-path finder that synthesises a harmless
stub for any import under those prefixes.  See ``tests/_isolation.py``.

Note that the stub only covers the top-level ``gen`` package (the absolute
import form used by the metric modules); ``openunderstand.gen.*`` is *not*
stubbed, which is what lets ``tests/integration/`` drive the real parser.

Every test runs against a fresh in-memory SQLite database, so tests never touch
the developer's real ``.oudb`` files and cannot interfere with one another.
"""

import pytest
from peewee import SqliteDatabase

from tests._isolation import install_stub_finder

# ---------------------------------------------------------------------------
# 1. Isolation bootstrap: stub the heavy parser/metric stack before importing api
# ---------------------------------------------------------------------------
install_stub_finder()

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
