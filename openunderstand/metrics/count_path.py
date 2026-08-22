"""CountPath and CountPathLog -- unique paths through a method body.

Understand's name for this is NPATH, but its rule is *not* Nejmeh's: boolean
operators do not count. `if (x > 0 && x < 5)` and `if (x > 0)` both score 2, and
a ternary scores 1. Nor is a body simply the product of its statements -- a
`return` ends the path it is on, so the statements after it do not multiply with
it. `JSONObject.convertValue` is sixteen guarded returns in a row: 16 by
Understand's count, and 360 by the product.

Both rules were read off hand-written fixtures (`und create -languages Java` on
one file, 22 and 31 methods), which is the only thing that answers what the rule
is -- the benchmark says a number is wrong and never why.

So each construct carries a *pair*: how many ways it can complete and fall
through to the next statement, and how many paths leave the body from inside it.

    statement           complete 1, exits 0
    return/throw        complete 0, exits 1
    break/continue      complete 0, exits 1     -- measured, not assumed
    sequence            alive *= complete, exits += alive * exits, in order
    if                  complete(then) + complete(else, or 1), exits sum
    while / for         complete(body) + 1, exits(body)
    do-while            complete(body)          -- the body always runs
    switch              sum over groups, plus 1 when there is no default
    try                 try + catches, all times complete(finally)
    synchronized/label  whatever it wraps

and the answer is `exits + complete` of the body as a whole.

An anonymous class body hangs off an *expression*, and this only ever walks
statements, so a listener inside a method is unreachable by construction; a
named local class arrives as a `localTypeDeclaration` and counts 1.

`CountPathLog` is documented as "log10, truncated" and is not: Understand
reports 1 for a path count of 4, and 0 for 3. It is log10 *rounded*.
"""

import math

from openunderstand.metrics import context

_MAX = 10**9  # A path count is a product; deep nesting overflows meaning.

#: `complete, exits` for a statement that just runs, and for one that leaves.
_RUNS = (1, 0)
_LEAVES = (0, 1)


def _kids(ctx, prefix):
    return [
        c
        for c in (getattr(ctx, "children", None) or ())
        if type(c).__name__.startswith(prefix)
    ]


def _sequence(statements):
    """Fold `complete, exits` along a run of statements."""
    alive, exits = 1, 0
    for statement in statements:
        complete, escaped = _flow(statement)
        exits = min(exits + alive * escaped, _MAX)
        alive = min(alive * complete, _MAX)
    return alive, exits


def _flow(ctx):
    """`complete, exits` for one statement, block or block statement."""
    if ctx is None:
        return _RUNS
    name = type(ctx).__name__

    if name == "BlockContext":
        return _sequence(_kids(ctx, "BlockStatement"))
    if name.startswith("BlockStatement"):
        # localVariableDeclaration and localTypeDeclaration both just run.
        inner = _kids(ctx, "Statement")
        return _flow(inner[0]) if inner else _RUNS

    if name == "Statement0Context":  # bare block
        return _flow(_kids(ctx, "Block")[0])
    if name == "Statement2Context":  # if / else
        branches = _kids(ctx, "Statement")
        then_c, then_e = _flow(branches[0])
        else_c, else_e = _flow(branches[1]) if len(branches) > 1 else _RUNS
        return min(then_c + else_c, _MAX), min(then_e + else_e, _MAX)
    if name in ("Statement3Context", "Statement4Context"):  # for, while
        body_c, body_e = _flow(_kids(ctx, "Statement")[0])
        return min(body_c + 1, _MAX), body_e
    if name == "Statement5Context":  # do-while
        return _flow(_kids(ctx, "Statement")[0])
    if name in ("Statement6Context", "Statement7Context"):  # try
        blocks = _kids(ctx, "Block")
        complete, exits = _flow(blocks[0]) if blocks else _RUNS
        for clause in _kids(ctx, "CatchClause"):
            catch_c, catch_e = _flow(_kids(clause, "Block")[0])
            complete, exits = complete + catch_c, exits + catch_e
        for block in _kids(ctx, "FinallyBlock"):
            complete *= _flow(_kids(block, "Block")[0])[0]
        return min(complete, _MAX), min(exits, _MAX)
    if name == "Statement8Context":  # switch
        groups = _kids(ctx, "SwitchBlockStatementGroup")
        complete = exits = 0
        for group in groups:
            group_c, group_e = _sequence(_kids(group, "BlockStatement"))
            complete, exits = complete + group_c, exits + group_e
        labels = _kids(ctx, "SwitchLabel") + [
            label for group in groups for label in _kids(group, "SwitchLabel")
        ]
        if not any(label.getText().startswith("default") for label in labels):
            complete += 1  # falling straight out of the switch is a path
        return min(complete, _MAX), min(exits, _MAX)
    if name == "Statement9Context":  # synchronized
        return _flow(_kids(ctx, "Block")[0])
    if name == "Statement16Context":  # label: statement
        return _flow(_kids(ctx, "Statement")[0])
    if name in (
        "Statement10Context",
        "Statement11Context",  # return, throw
        "Statement12Context",
        "Statement13Context",
    ):  # break, continue
        return _LEAVES
    return _RUNS


def count_path(ent_model):
    # A body-less declaration is 0, not the 1 an empty body earns.
    if context.declares_without_body(ent_model):
        return 0
    complete, exits = _flow(context.method_body(ent_model))
    return min(complete + exits, _MAX) or 1


def count_path_log(ent_model):
    return round(math.log10(max(count_path(ent_model), 1)))


def demo():
    """Every rule above, checked against Understand's number for the method."""
    from antlr4 import CommonTokenStream, InputStream

    from openunderstand.gen.javaLabeled.JavaLexer import JavaLexer
    from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled

    cases = [
        # No early exit: the body is the product of its statements.
        ("{ }", 1),
        ("{ int a = 1; int b = 2; a = b; }", 1),
        ("{ if (x > 0) { x++; } }", 2),
        ("{ if (x > 0) { x++; } else { x--; } }", 2),
        ("{ if (x > 0 && x < 5) { x++; } }", 2),
        ("{ if (x > 0) { x++; } if (x < 0) { x--; } }", 4),
        ("{ if (x>0){x++;} if(x>1){x++;} if(x>2){x++;} }", 8),
        ("{ if (x > 0) { if (x < 5) { x++; } } }", 3),
        ("{ if (x > 0) { x++; } else if (x < 0) { x--; } }", 3),
        ("{ while (x > 0) { x--; } }", 2),
        ("{ do { x--; } while (x > 0); }", 1),
        ("{ for (int i = 0; i < x; i++) { x--; } }", 2),
        ("{ for (int i : a) { i++; } }", 2),
        ("{ while (x > 0) { if (x < 5) { x++; } } }", 3),
        ("{ switch (x) { case 1: x++; break; case 2: x--; break; } }", 3),
        ("{ switch (x) { case 1: x++; break; default: x--; break; } }", 2),
        ("{ switch (x) { case 1: break; case 2: break; default: break; } }", 3),
        ("{ try { x++; } catch (Exception e) { x--; } }", 2),
        (
            "{ try { x++; } catch (RuntimeException e) { x--; }"
            " catch (Exception e) { x = 0; } }",
            3,
        ),
        ("{ try { x++; } finally { x--; } }", 1),
        ("{ try { x++; } catch (Exception e) { x--; } finally { x = 0; } }", 2),
        ("{ return x > 0 ? 1 : 2; }", 1),
        ("{ synchronized (this) { x++; } }", 1),
        ("{ outer: while (x > 0) { x--; } }", 2),
        ("{ assert x > 0; }", 1),
        # An early exit ends its path instead of multiplying with what follows.
        ("{ if (x > 0) return 1; return 2; }", 2),
        ("{ if (x > 0) return 1; if (x > 1) return 2; return 3; }", 3),
        ("{ if (x > 0) { return 1; } else { return 2; } }", 2),
        ("{ if (x > 0) { x++; } return x; }", 2),
        ("{ if (x > 0) return; x++; }", 2),
        (
            "{ if (x == 1) return 1; else if (x == 2) return 2;"
            " else if (x == 3) return 3; return 4; }",
            4,
        ),
        ("{ if (x == 1) return 1; else if (x == 2) return 2; else return 3; }", 3),
        ("{ while (x > 0) { if (x == 5) return 1; x--; } return 2; }", 3),
        ("{ while (x > 0) { x--; } return 2; }", 2),
        ("{ if (x > 0) throw new RuntimeException(); return 1; }", 2),
        ("{ while (x > 0) { if (x == 5) break; x--; } return 1; }", 3),
        ("{ while (x > 0) { if (x == 5) continue; x--; } return 1; }", 3),
        ("{ switch (x) { case 1: return 1; case 2: return 2; } return 3; }", 3),
        ("{ switch (x) { case 1: return 1; default: return 2; } }", 2),
        ("{ try { return 1; } catch (Exception e) { return 2; } }", 2),
        ("{ if (x > 0) { x++; } if (x > 1) { x++; } return x; }", 4),
        (
            "{ if (x > 0) { x++; } if (x > 1) { x++; } if (x > 2) { x++; } return x; }",
            8,
        ),
        (
            "{ if (x > 0) return 1; if (x > 1) { x++; } if (x > 2) { x++; } return x; }",
            5,
        ),
        ("{ if (x > 0) { if (x > 1) { return 1; } x++; } return 2; }", 3),
        ("{ for (int i = 0; i < x; i++) { if (i == 3) return i; } return -1; }", 3),
        (
            "{ if (x>0){ if(x>1){ if(x>2){ return 3; } return 2; } return 1; } return 0; }",
            4,
        ),
        ("{ if (x > 0) { return 1; } throw new RuntimeException(); }", 2),
    ]
    for source, expected in cases:
        parser = JavaParserLabeled(CommonTokenStream(JavaLexer(InputStream(source))))
        complete, exits = _flow(parser.block())
        got = complete + exits or 1
        assert got == expected, f"{source!r}: {got} != {expected}"
    for paths, expected in ((1, 0), (2, 0), (3, 0), (4, 1), (8, 1), (100, 2)):
        assert round(math.log10(paths)) == expected, paths
    print(f"count_path: {len(cases)} cases ok")


if __name__ == "__main__":
    demo()
