import oudb.api as und
from oudb.fill import fill
from understand.main import runner
from os import path, getcwd
from utils.utilities import setup_logger

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
from pathlib import Path
_db = und.open(dbname="json.oudb")
classes = _db.ents("class")
print(len(classes))
logger = setup_logger()
for i, c in enumerate(classes):
    source_class = c.simplename()
    try:
        file_path = c.parent().longname()
    except:
        continue
    class_fields = []
    class_methods = []
    for ref in c.refs("define", "variable"):
        # print(" g : ", ref.ent().simplename())
        class_fields.append(ref.ent())
    for ref in c.refs("define", "method"):
        class_methods.append(ref.ent())
        moved_fields = [ent.simplename() for ent in class_fields]
        moved_methods = [ent.simplename() for ent in class_methods]
        for field in moved_fields:
            # print(f"{source_class}.{field}")
            for ent in _db.lookup(f"{source_class}.{field}"):
                logger.info(f"here : {source_class}.{field}")
                logger.info(f"longname : {ent.longname()}")
                logger.info(f"kind : {ent.kind()}")

                # for ref in ent.refs("Useby, Setby, Modifyby"):
                #     print("yo")
                #     print("here : ", ref.file().longname())
                #     print("here2 : ", Path(file_path))
                #     if Path(ref.file().longname()) == Path(file_path):
                #         continue
                #     field_usage = {
                #         "field_name": field,
                #         "file_path": ref.file().longname(),
                #     }
                #     print(field_usage)