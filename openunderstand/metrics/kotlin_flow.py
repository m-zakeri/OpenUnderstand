"""Essential complexity and knots for Kotlin: Java's rules (``essential.py``, ``knots.py``) over a neutral tree.

Both metrics were read off Understand for Java on hand-written fixtures; nothing here is measured for Kotlin, only
transposed. The Kotlin body is first reduced to a few statement kinds, so the two algorithms are Java's own:

    seq(statements)   block   if(then, else)   loop(body, do?)   when(bodies, has else)
    try(body, catches, finallys)   label(name, statement)   run   return   throw   break   continue

Differences from Java that the reduction carries: a ``when`` entry never falls into the next, and a ``break``
inside a ``when`` leaves the enclosing loop (Kotlin 1.4+), where Java's leaves the switch.
"""

from __future__ import annotations

from antlr4.tree.Tree import TerminalNode

from openunderstand.analysis_passes.kotlin_tree import children, first, rule


class Node:
    __slots__ = ("kind", "kids", "name", "flag")

    def __init__(self, kind, kids=(), name=None, flag=False):
        self.kind, self.kids, self.name, self.flag = kind, list(kids), name, flag


_RUN = lambda: Node("run")  # noqa: E731


def _unwrap(node):
    from openunderstand.metrics.kotlin_metrics import _unwrap as unwrap

    return unwrap(node)


def convert(node) -> Node:
    node = _unwrap(node)
    if node is None or isinstance(node, TerminalNode):
        return _RUN()
    kind = rule(node)
    if kind == "functionBody":
        inner = first(node, "block")
        return convert(inner) if inner is not None else _RUN()
    if kind == "block":
        statements = first(node, "statements")
        return Node("seq", [convert(s) for s in children(statements, "statement")] if statements is not None else [])
    if kind == "statements":
        return Node("seq", [convert(s) for s in children(node, "statement")])
    if kind == "controlStructureBody":
        block = first(node, "block")
        if block is not None:
            return Node("bare", [convert(block)])
        return convert(first(node, "statement") or first(node, "controlStatement"))
    if kind in ("statement", "controlStatement"):
        if first(node, "declaration") is not None:
            return _RUN()
        result = convert(first(node, "loopStatement") or first(node, "expressionStatement"))
        for label in reversed(children(node, "label")):
            result = Node("label", [result], name=label.getText().strip().rstrip("@"))
        return result
    if kind == "loopStatement":
        return convert(node.children[0])
    if kind == "expressionStatement":
        real = [c for c in node.children or [] if not (isinstance(c, TerminalNode) and not c.getText().strip())]
        return convert(first(node, "expression")) if len(real) == 1 else _RUN()
    if kind == "ifExpression":
        bodies = children(node, "controlStructureBody")
        has_else = any(isinstance(c, TerminalNode) and c.getText() == "else" for c in node.children or [])
        return Node("if", [convert(bodies[0]) if bodies else _RUN()] + ([convert(bodies[1])] if has_else and len(bodies) > 1 else []))
    if kind in ("forStatement", "whileStatement", "doWhileStatement"):
        body = first(node, "controlStructureBody")
        return Node("loop", [convert(body) if body is not None else _RUN()], flag=kind == "doWhileStatement")
    if kind == "whenExpression":
        entries = children(node, "whenEntry")
        has_else = any(any(isinstance(c, TerminalNode) and c.getText() == "else" for c in e.children or []) for e in entries)
        bodies = []
        for entry in entries:
            body = convert(first(entry, "controlStructureBody"))
            bodies.append(body.kids[0] if body.kind == "bare" else Node("seq", [body]))
        return Node("when", bodies, flag=has_else)
    if kind == "tryExpression":
        blocks = children(node, "block")
        head = convert(blocks[0]) if blocks else Node("seq")
        catches = [convert(first(c, "block")) for c in children(node, "catchBlock")]
        finals = [convert(first(f, "block")) for f in children(node, "finallyBlock")]
        return Node("try", [head, Node("seq", catches), Node("seq", finals)])
    if kind == "jumpExpression":
        text = node.start.text if node.start is not None else ""
        label = text.split("@", 1)[1] if "@" in text and text.split("@", 1)[0] in ("break", "continue") else None
        word = text.split("@", 1)[0]
        if word == "return":
            return Node("return")
        if word in ("break", "continue", "throw"):
            return Node(word, name=label)
    return _RUN()


# -- essential ----------------------------------------------------------------------------------
_N, _R = "N", "R"


class _Result:
    __slots__ = ("exits", "structured", "points")

    def __init__(self, exits, structured=True, points=0):
        self.exits, self.structured, self.points = exits, structured, points


def _sequence(statements, label=None):
    exits, structured, points, reachable = set(), True, 0, True
    for statement in statements:
        result = _analyse(statement, label)
        structured &= result.structured
        points += result.points
        exits |= result.exits - {_N}
        if _N not in result.exits:
            reachable = False
            break
    if reachable:
        exits.add(_N)
    return _Result(exits, structured, points)


def _loop(body, label):
    inner = _analyse(body, None)
    consumed = {("B", None), ("B", label), ("C", None), ("C", label)}
    escaping = inner.exits - consumed - {_N}
    structured = inner.structured and not escaping
    return _Result({_N} | escaping, structured, 0 if structured else 1 + inner.points)


def _analyse(node, label=None):
    kind = node.kind
    if kind == "seq":
        return _sequence(node.kids, label)
    if kind == "bare":
        return _analyse(node.kids[0], label)
    if kind == "label":
        inner = _analyse(node.kids[0], node.name)
        return _Result((inner.exits - {("B", node.name)}) | {_N}, inner.structured, inner.points)
    if kind == "if":
        then = _analyse(node.kids[0], None)
        other = _analyse(node.kids[1], None) if len(node.kids) > 1 else _Result({_N})
        exits = then.exits | other.exits
        structured = then.structured and other.structured and exits == {_N}
        return _Result(exits, structured, 0 if structured else 1 + then.points + other.points)
    if kind == "loop":
        return _loop(node.kids[0], label)
    if kind == "try":
        head, catches, finals = node.kids
        parts = [_analyse(head, None)] + [_analyse(c, None) for c in catches.kids] + [_analyse(f, None) for f in finals.kids]
        exits = set().union(*(p.exits for p in parts))
        structured = all(p.structured for p in parts) and exits == {_N}
        return _Result(exits, structured, 0 if structured else len(catches.kids) + sum(p.points for p in parts))
    if kind == "when":
        exits, structured, points = set(), True, 0
        for body in node.kids:
            result = _analyse(body, None)
            structured &= result.structured
            points += result.points
            leaving = result.exits
            if leaving == {_R}:
                leaving = {_N}          # an entry that always returns ends normally, as a returning case does
            exits |= leaving if leaving else {_N}
        if not node.flag:
            exits.add(_N)
        structured = structured and exits == {_N}
        return _Result(exits or {_N}, structured, 0 if structured else len(node.kids) - (1 if node.flag else 0) + points)
    if kind == "return":
        return _Result({_R})
    if kind == "break":
        return _Result({("B", node.name)})
    if kind == "continue":
        return _Result({("C", node.name)})
    return _Result({_N})                   # run, and throw (an abnormal exit does not count)


def essential(body) -> int:
    value = 1 + _analyse(convert(body)).points
    return 1 if value == 2 else value      # a graph of complexity 2 always reduces to 1


# -- knots ----------------------------------------------------------------------------------------
def _falls(node) -> bool:
    return _N in _analyse(node).exits


class _Program:
    def __init__(self):
        self.next, self.arcs = 1, []

    def slot(self):
        value, self.next = self.next, self.next + 1
        return value

    def arc(self, source, target):
        if source is None or target is None or source == target:
            return
        self.arcs.append((min(source, target), max(source, target)))

    def number(self, node, scope):
        if node.kind == "seq":
            for kid in node.kids:
                self.number(kid, scope)
            return
        scope[id(node)] = self.slot()
        if node.kind in ("bare", "label"):
            self.number(node.kids[0], scope)
        elif node.kind == "if":
            self.number(node.kids[0], scope)
            if len(node.kids) > 1:
                if _falls(node.kids[0]):
                    scope[("goto", id(node))] = self.slot()
                self.number(node.kids[1], scope)
        elif node.kind == "loop":
            self.number(node.kids[0], scope)
            if _falls(node.kids[0]):
                scope[("goto", id(node))] = self.slot()
        elif node.kind == "when":
            for body in node.kids:
                scope[("case", id(body))] = self.next
                self.number(body, scope)
        elif node.kind == "try":
            head, catches, finals = node.kids
            scope[("try", id(node))] = self.next
            self.number(head, scope)
            for index, clause in enumerate(catches.kids):
                if _falls(head if index == 0 else catches.kids[index - 1]):
                    scope[("goto", id(clause))] = self.slot()
                scope[("catch", id(clause))] = self.next
                self.number(clause, scope)
            for block in finals.kids:
                self.number(block, scope)

    def start(self, node, scope):
        return scope.get(id(node))

    def draw(self, node, scope, after, exit_slot, breaks, continues):
        kind = node.kind
        if kind == "seq":
            for index, statement in enumerate(node.kids):
                following = self.start(node.kids[index + 1], scope) if index + 1 < len(node.kids) else after
                self.draw(statement, scope, following, exit_slot, breaks, continues)
            return
        here = scope.get(id(node))
        if kind == "bare":
            self.draw(node.kids[0], scope, after, exit_slot, breaks, continues)
        elif kind == "label":
            inner = node.kids[0]
            self.draw(inner, scope, after, exit_slot, {**breaks, node.name: after},
                      {**continues, node.name: self.start(inner, scope)})
        elif kind == "if":
            if len(node.kids) > 1:
                self.arc(here, self.start(node.kids[1], scope))
                self.arc(scope.get(("goto", id(node))), after)
                self.draw(node.kids[1], scope, after, exit_slot, breaks, continues)
            else:
                self.arc(here, after)
            self.draw(node.kids[0], scope, after, exit_slot, breaks, continues)
        elif kind == "loop":
            body, goto = node.kids[0], scope.get(("goto", id(node)))
            if node.flag:                                                 # do-while
                self.arc(goto or here, self.start(body, scope))
            else:
                self.arc(here, after)
                self.arc(goto, here)
            self.draw(body, scope, goto or after, exit_slot, {**breaks, None: after}, {**continues, None: here})
        elif kind == "when":
            for body in node.kids:
                self.arc(here, scope.get(("case", id(body))))
            if not node.flag:
                self.arc(here, after)
            for body in node.kids:
                self.draw(body, scope, after, exit_slot, breaks, continues)
        elif kind == "try":
            head, catches, finals = node.kids
            for clause in catches.kids:
                self.arc(scope.get(("try", id(node))), scope.get(("catch", id(clause))))
                self.arc(scope.get(("goto", id(clause))), after)
                self.draw(clause, scope, after, exit_slot, breaks, continues)
            first_catch = (scope.get(("goto", id(catches.kids[0]))) or scope.get(("catch", id(catches.kids[0])))
                           if catches.kids else after)
            self.draw(head, scope, first_catch or after, exit_slot, breaks, continues)
            for block in finals.kids:
                self.draw(block, scope, after, exit_slot, breaks, continues)
        elif kind == "return":
            self.arc(here, exit_slot)
        elif kind == "break":
            self.arc(here, breaks.get(node.name))
        elif kind == "continue":
            self.arc(here, continues.get(node.name))


def knots(body) -> int:
    root = convert(body)
    program, scope = _Program(), {}
    program.number(root, scope)
    exit_slot = program.slot()
    program.draw(root, scope, exit_slot, exit_slot, {}, {})
    unique = sorted(set(program.arcs))
    return sum(1 for i, (a, b) in enumerate(unique) for c, d in unique[i + 1:] if a < c < b < d)
