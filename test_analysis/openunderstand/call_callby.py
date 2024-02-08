import sys
import os

script_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.abspath(os.path.join(script_dir, "..", os.pardir))
parent_dir_openunderstand = os.path.abspath(
    os.path.join(script_dir, "..", os.pardir, "openunderstand")
)
sys.path.append(parent_dir)
sys.path.append(parent_dir_openunderstand)

# Now import the 'openunderstand' module
import openunderstand.ounderstand as und

my_path = "/home/y/Desktop/iust/OpenUnderstand/mydb.udb"
_db = und.open(my_path)


b = 0

for j, ent in enumerate(_db.ents()):

    c = 0
    for i, ref in enumerate(ent.refs("Call, CallBy")):
        c = i
        print(f"+++++++++++ {j} +++++++++++")
        print("name: ", ent.name())
        print("longname: ", ent.longname())
        print("value: ", ent.value())
        print("type: ", ent.type())
        print("parent: ", ent.parent())
        print("contents: ", ent.contents())
        print("kind: ", ent.kind())
        print(f"--------- {i} ---------")
        print("line: ", ref.line())
        print("col: ", ref.column())
        print("file: ", ref.file())
        print("scope: ", ref.scope())
        print("ent: ", ref.ent())
        print("kind: ", ref.kind())
        print()
    b+=c

print(b)