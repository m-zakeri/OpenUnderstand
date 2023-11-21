import sys
from os import getcwd
from os.path import join
sys.path.append(join(getcwd(), "openunderstand"))
sys.path.append(join(getcwd(), "openunderstand", "oudb"))
sys.path.append(join(getcwd(), "openunderstand", "utils"))
sys.path.append(join(getcwd(), "openunderstand", "metrics"))
import openunderstand.ounderstand as und

_db = und.open("/home/y/Desktop/iust/OpenUnderstand/mydb.udb")

und_all_results = {}
for ent in _db.ents("Class"):
    ent_name = ent.name()
    print(ent.metric(["CountDeclMethodAll"]))
    all_methods = ent.metric(["CountDeclMethodAll"]).get("CountDeclMethodAll", 0)
    und_all_results[ent_name] = all_methods

print(und_all_results)