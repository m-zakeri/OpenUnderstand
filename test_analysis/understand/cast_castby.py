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
    # print(f"+++++++++++ {j} +++++++++++")
    # print("name: ", ent.name())
    # print("longname: ", ent.longname())
    # print(len(ent.refs("Cast, CastBy")))
    c = 0
    for i, ref in enumerate(ent.refs("Cast, CastBy")):
        c = i
        print(f"--------- {i} ---------")
        print("line: ", ref.line())
        print("file: ", ref.file())
        print("scope: ", ref.scope())
        print()
    b += c

print(b)
