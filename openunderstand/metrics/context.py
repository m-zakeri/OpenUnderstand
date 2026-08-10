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

from openunderstand.gen.javaLabeled.JavaLexer import JavaLexer
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
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


#: Name of the synthetic class parse_entity() wraps a member in, so the
#: classifiers can tell it apart from a real declaration.
_WRAPPER = "__OpenUnderstandScope"


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

    for candidate in (source, f"class {_WRAPPER} {{\n{source}\n}}"):
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
        return {"sum": listener.project_cyclomatic,
                "max": max(values, default=0),
                "avg": round(sum(values) / len(values)) if values else 0}
    values = list(counts.values()) or [1]
    return {"sum": sum(values), "max": max(values),
            "avg": round(sum(values) / len(values))}


# Derived from Understand's own numbers for `Main.main` (CountStmt 9,
# CountStmtDecl 4, CountStmtExe 8, CountLineCodeDecl 4, CountLineCodeExe 8)
# over a 13-line method with 3 initialised locals and 5 call statements:
#
#   * the declaration itself counts as one declarative statement;
#   * a local declaration counts as declarative, and *also* as executable when
#     it has an initialiser -- which is why Decl + Exe exceeds CountStmt;
#   * a declaration's lines are its signature only, since its body is made of
#     statements counted in their own right.
_DECLARATIVE = (
    "LocalVariableDeclarationContext", "FieldDeclarationContext",
    "MethodDeclarationContext", "ConstructorDeclarationContext",
    "ClassDeclarationContext", "InterfaceDeclarationContext",
    "EnumDeclarationContext", "AnnotationTypeDeclarationContext",
    "ConstDeclarationContext", "InterfaceMethodDeclarationContext",
)
# Every `statement` alternative except a bare block (#statement0), an empty
# statement (#statement14) and a label (#statement16), which do nothing.
_EXECUTABLE = tuple(
    f"Statement{n}Context" for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15)
)


class _StatementClassifier:
    """Splits an entity's statements and code lines into declarative and executable."""

    def __init__(self):
        self.statements = 0
        self.decl_statements = 0
        self.exe_statements = 0
        self.decl_lines = set()
        self.exe_lines = set()

    def visit(self, ctx):
        name = type(ctx).__name__
        if name == "ClassDeclarationContext" and declared_name(ctx) == _WRAPPER:
            # The wrapper parse_entity() adds is not part of the entity.
            for child in getattr(ctx, "children", None) or ():
                if hasattr(child, "getRuleIndex"):
                    self.visit(child)
            return
        if name in _DECLARATIVE:
            self.statements += 1
            self.decl_statements += 1
            self._add_signature_lines(ctx, self.decl_lines)
            if name == "LocalVariableDeclarationContext" and _has_initialiser(ctx):
                # `int x = f();` both declares and executes.
                self.exe_statements += 1
                if ctx.start is not None:
                    self.exe_lines.add(ctx.start.line)
        elif name in _EXECUTABLE:
            self.statements += 1
            self.exe_statements += 1
            if ctx.start is not None:
                self.exe_lines.add(ctx.start.line)
        for child in getattr(ctx, "children", None) or ():
            if hasattr(child, "getRuleIndex"):
                self.visit(child)

    @staticmethod
    def _add_signature_lines(ctx, target):
        if ctx.start is None:
            return
        last = ctx.start.line
        parameters = getattr(ctx, "formalParameters", None)
        if parameters is not None:
            try:
                params = parameters()
            except TypeError:
                params = None
            if params is not None and params.stop is not None:
                last = params.stop.line
        elif ctx.stop is not None and type(ctx).__name__ in (
            "LocalVariableDeclarationContext", "FieldDeclarationContext",
            "ConstDeclarationContext",
        ):
            last = ctx.stop.line
        target.update(range(ctx.start.line, last + 1))


def _has_initialiser(ctx):
    for declarator in _descend(ctx, "VariableDeclaratorContext"):
        if getattr(declarator, "variableInitializer", None) is not None:
            try:
                if declarator.variableInitializer() is not None:
                    return True
            except TypeError:
                pass
    return False


def _descend(ctx, type_name):
    for child in getattr(ctx, "children", None) or ():
        if not hasattr(child, "getRuleIndex"):
            continue
        if type(child).__name__ == type_name:
            yield child
        yield from _descend(child, type_name)


def statement_counts(ent_model) -> dict:
    """Understand's four statement/code-line counts for an entity.

    They used to come from a listener that was constructed but never walked --
    so CountLineCodeDecl and CountLineCodeExe were 0 everywhere -- and from a
    statement counter that did not distinguish declarative from executable.
    """
    classifier = _StatementClassifier()
    classifier.visit(parse_entity(ent_model.contents() or ""))
    return {
        "stmt": classifier.statements,
        "stmt_decl": classifier.decl_statements,
        "stmt_exe": classifier.exe_statements,
        "line_decl": len(classifier.decl_lines),
        "line_exe": len(classifier.exe_lines),
    }


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
    # split(), not splitlines(): the last element is the text after the final
    # newline, which Understand does not count as a line unless it is
    # terminated. Dropping it makes both cases uniform.
    for raw in (source or "").split("\n")[:-1]:
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
