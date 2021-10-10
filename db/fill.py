import peewee
import unittest

from models import Kind


def append_java_ent_kinds():
    with open("./java_ent_kinds.txt", "r") as f:
        for line in f.readlines():
            if line.startswith("Java"):
                query = line.strip()
                try:
                    kind = Kind.get(Kind.name == query)
                    if kind:
                        print(f"Kind exists: {kind}")
                        continue
                except Kind.DoesNotExist:
                    kind = Kind(
                        name=query
                    )
                    res = kind.save()
                    if res:
                        print(f"Created: {kind}")
                    else:
                        raise ConnectionError("Database disconnected, please try again!")


def append_java_ref_kind(kind: str, inverse: str, ref: str) -> bool:
    result = 0
    ref_kind = Kind(name=ref, is_ent_kind=False)
    result += ref_kind.save()

    inv = ref.replace(kind, inverse)
    inv_kind = Kind(name=inv, is_ent_kind=False, inverse=ref_kind)
    result += inv_kind.save()

    ref_kind.inverse = inv_kind
    result += ref_kind.save()
    return result == 3


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


class TestFill(unittest.TestCase):
    def setUp(self) -> None:
        self.ent_kind = Kind.get(Kind.name == "Java Method Constructor Member Default")
        self.ref_kind = Kind.get(Kind.name == "Java Open")

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
    append_java_ent_kinds()
    append_java_ref_kinds()
