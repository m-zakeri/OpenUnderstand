import os
import understand as und
from utils_g10 import get_project_info


os.add_dll_directory("C:\\Program Files\\SciTools\\bin\\pc-win64")

PRJ_INDEX = -1
REF_NAME = "origin"


def test_understand_kinds():
    info = get_project_info(PRJ_INDEX, REF_NAME)
    db = und.open(info['DB_PATH'])
    my_set = set()
    for ent in db.ents():
        cycle = ent.metric(['CountStmtExe']).get('CountStmtExe', 0)
        ent_kind = ent.kind()
        if cycle and 'Java' in ent_kind.__repr__():
            my_set.add(ent_kind.__repr__())
            print(ent_kind)
            print(ent_kind.__repr__())
            print(ent.longname())
            print(cycle)
            print("-" * 25)

    for i in my_set:
        print(i)


if __name__ == '__main__':
    test_understand_kinds()
