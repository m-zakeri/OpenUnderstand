"""Analyse every ``.java`` file under a project, and parse its Kotlin files.

Workers only *collect* and the parent writes, which is the layering
``analysis_passes/`` always claimed. Getting there needed two things that were
not true before:

* the write layer had to stop walking the parse tree.
  ``Project.getClassProperties`` and ``getInterfaceProperties`` did, once per
  distinct name asked, and so did ``EntityGenerator``. They read precollected
  declarations now, which a worker computes where the tree is.
* every pass had to be split into "build a listener" and "write its result",
  so the two halves can run in different processes.

A ``Pool`` here used to hand every forked worker the parent's already-open
SQLite connection and its own copy of the process-local entity identity cache,
so writes were lost and duplicated *with no exception raised*: ``pool.map`` on
calculator_app committed 43 entities and 208 references against the sequential
90 and 578. That cannot happen now, because a worker never writes -- and to
make sure of it, ``_isolate`` rebinds the models to a throwaway in-memory
database in each worker, so a stray write goes nowhere near the real one.

Kotlin files are found and analysed after the Java ones, in the parent, by the
declaration pass in ``kotlin_project`` (`runner` returns its
``kotlin_parser.Summary``). They never reach the Java passes, which would write
nonsense for them; with no database bound they are only parsed.
``get_files`` therefore stays Java-only, which the symbol table, the update path
and the comparison harness all rely on.

Results are consumed with ``imap``, which preserves order. That is not a
detail: an entity's parent is set by whichever file creates it first, and
``get_files`` sorts for the same reason.
"""

import os

from openunderstand.utils import kotlin_parser
from openunderstand.ounderstand import kotlin_project
from openunderstand.ounderstand.parsing_process import (
    collect_file,
    get_files,
    process_file,
    write_file,
)


def _isolate():
    """A worker must not reach the real database. Give it a dead one."""
    from peewee import SqliteDatabase

    from openunderstand.oudb.models import (
        EntityModel,
        KindModel,
        ProjectModel,
        ReferenceModel,
    )

    SqliteDatabase(":memory:").bind(
        [KindModel, EntityModel, ReferenceModel, ProjectModel]
    )


def _default_jobs():
    """One worker per core, less the one writing. `OU_JOBS` overrides."""
    override = os.environ.get("OU_JOBS")
    if override:
        return max(1, int(override))
    return max(1, (os.cpu_count() or 2) - 1)


def runner(path_project: str = "", jobs: int = None, kotlin: bool = True):
    """Analyse the Java files, then the Kotlin ones. Returns the Kotlin summary.

    ``kotlin=False`` skips the Kotlin files, which is the only cost a mixed
    project pays; a Java-only project has nothing to find.
    """
    _analyse_java(path_project, jobs)
    if not kotlin:
        return kotlin_parser.Summary()
    return kotlin_project.analyse_project(path_project)


def _analyse_java(path_project: str, jobs: int = None):
    files = get_files(path_project)
    jobs = _default_jobs() if jobs is None else jobs
    if jobs <= 1 or len(files) < 4:
        for file_address in files:
            process_file(file_address)
        return

    from multiprocessing import get_context

    from openunderstand.oudb.models import ReferenceModel

    # fork, so a worker inherits the symbol table the caller already built
    # rather than spending a second rebuilding it.
    context = get_context("fork") if "fork" in _methods() else get_context()
    with context.Pool(processes=jobs, initializer=_isolate) as pool:
        for file_address, payload in zip(
            files, pool.imap(collect_file, files, chunksize=2)
        ):
            with ReferenceModel._meta.database.atomic():
                write_file(file_address, payload)


def _methods():
    from multiprocessing import get_all_start_methods

    return get_all_start_methods()
