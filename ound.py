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
    ent = db.lookup("Admin", "method")[0]
    """
    Use name Admin.java(3) Java Use
Use id Admin.java(4) Java Use
Use grade Admin.java(5) Java Use
    """
    print(ent, ent.kind())
    print(ent, ent.simplename())
    for ref in ent.refs(entkindstring="method", unique=True):
        print(ref)

