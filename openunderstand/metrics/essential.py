"""Essential complexity -- ev(G), Cyclomatic after the structured parts collapse.

Understand's definition: "the cyclomatic complexity after iteratively replacing
all well structured control structures with a single statement... Any branches
into or out of a loop or decision will make the graph non-reducible."

Java has no `goto`, so every construct is structured *by construction* and the
only thing that can make one irreducible is a jump leaving it: a `return` out
of the middle of an `if`, a `break` out of a loop, a labelled `continue`. So
rather than build a control-flow graph and search it for primes, this walks the
statement tree once and asks of each construct: where can control be when it
leaves you? A construct with a single answer is well structured and collapses;
one with two is a branch out, and it and everything above it stay.

    ev = 1 + the decision points of every construct that does not collapse

Three rules are not guessable and were read off Understand, from three
hand-written fixtures of 80 methods (`und create -languages Java`):

  * **A `throw` is invisible.** "Not counting abnormal exits" is meant
    literally: `if (x > 0) throw new RuntimeException(); return x;` is
    Cyclomatic 3, Essential 1 -- the `if` still counts as a decision and still
    collapses, so the throw cannot be an exit out of it. Two of them in a row
    is still 1.

  * **A `return` ending a switch case is not a branch out.** A case terminates
    with `break` or with `return`, and Understand treats both as the case
    prime's normal end: a switch of three returning cases is Essential 1. A
    `return` from *inside* an `if` inside a case is a branch out, and then
    nothing in that method reduces at all -- that pair is `d2` at 1 and `d4` at
    4, on the same Cyclomatic 4.

  * **Essential is never 2.** Understand's own note: a graph of complexity 2 is
    always reducible to 1. A single guarded return scores 1, two score 3.
"""

from openunderstand.metrics import context

#: Where control can be when it leaves a statement. "N" is the statement after
#: it, "R" is the method's exit; a break or a continue carries its label.
_NORMAL = "N"
_RETURN = "R"


def _kids(ctx, prefix):
    return [
        c
        for c in (getattr(ctx, "children", None) or ())
        if type(c).__name__.startswith(prefix)
    ]


def _label_of(ctx):
    """The label a `L: while (...)` puts on the statement it wraps."""
    if type(ctx).__name__ != "Statement16Context":
        return None
    identifier = ctx.IDENTIFIER()
    return identifier.getText() if identifier is not None else None


def _jump_label(ctx):
    identifier = ctx.IDENTIFIER()
    return identifier.getText() if identifier is not None else None


class _Result:
    """What a statement contributes: where it goes, and what stays behind.

    `points` is the decision count of everything inside it that did not
    collapse -- 0 when the statement is wholly well structured.
    """

    __slots__ = ("exits", "structured", "points")

    def __init__(self, exits, structured=True, points=0):
        self.exits = exits
        self.structured = structured
        self.points = points


_RUNS = lambda: _Result({_NORMAL})  # noqa: E731


def _sequence(statements, label=None):
    """Fold a run of statements. Anything after an unconditional jump is dead."""
    exits, structured, points, reachable = set(), True, 0, True
    for statement in statements:
        result = _analyse(statement, label)
        structured &= result.structured
        points += result.points
        exits |= result.exits - {_NORMAL}
        if _NORMAL not in result.exits:
            reachable = False
            break
    if reachable:
        exits.add(_NORMAL)
    return _Result(exits, structured, points)


def _loop(body, label, decisions=1):
    """A while, for or do-while: reducible when nothing escapes its body."""
    inner = _analyse(body, None)
    consumed = {("B", None), ("B", label), ("C", None), ("C", label)}
    escaping = inner.exits - consumed - {_NORMAL}
    structured = inner.structured and not escaping
    return _Result(
        {_NORMAL} | escaping, structured, 0 if structured else decisions + inner.points
    )


def _analyse(ctx, label=None):
    if ctx is None:
        return _RUNS()
    name = type(ctx).__name__

    if name == "BlockContext":
        return _sequence(_kids(ctx, "BlockStatement"), label)
    if name.startswith("BlockStatement"):
        inner = _kids(ctx, "Statement")
        # A local variable or a local class declaration just runs; a nested
        # class's own methods are entities in their own right.
        return _analyse(inner[0], label) if inner else _RUNS()

    if name == "Statement0Context":  # bare block
        return _analyse(_kids(ctx, "Block")[0], label)
    if name == "Statement16Context":  # L: statement
        own = _label_of(ctx)
        inner = _analyse(_kids(ctx, "Statement")[0], own)
        exits = inner.exits - {("B", own)}
        return _Result(exits | {_NORMAL}, inner.structured, inner.points)

    if name == "Statement2Context":  # if / else
        branches = _kids(ctx, "Statement")
        then = _analyse(branches[0], None)
        other = _analyse(branches[1], None) if len(branches) > 1 else _RUNS()
        exits = then.exits | other.exits
        structured = then.structured and other.structured and exits == {_NORMAL}
        return _Result(
            exits, structured, 0 if structured else 1 + then.points + other.points
        )

    if name in ("Statement3Context", "Statement4Context"):  # for, while
        return _loop(_kids(ctx, "Statement")[0], label)
    if name == "Statement5Context":  # do-while
        return _loop(_kids(ctx, "Statement")[0], label)

    if name in ("Statement6Context", "Statement7Context"):  # try
        blocks = _kids(ctx, "Block")
        parts = [_analyse(blocks[0], None)] if blocks else [_RUNS()]
        catches = _kids(ctx, "CatchClause")
        parts += [_analyse(_kids(c, "Block")[0], None) for c in catches]
        finallys = _kids(ctx, "FinallyBlock")
        parts += [_analyse(_kids(f, "Block")[0], None) for f in finallys]
        exits = set().union(*(p.exits for p in parts))
        structured = all(p.structured for p in parts) and exits == {_NORMAL}
        return _Result(
            exits,
            structured,
            0 if structured else len(catches) + sum(p.points for p in parts),
        )

    if name == "Statement8Context":  # switch
        groups = _kids(ctx, "SwitchBlockStatementGroup")
        labels = _kids(ctx, "SwitchLabel") + [
            l for g in groups for l in _kids(g, "SwitchLabel")
        ]
        cases = sum(1 for l in labels if not l.getText().startswith("default"))
        has_default = len(labels) > cases
        exits, structured, points = set(), True, 0
        for group in groups:
            body = _sequence(_kids(group, "BlockStatement"), None)
            structured &= body.structured
            points += body.points
            leaving = body.exits - {("B", None), ("B", label)}
            # A case that always returns has terminated normally, exactly as
            # one ending in `break` has. Understand scores a switch of three
            # returning cases 1, and treating the return as an escape would
            # make it 4.
            if leaving == {_RETURN}:
                leaving = {_NORMAL}
            exits |= leaving if leaving else {_NORMAL}
        if not has_default:
            exits.add(_NORMAL)  # no case matched
        structured = structured and exits == {_NORMAL}
        return _Result(
            exits or {_NORMAL}, structured, 0 if structured else cases + points
        )

    if name == "Statement9Context":  # synchronized
        return _analyse(_kids(ctx, "Block")[0], label)

    if name == "Statement10Context":  # return
        return _Result({_RETURN})
    if name == "Statement11Context":  # throw
        # An abnormal exit, and the metric's definition excludes those. Read
        # off Understand: `if (x > 0) throw ...; return x;` is Essential 1, so
        # the throw cannot be a second way out of the `if`.
        return _RUNS()
    if name == "Statement12Context":  # break
        return _Result({("B", _jump_label(ctx))})
    if name == "Statement13Context":  # continue
        return _Result({("C", _jump_label(ctx))})
    return _RUNS()


def essential(ent_model=None):
    """Essential complexity of one method or constructor."""
    if ent_model is None:
        return 0
    if context.declares_without_body(ent_model):
        return 0
    body = context.method_body(ent_model)
    if body is None:
        return 1
    value = 1 + _analyse(body).points
    # "You never get 2 since a graph with complexity 2 is always reducible to a
    # graph with complexity 1." -- Understand's own description of the metric.
    return 1 if value == 2 else value


def demo():
    """Every method of the three fixtures, against Understand's number for it."""
    from antlr4 import CommonTokenStream, InputStream

    from openunderstand.gen.javaLabeled.JavaLexer import JavaLexer
    from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled

    cases = [
        # Structured: every one of these is 1 however deep it nests.
        ("{ }", 1),
        ("{ int a = 1; a++; }", 1),
        ("{ if (x>0) { x++; } }", 1),
        ("{ if (x>0) { x++; } else { x--; } }", 1),
        ("{ while (x>0) { x--; } }", 1),
        ("{ do { x--; } while (x>0); }", 1),
        ("{ for (int i=0;i<x;i++) { x--; } }", 1),
        ("{ if (x>0) { if (x>1) { x++; } } if (x>2) { x++; } return x; }", 1),
        ("{ while (x>0) { x--; } while (x<0) { x++; } return x; }", 1),
        ("{ switch (x) { case 1: x++; break; case 2: x--; break; } return x; }", 1),
        (
            "{ try { x++; } catch (Exception e) { x--; } if (x>1) { x++; } return x; }",
            1,
        ),
        # A throw is an abnormal exit and does not count as a way out.
        ("{ if (x>0) throw new RuntimeException(); return 1; }", 1),
        ("{ if (x>0) { x++; } if (x>1) throw new RuntimeException(); return x; }", 1),
        (
            "{ if (x>0) throw new RuntimeException();"
            " if (x>1) throw new RuntimeException(); return x; }",
            1,
        ),
        ("{ if (x>0) { return 1; } throw new RuntimeException(); }", 1),
        # One guarded return is 1, because Essential is never 2.
        ("{ if (x>0) return 1; return 2; }", 1),
        ("{ if (x>0) { x++; } if (x>1) { return 1; } return 2; }", 1),
        ("{ if (x>0) return 1; if (x>1) { x++; } return 2; }", 1),
        ("{ if (x>0) { x++; return 1; } if (x>1) { x++; } return 2; }", 1),
        ("{ if (x>0) { return 1; } else { x--; } if (x>1) { x++; } return 2; }", 1),
        ("{ if (x>0) return; x++; }", 1),
        # Both branches leaving the same way is still one exit.
        ("{ if (x>0) { return 1; } else { return 2; } }", 1),
        ("{ if (x>0) { x++; } if (x>1) { return 1; } else { return 2; } }", 1),
        ("{ try { return 1; } catch (Exception e) { return 2; } }", 1),
        (
            "{ if (x>0) { x++; } try { return 1; } catch (Exception e) { return 2; } }",
            1,
        ),
        ("{ try { return 1; } catch (Exception e) { return 2; } finally { x++; } }", 1),
        # A returning switch case terminates normally.
        ("{ switch (x) { case 1: return 1; case 2: return 2; } return 3; }", 1),
        ("{ switch (x) { case 1: return 1; default: return 2; } }", 1),
        (
            "{ switch (x) { case 1: return 1; case 2: return 2; case 3: return 3; }"
            " return 4; }",
            1,
        ),
        (
            "{ if (x>0) { x++; } switch (x) { case 1: return 1; case 2: return 2; }"
            " return 3; }",
            1,
        ),
        (
            "{ if (x>0) { x++; } switch (x) { case 1: return 1; default: return 2; } }",
            1,
        ),
        # Two guarded returns do not reduce, and it goes 1 -> 3 -> 4.
        ("{ if (x>0) return 1; if (x>1) return 2; return 3; }", 3),
        ("{ if (x>0) return 1; if (x>1) return 2; if (x>2) { x++; } return 3; }", 3),
        ("{ if (x>0) return 1; if (x>1) return 2; if (x>2) return 3; return 4; }", 4),
        (
            "{ if (x==1) return 1; else if (x==2) return 2;"
            " else if (x==3) return 3; return 4; }",
            4,
        ),
        ("{ if (x==1) return 1; else if (x==2) return 2; else return 3; }", 3),
        # A return from inside a nested decision is a branch out of both.
        ("{ if (x>0) { if (x>1) { return 1; } x++; } return 2; }", 3),
        ("{ if (x>0) { if (x>1) { return 1; } } return 2; }", 3),
        ("{ if (x>0) { x++; if (x>1) { return 1; } } return 2; }", 3),
        (
            "{ if (x>0) { if (x>1) { if (x>2) { return 3; } return 2; } return 1; }"
            " return 0; }",
            4,
        ),
        # ... including out of a loop, or a switch case.
        ("{ while (x>0) { if (x==5) return 1; x--; } return 2; }", 3),
        ("{ while (x>0) { if (x==5) return 1; x--; } if (x>1) { x++; } return 2; }", 3),
        ("{ for (int i=0;i<x;i++) { if (i==3) return i; } return -1; }", 3),
        ("{ while (x>0) { if (x==5) break; x--; } return 1; }", 3),
        ("{ while (x>0) { if (x==5) continue; x--; } return 1; }", 3),
        (
            "{ for (int i=0;i<x;i++) { if (i==3) break; } if (x>1) { x++; } return x; }",
            3,
        ),
        (
            "{ switch (x) { case 1: if (x>5) return 1; break; case 2: break; }"
            " return 2; }",
            4,
        ),
        (
            "{ outer: for (int i=0;i<x;i++) { for (int j=0;j<x;j++)"
            " { if (j==2) continue outer; } } return x; }",
            4,
        ),
    ]
    for source, expected in cases:
        parser = JavaParserLabeled(CommonTokenStream(JavaLexer(InputStream(source))))
        value = 1 + _analyse(parser.block()).points
        got = 1 if value == 2 else value
        assert got == expected, f"{source!r}: {got} != {expected}"
    print(f"essential: {len(cases)} cases ok")


if __name__ == "__main__":
    demo()
