import oudb.api as und
from oudb.fill import fill
from understand.main import runner
from os import path, getcwd

db = und.create_db(
    dbname="json.oudb",
    project_dir="/home/y/Desktop/iust/OpenUnderstand/benchmark/JSON",
)

fill(udb_path=path.join(getcwd(), "../json.oudb"))

_db = und.open(dbname="json.oudb")
runner(
    path_project="/home/y/Desktop/iust/OpenUnderstand/benchmark/JSON"
)

classes = _db.ents("Type Class ~Unknown ~Anonymous")
print(len(classes))