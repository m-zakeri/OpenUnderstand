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


def _contra(projection) -> bool:
    """Whether a type argument is written ``in T``: reading through it yields ``Any``, not ``T``."""
    mods = first(projection, "typeProjectionModifiers")
    return mods is not None and "in" in [leaf.getText() for leaf in _leaves(mods)]


def _leaves(node):
    if not getattr(node, "children", None):
        yield node
    else:
        for c in node.children:
            yield from _leaves(c)


def type_expr(ctx, tparams=frozenset()):
    """A written type as a nested tuple, keeping its type arguments; ``None`` when it has none to keep.

    ``("c", "Map.Entry", (args...))`` is a class by name (as written, resolved later in the file that
    wrote it), ``("p", "T")`` a reference to a type parameter in ``tparams``, ``("fn", receiver,
    (parameters...), result)`` a function type, and ``"*"`` a star projection. Nullability, variance
    and annotations are dropped: they change what a value may be, not what it is.
    """
    if ctx is None:
        return None
    name = rule(ctx)
    if name in ("type_", "receiverType"):
        if name == "type_" and first(ctx, "type_") is not None:   # `A & B`
            return None
        for c in ctx.children or []:
            if rule(c) in ("parenthesizedType", "nullableType", "typeReference", "functionType"):
                return type_expr(c, tparams)
        return None
    if name == "parenthesizedType":
        return type_expr(first(ctx, "type_"), tparams)
    if name == "nullableType":
        return type_expr(first(ctx, "typeReference") or first(ctx, "parenthesizedType"), tparams)
    if name in ("typeReference", "userType"):
        user = ctx if name == "userType" else first(ctx, "userType")
        if user is None:
            return None
        parts = children(user, "simpleUserType")
        names = [name_pos(first(p, "simpleIdentifier"))[0] for p in parts]
        if len(names) == 1 and names[0] in tparams:
            bound = tparams.get(names[0]) if isinstance(tparams, dict) else None
            return ("p", names[0], bound) if bound else ("p", names[0])
        arguments = first(parts[-1], "typeArguments")
        args = tuple(
            "*" if not children(a, "type_") else (
                None if _contra(a) else type_expr(first(a, "type_"), tparams))      # `in T` reads as Any
            for a in (children(arguments, "typeProjection") if arguments is not None else [])
        )
        return ("c", ".".join(names), args)
    if name == "functionType":
        receiver = first(ctx, "receiverType")
        parameters = first(ctx, "functionTypeParameters")
        params = []
        for c in (parameters.children if parameters is not None else []) or []:
            if rule(c) == "parameter":
                params.append(type_expr(first(c, "type_"), tparams))
            elif rule(c) == "type_":
                params.append(type_expr(c, tparams))
        result = [c for c in ctx.children or [] if rule(c) == "type_"]
        return ("fn", type_expr(receiver, tparams) if receiver is not None else None, tuple(params),
                type_expr(result[-1], tparams) if result else None)
    return None
