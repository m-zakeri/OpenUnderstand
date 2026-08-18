"""Analyse every ``.java`` file under a project, one file at a time.

Sequential on purpose. A ``Pool`` here handed every forked worker the parent's
already-open SQLite connection and its own copy of the process-local entity
identity cache, so writes were lost and duplicated *with no exception raised*:
``pool.map`` on calculator_app committed 43 entities and 208 references against
the sequential 90 and 578, and JSON came out at 5606 entities against 5186.
``map_async`` without ``.get()`` then discarded whatever the workers did raise,
which is why this looked like it worked.

``mcp_server.analyze()`` and ``scripts/compare/02_build_ou.py`` have always
looped sequentially for this reason. This is the same loop, so every entry
point -- the CLI, ``start_parsing()``, the MCP server and the comparison
harness -- now builds the same database from the same source.

Parallelism needs workers that only *collect* and a parent that writes, which
is the layering ``analysis_passes/`` already claims. That is a project, not a
flag, and it is not what a wall-clock number is worth here: JSON is dominated
by per-file work that was already halved by doing less of it, not by a missing
core.
"""

from openunderstand.ounderstand.parsing_process import process_file, get_files


def runner(path_project: str = ""):
    for file_address in get_files(path_project):
        process_file(file_address)
