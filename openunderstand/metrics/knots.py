"""Knots -- pairs of control-flow jumps that cross each other.

Understand: "If a piece of code has arrowed lines indicating where every jump in
the flow of control occurs, a knot is defined as where two such lines cross each
other."

So lay the method out as a numbered sequence of slots, draw each jump as an arc
between two slot numbers, and count the pairs that interleave -- `a < c < b < d`
for arcs spanning `[a,b]` and `[c,d]`. Two arcs that share an endpoint, or that
nest one inside the other, do not cross.

The slots are the statements in source order plus the jumps a compiler would
insert and the source does not spell:

  * an `if` with an `else` gets one after the then-branch, to skip the else --
    without it `if (a) { x++; } else { x--; }` has a single arc and scores 0,
    where Understand scores 1;
  * a loop gets one at the end of its body, for the branch back to the header.

Neither is allocated when the branch cannot reach it -- a then-branch ending in
`return` never jumps over the else, and that is what separates
`if (a) return 1; else if (b) return 2; else return 3;` at 2 from the same
shape with falling-through branches.

A `throw` draws no arc: it is an abnormal exit, which this metric's family
excludes. Read off the same three fixtures as `essential.py` -- 80 methods, of
which these reproduce every Knots value.
"""

from openunderstand.metrics import context
from openunderstand.metrics.essential import _analyse as _flow


def _kids(ctx, prefix):
    return [c for c in (getattr(ctx, "children", None) or ())
            if type(c).__name__.startswith(prefix)]


def _falls_through(ctx):
    """Whether control can reach the statement after this one."""
    return "N" in _flow(ctx).exits


class _Program:
    """Statements flattened to numbered slots, with the arcs between them."""

    def __init__(self):
        self.next = 1
        self.arcs = []

    def slot(self):
        value = self.next
        self.next += 1
        return value

    def arc(self, source, target):
        if source is None or target is None or source == target:
            return
        self.arcs.append((min(source, target), max(source, target)))

    # -- pass 1: assign a slot to every statement, in source order ------------

    def number(self, ctx, scope):
        """Assign slots to `ctx` and its children. `scope` collects extras."""
        name = type(ctx).__name__
        if name == "BlockContext":
            for block_statement in _kids(ctx, "BlockStatement"):
                inner = _kids(block_statement, "Statement")
                if inner:
                    self.number(inner[0], scope)
                else:
                    scope[id(block_statement)] = self.slot()
            return
        here = self.slot()
        scope[id(ctx)] = here

        if name == "Statement0Context":                       # bare block
            self.number(_kids(ctx, "Block")[0], scope)
        elif name == "Statement16Context":                    # L: statement
            self.number(_kids(ctx, "Statement")[0], scope)
        elif name == "Statement2Context":                     # if / else
            branches = _kids(ctx, "Statement")
            self.number(branches[0], scope)
            if len(branches) > 1:
                if _falls_through(branches[0]):
                    scope[("goto", id(ctx))] = self.slot()
                self.number(branches[1], scope)
        elif name in ("Statement3Context", "Statement4Context",
                      "Statement5Context"):                   # for, while, do
            body = _kids(ctx, "Statement")[0]
            self.number(body, scope)
            if _falls_through(body):
                scope[("goto", id(ctx))] = self.slot()
        elif name == "Statement9Context":                     # synchronized
            self.number(_kids(ctx, "Block")[0], scope)
        elif name == "Statement8Context":                     # switch
            for group in _kids(ctx, "SwitchBlockStatementGroup"):
                scope[("case", id(group))] = self.next
                for block_statement in _kids(group, "BlockStatement"):
                    inner = _kids(block_statement, "Statement")
                    if inner:
                        self.number(inner[0], scope)
                    else:
                        scope[id(block_statement)] = self.slot()
        elif name in ("Statement6Context", "Statement7Context"):   # try
            blocks = _kids(ctx, "Block")
            catches = _kids(ctx, "CatchClause")
            finallys = _kids(ctx, "FinallyBlock")
            if blocks:
                scope[("try", id(ctx))] = self.next
                self.number(blocks[0], scope)
            for index, clause in enumerate(catches):
                previous = blocks[0] if index == 0 else _kids(
                    catches[index - 1], "Block")[0]
                if _falls_through(previous):
                    scope[("goto", id(clause))] = self.slot()
                scope[("catch", id(clause))] = self.next
                self.number(_kids(clause, "Block")[0], scope)
            for block in finallys:
                self.number(_kids(block, "Block")[0], scope)

    # -- pass 2: draw the arcs, now that every slot number is known -----------

    def draw(self, ctx, scope, after, exit_slot, breaks, continues):
        name = type(ctx).__name__
        if name == "BlockContext":
            statements = []
            for block_statement in _kids(ctx, "BlockStatement"):
                inner = _kids(block_statement, "Statement")
                statements.append(inner[0] if inner else block_statement)
            for index, statement in enumerate(statements):
                nxt = (self.start(statements[index + 1], scope)
                       if index + 1 < len(statements) else after)
                if type(statement).__name__.startswith("Statement"):
                    self.draw(statement, scope, nxt, exit_slot, breaks, continues)
            return
        here = scope.get(id(ctx))

        if name == "Statement0Context":
            self.draw(_kids(ctx, "Block")[0], scope, after, exit_slot,
                      breaks, continues)
        elif name == "Statement16Context":
            label = ctx.IDENTIFIER().getText() if ctx.IDENTIFIER() else None
            inner = _kids(ctx, "Statement")[0]
            self.draw(inner, scope, after, exit_slot,
                      {**breaks, label: after},
                      {**continues, label: self.start(inner, scope)})
        elif name == "Statement2Context":                     # if / else
            branches = _kids(ctx, "Statement")
            if len(branches) > 1:
                self.arc(here, self.start(branches[1], scope))
                self.arc(scope.get(("goto", id(ctx))), after)
                self.draw(branches[1], scope, after, exit_slot, breaks, continues)
            else:
                self.arc(here, after)
            self.draw(branches[0], scope, after, exit_slot, breaks, continues)
        elif name in ("Statement3Context", "Statement4Context"):   # for, while
            body = _kids(ctx, "Statement")[0]
            self.arc(here, after)
            self.arc(scope.get(("goto", id(ctx))), here)
            self.draw(body, scope, scope.get(("goto", id(ctx))) or after, exit_slot,
                      {**breaks, None: after},
                      {**continues, None: here})
        elif name == "Statement5Context":                     # do-while
            body = _kids(ctx, "Statement")[0]
            self.arc(scope.get(("goto", id(ctx))) or here,
                     self.start(body, scope))
            self.draw(body, scope, scope.get(("goto", id(ctx))) or after, exit_slot,
                      {**breaks, None: after},
                      {**continues, None: here})
        elif name == "Statement9Context":                     # synchronized
            self.draw(_kids(ctx, "Block")[0], scope, after, exit_slot,
                      breaks, continues)
        elif name == "Statement8Context":                     # switch
            groups = _kids(ctx, "SwitchBlockStatementGroup")
            labels = _kids(ctx, "SwitchLabel") + [
                l for g in groups for l in _kids(g, "SwitchLabel")]
            has_default = any(l.getText().startswith("default") for l in labels)
            for group in groups:
                self.arc(here, scope.get(("case", id(group))))
            if not has_default:
                self.arc(here, after)
            inner_breaks = {**breaks, None: after}
            for index, group in enumerate(groups):
                statements = []
                for block_statement in _kids(group, "BlockStatement"):
                    child = _kids(block_statement, "Statement")
                    statements.append(child[0] if child else block_statement)
                nxt = (scope.get(("case", id(groups[index + 1])))
                       if index + 1 < len(groups) else after)
                for position, statement in enumerate(statements):
                    following = (self.start(statements[position + 1], scope)
                                 if position + 1 < len(statements) else nxt)
                    if type(statement).__name__.startswith("Statement"):
                        self.draw(statement, scope, following, exit_slot,
                                  inner_breaks, continues)
        elif name in ("Statement6Context", "Statement7Context"):   # try
            blocks = _kids(ctx, "Block")
            catches = _kids(ctx, "CatchClause")
            finallys = _kids(ctx, "FinallyBlock")
            body_start = scope.get(("try", id(ctx)))
            for clause in catches:
                self.arc(body_start, scope.get(("catch", id(clause))))
                self.arc(scope.get(("goto", id(clause))), after)
                self.draw(_kids(clause, "Block")[0], scope, after, exit_slot,
                          breaks, continues)
            if blocks:
                first_catch = (scope.get(("goto", id(catches[0])))
                               or scope.get(("catch", id(catches[0])))
                               if catches else after)
                self.draw(blocks[0], scope, first_catch or after, exit_slot,
                          breaks, continues)
            for block in finallys:
                self.draw(_kids(block, "Block")[0], scope, after, exit_slot,
                          breaks, continues)
        elif name == "Statement10Context":                    # return
            self.arc(here, exit_slot)
        elif name == "Statement12Context":                    # break
            identifier = ctx.IDENTIFIER()
            self.arc(here, breaks.get(
                identifier.getText() if identifier else None))
        elif name == "Statement13Context":                    # continue
            identifier = ctx.IDENTIFIER()
            self.arc(here, continues.get(
                identifier.getText() if identifier else None))
        # Statement11 is `throw` -- an abnormal exit, and it draws nothing.

    def start(self, ctx, scope):
        return scope.get(id(ctx))


def _crossings(arcs):
    """Pairs of arcs that interleave: a < c < b < d."""
    unique = sorted(set(arcs))
    total = 0
    for index, (a, b) in enumerate(unique):
        for c, d in unique[index + 1:]:
            if a < c < b < d:
                total += 1
    return total


def count_knots(body):
    """Knots of an already-parsed method body."""
    program = _Program()
    scope = {}
    program.number(body, scope)
    exit_slot = program.slot()
    program.draw(body, scope, exit_slot, exit_slot, {}, {})
    return _crossings(program.arcs)


def knot(ent_model=None):
    if ent_model is None:
        return 0
    if context.declares_without_body(ent_model):
        return 0
    body = context.method_body(ent_model)
    return count_knots(body) if body is not None else 0


def essential_knots(ent_model=None):
    """"Knots after structured programming constructs have been removed."

    A method whose constructs all collapse has no jumps left to cross, and
    Understand reports 0 for every one of them; when something does not
    collapse, its knots survive. Measured on JSON: 0.965 against Understand,
    where answering 0 unconditionally -- which is what this used to do, for
    every entity -- scores 0.932.

    Understand reports the same number for Max and Min on 1,023 of JSON's
    1,034 methods, and nothing here distinguishes them: a method has one body,
    so there is no set to take the extremes of.
    """
    if ent_model is None:
        return 0
    from openunderstand.metrics.essential import essential

    return 0 if essential(ent_model) == 1 else knot(ent_model)


def demo():
    """Every Knots value the three Understand fixtures report."""
    from antlr4 import CommonTokenStream, InputStream

    from openunderstand.gen.javaLabeled.JavaLexer import JavaLexer
    from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled

    cases = [
        ("{ }", 0),
        ("{ int a = 1; a++; }", 0),
        ("{ if (x>0) { x++; } }", 0),
        ("{ if (x>0) { x++; } else { x--; } }", 1),
        ("{ if (x>0) { x++; } else if (x<0) { x--; } }", 1),
        ("{ if (x>0) { if (x<5) { x++; } } }", 0),
        ("{ if (x>0) { x++; } if (x<0) { x--; } }", 0),
        ("{ while (x>0) { x--; } }", 0),
        ("{ do { x--; } while (x>0); }", 0),
        ("{ for (int i=0;i<x;i++) { x--; } }", 0),
        ("{ for (int i : a) { i++; } }", 0),
        ("{ while (x>0) { if (x<5) { x++; } } }", 0),
        ("{ switch (x) { case 1: x++; break; case 2: x--; break; } }", 1),
        ("{ switch (x) { case 1: x++; break; default: x--; break; } }", 1),
        ("{ switch (x) { case 1: break; case 2: break; default: break; } }", 3),
        ("{ try { x++; } catch (Exception e) { x--; } }", 1),
        ("{ try { x++; } catch (RuntimeException e) { x--; }"
         " catch (Exception e) { x = 0; } }", 3),
        ("{ try { x++; } finally { x--; } }", 0),
        ("{ try { x++; } catch (Exception e) { x--; } finally { x = 0; } }", 1),
        ("{ return x > 0 ? 1 : 2; }", 0),
        ("{ synchronized (this) { x++; } }", 0),
        ("{ outer: while (x>0) { x--; } }", 0),
        ("{ assert x > 0; }", 0),
        ("{ if (x>0) { throw new RuntimeException(); } }", 0),
        ("{ boolean b = x > 0 && x < 5; }", 0),
        # Early exits.
        ("{ if (x>0) return 1; return 2; }", 1),
        ("{ if (x>0) return 1; if (x>1) return 2; return 3; }", 2),
        ("{ if (x>0) { return 1; } else { return 2; } }", 1),
        ("{ if (x>0) { x++; } return x; }", 0),
        ("{ if (x>0) return; x++; }", 1),
        ("{ if (x==1) return 1; else if (x==2) return 2;"
         " else if (x==3) return 3; return 4; }", 3),
        ("{ if (x==1) return 1; else if (x==2) return 2; else return 3; }", 2),
        ("{ while (x>0) { if (x==5) return 1; x--; } return 2; }", 3),
        ("{ while (x>0) { x--; } return 2; }", 0),
        ("{ if (x>0) throw new RuntimeException(); return 1; }", 0),
        ("{ while (x>0) { if (x==5) break; x--; } return 1; }", 2),
        ("{ while (x>0) { if (x==5) continue; x--; } return 1; }", 1),
        ("{ if (x>0) { x++; } if (x>1) { x++; } return x; }", 0),
        ("{ if (x>0) return 1; if (x>1) { x++; } if (x>2) { x++; } return x; }", 1),
        ("{ if (x>0) { if (x>1) { return 1; } x++; } return 2; }", 2),
        ("{ for (int i=0;i<x;i++) { if (i==3) return i; } return -1; }", 3),
        ("{ if (x>0){ if(x>1){ if(x>2){ return 3; } return 2; } return 1; }"
         " return 0; }", 6),
        ("{ if (x>0) { return 1; } throw new RuntimeException(); }", 1),
    ]
    for source, expected in cases:
        parser = JavaParserLabeled(CommonTokenStream(JavaLexer(InputStream(source))))
        got = count_knots(parser.block())
        assert got == expected, f"{source!r}: {got} != {expected}"
    print(f"knots: {len(cases)} cases ok")


if __name__ == "__main__":
    demo()
