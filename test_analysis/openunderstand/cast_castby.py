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
