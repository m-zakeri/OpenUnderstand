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
und_all_results = {}
for ent in _db.ents("Class"):
    ent_name = ent.name()
    print(ent_name)
    print(ent.metric(["RatioCommentToCode"]))
    all_methods = ent.metric(["RatioCommentToCode"]).get("RatioCommentToCode", 0)
    und_all_results[ent_name] = all_methods
