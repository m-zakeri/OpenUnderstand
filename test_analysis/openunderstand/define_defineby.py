import sys
from os import getcwd
from os.path import join
from pathlib import Path

sys.path.append(join(getcwd(), "openunderstand"))
sys.path.append(join(getcwd(), "openunderstand", "oudb"))
sys.path.append(join(getcwd(), "openunderstand", "utils"))
import ounderstand as und

_db = und.open("/home/y/Desktop/CodART/benchmark_projects/JSON20201115/mydb.udb")
dbents = _db.ents()

print("---------Define---------")
all_things = []
print(len(dbents))
class_ents = _db.lookup("JSONML", "Class")
class_ent = None
for ent in class_ents:
    if ent.parent() is not None:
        print("ent.parent().longname()", ent.parent().longname())
        print("ent.parent().simplename()", ent.parent().simplename())
        if Path(ent.parent().longname()) == Path(
            "/home/y/Desktop/CodART/benchmark_projects/JSON20201115/src/main/java/org/json/JSONML.java"
        ):
            class_ent = ent
            # break
if class_ent is None:
    _db.close()

for ref in class_ent.refs("Define", "Definein"):
    method_ent = ref.ent()
    print("here1 : ", method_ent.simplename())
    print("here2 : ", method_ent.parent())
    print("here3 : ", method_ent.value())
    print("here4 : ", method_ent.type())
