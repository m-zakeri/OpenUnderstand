from openunderstand.ounderstand.project import Project
from openunderstand.ounderstand.listeners_and_parsers import ListenersAndParsers
from openunderstand.oudb.models import ReferenceModel
import os
from fnmatch import fnmatch


def get_files(dirName: str = ""):
    """Every .java file under ``dirName``, sorted by path.

    Sorted because an entity's ``_parent`` is set by whichever file created it
    first, so os.listdir order -- which is neither sorted nor stable across
    machines -- decides it. Twelve of calculator_app's 90 entities landed under
    a different parent depending on the walk, and the comparison harness
    carried its own sorted walk to work around exactly this.
    """
    listOfFile = os.listdir(dirName)
    allFiles = list()
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        if os.path.isdir(fullPath):
            allFiles = allFiles + get_files(fullPath)
        # checks whether the fullPath content is a .java or not
        elif fnmatch(fullPath, "*.java"):
            allFiles.append(fullPath)
    return sorted(allFiles)


def _process_file(file_address):
    p = Project()
    lap = ListenersAndParsers()
    tree, parse_tree, file_ent = lap.parser(file_address=file_address, p=p)
    if tree is None and parse_tree is None and file_ent is None:
        return
    entity_generator = lap.entity_gen(file_address=file_address, parse_tree=parse_tree)
    listeners = [
        lap.type_listener,
        lap.define_listener,
        lap.create_listener,
        lap.lambda_listener,
        lap.use_variant_listener,
        lap.method_call_listener,
        lap.declare_listener,
        lap.field_use_listener,
        lap.static_import_listener,
        lap.overrides_listener,
        lap.couple_listener,
        lap.useby_listener,
        lap.setby_listener,
        lap.setinitby_listener,
        lap.setbypartialby_listener,
        lap.dotref_listener,
        lap.throws_listener,
        lap.extend_coupled_listener,
        lap.variable_listener,
        lap.callbyNonDynamic_listener,
        lap.cast_by_listener,
        lap.contain_in_listener,
        lap.extend_implict_listener,
        lap.import_demand_listener,
    ]
    for listener in listeners:
        listener(file_address=file_address, p=p, file_ent=file_ent, tree=tree)
    lap.modify_listener(
        entity_generator=entity_generator,
        parse_tree=parse_tree,
        file_address=file_address,
        p=p,
    )


def process_file(file_address):
    """Analyse one file inside a single database transaction.

    Every ``create()`` outside a transaction is its own implicit transaction,
    and one file produces hundreds of reference rows -- half a million across
    jfreechart. WAL and ``synchronous=0`` are already set in ``api.py``, so the
    cost being removed here is per-statement commit overhead, not fsync.

    The boundary is one file because that is the unit ``runner`` retries and
    the unit whose failure is already logged-and-swallowed: a file that raises
    mid-way now leaves no partial rows instead of some, which is strictly
    better for a database whose entity identity is enforced in Python.

    Batching changes when rows commit, never which rows are written, so the
    committed fingerprints must reproduce byte for byte.
    """
    with ReferenceModel._meta.database.atomic():
        return _process_file(file_address)
