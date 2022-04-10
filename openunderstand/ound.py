"""
Open Understand main driver
to create project parse tree, analyze project, and create symbol table oudb
It is the same Understand und command line tool

"""
from pprint import pprint

from oudb.api import open as db_open, create_db, Kind
from oudb.fill import main


class Project():
    # Todo: Implement project class
    pass


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    p = Project()
    create_db("H:\Developement\PythonProjects\CompilerProject\OpenUnderstand\OpenUnderstand\database.db", project_dir="H:\Developement\PythonProjects\OpenUnderstand\OpenUnderstand\\benchmark")
    main()
    db = db_open("H:\Developement\PythonProjects\CompilerProject\OpenUnderstand\OpenUnderstand\database.db")
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

