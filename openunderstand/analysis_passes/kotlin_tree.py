"""Parse-tree helpers shared by the Kotlin passes.

Rules are named from the generated context class, so they work the same on a
tree built by the Python runtime and on one the C++ accelerator built.
"""

from __future__ import annotations

from antlr4.tree.Tree import TerminalNode

_RULE_CACHE: dict = {}


def rule(ctx) -> str | None:
    """The grammar rule a context came from (``None`` for a token)."""
    if isinstance(ctx, TerminalNode):
        return None
    cls = type(ctx)
    name = _RULE_CACHE.get(cls)
    if name is None:
        raw = cls.__name__[: -len("Context")]
        name = _RULE_CACHE[cls] = raw[0].lower() + raw[1:]
    return name


def children(ctx, name: str | None = None):
    return [
        c for c in (ctx.children or []) if name is None or rule(c) == name
    ]


def first(ctx, name: str):
    for c in ctx.children or []:
        if rule(c) == name:
            return c
    return None


def find(ctx, name: str):
    """The first descendant of rule ``name`` in pre-order, or ``None``."""
    for c in ctx.children or []:
        if rule(c) == name:
            return c
        if not isinstance(c, TerminalNode):
            hit = find(c, name)
            if hit is not None:
                return hit
    return None


def has_token(ctx, text: str) -> bool:
    return any(isinstance(c, TerminalNode) and c.getText() == text for c in ctx.children or [])


def has_equals(entry) -> bool:
    """Whether a destructuring entry is the name-based ``(val a = name)`` form."""
    return any(isinstance(c, TerminalNode) and c.getText() == "=" for c in entry.children or [])


def source_text(ctx) -> str:
    start, stop = ctx.start, ctx.stop
    if stop is None:
        return ""
    return start.getInputStream().getText(start.start, stop.stop)


def name_pos(simple_identifier) -> tuple[str, int, int]:
    token = simple_identifier.start
    return token.text.strip("`"), token.line, token.column


def named_type(type_ctx):
    """``(dotted name, line, col)`` of the class a type names, or ``None``.

    The position is the last identifier, where Understand anchors a ``Typed``.
    A nullable ``T?`` and a parenthesised type name ``T``; a function type, an
    intersection and ``dynamic`` name no class, and type arguments are left to a
    later pass.
    """
    if type_ctx is None:
        return None
    ctx = type_ctx
    for _ in range(8):
        name = rule(ctx)
        if name == "receiverType":
            inner = None
            for c in ctx.children or []:
                if rule(c) in ("parenthesizedType", "nullableType", "typeReference"):
                    inner = c
            ctx = inner
        elif name == "type_":
            if first(ctx, "type_") is not None:  # `A & B`
                return None
            inner = None
            for c in ctx.children or []:
                if rule(c) in ("parenthesizedType", "nullableType", "typeReference", "functionType"):
                    inner = c
            if inner is None:
                return None
            ctx = inner
        elif name == "parenthesizedType":
            ctx = first(ctx, "type_")
        elif name == "nullableType":
            ctx = first(ctx, "typeReference") or first(ctx, "parenthesizedType")
        elif name == "typeReference":
            user = first(ctx, "userType")
            if user is None:
                return None
            parts = children(user, "simpleUserType")
            names = [name_pos(first(p, "simpleIdentifier"))[0] for p in parts]
            _, line, col = name_pos(first(parts[-1], "simpleIdentifier"))
            return ".".join(names), line, col
        else:
            return None
        if ctx is None:
            return None
    return None




def name_of(ctx) -> str | None:
    """The dotted class name a type (or receiver type) names, or ``None``."""
    named = named_type(ctx)
    return named[0] if named else None


def user_type_name(user_type) -> str:
    """``a.b.C`` for a userType, ignoring type arguments."""
    return ".".join(
        name_pos(first(p, "simpleIdentifier"))[0] for p in children(user_type, "simpleUserType")
    )
