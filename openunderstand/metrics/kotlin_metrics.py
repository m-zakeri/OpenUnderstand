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

from functools import lru_cache

from antlr4.tree.Tree import TerminalNode

from openunderstand.analysis_passes.kotlin_tree import rule
from openunderstand.metrics import context as metric_context
from openunderstand.oudb.models import _kind_name
from openunderstand.utils import kotlin_parser

UNHANDLED = object()

#: Text metrics Java derives by reparsing that are not implemented for Kotlin.
UNAVAILABLE = frozenset(
    {"Essential", "Knots", "CountPath", "CountPathLog", "MaxEssentialKnots", "MinEssentialKnots"}
)

_LINE = {"CountLine", "CountLineBlank", "CountLineCode", "CountLineComment", "CountSemicolon",
         "RatioCommentToCode"}
_TREE = {"CountLineCodeDecl", "CountLineCodeExe", "CountStmt", "CountStmtDecl", "CountStmtExe", "Cyclomatic",
         "CyclomaticModified", "CyclomaticStrict", "MaxNesting"}


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


@lru_cache(maxsize=256)
def _parse(text: str, kind: str):
    """The tree of an entity's own source, wrapped when it is not a file on its own."""
    stripped = text.strip()
    if not stripped:
        return None
    candidates = [("", 0, 0)]
    if kind == "lambda" or stripped.startswith(("{", "fun(")):
        candidates = [("val _l = ", 0, 1)]
    elif stripped.startswith(("get", "set")):
        candidates = [("val _p: Int\n", 1, 1)]
    candidates.append(("class _W {\n", 1, 1))
    for prefix, shift, wrapper in candidates:
        suffix = "\n}" if prefix.startswith("class") else ""
        result = kotlin_parser.parse_text(prefix + text + suffix)
        if result.tree is not None and not result.errors:
            return result.tree, shift, wrapper if prefix else 0
    return None


def _walk(node):
    yield node
    for child in node.children or []:
        if not isinstance(child, TerminalNode):
            yield from _walk(child)


def _tree_metric(ent, name: str):
    text = _text(ent)
    kind = _kind_name(ent._kind_id) if hasattr(ent, "_kind_id") else ""
    lambda_like = "Lambda" in kind
    parsed = _parse(text, "lambda" if lambda_like else "")
    if parsed is None:
        return None
    tree, shift, wrapper = parsed
    nodes = list(_walk(tree))
    names = [rule(n) for n in nodes]
    if name == "MaxNesting":
        return 0 if lambda_like else _max_nesting(tree)
    if name.startswith("Cyclomatic") or name == "Cyclomatic":
        return _cyclomatic(nodes, names, name)
    declarations = max(sum(1 for n in names if n in _DECLARATIONS) - wrapper, 0)   # the wrapper is not the entity's
    executable = sum(
        1 for n in nodes if rule(n) == "statement" and not _holds_declaration(n)
    ) + sum(1 for x in names if x == "controlStatement")
    if name == "CountStmtDecl":
        return declarations
    if name == "CountStmtExe":
        return executable
    if name == "CountStmt":
        return declarations + executable
    return _line_split(text, nodes, name, shift, wrapper)


def _holds_declaration(statement) -> bool:
    return any(rule(c) == "declaration" for c in statement.children or [])


def _cyclomatic(nodes, names, name: str) -> int:
    value = 1
    when_entries = 0
    for node, kind in zip(nodes, names):
        if kind in ("ifExpression", "forStatement", "whileStatement", "doWhileStatement", "catchBlock", "elvis"):
            value += 1
        elif kind == "whenEntry":
            if not any(isinstance(c, TerminalNode) and c.getText() == "else" for c in node.children or []):
                when_entries += 1
        elif kind in ("disjunction", "conjunction") and name == "CyclomaticStrict":
            value += sum(
                1 for c in node.children or []
                if isinstance(c, TerminalNode) and c.getText() in ("||", "&&")
            )
    if name == "CyclomaticModified":
        value += sum(1 for n, k in zip(nodes, names) if k == "whenExpression" and _has_condition(n))
    else:
        value += when_entries
    return value


def _has_condition(when) -> bool:
    return any(
        rule(n) == "whenEntry" and not any(isinstance(c, TerminalNode) and c.getText() == "else" for c in n.children or [])
        for n in _walk(when)
    )


def _max_nesting(tree) -> int:
    def depth(node, level):
        here = level + (1 if rule(node) in _NESTING else 0)
        best = here
        for child in node.children or []:
            if not isinstance(child, TerminalNode):
                best = max(best, depth(child, here))
        return best

    return depth(tree, 0)


def _line_split(text: str, nodes, name: str, shift: int, wrapper: int):
    """Declarative lines are those a declaration (or an annotation on it) starts on; the rest of the code is
    executable. Java's finer rule (an initialiser's lines are executable) is not carried over."""
    code, _, _, _ = scan(text)
    wrapper_seen = 0
    declarative = set()
    for node in nodes:
        if rule(node) in _DECLARATIONS and node.start is not None:
            if wrapper and wrapper_seen < wrapper:
                wrapper_seen += 1               # the first declaration is the wrapper's own
                continue
            declarative.add(node.start.line - 1 - shift)
    decl = sum(1 for i, c in enumerate(code) if c and i in declarative)
    total = sum(code)
    return decl if name == "CountLineCodeDecl" else total - decl
