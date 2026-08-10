import peewee
import os
import sys
import unittest

from openunderstand.oudb.models import KindModel, EntityModel, ReferenceModel
from openunderstand.oudb.utils import get_entity_object_from_understand
import pkg_resources


def append_java_ent_kinds(path_dir: str = ""):
    current_directory = os.path.abspath(os.path.dirname(__file__))
    path_dir = os.path.join(current_directory, "java_ent_kinds.txt")
    with open(path_dir, "r") as f:
        for line in f.readlines():
            if line.startswith("Java"):
                KindModel.get_or_create(_name=line.strip())


def append_java_ref_kind(forward: str, inverse: str) -> int:
    ref_kind, _ = KindModel.get_or_create(_name=forward, is_ent_kind=False)
    inv_kind, _ = KindModel.get_or_create(
        _name=inverse, is_ent_kind=False, _inv=ref_kind
    )
    # `_inv`, not `inverse`. KindModel has no field called `inverse`, so this
    # assignment used to set a stray attribute that save() ignored -- leaving
    # every forward reference kind with a NULL inverse, and Kind.inv() unable
    # to resolve forward -> inverse.
    ref_kind._inv = inv_kind
    return ref_kind.save()


def append_java_ref_kinds(path_dir: str = ""):
    """Seed reference kinds from "<forward> | <inverse>" lines.

    The inverse used to be derived by substituting one word for another out of
    a section header, which cannot express the pairings Understand actually
    uses -- Extend Couple/Extendby Coupleby, Use Cast/Useby Castby,
    Overrides/Overriddenby all have inverses that change more than one token.
    """
    current_directory = os.path.abspath(os.path.dirname(__file__))
    path_dir = os.path.join(current_directory, "java_ref_kinds.txt")
    with open(path_dir, "r") as f:
        for line in f.readlines():
            line = line.strip()
            if not line.startswith("Java"):
                continue
            if "|" not in line:
                raise ValueError(f"reference kind line has no inverse: {line!r}")
            forward, inverse = (part.strip() for part in line.split("|", 1))
            try:
                if not append_java_ref_kind(forward, inverse):
                    raise ConnectionError("Database disconnected, please try again!")
            except peewee.IntegrityError:
                print(f"KindModel exists: {line}")


def append_entities_with_understand(udb_path: str):
    try:
        from oudb import api as und
    except ImportError:
        print("Understand Python API is not installed correctly.")

    db = und.open(udb_path)
    for ent in db.ents():
        if ent.language() == "Java":
            # Create parents first
            parent_obj = None
            parents = []
            parent = ent.parent()
            while parent is not None:
                parents.append(parent)
                parent = parent.parent()
            parents.reverse()
            for index, parent in enumerate(parents):
                kind, _ = KindModel.get_or_create(_name=parent.kind().longname())
                parent_obj, _ = EntityModel.get_or_create(
                    _kind=kind,
                    _parent=parent_obj,
                    _name=parent.name(),
                    _longname=parent.longname(),
                    _value=parent.value(),
                    _type=parent.type(),
                    _contents=parent.contents(),
                )

            # Create entity it-self!
            kind, _ = KindModel.get_or_create(_name=ent.kind().longname())
            ent, _ = EntityModel.get_or_create(
                _kind=kind,
                _parent=parent_obj,
                _name=ent.name(),
                _longname=ent.longname(),
                _value=ent.value(),
                _type=ent.type(),
                _contents=ent.contents(),
            )
            print(ent)


def append_references_with_understand(udb_path: str):
    # TODO: Implement this method!
    try:
        from openunderstand import ounderstand as und
    except ImportError:
        print("Understand Python API is not installed correctly.")

    db = und.open(udb_path)
    for ent in db.ents():
        for ref in ent.refs():
            ent = get_entity_object_from_understand(ref.ent())
            scope = get_entity_object_from_understand(ref.scope())
            file = get_entity_object_from_understand(ref.file())
            assert ent is not None
            assert scope is not None
            assert file is not None
            kind, _ = KindModel.get_or_create(_name=ref.kind().longname())
            ref, has_created = ReferenceModel.get_or_create(
                _kind=kind,
                _file=file,
                _line=ref.line(),
                _column=ref.column(),
                _ent=ent,
                _scope=scope,
            )
            print(f"Reference created [{has_created}]: {ref}")
        print("===============")


class TestFill(unittest.TestCase):
    def setUp(self) -> None:
        self.ent_kind = KindModel.get(_name="Java Method Constructor Member Default")
        self.ref_kind = KindModel.get(_name="Java Open")

    def test_valid_inverse(self):
        inv = self.ref_kind.inv()
        self.assertEqual(inv._name, "Java Openby")
        self.assertTrue(inv.is_ref_kind)
        self.assertEqual(inv.inv(), self.ref_kind)

    def test_invalid_inverse(self):
        inv = self.ent_kind.inverse
        self.assertIsNone(inv)
        self.assertRaises(peewee.OperationalError, lambda: self.ent_kind.inv())


def fill(udb_path: str = ""):

    # udb_path = "D:\Dev\JavaSample\JavaSample1.udb"
    append_java_ent_kinds()
    append_java_ref_kinds()
    # print("=" * 50)
    # append_entities_with_understand(udb_path)
    # append_references_with_understand(udb_path)
