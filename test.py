import openunderstand.oudb.api as und
from openunderstand.oudb.fill import main
from os import path, getcwd
from openunderstand.main import runner


# db = und.create_db(dbname="xerces2-j.oudb", project_dir="/home/y/Desktop/iust/Openundertand_testing_api/projects_bench/xerces2-j")
#
# main(udb_path=path.join(getcwd(), "xerces2-j.oudb"))
#
_db = und.open(dbname="xerces2-j.oudb")
#
# runner(path_project="/home/y/Desktop/iust/Openundertand_testing_api/projects_bench/xerces2-j")

classes = _db.ents("Type Class ~Unknown ~Anonymous")
# classes = _db.ents("Java Class ~Unknown ~Unresolved")
#

print(classes)
