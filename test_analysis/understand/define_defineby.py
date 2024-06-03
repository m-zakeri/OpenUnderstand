import sys
import os
from pathlib import Path

sys.path.insert(
    0,
    "/home/y/Downloads/Scientific.Toolworks.Understand.5.1.1023.Linux/Understand-5.1.1023-Linux-64bit/scitools/bin/linux64/Python",
)
os.environ["LD_LIBRARY_PATH"] = (
    "/home/y/Downloads/Scientific.Toolworks.Understand.5.1.1023.Linux/Understand-5.1.1023-Linux-64bit/scitools/bin/linux64/Python"
)

import understand as und

_db = und.open(
    "/home/y/Desktop/CodART/benchmark_projects/JSON20201115/JSON20201115.udb"
)
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

for ref in class_ent.refs("Define", "DefineBy"):
    method_ent = ref.ent()
    print("here1 : ", method_ent.simplename())
    print("here2 : ", method_ent.parent())
    print("here3 : ", method_ent.value())
    print("here4 : ", method_ent.type())
    # print("here4 : ", method_ent.contents())
# for i in dbents:
#     for j in i.refs('Define, DefineBy'):
#         longname = i.longname()
#         file = j.file()
#         ent = j.ent()
#         line = j.line()
#         kind = j.kind()
#         column = j.column()
#         isforward = j.isforward()
#         kindname = j.kindname()
#         scope = j.scope()
#         all_things.append({
#             'longname ': longname,
#             'file ':file,
#             'ent ': ent,
#             'line ': line,
#             'kind ': kind,
#             'column ': column,
#             'isforward ': isforward,
#             'kindname ': kindname,
#             'scope ': scope
#         })

for i in all_things:
    print(i)
print(len(all_things))
