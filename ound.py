"""
Open Understand main driver
to create project parse tree, analyze project, and create symbol table db
It is the same Understand und command line tool

"""
from pprint import pprint

from db.api import open as db_open, create_db, Kind
from db.fill import main

class Project():
    # Todo: Implement project class
    pass


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    p = Project()
    # create_db("G:\Dev\OpenUnderstand\database.db", project_dir="G:\Dev\OpenUnderstand\benchmark\calculator_app")
    # main()
    db = db_open("G:\Dev\OpenUnderstand\database.db")
    ent = db.ent_from_id(16)
    ents = db.lookup("admin")
    pprint(ents)
