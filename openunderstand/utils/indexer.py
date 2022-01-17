import os
from pathlib import Path

from db.api import create_db
from db.fill import main as main_fill
from db.models import EntityModel, KindModel
from utils.listeners import FileIndexListener
from utils.tools import get_filenames_in_dir, get_tree, walk_tree

trees = {}


def index_files(project_directory: str):
    if not Path(project_directory).is_dir():
        raise ValueError(f"project_directory is not a valid directory.")
    print(f"Indexing {project_directory}...")
    packages = set()
    package_parent = None

    for file in get_filenames_in_dir(project_directory):
        # Create File Entity
        kind, _ = KindModel.get_or_create(_name="Java File")
        ent, _ = EntityModel.get_or_create(
            _kind=kind,
            _parent=None,
            _name=os.path.basename(file),
            _longname=file,
            _value=None,
            _type=None,
            _contents=None
        )
        print(f"Created ({_}): {kind}: {ent}")
        tree = get_tree(file)
        listener = walk_tree(tree, FileIndexListener)
        print(listener.methods)
        exit(-1)
        # Indexing packages
        package_name = listener.package_name
        if package_name not in packages:
            packages.add(package_name)
            package_parent = ent
        kind, _ = KindModel.get_or_create(_name="Java Package")
        ent, _ = EntityModel.get_or_create(
            _kind=kind,
            _parent=package_parent,
            _name=package_name,
            _longname=package_name,
            _value=None,
            _type=None,
            _contents=None
        )
        print(f"Created ({_}): {kind}: {ent}")
        # Indexing classes
        kind, _ = KindModel.get_or_create(_name=" Java Class Type Public Member")
        for cls in listener.classes:
            parent = EntityModel.get(_longname=cls["parent_longname"])
            ent, _ = EntityModel.get_or_create(
                _kind=kind,
                _parent=parent,
                _name=cls["name"],
                _longname=cls["longname"],
                _value=None,
                _type=None,
                _contents=None
            )
            print(f"Created ({_}): {kind}: {ent}")

        trees[file] = tree


if __name__ == '__main__':
    directory = "D:\Dev\JavaSample\JavaSample"
    create_db(
        dbname="test.db",
        project_dir=directory,
        project_name="JavaSample"
    )
    main_fill()
    index_files(directory)
