import os

from antlr4 import *

from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from oudb.api import open as db_open
from oudb.models import EntityModel

PRJ_INDEX = 4
PROJECTS_NAME = [
    'calculator_app',
    'JSON',
    'testing_legacy_code',
    'jhotdraw-develop',
    'xerces2j',
    'jvlt-1.3.2',
    'jfreechart',
    'ganttproject',
    '105_freemind',
]
DB_PATH = "../../database/jvlt-1.3.2.oudb"
PROJECT_NAME = "Sample App"


class Project:
    def __init__(self, db_name, project_name=None):
        self.db_name = db_name
        self.project_name = project_name

    def init_db(self):
        db_open(self.db_name)

def main():
    p = Project(DB_PATH, PROJECT_NAME)
    p.init_db()
    count = 0
    class_count_function = {}
    for ent in EntityModel.select():
        if "Method" in ent._kind._name:
            parent = None
            child = ent
            while True:
                try:
                    if isinstance(child._parent, EntityModel):
                        parent = child._parent
                        child = child._parent
                    else:
                        break
                except:
                    break
            basename = os.path.basename(parent.__repr__())
            class_count_function[basename] = class_count_function.get(basename, 0) + 1
            count += 1

    print(class_count_function)
    print(count)
    return class_count_function


if __name__ == '__main__':
    main()
