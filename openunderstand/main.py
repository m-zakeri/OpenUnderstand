import oudb.api as und
from oudb.fill import fill
from understand.main import runner
from os import path, getcwd
from extract_class_api import ExtractClassAPI

# Clone projects

# sp = SourceProvider()
# sp.start_clone_projects("Source_id_0")
# sp.start_clone_projects("Source_id_1")
# sp.start_clone_projects("Source_id_2")
# sp.start_clone_projects("Source_id_3")

# create db for projects

# db = und.create_db(
#     dbname="xerces2-j.oudb",
#     project_dir="/home/y/Desktop/iust/Openundertand_testing_api/projects_bench/xerces2-j",
# )
# fill(udb_path=path.join(getcwd(), "../xerces2-j.oudb"))
# _db = und.open(dbname="xerces2-j.oudb")
# runner(
#     path_project="/home/y/Desktop/iust/Openundertand_testing_api/projects_bench/xerces2-j"
# )
# classes = _db.ents("Type Class ~Unknown ~Anonymous")
# print(len(classes))


und.create_db(dbname="/home/y/Desktop/iust/Openundertand_testing_api/udb_projects/xerces2-j.und", project_dir="/home/y/Desktop/iust/Openundertand_testing_api/projects_bench/xerces2-j")

# test Extract class

eca = ExtractClassAPI(
    udb_path="xerces2-j.oudb"
)

eca.get_source_class_map()
