"""
Coverage-completing unit tests for the small, in-scope helpers of
``openunderstand.oudb.api``: module-level helpers, simple ``Ent`` accessors and
dunder methods, and ``Db`` housekeeping.
"""

from openunderstand.oudb import api


def test_version_returns_semver_string():
    assert api.version() == "0.1.0"


def test_understand_error_is_exception():
    assert issubclass(api.UnderstandError, Exception)
    assert isinstance(api.UnderstandError(), Exception)


def test_db_close_returns_none(open_db):
    assert open_db.close() is None


def test_db_str_is_name(open_db):
    assert str(open_db) == "example"


def test_parameters_lists_method_parameters(entities, make_ent):
    assert make_ent(entities["method"]).parameters() == "int x"


def test_parameters_returns_none_when_no_parameters(entities, make_ent):
    assert make_ent(entities["parameter"]).parameters() is None


def test_value_returns_string_when_set(entities, make_ent):
    assert make_ent(entities["method"]).value() == ""


def test_value_returns_none_when_unset():
    ent = api.Ent(
        _id=1, _kind=1, _parent=None, _name="t", _longname="t",
        _value=None, _type=None, _contents="",
    )
    assert ent.value() is None


def test_type_returns_none_when_unset():
    ent = api.Ent(
        _id=1, _kind=1, _parent=None, _name="t", _longname="t",
        _value=None, _type=None, _contents="",
    )
    assert ent.type() is None


def test_freetext_parsetime_relname_uniquename_defaults(entities, make_ent):
    ent = make_ent(entities["file"])
    assert ent.freetext("anything") == ""
    assert ent.parsetime() == 0
    assert ent.relname() == ""
    assert ent.uniquename() == ""


def test_eq_same_id(entities, make_ent):
    assert make_ent(entities["method"]) == make_ent(entities["method"])


def test_eq_different_id(entities, make_ent):
    assert not (make_ent(entities["method"]) == make_ent(entities["class"]))


def test_eq_with_non_ent_is_not_implemented(entities, make_ent):
    assert make_ent(entities["method"]).__eq__(123) is NotImplemented


def test_hash_is_hash_of_id(entities, make_ent):
    a = make_ent(entities["method"])
    assert hash(a) == hash(a.id())


def test_str_and_repr(entities, make_ent):
    method = make_ent(entities["method"])
    assert str(method) == "run"
    assert repr(method) == "com.example.Main.run"


def test_unimplemented_orderings_return_none(entities, make_ent):
    a = make_ent(entities["method"])
    b = make_ent(entities["class"])
    assert a.__ge__(b) is None
    assert a.__gt__(b) is None
    assert a.__le__(b) is None
    assert a.__lt__(b) is None
    assert a.__ne__(b) is None
