import oudb.api as und
from oudb.fill import fill
from understand.main import runner
from os import path, getcwd

# db = und.create_db(
#     dbname="json.oudb",
#     project_dir="/home/y/Desktop/iust/JSON-java",
# )
#
# fill(udb_path=path.join(getcwd(), "../json.oudb"))
#
#
# runner(
#     path_project="/home/y/Desktop/iust/JSON-java"
# )
_db = und.open(dbname="json.oudb")
classes = _db.ents("class")
print(len(classes))
class_fields = []
class_methods = []
for i, c in enumerate(classes):
    source_class = c.simplename()
    try:
        file_path = c.parent().longname()
    except:
        continue
    for ref in c.refs("define", "variable"):
        class_fields.append(ref.ent())
    for ref in c.refs("define", "method"):
        class_methods.append(ref.ent())
print("cm : ", class_methods)
print("cf : ", class_fields)