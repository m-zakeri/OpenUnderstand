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
und_all_results = {}
for ent in _db.ents("Class"):
    ent_name = ent.name()
    print(ent_name)
    print(ent.metric(["AvgCyclomaticModified"]))
    all_methods = ent.metric(["AvgCyclomaticModified"]).get("AvgCyclomaticModified", 0)
    und_all_results[ent_name] = all_methods
