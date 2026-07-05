"""
Manual unit tests for ``openunderstand.oudb.api.Ref``.

A ``Ref`` models a single reference of a given reference kind (here ``Java
Call``) connecting a scope entity to a referenced ent at file/line/column.
"""

import pytest

from openunderstand.oudb import api
from openunderstand.oudb.models import EntityModel


def test_line_and_column(references, make_ref):
    ref = make_ref(references["call"])
    assert ref.line() == 3
    assert ref.column() == 5


def test_isforward_is_false(references, make_ref):
    assert make_ref(references["call"]).isforward() is False


def test_macroexpansion_is_empty_string(references, make_ref):
    assert make_ref(references["call"]).macroexpansion() == ""


def test_kind_returns_kind_object(references, make_ref):
    kind = make_ref(references["call"]).kind()
    assert isinstance(kind, api.Kind)
    assert kind.name() == "Java Call"


def test_kindname_matches_kind_name(references, make_ref):
    assert make_ref(references["call"]).kindname() == "Java Call"


def test_ent_returns_referenced_entity(references, make_ref):
    ent = make_ref(references["call"]).ent()
    assert isinstance(ent, api.Ent)
    assert ent.name() == "run"


def test_file_returns_file_entity(references, make_ref):
    assert make_ref(references["call"]).file().name() == "Main.java"


def test_scope_returns_scope_entity(references, make_ref):
    assert make_ref(references["call"]).scope().name() == "run"


def test_str_contains_kind_and_location(references, make_ref):
    text = str(make_ref(references["call"]))
    assert "Java Call" in text
    assert "(3, 5)" in text


def test_repr_equals_str(references, make_ref):
    ref = make_ref(references["call"])
    assert repr(ref) == str(ref)


def test_ent_for_unknown_id_raises_does_not_exist(references, kinds, entities):
    """A reference pointing at a non-existent entity id must not silently pass."""
    broken = api.Ref(
        _id=999,
        _kind=kinds["call"].get_id(),
        _file=entities["file"].get_id(),
        _line=1,
        _column=1,
        _ent=999_999,
        _scope=entities["method"].get_id(),
    )
    with pytest.raises(EntityModel.DoesNotExist):
        broken.ent()
