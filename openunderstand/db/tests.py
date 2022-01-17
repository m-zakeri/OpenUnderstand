from pprint import pprint

try:
    import understand as und
except ImportError:
    print("Can not import understand")

db = und.open("D:\Dev\JavaSample\JavaSample\JavaSample.und")

for ent in db.ents():
    print(ent.longname(), ent.kind())
    parent = ent.parent()
    while parent is not None:
        print(f"\t{parent.longname()} {parent.kind()}")
        parent = parent.parent()
    print("=" * 25)

for ent in db.ents("Method"):
    print(
        f"ent: {ent.longname()}\ntype: {ent.type()}\nvalue: {ent.value()}\ncontents: {ent.contents()}\nkind: {ent.kind().longname()}"
    )
    print("=========")
"""
Parents:
    File: None
    Unknown X: None
    Package: File, first file
    Public Class: File
    Class Method: Class
    Parameter: Method
    Variable: Method or Class
"""