"""Shared plumbing for metrics that reparse source.

Most metric modules did `JavaParserLabeled(...).compilationUnit()` on
`ent.contents()`. That only works when the entity is a file or a top-level
type: a *method's* contents is not a compilation unit, so the parse failed and
the metric quietly returned 0 or the whole-file value. Every one of them scored
0% against Understand.

The fix is the same everywhere: parse the file the entity lives in, then pick
out the entity's own scope.
"""

from functools import lru_cache

from antlr4 import CommonTokenStream, InputStream, ParseTreeWalker

from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.oudb.models import EntityModel, ReferenceModel, kind_id


def enclosing_file(ent_model):
    """The File entity an entity is declared in, or None.

    Taken from the entity's own Define reference, which records the file the
    declaration was found in. Walking `_parent` instead goes class -> package
    -> file, and a package entity is shared by every file that declares it --
    so the walk returned whichever file happened to create the package first.
    """
    file_kind = kind_id("Java File")
    entity_id = getattr(ent_model, "_id", None)
    if entity_id is None:
        return None

    current = EntityModel.get_or_none(_id=entity_id)
    if current is not None and current._kind_id == file_kind:
        return current

    ref = ReferenceModel.get_or_none(
        (ReferenceModel._kind == kind_id("Java Define"))
        & (ReferenceModel._ent == entity_id)
    )
    if ref is not None:
        found = EntityModel.get_or_none(_id=ref._file_id)
        if found is not None and found._kind_id == file_kind:
            return found

    seen = set()
    while current is not None and current._id not in seen:
        if current._kind_id == file_kind:
            return current
        seen.add(current._id)
        current = EntityModel.get_or_none(_id=current._parent_id)
    return None


def file_source(ent_model):
    """Source of the whole file the entity is in, falling back to its own."""
    enclosing = enclosing_file(ent_model)
    if enclosing is not None and enclosing._contents:
        return enclosing._contents
    return ent_model.contents() or ""


# Every metric reparses the same file, and a dump asks for ~40 metrics per
# entity. Parse trees are only ever walked, never mutated, so they are safe to
# share -- caching them turns O(entities x metrics) parses into O(files).
@lru_cache(maxsize=64)
def parse(source):
    lexer = JavaLexer(InputStream(source))
    return JavaParserLabeled(CommonTokenStream(lexer)).compilationUnit()


@lru_cache(maxsize=256)
def parse_entity(source):
    """Parse an entity's own source, whatever kind of declaration it is.

    A method or field declaration is not a compilation unit, so parsing it
    directly fails and every metric built on it returned 0. Wrapping it in a
    synthetic class makes it parseable, which scopes the metric to the entity
    without any name matching.
    """
    from antlr4.error.ErrorListener import ErrorListener

    class _Failed(ErrorListener):
        def __init__(self):
            self.failed = False

        def syntaxError(self, *_args):
            self.failed = True

    for candidate in (source, f"class __Scope {{\n{source}\n}}"):
        lexer = JavaLexer(InputStream(candidate))
        parser = JavaParserLabeled(CommonTokenStream(lexer))
        detector = _Failed()
        parser.removeErrorListeners()
        parser.addErrorListener(detector)
        tree = parser.compilationUnit()
        if not detector.failed:
            return tree
    return tree


def walk_entity(ent_model, listener):
    """Walk `listener` over the entity's own source. Returns the listener."""
    ParseTreeWalker().walk(t=parse_entity(ent_model.contents() or ""),
                           listener=listener)
    return listener


def walk_file(ent_model, listener):
    """Walk `listener` over the entity's whole file. Returns the listener."""
    ParseTreeWalker().walk(t=parse(file_source(ent_model)), listener=listener)
    return listener


def declared_name(ctx):
    """Simple name of a method/constructor/class declaration context, or None."""
    name = type(ctx).__name__
    if name.startswith(("GenericMethodDeclaration", "GenericConstructorDeclaration")):
        ctx = ctx.children[1]
    identifier = getattr(ctx, "IDENTIFIER", None)
    if identifier is None:
        return None
    try:
        node = identifier()
    except TypeError:
        return None
    if node is None or isinstance(node, list):
        return None
    return node.getText()


def enclosing_type_name(ctx):
    """Simple name of the type a declaration is nested in, or None."""
    current = ctx.parentCtx
    while current is not None:
        if type(current).__name__.startswith(
            ("ClassDeclaration", "InterfaceDeclaration", "EnumDeclaration")
        ):
            return declared_name(current)
        current = current.parentCtx
    return None


def scoped_counts(ent_model, listener_factory):
    """Per-declaration counts from `listener.repository`, limited to an entity.

    The listeners that count decision points collect one context per
    occurrence, so `Counter(repository)` is a per-declaration map. What was
    missing is the restriction to the entity being asked about: a file gets
    everything, a type gets its own members, a method gets itself. Without it,
    SumCyclomatic and MaxCyclomatic answered every question with the whole
    file's number.
    """
    from collections import Counter

    listener = walk_file(ent_model, listener_factory())
    counts = Counter(getattr(listener, "repository", []))

    if is_file(ent_model):
        return {id(ctx): n for ctx, n in counts.items()}, listener

    name = ent_model.name()
    family_is_type = "Type" in (ent_model.kindname() or "")
    out = {}
    for ctx, n in counts.items():
        if family_is_type:
            if enclosing_type_name(ctx) == name:
                out[id(ctx)] = n
        elif declared_name(ctx) == name:
            out[id(ctx)] = n
    return out, listener


def cyclomatic_summary(ent_model) -> dict:
    """Sum and max of the cyclomatic complexity of an entity's methods.

    Both metrics used to reparse the entity's own contents -- which fails for
    anything that is not a compilation unit -- and then return the whole
    file's number regardless of what was asked.
    """
    from openunderstand.metrics.cyclomatic import CyclomaticListener

    counts, listener = scoped_counts(ent_model, CyclomaticListener)
    if is_file(ent_model):
        values = list(counts.values())
        return {"sum": listener.project_cyclomatic, "max": max(values, default=0)}
    values = list(counts.values()) or [1]
    return {"sum": sum(values), "max": max(values)}


def line_counts(source: str) -> dict:
    """Understand's line metrics for a block of source.

    A line is counted once per category it belongs to, and a line holding both
    code and a trailing comment counts in both -- which is why the categories
    do not sum to the total.

    Counted straight from the entity's own text rather than by walking a parse
    tree: the listener that used to do this was constructed but never walked,
    so every one of these metrics returned 0.
    """
    total = blank = code = comment = 0
    in_block = False
    for raw in (source or "").splitlines():
        total += 1
        line = raw.strip()
        if not line:
            blank += 1
            continue

        has_comment = in_block
        has_code = False
        i = 0
        while i < len(line):
            if in_block:
                end = line.find("*/", i)
                if end == -1:
                    i = len(line)
                else:
                    in_block = False
                    i = end + 2
                continue
            if line.startswith("//", i):
                has_comment = True
                break
            if line.startswith("/*", i):
                has_comment = True
                in_block = True
                i += 2
                continue
            if not line[i].isspace():
                has_code = True
            i += 1

        code += has_code
        comment += has_comment
    return {"total": total, "blank": blank, "code": code, "comment": comment}


def is_file(ent_model):
    return getattr(ent_model, "_kind_id", None) == kind_id("Java File")
