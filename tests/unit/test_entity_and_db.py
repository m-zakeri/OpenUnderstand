"""
Manual unit tests for ``openunderstand.oudb.api.Ent`` and ``api.Db``:
parent-child relationships, unresolved/unknown entities, entity-kind lookups,
inverse references in context, and the multi-pass note.
"""

import os

import pytest

from openunderstand.oudb import api
from openunderstand.oudb.models import EntityModel, ReferenceModel


# --- Ent scalar accessors --------------------------------------------------
def test_name_and_longname(entities, make_ent):
    method = make_ent(entities["method"])
    assert method.name() == "run"
    assert method.longname() == "com.example.Main.run"


def test_simplename_strips_dotted_path(entities, make_ent):
    assert make_ent(entities["method"]).simplename() == "run"


def test_type_returns_declared_type(entities, make_ent):
    assert make_ent(entities["method"]).type() == "void"
    assert make_ent(entities["parameter"]).type() == "int"


def test_contents_returns_source(entities, make_ent):
    assert "void run" in make_ent(entities["method"]).contents()


def test_language_is_java(entities, make_ent):
    assert make_ent(entities["file"]).language() == "Java"


def test_id_returns_primary_key(entities, make_ent):
    assert make_ent(entities["file"]).id() == entities["file"].get_id()


# --- Ent kind --------------------------------------------------------------
def test_kind_returns_entity_kind(entities, make_ent):
    cls = make_ent(entities["class"])
    assert isinstance(cls.kind(), api.Kind)
    assert cls.kind().name() == "Java Class"


def test_kindname_matches_kind_name(entities, make_ent):
    assert make_ent(entities["class"]).kindname() == "Java Class"


# --- Parent / child relationships ------------------------------------------
def test_root_entity_has_no_parent(entities, make_ent):
    assert make_ent(entities["file"]).parent() is None


def test_child_resolves_immediate_parent(entities, make_ent):
    assert make_ent(entities["method"]).parent().name() == "Main"


def test_parent_chain_walks_to_root(entities, make_ent):
    param = make_ent(entities["parameter"])
    assert param.parent().name() == "run"
    assert param.parent().parent().name() == "Main"
    assert param.parent().parent().parent().name() == "Main.java"
    assert param.parent().parent().parent().parent() is None


# --- References in context -------------------------------------------------
def test_ents_returns_referenced_entities(references, entities, make_ent):
    related = make_ent(entities["method"]).ents("Call")
    assert [e.name() for e in related] == ["run"]


def test_ents_filtered_by_entity_kind(references, entities, make_ent):
    related = make_ent(entities["method"]).ents("Call", "Method")
    assert [e.name() for e in related] == ["run"]


def test_ents_filtered_by_non_matching_entity_kind(references, entities, make_ent):
    assert make_ent(entities["method"]).ents("Call", "Parameter") == []


# The three tests below were added to kill specific mutants that survived the
# Cosmic Ray run (docs/REPORT.md section 5.2).  Each pins down a behaviour the
# original assertions left ambiguous.
def test_ents_without_a_ref_kind_filter_returns_every_kind(
    db, kinds, entities, make_ent
):
    """
    Kills `AddNot` on `if refkindstring:` -- with no filter, references of
    *every* kind must be followed, not just one kind.
    """
    ReferenceModel.create(
        _kind=kinds["call"], _file=entities["file"], _line=3, _column=5,
        _ent=entities["method"], _scope=entities["method"],
    )
    ReferenceModel.create(
        _kind=kinds["define"], _file=entities["file"], _line=4, _column=5,
        _ent=entities["parameter"], _scope=entities["method"],
    )

    unfiltered = {e.name() for e in make_ent(entities["method"]).ents(None)}
    filtered = {e.name() for e in make_ent(entities["method"]).ents("Call")}

    assert unfiltered == {"run", "x"}
    assert filtered == {"run"}
    assert filtered < unfiltered


def test_ents_skips_non_matching_refs_instead_of_stopping(
    db, kinds, entities, make_ent
):
    """
    Kills `ReplaceContinueWithBreak`: the entity-kind filter must *skip* a
    non-matching reference and keep scanning.

    Both references below are found through their `_scope`, so they are scanned
    in insertion order.  The first does not match `Method`, so a `break` would
    discard the second one and return an empty list.
    """
    callee = EntityModel.create(
        _kind=kinds["method"], _parent=entities["class"], _name="other",
        _longname="com.example.Main.other", _value="", _type="void", _contents="",
    )
    ReferenceModel.create(  # scanned first, target is a Parameter -> no match
        _kind=kinds["call"], _file=entities["file"], _line=1, _column=1,
        _ent=entities["parameter"], _scope=entities["method"],
    )
    ReferenceModel.create(  # scanned second, target is a Method -> matches
        _kind=kinds["call"], _file=entities["file"], _line=2, _column=1,
        _ent=callee, _scope=entities["method"],
    )

    related = make_ent(entities["method"]).ents("Call", "Method")
    assert [e.name() for e in related] == ["other"]


def test_parameters_only_reads_direct_children(db, kinds, entities, make_ent):
    """
    Kills `ReplaceComparisonOperator_Eq_GtE` on the `_parent == self._id`
    lookup: a parameter belonging to a *different* method must never leak into
    this method's signature.
    """
    other_method = EntityModel.create(
        _kind=kinds["method"], _parent=entities["class"], _name="other",
        _longname="com.example.Main.other", _value="", _type="void", _contents="",
    )
    EntityModel.create(  # higher id, belongs to `other`, must not appear below
        _kind=kinds["parameter"], _parent=other_method, _name="y",
        _longname="com.example.Main.other.y", _value="", _type="long", _contents="",
    )

    assert make_ent(entities["method"]).parameters() == "int x"
    assert make_ent(other_method).parameters() == "long y"


def test_depends_and_dependsby_are_empty_dicts(entities, make_ent):
    ent = make_ent(entities["class"])
    assert ent.depends() == {}
    assert ent.dependsby() == {}


def test_filerefs_returns_empty_list(entities, make_ent):
    assert make_ent(entities["file"]).filerefs() == []


# --- Db queries ------------------------------------------------------------
def test_db_name_and_language(open_db):
    assert open_db.name() == "example"
    assert open_db.language() == "Java"


def test_db_ents_returns_all_entities(open_db):
    assert {e.name() for e in open_db.ents()} == {"Main.java", "Main", "run", "x"}


def test_db_ents_filtered_by_kind(open_db):
    assert {e.name() for e in open_db.ents("Class")} == {"Main"}


def test_db_ents_unknown_kind_returns_empty(open_db):
    assert open_db.ents("NoSuchKind") == set()


def test_ent_from_id_roundtrip(open_db, entities):
    ent = open_db.ent_from_id(entities["method"].get_id())
    assert ent is not None
    assert ent.name() == "run"


def test_ent_from_id_unknown_returns_none(open_db):
    assert open_db.ent_from_id(999_999) is None


def test_lookup_with_kind_filter_finds_entity(open_db):
    assert [e.name() for e in open_db.lookup("Main", "Class")] == ["Main"]


def test_relative_file_name(open_db):
    rel = open_db.relative_file_name(os.path.join("com", "example", "Main.java"))
    assert os.path.basename(rel) == "Main.java"


# --- Documented fault: lookup without a kind filter ------------------------
@pytest.mark.xfail(
    strict=False,
    reason=(
        "FAULT #2: Db.lookup(name) with no kindstring always returns [] because "
        "the final re.search uses the literal pattern 'java\\\\s+None'. "
        "See docs/FAULTS.md."
    ),
)
def test_lookup_without_kind_filter_should_find_entities(open_db):
    assert len(open_db.lookup("Main")) >= 1


# --- Requirement #8: multi-pass analysis -----------------------------------
@pytest.mark.skip(
    reason=(
        "Multi-pass analysis is a property of the parser/listener stage "
        "(openunderstand.ounderstand), intentionally stubbed for isolated unit "
        "testing of the api/db layer; validated via oracle/differential testing."
    )
)
def test_multi_pass_analysis_placeholder():
    pass
