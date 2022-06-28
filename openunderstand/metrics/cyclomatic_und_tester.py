import understand as und
from utils_g10 import get_project_info, report_cyclomatic


PRJ_INDEX = 10
REF_NAME = "origin"


def test():
    info = get_project_info(PRJ_INDEX, REF_NAME)
    db = und.open(info['DB_PATH'])

    project_cyclomatic = 0
    cyclomatic_list = []
    ent_kind_set = set()

    for ent in db.ents():
        ent_kind = ent.kind().__repr__()
        ent_cyclomatic = ent.metric(['Cyclomatic']).get('Cyclomatic', 0)

        if ent_cyclomatic and ent_kind.startswith("Java"):
            project_cyclomatic += ent_cyclomatic
            cyclomatic_list.append({
                'kind': ent_kind,
                'name': ent.simplename(),
                'cyclomatic': ent_cyclomatic,
                'longname': ent.longname()
            })
            ent_kind_set.add(ent_kind)

    report_cyclomatic(project_cyclomatic, ent_kind_set, cyclomatic_list)


if __name__ == '__main__':
    test()
