import peewee
import unittest

from models import Kind, Entity
from utils import get_object_or_create


def append_java_ent_kinds():
    with open("./java_ent_kinds.txt", "r") as f:
        for line in f.readlines():
            if line.startswith("Java"):
                query = line.strip()
                kind, _ = get_object_or_create(Kind, name=query)
                print(f"Created ({_}): {kind}")


def append_java_ref_kind(kind: str, inverse: str, ref: str) -> int:
    ref_kind, _ = get_object_or_create(Kind, name=ref, is_ent_kind=False)
    inv = ref.replace(kind, inverse)
    inv_kind, _ = get_object_or_create(Kind, name=inv, is_ent_kind=False, inverse=ref_kind)
    ref_kind.inverse = inv_kind
    return ref_kind.save()


def append_java_ref_kinds():
    kind, inv_kind = "", ""
    with open("./java_ref_kinds.txt", "r") as f:
        for line in f.readlines():
            line = line.strip()
            if line.startswith("Java"):
                try:
                    if append_java_ref_kind(kind, inv_kind, line):
                        print(f"Created: {line}")
                        continue
                    else:
                        raise ConnectionError("Database disconnected, please try again!")
                except peewee.IntegrityError:
                    print(f"Kind exists: {line}")
            else:
                if line:
                    kind, inv_kind = line.split()
                    inv_kind = inv_kind[1:-1]


def append_entities_with_understand(udb_path: str):
    try:
        import understand as und
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
                kind, _ = get_object_or_create(Kind, name=parent.kind().longname())
                parent_obj, _ = get_object_or_create(
                    Entity,
                    kind=kind,
                    parent=parent_obj,
                    name=parent.name(),
                    longname=parent.longname(),
                    value=parent.value(),
                    type=parent.type()
                )

            # Create entity it-self!
            kind, _ = get_object_or_create(Kind, name=ent.kind().longname())
            ent, _ = get_object_or_create(
                Entity,
                kind=kind,
                parent=parent_obj,
                name=ent.name(),
                longname=ent.longname(),
                value=ent.value(),
                type=ent.type()
            )
            print(ent)


def append_references_with_understand(udb_path: str):
    # TODO: Implement this method!
    try:
        import understand as und
    except ImportError:
        print("Understand Python API is not installed correctly.")


class TestFill(unittest.TestCase):
    def setUp(self) -> None:
        self.ent_kind = Kind.get(name="Java Method Constructor Member Default")
        self.ref_kind = Kind.get(name="Java Open")

    def test_valid_inverse(self):
        inv = self.ref_kind.inv()
        self.assertEqual(inv.name, "Java Openby")
        self.assertTrue(inv.is_ref_kind)
        self.assertEqual(inv.inv(), self.ref_kind)

    def test_invalid_inverse(self):
        inv = self.ent_kind.inverse
        self.assertIsNone(inv)
        self.assertRaises(peewee.OperationalError, lambda: self.ent_kind.inv())


if __name__ == '__main__':
    udb_path = "D:\Dev\JavaSample\JavaSample1.udb"
    append_java_ent_kinds()
    append_java_ref_kinds()
    print("=" * 50)
    append_entities_with_understand(udb_path)
    append_references_with_understand(udb_path)
