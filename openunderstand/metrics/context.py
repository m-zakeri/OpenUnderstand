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


# 2048, not 256: a package's Sum/Max/Avg roll-up asks every method in the
# package for sixteen metrics, and org.json alone declares over a thousand --
# at 256 the cache evicted each tree before the next metric asked for it.
@lru_cache(maxsize=2048)
def parse_entity(source):
    """Parse an entity's own source, whatever kind of declaration it is.

    A method or field declaration is not a compilation unit, so parsing it
    directly fails and every metric built on it returned 0. Wrapping it in a
    synthetic class makes it parseable, which scopes the metric to the entity
    without any name matching.
    """
    return parse_entity_source(source)[0]


@lru_cache(maxsize=2048)
def parse_entity_source(source):
    """`parse_entity`, plus the text the line numbers in the tree refer to.

    The wrapper adds a line above the entity, so a caller that maps tree lines
    back onto text has to know which of the two candidates parsed.
    """
    from antlr4.error.ErrorListener import ErrorListener

    class _Failed(ErrorListener):
        def __init__(self):
            self.failed = False

        def syntaxError(self, *_args):
            self.failed = True

    # The middle candidate is for an anonymous class, whose own source is a
    # bare class *body*. Without it the last candidate wins -- `class W { { ...
    # } }` parses, as an instance initializer -- and every member inside reads
    # as a statement rather than a declaration: CountLineCodeDecl 0 against 1,
    # CountStmtDecl 6 against 7, MaxCyclomatic 2 against 1. It adds no line, so
    # the tree's line numbers still index the entity's own source.
    for candidate in (
        source,
        f"class {_WRAPPER} {source}",
        f"class {_WRAPPER} {{\n{source}\n}}",
    ):
        lexer = JavaLexer(InputStream(candidate))
        parser = JavaParserLabeled(CommonTokenStream(lexer))
        detector = _Failed()
        parser.removeErrorListeners()
        parser.addErrorListener(detector)
        tree = parser.compilationUnit()
        if not detector.failed:
            return tree, candidate
    return tree, candidate


_DECLARATION = (
    "MethodDeclaration",
    "ConstructorDeclaration",
    "GenericMethodDeclaration",
    "GenericConstructorDeclaration",
    "InterfaceMethodDeclaration",
)


def _declaration_and_body(ent_model):
    """(declaration found?, its block) for an entity's own source."""
    stack = [parse_entity(ent_model.contents() or "")]
    found = False
    while stack:
        node = stack.pop()
        name = type(node).__name__
        if name.startswith(_DECLARATION):
            found = True
            for child in node.children or ():
                if type(child).__name__ == "BlockContext":
                    return True, child
                if type(child).__name__.startswith(("MethodBody", "ConstructorBody")):
                    blocks = [
                        c
                        for c in (child.children or ())
                        if type(c).__name__ == "BlockContext"
                    ]
                    if blocks:
                        return True, blocks[0]
        stack.extend(
            c
            for c in (getattr(node, "children", None) or ())
            if hasattr(c, "getRuleIndex")
        )
    return found, None


def method_body(ent_model):
    """The `block` of a method or constructor's own source, or None."""
    return _declaration_and_body(ent_model)[1]


def declares_without_body(ent_model):
    """True when the entity's source is a declaration carrying no body.

    An abstract or interface method: Understand scores those 0 on the whole
    complexity family, not the 1 an empty body earns. A *lambda* is an entity
    too and is none of this -- its source holds no declaration at all, and
    treating "no body found" as body-less zeroed all 34 of JSON's.
    """
    declared, body = _declaration_and_body(ent_model)
    return declared and body is None


def walk_entity(ent_model, listener):
    """Walk `listener` over the entity's own source. Returns the listener."""
    ParseTreeWalker().walk(
        t=parse_entity(ent_model.contents() or ""), listener=listener
    )
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


@lru_cache(maxsize=256)
def _scoped_counts(source, name, family_is_type, file_scoped, listener_factory):
    from collections import Counter

    listener = listener_factory()
    ParseTreeWalker().walk(t=parse(source), listener=listener)
    counts = Counter(getattr(listener, "repository", []))

    if file_scoped:
        return {id(ctx): n for ctx, n in counts.items()}, listener

    out = {}
    for ctx, n in counts.items():
        if family_is_type:
            if enclosing_type_name(ctx) == name:
                out[id(ctx)] = n
        elif declared_name(ctx) == name:
            out[id(ctx)] = n
    return out, listener


def scoped_counts(ent_model, listener_factory):
    """Per-declaration counts from `listener.repository`, limited to an entity.

    The listeners that count decision points collect one context per
    occurrence, so `Counter(repository)` is a per-declaration map. What was
    missing is the restriction to the entity being asked about: a file gets
    everything, a type gets its own members, a method gets itself. Without it,
    SumCyclomatic and MaxCyclomatic answered every question with the whole
    file's number.

    Memoized on its real inputs -- the file's source and the entity's name and
    family. Ent.metric() dispatches one metric at a time through an if/elif
    chain, so asking an entity for SumCyclomatic, MaxCyclomatic and
    AvgCyclomatic walked the same file three times. The returned dict and
    listener are shared between callers and must not be mutated.
    """
    return _scoped_counts(
        file_source(ent_model),
        ent_model.name(),
        "Type" in (ent_model.kindname() or ""),
        is_file(ent_model),
        listener_factory,
    )


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
        return {
            "sum": listener.project_cyclomatic,
            "max": max(values, default=0),
            "avg": round(sum(values) / len(values)) if values else 0,
        }
    values = list(counts.values()) or [1]
    return {
        "sum": sum(values),
        "max": max(values),
        "avg": round(sum(values) / len(values)),
    }


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
    "LocalVariableDeclarationContext",
    "FieldDeclarationContext",
    "MethodDeclarationContext",
    "ConstructorDeclarationContext",
    "ClassDeclarationContext",
    "InterfaceDeclarationContext",
    "EnumDeclarationContext",
    "AnnotationTypeDeclarationContext",
    "ConstDeclarationContext",
    "InterfaceMethodDeclarationContext",
    # `for (char c : items)` declares c. It is not a localVariableDeclaration,
    # so it was the declarative statement validForBase was short by -- and its
    # *line* still belongs to the loop, which _add_signature_lines skips.
    "EnhancedForControlContext",
)
# Every `statement` alternative except a bare block (#statement0), an empty
# statement (#statement14) and a label (#statement16), which do nothing.
_EXECUTABLE = tuple(
    f"Statement{n}Context" for n in (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15)
)


#: Contexts that make an initialiser *do* something rather than copy a value.
_INVOKING = ("MethodCall", "Creator", "CreatedName")


def _initialiser_invokes(ctx):
    """Whether a declaration's initialiser does something rather than copy.

    `T temp = item;` is declarative only -- CycleSort.replace is Understand's
    StmtDecl 2 / StmtExe 3 -- while `int comp = key.compareTo(...)` also
    executes, which is how BinarySearch.search reaches 8.

    Calling *anything else* executable was tried and measured worse: array
    literals and arithmetic pushed CountStmtExe from 64.5% down to 59.5%, so
    invoking something is the line, until a traced method says otherwise.
    """
    stack = [ctx]
    while stack:
        node = stack.pop()
        if type(node).__name__.startswith(_INVOKING):
            return True
        stack.extend(
            c
            for c in (getattr(node, "children", None) or ())
            if hasattr(c, "getRuleIndex")
        )
    return False


class _StatementClassifier:
    """Splits an entity's statements and code lines into declarative and executable."""

    def __init__(self):
        self.statements = 0
        self.decl_statements = 0
        self.exe_statements = 0
        self.decl_lines = set()
        self.exe_lines = set()
        #: Depth inside `new Runnable() { ... }` bodies. What they declare
        #: belongs to the anonymous class, which is an entity of its own.
        self.anonymous = 0

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
            # `for (int i = 0; ...)` declares i, but the line belongs to the
            # loop: Understand counts validForBase at 7 declarative lines and
            # the eighth this produced was the `for`. Every counted loop with
            # an init declaration added one.
            in_for = (
                type(ctx.parentCtx).__name__.startswith("ForInit")
                or name == "EnhancedForControlContext"
            )
            # Inside `new Runnable() { ... }` the declaration still counts as a
            # declarative *statement* -- Understand puts the method holding one
            # at CountStmtDecl 3 and CountLineCodeDecl 1 -- but its lines belong
            # to the anonymous class, which is an entity in its own right and
            # reports 0 declarative lines for them.
            if not in_for and not self.anonymous:
                if name in _DECLARATION_STATEMENTS:
                    self._add_declaration_lines(ctx)
                else:
                    self._add_signature_lines(ctx, self.decl_lines)
            if name == "LocalVariableDeclarationContext" and _has_initialiser(ctx):
                # The line carries executable code either way -- CycleSort's
                # `T temp = item;` is one of that method's four
                # CountLineCodeExe lines. Off the `for` path
                # _add_declaration_lines has already said so, and with the
                # initialiser's other lines.
                if in_for and ctx.start is not None:
                    self.exe_lines.add(ctx.start.line)
                # Whether it is also an executable *statement* depends on what
                # the initialiser does. `T temp = item;` is not one and
                # `int comp = key.compareTo(...)` is: BinarySearch.search
                # declares both and Understand counts exactly one of them.
                if _initialiser_invokes(ctx):
                    self.exe_statements += 1
        elif name in _EXECUTABLE:
            self.statements += 1
            self.exe_statements += 1
            self._add_statement_lines(ctx)
        elif name.startswith("SwitchLabel") and ctx.start is not None:
            # `case 0:` is an executable line of its own -- Understand puts a
            # switch with three groups and four labels at 8 executable lines,
            # and counting only the group's first label reported 7.
            self.exe_lines.add(ctx.start.line)
        elif name == "Statement0Context" and ctx.start is not None:
            # A bare block is not a statement Understand counts, but the line
            # it opens on carries executable code: `} else {` is the ninth of
            # BinarySearch.search's nine CountLineCodeExe lines and the only
            # one this missed.
            self.exe_lines.add(ctx.start.line)
        # `new Runnable() { ... }` parses as creator -> classCreatorRest ->
        # classBody, so the anonymous body is everything under the rest.
        anonymous = name == "ClassCreatorRestContext"
        self.anonymous += anonymous
        for child in getattr(ctx, "children", None) or ():
            if hasattr(child, "getRuleIndex"):
                self.visit(child)
        self.anonymous -= anonymous

    def _add_statement_lines(self, ctx):
        """Every line a statement occupies, not just the one it opens on.

        `return (a\\n && b\\n && c);` is three executable lines to Understand
        and this counted one, which is most of the 332 methods still short.

        A compound statement stops at the line its body opens on: the body is
        made of statements counted in their own right, and running to the
        statement's own stop would swallow the closing braces. Understand puts
        `if (n == 1\\n && n > 0) {` at two executable lines and the whole
        method at three.
        """
        if ctx.start is None:
            return
        children = list(getattr(ctx, "children", None) or ())
        if not children:
            self.exe_lines.add(ctx.start.line)
            return
        for child in children:
            span = _child_span(child)
            if span is None:
                continue
            if type(child).__name__.startswith(_BODY):
                # Only the line the body opens on: `} else {` and
                # `} catch (E e) {` execute, the `}` that closes them does not.
                self.exe_lines.add(span[0])
            elif getattr(child, "symbol", None) is not None and child.getText() == "}":
                continue
            else:
                self.exe_lines.update(range(span[0], span[1] + 1))

    def _add_declaration_lines(self, ctx):
        """Split a variable declaration's lines the way Understand does.

        Every line of the declaration used to be declarative and only its
        first line executable, which is exactly backwards for the shape that
        dominates the benchmark's long methods -- a string built by `+` over a
        hundred lines. `JSONMLTest.toJSONObjectToJSONArray` came out
        decl 174 / exe 18 against Understand's 18 / 175.

        Measured against Understand 7.0.1217 on a fixture written for it
        (`String s = "a" + <n lines>` for n in 1..6, the same with an array
        initialiser, a ternary, a nested call, two declarators one of which
        spans lines, a declaration whose name and `=` sit on their own lines,
        and one with no initialiser):

          * with no initialiser, every line is declarative and none executes;
          * with an expression initialiser, declarative is the run from the
            declaration's start through the line the initialiser starts on,
            plus the line the `;` lands on -- and executable is the
            initialiser's whole span. `String s = "a" +` / `"b" +` / `"c";` is
            2 declarative and 3 executable;
          * an array initialiser is a declarative *list*: every line of it is
            declarative, and only the element lines execute.
        """
        if ctx.start is None or ctx.stop is None:
            return
        start, stop = _signature_start(ctx), ctx.stop.line
        declarator = _first_initialised_declarator(ctx)
        initialiser = declarator[1] if declarator else None
        if initialiser is None or initialiser.start is None:
            self.decl_lines.update(range(start, stop + 1))
            return
        elements = _array_element_lines(initialiser)
        if elements is not None:
            self.decl_lines.update(range(start, stop + 1))
            self.exe_lines.update(elements)
            return
        opens = initialiser.start.line
        # The declarative half ends at the `=`, not at the initialiser: with
        # `String s =` alone on its line the initialiser starts on the *next*
        # one, and counting through it made CookieTest.multiPartCookie 10
        # declarative lines against Understand's 8. Where the two sit on one
        # line -- `= "a" +` -- the answer is the same either way.
        self.decl_lines.update(range(start, (_assign_line(declarator[0]) or opens) + 1))
        self.decl_lines.add(stop)
        self.exe_lines.update(range(opens, stop + 1))

    @staticmethod
    def _add_signature_lines(ctx, target):
        if ctx.start is None:
            return
        first = _signature_start(ctx)
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
            "LocalVariableDeclarationContext",
            "FieldDeclarationContext",
            "ConstDeclarationContext",
        ):
            last = ctx.stop.line
        target.update(range(first, last + 1))


#: Declarations whose lines split into declarative and executable halves.
_DECLARATION_STATEMENTS = (
    "LocalVariableDeclarationContext",
    "FieldDeclarationContext",
    "ConstDeclarationContext",
)


#: Direct children that mean "the rest of this statement is its body".
_BODY = (
    "Statement",
    "Block",
    "SwitchBlockStatementGroup",
    "CatchClause",
    "FinallyBlock",
)


def _child_span(child):
    """First and last line of a parse-tree child, terminal or context."""
    symbol = getattr(child, "symbol", None)
    if symbol is not None:
        return symbol.line, symbol.line
    start = getattr(child, "start", None)
    if start is None:
        return None
    stop = getattr(child, "stop", None)
    return start.line, (stop.line if stop is not None else start.line)


def _signature_start(ctx):
    """First line of a declaration, annotations included.

    `@Override` and `@Test(expected = ...)` sit on the enclosing
    classBodyDeclaration, not on the methodDeclaration, so counting from the
    declaration's own start line lost them: Understand puts
    MyBeanCustomNameSubClass.getSomeInt at 3 declarative lines -- two
    annotations and the signature -- and this reported 1. Verified against
    Understand on one, two and a three-line annotation.

    The enclosing declaration is the run of ancestors that end on the very same
    token, which is what "adds only leading modifiers" looks like in the tree.
    A localVariableDeclaration stops before its `;` and its parent does not, so
    the climb stops there and its own `final`/annotations are already inside.
    """
    start = ctx.start.line
    node, stop = ctx, ctx.stop
    while stop is not None:
        parent = getattr(node, "parentCtx", None)
        if parent is None or getattr(parent, "stop", None) is not stop:
            break
        node = parent
        if node.start is not None:
            start = min(start, node.start.line)
    return start


def _first_initialised_declarator(ctx):
    """The first declarator that assigns something, as `(declarator, value)`.

    `int a = 1, b = 2 + \\n 3;` starts executing on the first declarator's
    line, which is where Understand starts counting.
    """
    for declarator in _descend(ctx, "VariableDeclaratorContext"):
        if getattr(declarator, "variableInitializer", None) is None:
            continue
        try:
            initialiser = declarator.variableInitializer()
        except TypeError:
            continue
        if initialiser is not None:
            return declarator, initialiser
    return None


def _assign_line(declarator):
    """Line of the `=` in a declarator, or None when it has no children."""
    for child in getattr(declarator, "children", None) or ():
        symbol = getattr(child, "symbol", None)
        if symbol is not None and child.getText() == "=":
            return symbol.line
    return None


def _array_element_lines(initialiser):
    """Lines of an array initialiser's elements, or None when it is not one."""
    for child in getattr(initialiser, "children", None) or ():
        if type(child).__name__ != "ArrayInitializerContext":
            continue
        # The labelled grammar numbers the alternatives:
        # `variableInitializer` is VariableInitializer0/1Context, never the
        # bare name, so an exact match found no elements and every array
        # declaration executed nothing.
        return {
            element.start.line
            for element in getattr(child, "children", None) or ()
            if type(element).__name__.startswith("VariableInitializer")
            and element.start is not None
        }
    return None


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

    Five metrics read this one result, and each used to recompute it. The
    returned dict is shared and must not be mutated.
    """
    return _statement_counts(ent_model.contents() or "")


@lru_cache(maxsize=256)
def _statement_counts(source: str) -> dict:
    tree, text = parse_entity_source(source)
    classifier = _StatementClassifier()
    classifier.visit(tree)
    # A statement's span can cross a blank or comment-only line -- `f(1,` /
    # blank / `2);` is two executable lines to Understand, not three -- so the
    # spans are intersected with the lines that actually hold code. `text`,
    # not `source`: the wrapper shifts every line number by one.
    code = {number for number, has_code, _ in _scan_lines(text) if has_code}
    # A line holding nothing but `}` closes something; it never executes. The
    # brace lines that do -- `} else {`, `} catch (E e) {`, `} while (c);`,
    # `};` -- all carry something else. A statement's span crosses the closing
    # brace of any block nested inside it, which is the line that put a method
    # holding `new Runnable() { ... }` at 7 executable lines against 6.
    closing = {
        number
        for number, raw in enumerate(text.split("\n")[:-1], 1)
        if raw.strip() == "}"
    }
    return {
        "stmt": classifier.statements,
        "stmt_decl": classifier.decl_statements,
        "stmt_exe": classifier.exe_statements,
        "line_decl": len(classifier.decl_lines & code),
        "line_exe": len((classifier.exe_lines & code) - closing),
    }


def _scan_lines(source: str):
    """Yield `(line number, has code, has comment)` for each line of `source`.

    One scanner for both line_counts() and the code-line filter the statement
    classifier needs: a line's category is decided here, and nowhere else.
    """
    in_block = False
    # split(), not splitlines(): the last element is the text after the final
    # newline, which Understand does not count as a line unless it is
    # terminated. Dropping it makes both cases uniform.
    for number, raw in enumerate((source or "").split("\n")[:-1], 1):
        line = raw.strip()
        if not line:
            yield number, False, False
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
        yield number, has_code, has_comment


@lru_cache(maxsize=512)
def line_counts(source: str) -> dict:
    """Understand's line metrics for a block of source.

    Five metrics read this one result, and average_line_counts() calls it once
    per member of a class for each of four more, so it is memoized on the
    source it counts. The returned dict is shared and must not be mutated.

    A line is counted once per category it belongs to, and a line holding both
    code and a trailing comment counts in both -- which is why the categories
    do not sum to the total.

    Counted straight from the entity's own text rather than by walking a parse
    tree: the listener that used to do this was constructed but never walked,
    so every one of these metrics returned 0.
    """
    total = blank = code = comment = 0
    for _number, has_code, has_comment in _scan_lines(source):
        total += 1
        if not (has_code or has_comment):
            blank += 1
            continue
        code += has_code
        comment += has_comment
    return {"total": total, "blank": blank, "code": code, "comment": comment}


def is_file(ent_model):
    # An entity with no kind is not a file, and asking the database would need
    # one open -- which is what stopped tests/ exercising a metric on a stub.
    kind = getattr(ent_model, "_kind_id", None)
    return kind is not None and kind == kind_id("Java File")
