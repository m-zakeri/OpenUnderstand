"""
Manual unit tests for ``openunderstand.oudb.api.Kind``.

Chosen unit under test (Part 3): the ``Kind`` class, covering both **entity
kinds** (e.g. ``Java Class``) and **reference kinds** (e.g. ``Java Call`` and
its inverse ``Java Callby``).

Two tests are marked ``xfail`` -- they document genuine faults discovered in the
code under test (see docs/FAULTS.md).
"""

import pytest

from openunderstand.oudb import api


# --- Normal behaviour ------------------------------------------------------
def test_name_returns_kind_name(kinds, make_kind):
    kind = make_kind(kinds["class"])
    assert kind.name() == "Java Class"
    assert isinstance(kind.name(), str)


def test_longname_equals_name(kinds, make_kind):
    kind = make_kind(kinds["call"])
    assert kind.longname() == kind.name() == "Java Call"


def test_str_and_repr_are_the_name(kinds, make_kind):
    kind = make_kind(kinds["method"])
    assert str(kind) == "Java Method Public Member"
    assert repr(kind) == "Java Method Public Member"


def test_is_ent_kind_flag(kinds, make_kind):
    assert make_kind(kinds["class"]).is_ent_kind is True
    assert make_kind(kinds["call"]).is_ent_kind is False


# --- Kind.check ------------------------------------------------------------
def test_check_matches_case_insensitive_substring(kinds, make_kind):
    kind = make_kind(kinds["class"])
    assert kind.check("class") is True
    assert kind.check("CLASS") is True
    assert kind.check("Java") is True


def test_check_returns_false_for_non_substring(kinds, make_kind):
    assert make_kind(kinds["class"]).check("method") is False


def test_check_empty_string_is_true_edge_case(kinds, make_kind):
    assert make_kind(kinds["class"]).check("") is True


# --- Kind.list_entity ------------------------------------------------------
def test_list_entity_returns_all_entity_kinds(kinds):
    names = {k.name() for k in api.Kind.list_entity()}
    assert names == {
        "Java Class",
        "Java Method Public Member",
        "Java Parameter",
        "Java File",
    }


def test_list_entity_returns_kind_instances(kinds):
    result = api.Kind.list_entity()
    assert result and all(isinstance(k, api.Kind) for k in result)


def test_list_entity_filter_matches_subset(kinds):
    assert [k.name() for k in api.Kind.list_entity("Class")] == ["Java Class"]


def test_list_entity_no_match_falls_back_to_all(kinds):
    assert len(api.Kind.list_entity("NoSuchKind")) == 4


def test_list_entity_never_returns_reference_kinds(kinds):
    assert all(k.is_ent_kind for k in api.Kind.list_entity())


# --- Kind.list_reference ---------------------------------------------------
def test_list_reference_returns_all_reference_kinds(kinds):
    names = {k.name() for k in api.Kind.list_reference()}
    assert names == {
        "Java Call",
        "Java Callby",
        "Java Define",
        "Java Definein",
        "Java Contain",
        "Java Containin",
    }


def test_list_reference_filter_matches_subset(kinds):
    assert [k.name() for k in api.Kind.list_reference("Callby")] == ["Java Callby"]


def test_list_reference_no_match_falls_back_to_all(kinds):
    assert len(api.Kind.list_reference("NoSuchKind")) == 6


def test_list_reference_never_returns_entity_kinds(kinds):
    assert all(not k.is_ent_kind for k in api.Kind.list_reference())


# --- Inverse references (Kind.inv) -----------------------------------------
def test_inv_on_entity_kind_raises_understand_error(kinds, make_kind):
    with pytest.raises(api.UnderstandError):
        make_kind(kinds["class"]).inv()


@pytest.mark.xfail(
    raises=TypeError,
    strict=False,
    reason=(
        "FAULT #1: Kind.inv() calls inverse.__data__.get('__data__') which is "
        "None (should be inverse.__dict__.get('__data__')), so Kind(**None) "
        "raises TypeError. See docs/FAULTS.md."
    ),
)
def test_inv_on_reference_kind_returns_forward_kind(kinds, make_kind):
    inverse_kind = make_kind(kinds["callby"])  # "Java Callby" -> _inv -> "Java Call"
    forward = inverse_kind.inv()
    assert isinstance(forward, api.Kind)
    assert forward.name() == "Java Call"
