import understand as und
import os


def get_project_info(index, ref_name):
    project_names = [
        'calculator_app',
        'JSON',
        'testing_legacy_code',
        'jhotdraw-develop',
        'xerces2j',
        'jvlt-1.3.2',
        'jfreechart',
        'ganttproject',
        '105_freemind',
        'custom'
    ]
    project_name = project_names[index]
    db_path = f"../../../databases/{ref_name}/{project_name}"
    if ref_name == "origin":
        db_path = db_path + ".udb"
    else:
        db_path = db_path + ".oudb"
    project_path = f"../../../benchmarks/{project_name}"

    db_path = os.path.abspath(db_path)
    project_path = os.path.abspath(project_path)

    return {
        'PROJECT_NAME': project_name,
        'DB_PATH': db_path,
        'PROJECT_PATH': project_path,
    }


PRJ_INDEX = 5
REF_NAME = "origin"


def test_understand_kinds():
    info = get_project_info(PRJ_INDEX, REF_NAME)
    db = und.open(info['DB_PATH'])
    my_set = set()
    for ent in db.ents():
        cycle = ent.metric(['Cyclomatic']).get('Cyclomatic', 0)
        ent_kind = ent.kind()
        if cycle and 'Java' in ent_kind.__repr__():
            my_set.add(ent_kind.__repr__())
            print(ent_kind)
            print(ent_kind.__repr__())
            print(ent.longname())
            print(cycle)
            print("-" * 25)

        # for ref in ent.refs("Import"):
        #     print(f'1. ref name: {ref.kindname()}')
        #     print(f'2. ref scope: {ref.scope().longname()} || kind: {ref.scope().kind()}')
        #     print(f'3. ref ent: {ref.ent().longname()} || kind: {ref.ent().kind()}')
        #     print(f'4. file location: {ref.file().longname()} || line: {ref.line()}')
        #     print("-" * 25)
    for i in my_set:
        print(i)

if __name__ == '__main__':
    test_understand_kinds()
