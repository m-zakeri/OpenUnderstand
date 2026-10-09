from openunderstand.ounderstand.project import Project
from openunderstand.ounderstand.listeners_and_parsers import ListenersAndParsers
from openunderstand.oudb.models import ReferenceModel, flush_reference_writes
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


#: Every pass, in the order their *writes* must run. `modify` is not here:
#: it is written last, after all of them.
_PASS_NAMES = (
    "type_listener",
    "define_listener",
    "module_listener",
    "create_listener",
    "lambda_listener",
    "use_variant_listener",
    "method_call_listener",
    "declare_listener",
    "field_use_listener",
    "static_import_listener",
    "overrides_listener",
    "couple_listener",
    "useby_listener",
    "setby_listener",
    "setinitby_listener",
    "setbypartialby_listener",
    "dotref_listener",
    "throws_listener",
    "extend_coupled_listener",
    # `variable_listener` is not here. It created variable entities from the
    # enclosing declaration's modifiers, after define_listener had declared
    # them properly, and wrote no references: a varargs parameter got a second
    # row named after the method's modifiers (`Static Variable Public Member`
    # beside its `Final Parameter`), and an anonymous class's fields a row
    # with the `(Anon_N)` segment missing.
    "callbyNonDynamic_listener",
    "cast_by_listener",
    "contain_in_listener",
    "extend_implict_listener",
)


def _passes(lap):
    """Every pass, in the order their writes must run."""
    return [getattr(lap, name) for name in _PASS_NAMES]


class _NoFileEntity:
    """Stands in for the entity generator while collecting.

    `ModifyListener` reads one thing from it during the walk -- `file_ent` --
    and that is a database row, which a worker must not create. The writer
    stamps the real one onto each record.
    """

    file_ent = None


def collect_file(file_address):
    """Parse and walk one file. Runs in a worker and must not touch the database.

    That is why it calls `Project.Parse` rather than
    `ListenersAndParsers.parser`, which creates the file entity, and why
    `modify` is handed `_NoFileEntity`. Forked workers sharing the parent's
    connection, each with its own copy of the identity cache, is what lost
    three quarters of the analysis the last time this was tried.
    """
    p = Project()
    lap = ListenersAndParsers(phase=ListenersAndParsers.BUILD)
    try:
        tree = p.Parse(file_address)
    except Exception:
        return None
    if tree is None:
        return None
    for listener in _passes(lap):
        listener(file_address=file_address, p=p, file_ent=None, tree=tree)
    lap.modify_listener(
        entity_generator=_NoFileEntity(),
        parse_tree=tree,
        file_address=file_address,
        p=p,
    )
    lap.walk_built(tree, p)
    classes, interfaces = p.declared_types()
    return {
        "listeners": lap.transfer_state(),
        # The two things the write layer used to read off the tree.
        "declared_types": (classes, interfaces),
        "package_data": _package_data(tree),
    }


def _package_data(tree):
    """The file's package declaration, which the writer needs and cannot walk."""
    from antlr4 import ParseTreeWalker

    from openunderstand.analysis_passes.entity_manager import PackageListener

    listener = PackageListener()
    listener.package_data = []
    ParseTreeWalker().walk(listener=listener, t=tree)
    return listener.package_data


def write_file(file_address, payload):
    """Write one file's collected result. Runs in the parent, in file order."""
    if payload is None:
        return
    p = Project()
    p.seed_declared_types(*payload["declared_types"])
    lap = ListenersAndParsers(phase=ListenersAndParsers.WRITE)
    lap.restore(
        payload["listeners"],
        tree_facts={
            "declared_types": payload["declared_types"],
            "package_data": payload["package_data"],
        },
    )
    file_ent = p.getFileEntity(path=file_address, name=os.path.basename(file_address))
    # Before any pass writes, as the sequential path does. An entity's parent
    # is set by whoever creates it first, so the package entities have to exist
    # in the same order or 199 of JSON's methods hang off the wrong one.
    lap.entity_gen(file_address=file_address, parse_tree=None)
    modify = lap._built.get("modify_listener")
    if modify is not None:
        for record in modify.modify:
            record["file"] = file_ent
    for listener in _passes(lap):
        listener(file_address=file_address, p=p, file_ent=file_ent, tree=None)
    lap.modify_listener(
        entity_generator=None, parse_tree=None, file_address=file_address, p=p
    )
    flush_reference_writes()


def _collect_then_write(file_address):
    write_file(file_address, collect_file(file_address))


def _process_file(file_address):
    p = Project()
    lap = ListenersAndParsers()
    tree, parse_tree, file_ent = lap.parser(file_address=file_address, p=p)
    if tree is None and parse_tree is None and file_ent is None:
        return
    entity_generator = lap.entity_gen(file_address=file_address, parse_tree=parse_tree)
    listeners = _passes(lap)
    # Two phases, not one. Each pass used to build a listener, walk the tree
    # and write in one breath, so the tree was descended once per pass and
    # nothing could be reordered. Build every listener first, then write in the
    # same order as before: the writes are what the ordering rules are about --
    # `modify_listener` runs last because it resolves a variable the declaring
    # passes have to have written.
    lap.phase = ListenersAndParsers.BUILD
    for listener in listeners:
        listener(file_address=file_address, p=p, file_ent=file_ent, tree=tree)
    # `modify_listener` is built here too: it walks the same tree, and it is
    # the last *write* because it resolves a variable the declaring passes have
    # to have written, which the write order below still guarantees.
    lap.modify_listener(
        entity_generator=entity_generator,
        parse_tree=parse_tree,
        file_address=file_address,
        p=p,
    )
    lap.walk_built(tree, p)
    lap.phase = ListenersAndParsers.WRITE
    for listener in listeners:
        listener(file_address=file_address, p=p, file_ent=file_ent, tree=tree)
    lap.modify_listener(
        entity_generator=entity_generator,
        parse_tree=parse_tree,
        file_address=file_address,
        p=p,
    )
    lap.phase = ListenersAndParsers.BOTH
    # One batched insert per file rather than one statement per reference.
    flush_reference_writes()


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
        return _collect_then_write(file_address)
