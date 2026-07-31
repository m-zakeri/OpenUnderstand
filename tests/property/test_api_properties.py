"""
Property-based tests for ``openunderstand.oudb.api`` (bonus challenge:
*Property-based testing using Hypothesis*).

Example-based tests pin down behaviour at the handful of inputs the author
happened to think of.  Property-based tests state an *invariant* that must hold
for **every** input in a domain, and let Hypothesis search for a counterexample
-- including the pathological inputs a human would not write by hand (empty
strings, lone surrogates, control characters, huge integers).

Each test below documents the invariant it encodes and why it matters.
"""

import os

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

from openunderstand.oudb import api

pytestmark = pytest.mark.property

# Function-scoped DB fixtures are reused across Hypothesis examples within one
# test; that is intended here (every example only *reads*), so silence the
# health check rather than paying for a fresh database per example.
_SETTINGS = settings(
    max_examples=200,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
    deadline=None,
)

# Printable text avoids Hypothesis generating lone surrogates, which SQLite
# cannot store; the invariants under test are about string logic, not encoding.
text_strategy = st.text(
    alphabet=st.characters(blacklist_categories=("Cs", "Cc")), max_size=64
)


def _ent(**overrides):
    """Build a detached `api.Ent` (no database round-trip needed)."""
    fields = {
        "_id": 1, "_kind": 1, "_parent": None, "_name": "n", "_longname": "n",
        "_value": "", "_type": "", "_contents": "",
    }
    fields.update(overrides)
    return api.Ent(**fields)


def _kind(name, *, is_ent_kind=True):
    """Build a detached `api.Kind`."""
    return api.Kind(_id=1, _inv=None, _name=name, is_ent_kind=is_ent_kind)


# --- Kind.check -------------------------------------------------------------
@_SETTINGS
@given(name=text_strategy, needle=text_strategy)
def test_check_is_exactly_case_insensitive_containment(name, needle):
    """
    INVARIANT: `Kind.check(s)` is true iff `s` is a case-insensitive substring
    of the kind name.  This is the filter primitive every `kindstring` lookup in
    the API is built on, so any deviation silently changes query semantics.
    """
    assert _kind(name).check(needle) == (needle.lower() in name.lower())


@_SETTINGS
@given(name=text_strategy)
def test_empty_filter_always_matches(name):
    """INVARIANT: the empty filter is the identity -- it must never exclude."""
    assert _kind(name).check("") is True


@_SETTINGS
@given(name=text_strategy)
def test_kind_matches_its_own_name(name):
    """INVARIANT: reflexivity -- a kind always matches itself."""
    assert _kind(name).check(name) is True


@_SETTINGS
@given(name=text_strategy, index=st.integers(min_value=0, max_value=63))
def test_every_substring_of_the_name_matches(name, index):
    """INVARIANT: any contiguous slice of the name is an accepted filter."""
    assume(name)
    start = index % len(name)
    assert _kind(name).check(name[start : start + 3]) is True


@_SETTINGS
@given(
    name=st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), max_size=64),
    needle=st.text(alphabet=st.characters(min_codepoint=32, max_codepoint=126), max_size=64),
)
def test_check_is_case_insensitive_for_ascii(name, needle):
    """
    INVARIANT: for ASCII, neither operand's case may affect the outcome.

    Restricted to ASCII on purpose -- see
    `test_case_folding_is_not_round_trip_safe_outside_ascii` for why the
    unrestricted version does not hold.
    """
    kind = _kind(name)
    assert kind.check(needle) == kind.check(needle.upper()) == kind.check(needle.lower())


def test_case_folding_is_not_round_trip_safe_outside_ascii():
    """
    DOCUMENTED LIMITATION (found by Hypothesis, not by hand).

    `Kind.check` uses `str.lower()`, which is locale-naive. Hypothesis produced
    the classic counterexample: U+0131 LATIN SMALL LETTER DOTLESS I. Because
    `'ı'.upper() == 'I'`, upper-casing a filter can change which kinds it
    matches:

        Kind("I").check("ı")          -> False
        Kind("I").check("ı".upper())  -> True

    This is correct Python behaviour, not a defect in the code under test --
    `str.lower()` cannot be both round-trip safe and Unicode-correct. It is
    recorded here so the limitation is a *known* property of kind filtering
    rather than a surprise. Java identifiers may legally contain such
    characters, so a caller filtering on them cannot rely on case folding.
    """
    kind = _kind("I")
    assert kind.check("ı") is False
    assert kind.check("ı".upper()) is True


# --- Kind name accessors ----------------------------------------------------
@_SETTINGS
@given(name=text_strategy)
def test_longname_str_and_repr_all_agree(name):
    """INVARIANT: the documented aliasing `longname() == str() == repr()`."""
    kind = _kind(name)
    assert kind.longname() == kind.name() == str(kind) == repr(kind)


# --- Ent.simplename ---------------------------------------------------------
@_SETTINGS
@given(name=text_strategy)
def test_simplename_never_contains_a_dot(name):
    """
    INVARIANT: `simplename()` is documented as "the simplest, shortest name
    possible ... not a name with any dots in it" for Java.
    """
    assert "." not in _ent(_name=name).simplename()


@_SETTINGS
@given(segments=st.lists(st.text(alphabet="abcXYZ_", min_size=1, max_size=6),
                         min_size=1, max_size=5))
def test_simplename_is_the_last_dotted_segment(segments):
    """INVARIANT: `simplename()` == the final component of a dotted name."""
    assert _ent(_name=".".join(segments)).simplename() == segments[-1]


@_SETTINGS
@given(name=text_strategy)
def test_simplename_is_a_suffix_of_name(name):
    """INVARIANT: it selects from the name; it never invents characters."""
    assert _ent(_name=name).name().endswith(_ent(_name=name).simplename())


# --- Ent identity: __eq__ / __hash__ ----------------------------------------
@_SETTINGS
@given(entity_id=st.integers())
def test_equality_is_reflexive(entity_id):
    """INVARIANT: an entity always equals itself."""
    assert _ent(_id=entity_id) == _ent(_id=entity_id)


@_SETTINGS
@given(left=st.integers(), right=st.integers())
def test_equality_is_symmetric(left, right):
    """INVARIANT: `a == b` implies `b == a` -- required of any `__eq__`."""
    a, b = _ent(_id=left), _ent(_id=right)
    assert (a == b) == (b == a)


@_SETTINGS
@given(left=st.integers(), right=st.integers())
def test_equal_entities_hash_equally(left, right):
    """
    INVARIANT: the hash/eq contract.  `Db.ents()` returns a `set`, so a
    violation here would silently drop or duplicate entities.
    """
    a, b = _ent(_id=left), _ent(_id=right)
    if a == b:
        assert hash(a) == hash(b)


@_SETTINGS
@given(entity_id=st.integers())
def test_hash_is_the_hash_of_the_id(entity_id):
    """INVARIANT: identity is defined by id alone, per the class docstring."""
    assert hash(_ent(_id=entity_id)) == hash(entity_id)


@_SETTINGS
@given(entity_id=st.integers(), other=st.one_of(st.integers(), st.text(), st.none()))
def test_comparison_with_a_non_entity_is_not_implemented(entity_id, other):
    """
    INVARIANT: comparing against a foreign type returns `NotImplemented` so
    Python can fall back to the reflected operation -- it must not raise.
    """
    assert _ent(_id=entity_id).__eq__(other) is NotImplemented


# --- Ent scalar accessors ---------------------------------------------------
@_SETTINGS
@given(value=st.one_of(st.none(), text_strategy))
def test_value_returns_none_only_for_none(value):
    """INVARIANT: `None` propagates; every other value is stringified."""
    result = _ent(_value=value).value()
    assert result is None if value is None else result == str(value)


@_SETTINGS
@given(type_name=st.one_of(st.none(), text_strategy))
def test_type_returns_none_only_for_none(type_name):
    """INVARIANT: same null-propagation contract as `value()`."""
    result = _ent(_type=type_name).type()
    assert result is None if type_name is None else result == str(type_name)


@_SETTINGS
@given(name=text_strategy, longname=text_strategy, contents=text_strategy)
def test_string_accessors_always_return_str(name, longname, contents):
    """
    INVARIANT: these accessors are `str`-typed in the Understand API, so callers
    may use string operations without defensive conversion.
    """
    entity = _ent(_name=name, _longname=longname, _contents=contents)
    assert isinstance(entity.name(), str)
    assert isinstance(entity.longname(), str)
    assert isinstance(entity.contents(), str)
    assert isinstance(str(entity), str)
    assert isinstance(repr(entity), str)


@_SETTINGS
@given(name=text_strategy, longname=text_strategy)
def test_str_is_name_and_repr_is_longname(name, longname):
    """INVARIANT: the documented `__str__`/`__repr__` mapping."""
    entity = _ent(_name=name, _longname=longname)
    assert str(entity) == entity.name()
    assert repr(entity) == entity.longname()


# --- Db.relative_file_name --------------------------------------------------
@pytest.mark.xfail(
    strict=False,
    reason=(
        "FAULT #5: Db.relative_file_name() uses os.path.commonprefix, which is "
        "character-wise rather than path-component-wise, so it can strip a "
        "partial directory name and return a path that escapes the project "
        "root. Found by Hypothesis. See docs/FAULTS.md."
    ),
)
@_SETTINGS
@given(
    segments=st.lists(
        st.text(alphabet="abcdef", min_size=1, max_size=5), min_size=1, max_size=4
    )
)
def test_relative_file_name_preserves_the_basename(open_db, segments):
    """
    INVARIANT: relativising a path may strip leading directories but must never
    alter the file name itself -- otherwise reported locations point at the
    wrong file.

    Hypothesis falsifies this: with root ``com/example`` and path ``c``,
    ``commonprefix`` returns the bare character ``"c"``, and the result
    collapses to ``"."``.
    """
    path = os.path.join(*segments)
    assert os.path.basename(open_db.relative_file_name(path)) == segments[-1]


def test_relative_file_name_can_escape_the_project_root():
    """
    FAULT #5, minimal deterministic reproduction (no Hypothesis needed).

    ``os.path.commonprefix`` compares *characters*, not path components. With
    root ``com/example``, the path ``common/Other.java`` shares the literal
    prefix ``"com"`` -- which is not a real directory of either path -- so the
    result is relativised against a directory that does not exist and escapes
    upward with ``..``.

    ``os.path.commonpath`` is the correct API: it splits on separators and
    raises rather than inventing a bogus prefix.
    """
    project = api.Db.__new__(api.Db)
    project._root = os.path.join("com", "example")

    result = project.relative_file_name(os.path.join("common", "Other.java"))

    assert result.startswith(".."), (
        "expected the documented bug: relativising against a character-wise "
        f"prefix escapes the root, got {result!r}"
    )
    assert os.path.basename(result) == "Other.java"


@_SETTINGS
@given(
    segments=st.lists(
        st.text(alphabet="abcdef", min_size=1, max_size=5), min_size=1, max_size=4
    )
)
def test_relative_file_name_is_relative(open_db, segments):
    """INVARIANT: the result is never an absolute path."""
    path = os.path.join(*segments)
    assert not os.path.isabs(open_db.relative_file_name(path))


# --- Ref accessors ----------------------------------------------------------
@_SETTINGS
@given(line=st.integers(), column=st.integers())
def test_ref_reports_the_position_it_was_built_with(line, column):
    """INVARIANT: position accessors are lossless -- no clamping, no offset."""
    reference = api.Ref(
        _id=1, _kind=1, _file=1, _line=line, _column=column, _ent=1, _scope=1
    )
    assert reference.line() == line
    assert reference.column() == column
