import sys
import os

sys.path.insert(
    0,
    "/home/y/Downloads/Scientific.Toolworks.Understand.5.1.1023.Linux/Understand-5.1.1023-Linux-64bit/scitools/bin/linux64/Python",
)
os.environ["LD_LIBRARY_PATH"] = (
    "/home/y/Downloads/Scientific.Toolworks.Understand.5.1.1023.Linux/Understand-5.1.1023-Linux-64bit/scitools/bin/linux64/Python"
)

import understand as und

my_path = "/home/y/Desktop/iust/OpenUnderstand/benchmark/JSON/JSON.udb"
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
    b += c

print(b)