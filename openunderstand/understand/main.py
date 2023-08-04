from understand.project import Project
from understand.listeners_and_parsers import ListenersAndParsers
from multiprocessing import Process, cpu_count, Pool


def process_file(file_address):
    p = Project()
    lap = ListenersAndParsers()
    tree, parse_tree, file_ent = lap.parser(file_address=file_address, p=p)
    if tree is None and parse_tree is None and file_ent is None:
        return
    entity_generator = lap.entity_gen(file_address=file_address, parse_tree=parse_tree)
    listeners = [
        lap.create_listener,
        lap.define_listener,
        lap.declare_listener,
        lap.override_listener,
        lap.callby_listener,
        lap.couple_listener,
        lap.useby_listener,
        lap.setby_listener,
        lap.dotref_listener,
        lap.throws_listener,
    ]
    lap.modify_listener(
        entity_generator=entity_generator,
        parse_tree=parse_tree,
        file_address=file_address,
        p=p,
    )
    for listener in listeners:
        listener(file_address=file_address, p=p, file_ent=file_ent, tree=tree)


def runner(path_project: str = ""):
    project = Project()
    files = project.getListOfFiles(path_project)
    with Pool(cpu_count()) as pool:
        pool.map(process_file, files)
