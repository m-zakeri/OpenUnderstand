"""Text metrics for Kotlin entities: lines, statements, cyclomatic complexity, nesting.

Understand has no Kotlin, so nothing here is measured against it: each definition is the Java one
transposed (what Understand's Java documentation says, tuned on Java fixtures), and says so where a
Kotlin construct has no Java twin. The metrics computed from the reference graph (fan, coupling,
cohesion, declaration counts) need nothing here: they read references, which Kotlin writes.

``compute()`` answers a value, or ``UNHANDLED`` for a name this module leaves to the graph
metrics. A text metric nobody implements for Kotlin (``Essential``, ``Knots``, ``CountPath``...) is
``None``: an honest "not available", not a Java parse of Kotlin source.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass
from functools import lru_cache

from antlr4.tree.Tree import TerminalNode

from openunderstand.analysis_passes.kotlin_tree import children, first, rule
from openunderstand.metrics import context as metric_context
from openunderstand.utils import kotlin_parser

UNHANDLED = object()

#: Text metrics Java derives by reparsing that are not implemented for Kotlin.
UNAVAILABLE = frozenset(
    {"MaxEssentialKnots", "MinEssentialKnots"}
)

_LINE = {"CountLine", "CountLineBlank", "CountLineCode", "CountLineComment", "CountSemicolon",
         "RatioCommentToCode"}
_TREE = {"Essential", "Knots", "CountPath", "CountPathLog", "CountLineCodeDecl", "CountLineCodeExe", "CountStmt", "CountStmtDecl", "CountStmtExe", "Cyclomatic",
         "CyclomaticModified", "CyclomaticStrict", "MaxNesting"}


_PRIMARY = re.compile(r"\s*(?:@\S+\s+|\w+\s+)*?(?:constructor\s*)?\(")


def is_kotlin(ent) -> bool:
    """Whether the entity is declared in a ``.kt`` or ``.kts`` file."""
    try:
        found = metric_context.enclosing_file(ent)
    except Exception:
        return False
    return found is not None and kotlin_parser.is_kotlin(found._longname or "")


def compute(ent, name: str):
    if name in UNAVAILABLE:
        return None
    if name in _LINE:
        return _line_metric(ent, name)
    if name in _TREE:
        return _tree_metric(ent, name)
    return UNHANDLED


# -- lines -----------------------------------------------------------------------------------
@lru_cache(maxsize=256)
def scan(text: str):
    """Per physical line: (has code, has comment, blank), plus the number of ``;`` outside strings
    and comments. Handles nested ``/* */``, ``"..."`` with ``${}`` templates, raw strings and chars."""
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    code = [False] * len(lines)
    comment = [False] * len(lines)
    semicolons = 0
    block = 0                        # depth of /* */ comments
    raw = False                      # inside a """ string
    stack = []                       # "{" depth inside string templates, innermost last
    in_string = False
    for number, line in enumerate(lines):
        i, n = 0, len(line)
        while i < n:
            c = line[i]
            pair = line[i:i + 2]
            if block:
                comment[number] = True
                if pair == "/*":
                    block, i = block + 1, i + 2
                elif pair == "*/":
                    block, i = block - 1, i + 2
                else:
                    i += 1
                continue
            if raw:
                code[number] = True
                if line.startswith('"""', i):
                    raw, i = False, i + 3
                elif pair == "${":
                    stack.append([1, True])
                    raw, i = False, i + 2
                else:
                    i += 1
                continue
            if in_string:
                code[number] = True
                if c == "\\":
                    i += 2
                elif c == '"':
                    in_string, i = False, i + 1
                elif pair == "${":
                    stack.append([1, False])
                    in_string, i = False, i + 2
                else:
                    i += 1
                continue
            if pair == "//":
                comment[number] = True
                break
            if pair == "/*":
                comment[number] = True
                block, i = 1, i + 2
                continue
            if line.startswith('"""', i):
                code[number] = True
                raw, i = True, i + 3
                continue
            if c == '"':
                code[number] = True
                in_string, i = True, i + 1
                continue
            if c == "'":
                code[number] = True
                end = line.find("'", i + 2 if line[i + 1:i + 2] == "\\" else i + 1)
                i = (end if end != -1 else n - 1) + 1
                continue
            if c.isspace():
                i += 1
                continue
            code[number] = True
            if c == ";":
                semicolons += 1
            elif stack and c == "{":
                stack[-1][0] += 1
            elif stack and c == "}":
                stack[-1][0] -= 1
                if stack[-1][0] == 0:
                    was_raw = stack.pop()[1]
                    raw, in_string = was_raw, not was_raw       # back into the string the template interrupted
            i += 1
    blank = [not line.strip() for line in lines]
    return tuple(code), tuple(comment), tuple(blank), semicolons


def _text(ent) -> str:
    return ent.contents() or ""


def _line_metric(ent, name: str):
    code, comment, blank, semicolons = scan(_text(ent))
    if name == "CountLine":
        return len(code)
    if name == "CountLineBlank":
        return sum(blank)
    if name == "CountLineCode":
        return sum(code)
    if name == "CountLineComment":
        return sum(comment)
    if name == "CountSemicolon":
        return semicolons
    total = sum(code)
    return f"{sum(comment) / total:.2f}" if total else "0.00"


# -- the tree --------------------------------------------------------------------------------
_DECLARATIONS = {"declaration", "secondaryConstructor", "anonymousInitializer", "companionObject"}
_NESTING = {"ifExpression", "forStatement", "whileStatement", "doWhileStatement", "whenExpression", "tryExpression"}


@dataclass(frozen=True)
class Parsed:
    tree: object
    line_offset: int        # lines the wrapper put before the entity's own first line
    wrapped: bool           # the tree holds a declaration of the wrapper's own, which is not the entity's


@lru_cache(maxsize=256)
def _parse(text: str, lambda_like: bool, accessor: bool = False) -> Parsed | None:
    """The tree of an entity's own source, wrapped when it is not a file on its own."""
    stripped = text.strip()
    if not stripped:
        return None
    attempts = [("", "", 0, False)]
    if lambda_like or stripped.startswith(("{", "fun(")):
        attempts = [("val _l = ", "", 0, True)]
    elif accessor or stripped.startswith(("get", "set")):
        attempts = [("val _p: Int\n", "", 1, True)]
    attempts.append(("class _W {\n", "\n}", 1, True))
    for prefix, suffix, offset, wrapped in attempts:
        result = kotlin_parser.parse_text(prefix + text + suffix)
        if result.tree is not None and not result.errors:
            return Parsed(result.tree, offset, wrapped)
    return None


def _walk(node):
    yield node
    for child in node.children or []:
        if not isinstance(child, TerminalNode):
            yield from _walk(child)


def _tree_metric(ent, name: str):
    text = _text(ent)
    kind = ent.kindname() or ""
    lambda_like = "Lambda" in kind
    parsed = _parse(text, lambda_like, (ent.longname() or "").endswith((".get", ".set")))
    if parsed is None:
        if "Constructor" in kind and _PRIMARY.match(text):    # a primary constructor: its parameters only
            return 1 if name.startswith("Cyclomatic") else 0
        return None
    if name == "MaxNesting":
        return 0 if lambda_like else _max_nesting(parsed.tree)
    nodes = list(_walk(parsed.tree))
    if name in ("CountPath", "CountPathLog"):
        return _count_path(nodes, name, parsed)
    if name in ("Essential", "Knots"):
        from openunderstand.metrics import kotlin_flow

        body = _body_of(nodes, parsed)
        if body is False:
            return None
        if body is None:
            return 0
        return kotlin_flow.essential(body) if name == "Essential" else kotlin_flow.knots(body)
    if name.startswith("Cyclomatic"):
        return _cyclomatic(nodes, name)
    if name in ("CountLineCodeDecl", "CountLineCodeExe"):
        return _line_split(text, nodes, name, parsed)
    declarations = max(sum(1 for n in nodes if rule(n) in _DECLARATIONS) - parsed.wrapped, 0)
    executable = sum(1 for n in nodes if rule(n) == "statement" and not _holds_declaration(n)) \
        + sum(1 for n in nodes if rule(n) == "controlStatement")
    return {"CountStmtDecl": declarations, "CountStmtExe": executable,
            "CountStmt": declarations + executable}[name]


def _holds_declaration(statement) -> bool:
    return any(rule(c) == "declaration" for c in statement.children or [])


def _is_else(entry) -> bool:
    return any(isinstance(c, TerminalNode) and c.getText() == "else" for c in entry.children or [])


def _cyclomatic(nodes, name: str) -> int:
    """1 plus the decision points. Strict also counts ``&&`` and ``||``; Modified counts a ``when`` once
    where the others count each of its branches."""
    value = 1
    for node in nodes:
        kind = rule(node)
        if kind in ("ifExpression", "forStatement", "whileStatement", "doWhileStatement", "catchBlock", "elvis"):
            value += 1
        elif kind == "whenEntry" and not _is_else(node) and name != "CyclomaticModified":
            value += 1
        elif kind == "whenExpression" and name == "CyclomaticModified":
            value += any(rule(n) == "whenEntry" and not _is_else(n) for n in _walk(node))
        elif kind in ("disjunction", "conjunction") and name == "CyclomaticStrict":
            value += sum(1 for c in node.children or [] if isinstance(c, TerminalNode) and c.getText() in ("||", "&&"))
    return value


def _max_nesting(tree) -> int:
    def depth(node, level):
        here = level + (1 if rule(node) in _NESTING else 0)
        best = here
        for child in node.children or []:
            if not isinstance(child, TerminalNode):
                best = max(best, depth(child, here))
        return best

    return depth(tree, 0)


def _declaration_lines(declaration) -> set:
    """The lines a declaration is declarative on: every line of its annotations and the line its keyword
    (or name) is on, as in Java. The lines of an initialiser or body after that are executable."""
    lines = {declaration.start.line}
    for node in _walk(declaration):
        if rule(node) == "annotation" and rule(node.parentCtx) == "modifiers" and node.stop is not None:
            lines.update(range(node.start.line, node.stop.line + 1))
    inner = declaration.children[0] if rule(declaration) == "declaration" and declaration.children else declaration
    for child in inner.children or []:
        if rule(child) != "modifiers" and getattr(child, "start", None) is not None:
            lines.add(child.start.line)
            break
    return lines


def _line_split(text: str, nodes, name: str, parsed: Parsed):
    """Declarative lines are those a declaration (or an annotation on it) starts on; the rest of the code is
    executable. Java's finer rule (an initialiser's lines are executable) is not carried over."""
    code, _, _, _ = scan(text)
    own = [n for n in nodes if rule(n) in _DECLARATIONS and n.start is not None][parsed.wrapped:]
    declarative = set()
    for n in own:
        declarative.update(line - 1 - parsed.line_offset for line in _declaration_lines(n))
    decl = sum(1 for i, c in enumerate(code) if c and i in declarative)
    return decl if name == "CountLineCodeDecl" else sum(code) - decl


# -- paths -------------------------------------------------------------------------------------
_MAX_PATHS = 10**9
_RUNS, _LEAVES = (1, 0), (0, 1)


def _count_path(nodes, name: str, parsed: Parsed):
    """Understand's CountPath for Java (``metrics/count_path.py``) transposed: how many ways a body can
    complete, plus how many paths leave it from inside. Boolean operators do not count; a ``return``
    ends its path. ``when`` is a switch (one more path without an ``else``), ``?:`` and lambdas run."""
    body = _body_of(nodes, parsed)
    if body is False:
        return None
    complete, exits = (0, 0) if body is None else _flow(body)
    total = min(complete + exits, _MAX_PATHS) if body is not None else 0
    total = total or (1 if body is not None else 0)
    return total if name == "CountPath" else round(math.log10(max(total, 1)))


def _body_of(nodes, parsed: Parsed):
    """The entity's own body: ``None`` when it has none (an abstract member), ``False`` when not found."""
    for node in nodes[parsed.wrapped:]:
        kind = rule(node)
        if kind in ("functionDeclaration", "getter", "setter"):
            body = first(node, "functionBody")
            return body if body is not None else None
        if kind == "secondaryConstructor":
            return first(node, "block")
        if kind == "lambdaLiteral":
            return first(node, "statements")
        if kind == "anonymousInitializer":
            return first(node, "block")
    return False


def _sequence(statements):
    alive, exits = 1, 0
    for statement in statements:
        complete, escaped = _flow(statement)
        exits = min(exits + alive * escaped, _MAX_PATHS)
        alive = min(alive * complete, _MAX_PATHS)
    return alive, exits


def _unwrap(node):
    """Down through the one-child expression levels to what the statement actually is."""
    while node is not None and not isinstance(node, TerminalNode):
        kids = [c for c in node.children or [] if not isinstance(c, TerminalNode)]
        if rule(node) in ("ifExpression", "whenExpression", "tryExpression", "jumpExpression", "forStatement",
                          "whileStatement", "doWhileStatement", "block", "statements", "controlStructureBody"):
            return node
        if len(kids) != 1 or len(node.children) != 1:
            return node
        node = kids[0]
    return node


def _flow(node):
    node = _unwrap(node)
    kind = rule(node)
    if node is None or isinstance(node, TerminalNode):
        return _RUNS
    if kind in ("functionBody",):
        inner = first(node, "block")
        return _flow(inner if inner is not None else first(node, "expression"))
    if kind in ("block", "statements"):
        return _sequence(children(first(node, "statements") if kind == "block" and first(node, "statements") is not None
                                  else node, "statement"))
    if kind == "controlStructureBody":
        return _flow(first(node, "block") or first(node, "statement") or first(node, "controlStatement"))
    if kind in ("statement", "controlStatement"):
        if first(node, "declaration") is not None:
            return _RUNS
        return _flow(first(node, "loopStatement") or first(node, "expressionStatement"))
    if kind == "loopStatement":
        return _flow(node.children[0])
    if kind == "expressionStatement":
        if len([c for c in node.children or [] if not (isinstance(c, TerminalNode) and not c.getText().strip())]) != 1:
            return _RUNS                                        # an assignment
        return _flow(first(node, "expression"))
    if kind == "ifExpression":
        bodies = children(node, "controlStructureBody")
        seen_else = any(isinstance(c, TerminalNode) and c.getText() == "else" for c in node.children or [])
        then_c, then_e = _flow(bodies[0]) if bodies else _RUNS
        else_c, else_e = _flow(bodies[1]) if seen_else and len(bodies) > 1 else _RUNS
        return min(then_c + else_c, _MAX_PATHS), min(then_e + else_e, _MAX_PATHS)
    if kind in ("forStatement", "whileStatement"):
        body_c, body_e = _flow(first(node, "controlStructureBody"))
        return min(body_c + 1, _MAX_PATHS), body_e
    if kind == "doWhileStatement":
        return _flow(first(node, "controlStructureBody"))
    if kind == "whenExpression":
        complete = exits = 0
        has_else = False
        for entry in children(node, "whenEntry"):
            has_else = has_else or _is_else(entry)
            entry_c, entry_e = _flow(first(entry, "controlStructureBody"))
            complete, exits = complete + entry_c, exits + entry_e
        return min(complete + (0 if has_else else 1), _MAX_PATHS), min(exits, _MAX_PATHS)
    if kind == "tryExpression":
        blocks = children(node, "block")
        complete, exits = _flow(blocks[0]) if blocks else _RUNS
        for clause in children(node, "catchBlock"):
            catch_c, catch_e = _flow(first(clause, "block"))
            complete, exits = complete + catch_c, exits + catch_e
        for final in children(node, "finallyBlock"):
            complete *= _flow(first(final, "block"))[0]
        return min(complete, _MAX_PATHS), min(exits, _MAX_PATHS)
    if kind == "jumpExpression":
        start = node.start.text if node.start is not None else ""
        return _LEAVES if start in ("return", "throw", "break", "continue") else _RUNS
    return _RUNS
