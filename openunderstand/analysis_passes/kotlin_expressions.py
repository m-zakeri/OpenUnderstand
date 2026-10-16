"""Calls and name occurrences in Kotlin expressions: tree to facts.

Walks the expressions of a function body, an initialiser, an accessor or an
``init`` block and records, for every call and every simple or qualified name,
*what is written* and *how it binds lexically*. Nothing is resolved here: a
call's callee needs the project's declarations, which other files hold, so this
only produces ``occurrences`` for ``kotlin_symbols`` to resolve once the whole
project is known.

An occurrence is a dict: ``o`` the owner entity key (the function, property or
class the code sits in), ``t`` ``"call"`` or ``"name"``, ``n`` the name, ``r`` the
receiver as a descriptor or ``None``, ``a`` the argument count (a trailing lambda
counts), ``m`` ``"use"``, ``"set"`` or ``"modify"``, ``b`` the lexical binding,
``l``/``c`` the position, ``s`` the enclosing scope names, ``lam`` the lambdas the
occurrence sits in, and ``id``.

**Descriptors** describe an expression's value so a later receiver can be typed:
``("unknown",)`` (written but untyped, so never mistaken for "no receiver"),
``("this",)``, ``("super",)``, ``("lit", fqname)``, ``("cast", type name)``,
``("name", name, binding)``, ``("member", receiver, name)`` and
``("call", receiver, name, nargs, occurrence id)``.

**Bindings** say what a bare name means before any project lookup: ``("local",
key)`` is a parameter or local this pass declared, ``("shadow",)`` a name
declared where this pass declares no entities (a lambda parameter, a ``catch``
variable), ``("fun", [keys])`` a local function, and ``None`` a free name.

**Lambdas** are the hard part. Inside one, an unqualified name may be a member of
the lambda's *receiver* (``apply``, ``with``, a DSL builder), which only the callee
knows. Each occurrence therefore records the lambdas it sits in as ``(call id,
argument position)``; the resolver drops the free names in a lambda whose callee
takes a receiver and keeps the rest. A lambda also hides what it declares: its
parameters and locals are shadows, never entities.

**Operators and infix calls** are calls too: ``a to b`` and ``a shl 2`` call the infix
function, ``a + b`` calls ``plus`` (and ``- * / % .. ..<`` likewise), ``a < b`` calls
``compareTo``, ``x in c`` calls ``c.contains(x)``, ``-a``/``+a``/``!a`` and ``a++`` call
``unaryMinus``/``unaryPlus``/``not``/``inc``, ``a[i]`` calls ``get`` (``set`` when
assigned), ``a += b`` tries ``plusAssign`` then ``plus``, and ``f(x)`` on a value calls
``invoke``. Each is an occurrence marked ``op``, positioned at the operator, so the
resolver can leave the intrinsic ones (``Int + Int``) alone.

**Destructuring and loops** desugar the same way: ``val (a, b) = e`` calls ``e.component1()``
and ``component2()`` (anchored on the opening parenthesis, since an entry's name is where
that variable is defined), and ``for (x in c)`` calls ``c.iterator()`` and then ``hasNext()``
and ``next()`` on the result, anchored on ``in``. Each destructured or loop variable is
typed by that call, so what is done with it resolves. A loop's ``occurrence["loop"]`` names
its iterable, so the resolver can leave a loop over a range, array or string alone.

An anonymous object is declared by the collector (``_Collector.anonymous``) and is a value of its own
class, ``("lit", longname)``; the header's ``Base(x)`` call is recorded by the creating walker.

An anonymous function is walked like a lambda: its parameters are shadows that carry their written
type, and it has an implicit receiver only if it writes one.

A callable reference is a ``ref`` occurrence at the name after ``::``, with the receiver as for a
qualified name; it is a read (a ``Use``) of whatever the name finds, with any arity, plus a
read of the type before the ``::`` (``type_only``: a class, not a variable).

Not walked: annotations, types.

**Delegated properties and ``==``** are calls as well. ``val x by d`` calls ``getValue``
(and ``setValue`` for a ``var``) on ``d``, after ``provideDelegate`` when ``d`` declares it, at
the ``by``; the property is typed by the ``getValue`` call. ``a == b`` and ``a != b`` call
``a.equals(b)`` at the operator; ``===``, ``!==`` and a comparison with ``null`` call nothing.

A lambda parameter's destructuring, ``{ (k, v) -> }``, is ``componentN`` on a ``("lparam", ...)``
value: the parameter's type is the one written (``{ (a, b): Pair<A, B> -> }``) or the first
parameter of the function type the callee declares for that lambda (``Map.forEach`` takes
``(Map.Entry<K, V>) -> Unit``). Its names stay shadows, never entities.

Name-based entries (``(val a = prop)``) read the property and bracketed ``[a, b]`` is ``componentN``
too. Not resolved: a lambda destructured in any
parameter the callee's function type does not give. A lambda parameter that is not
destructured (``it``, ``{ p -> }``) is typed by the same signature: its name carries the
same ``("lparam", call id, position, index, declared)`` as its binding, and a lambda records
the descriptor of its last statement (``("lambda", result)``) so the resolver can bind the
callee's result type parameter (``map { it.x }``). A call records its explicit type
arguments in ``targs``.
"""

from __future__ import annotations

from antlr4.tree.Tree import TerminalNode

from openunderstand.utils import kind_names as K
from openunderstand.analysis_passes.kotlin_tree import (
    children,
    find,
    first,
    has_equals,
    name_of,
    name_pos,
    rule,
)

_SKIPPED = {
    "callableReference",
    "annotation",
    "fileAnnotation",
    "type_",
    "typeArguments",
    "typeParameters",
    "typeConstraints",
}
_UNARY = {"-": "unaryMinus", "+": "unaryPlus", "!": "not", "++": "inc", "--": "dec"}
_BINARY = {
    "+": "plus", "-": "minus", "*": "times", "/": "div", "%": "rem",
    "..": "rangeTo", "..<": "rangeUntil",
    "<": "compareTo", ">": "compareTo", "<=": "compareTo", ">=": "compareTo",
}
_AUGMENTED = {"+=": ("plusAssign", "plus"), "-=": ("minusAssign", "minus"), "*=": ("timesAssign", "times"),
              "/=": ("divAssign", "div"), "%=": ("remAssign", "rem")}
_LITERALS = {
    "BooleanLiteral": "kotlin.Boolean",
    "CharacterLiteral": "kotlin.Char",
    "IntegerLiteral": "kotlin.Int",
    "HexLiteral": "kotlin.Int",
    "BinLiteral": "kotlin.Int",
    "LongLiteral": "kotlin.Long",
    "RealLiteral": "kotlin.Double",
}


#: The value of an expression whose type this pass cannot describe, used as a receiver.
UNKNOWN = ("unknown",)


class Env:
    """Lexical names: a parameter, a local, a shadow or a local function."""

    def __init__(self, parent: "Env | None" = None):
        self.parent = parent
        self.names: dict = {}
        self.pkeys: dict = {}       # name -> entity key of a declared lambda parameter
        self.lazy: dict = {}        # name -> declare-on-first-use function (the implicit `it`)

    def lookup(self, name: str):
        env = self
        while env is not None:
            if name in env.names:
                return env.names[name]
            env = env.parent
        return None

    def pkey(self, name: str):
        env = self
        while env is not None:
            if name in env.names:
                if name in env.lazy:
                    env.pkeys[name] = env.lazy.pop(name)()
                return env.pkeys.get(name)
            env = env.parent
        return None

    def child(self) -> "Env":
        return Env(self)

    def declare_fun(self, name: str, key):
        existing = self.names.get(name)
        if existing and existing[0] == "fun":
            existing[1].append(key)
        else:
            self.names[name] = ("fun", [key])


def _dereferenced(next_suffix) -> bool:
    """Whether a name is followed by ``.member`` or ``?.member`` (past any ``!!``): its value is only partly read."""
    next_suffix = [x for x in next_suffix if not (rule(x) == "postfixUnaryOperator" and x.getText().strip() == "!!")]
    if not next_suffix or rule(next_suffix[0]) != "navigationSuffix":
        return False
    operator = next_suffix[0].children[0].getText().strip() if next_suffix[0].children else ""
    return operator in (".", "?.") and first(next_suffix[0], "simpleIdentifier") is not None


class ExprWalker:
    """One owner's code. ``collector`` supplies declarations for locals."""

    def __init__(self, collector, owner, scope, env: Env, receiver_lambda: bool = False):
        self.c = collector
        self.owner = owner
        self.scope = tuple(scope)
        self.env = env
        self.lambdas: list = []  # (call id, argument position) enclosing the code
        self.lambda_depth = 0       # inside an anonymous function: its declarations are not made
        self.wowner = owner         # who references are written against: the innermost lambda, else the owner
        self.dscope = tuple(scope)  # where declarations inside the code go: the innermost lambda's scope
        self.receiver_lambda_next = receiver_lambda
        self.pending_lambda = None  # (call id, position) of the lambda being entered
        self.lambda_result = None   # the last statement's descriptor of the lambda just walked
        self.last = None  # the occurrence a following `++` may turn into a modify
        self.in_annotation = False  # walking the arguments of an annotation
        self.return_expr = None     # the enclosing function's written return type, as a type expression

    # -- recording ---------------------------------------------------------
    def occurrence(self, kind, name, line, col, receiver=None, nargs=0, mode="use", binding=None,
                   op=False, alt=None):
        occ = {
            "id": len(self.c.out.occurrences),
            "o": self.owner,
            "w": self.wowner,
            "pk": self.env.pkey(name) if receiver is None and binding is not None and binding[0] in ("lparam", "shadow") else None,
            "t": kind,
            "n": name,
            "r": receiver,
            "a": nargs,
            "m": mode,
            "b": binding,
            "l": line,
            "c": col,
            "s": self.scope,
            "lam": tuple(self.lambdas),
            "init": False,
            "op": op,      # written as an operator or infix call, not by name
            "alt": alt,    # the name to try if this one finds nothing (`plusAssign`, then `plus`)
            "args": [],    # a descriptor per argument (None: unknown, ("lambda",): a lambda)
            "named": False,  # a named or spread argument: the arguments' order says nothing
            "argnames": [],  # one per argument: its name when written `name = value`, else None
            "sym": False,    # an operator written as a symbol (see op_call)
            "loop": None,    # for `iterator`/`hasNext`/`next`: the loop's iterable
            "targs": (),     # explicit type arguments of the call, as type expressions
            "exp": None,     # the declared type the call's value is stored in, as a type expression
            "annot": self.in_annotation,   # inside an annotation's arguments: `Inner(1)` there is an annotation
        }
        self.c.out.occurrences.append(occ)
        return occ

    def expect(self, descriptor, type_ctx):
        """Note the declared type a call's value is assigned to: it may bind the call's type parameters."""
        if descriptor is not None and descriptor[0] == "call" and type_ctx is not None:
            self.c.out.occurrences[descriptor[4]]["exp"] = self.c.texpr(type_ctx)
        return descriptor

    def r_jumpExpression(self, ctx, mode):
        """``return call()``: the function's written return type is what the call's value is stored in."""
        kids = [c for c in ctx.children or [] if not (isinstance(c, TerminalNode) and not c.symbol.text.strip())]
        expression = first(ctx, "expression")
        desc = self.walk(expression) if expression is not None else None
        plain = bool(kids) and isinstance(kids[0], TerminalNode) and kids[0].getText() == "return"
        if plain and desc is not None and desc[0] == "call" and self.return_expr is not None:
            self.c.out.occurrences[desc[4]]["exp"] = self.return_expr
        for child in kids:                                   # `throw`/labels hold nothing else to walk
            if child is not expression and not isinstance(child, TerminalNode):
                self.walk(child)
        return None

    # -- walking -----------------------------------------------------------
    def walk(self, ctx, mode=None):
        """Visit any subtree; returns a descriptor if it is an expression with a value."""
        if ctx is None or isinstance(ctx, TerminalNode):
            return None
        name = rule(ctx)
        if name in _SKIPPED:
            return None
        handler = getattr(self, "r_" + name, None)
        if handler is not None:
            return handler(ctx, mode)
        # a wrapper rule (expression, disjunction, ...) with one child passes its value up
        kids = [c for c in ctx.children or [] if not (isinstance(c, TerminalNode) and not c.symbol.text.strip())]
        if len(kids) == 1 and not isinstance(kids[0], TerminalNode):
            return self.walk(kids[0], mode)
        for child in ctx.children or []:
            self.walk(child)
        return None

    def r_postfixUnaryExpression(self, ctx, mode):
        kids = list(ctx.children or [])
        primary = children(kids[0])[0] if kids and not isinstance(kids[0], TerminalNode) else None
        suffixes = [children(c)[0] for c in kids[1:]]
        return self.chain(primary, suffixes, mode)

    def r_expressionStatement(self, ctx, mode):
        kids = [c for c in ctx.children or [] if not (isinstance(c, TerminalNode) and c.symbol.text.strip() == "")]
        operator = None
        for c in kids:
            if isinstance(c, TerminalNode) and c.getText() == "=":
                operator = "set"
            elif rule(c) == "assignmentAndOperator":
                operator = "modify"
        if operator is None or len(kids) < 3:
            return self.walk(kids[0]) if len(kids) == 1 else self.generic(ctx)
        left, right = kids[0], kids[-1]
        assigned = self.walk(right)
        target = self.walk(left, operator)
        if operator == "modify":
            for c in kids:
                if rule(c) == "assignmentAndOperator":
                    names = _AUGMENTED.get(c.getText().strip())
                    if names:
                        self.op_call(target, names[0], 1, c.start, alt=names[1], args=(assigned,))
        return None

    def generic(self, ctx):
        for child in ctx.children or []:
            self.walk(child)
        return None

    def op_call(self, receiver, name, nargs, token, alt=None, args=(), symbol=True, loop=None):
        """A call the syntax implies (an operator, an index, an infix name): returns its descriptor.

        ``symbol`` is true for an operator written as a symbol (``+``, ``[]``, ``in``) and
        false for a named infix function (``a to b``): the resolver leaves a symbolic
        operator on a primitive alone, but ``1 to 2`` is a real call.
        """
        receiver = receiver if receiver is not None else UNKNOWN
        occ = self.occurrence(
            "call", name, token.line, token.column, receiver=receiver, nargs=nargs, op=True, alt=alt
        )
        occ["args"] = list(args)
        occ["sym"] = symbol
        occ["loop"] = loop       # the iterable of the `for` this call belongs to, if any
        return ("call", receiver, name, nargs, occ["id"])

    def r_prefixUnaryExpression(self, ctx, mode):
        kids = list(ctx.children or [])
        operand = kids[-1]
        prefixes = [c for c in kids[:-1] if rule(c) == "unaryPrefix"]
        increments = any(c.getText().strip() in ("++", "--") for c in prefixes)
        desc = self.walk(operand, "modify" if increments else mode)
        for c in reversed(prefixes):          # the one nearest the operand applies first
            text = c.getText().strip()
            name = _UNARY.get(text)
            if name:
                desc = self.op_call(desc, name, 0, c.start)
        return desc

    def _binary(self, ctx, mode):
        kids = self._operands(ctx)
        if len(kids) == 1:
            return self.walk(kids[0], mode)
        current = self.walk(kids[0])
        i = 1
        while i + 1 < len(kids):
            op = kids[i]
            right = self.walk(kids[i + 1])
            name = _BINARY.get(op.getText().strip())
            token = op.start if not isinstance(op, TerminalNode) else op.symbol
            current = self.op_call(current, name, 1, token, args=(right,)) if name else None
            i += 2
        return current

    r_additiveExpression = _binary
    r_multiplicativeExpression = _binary
    r_rangeExpression = _binary
    r_comparison = _binary

    @staticmethod
    def _operands(ctx):
        return [c for c in ctx.children or [] if not (isinstance(c, TerminalNode) and not c.symbol.text.strip())]

    def r_infixFunctionCall(self, ctx, mode):
        """``a to b``: operands with a function name between them."""
        kids = self._operands(ctx)
        if len(kids) == 1:
            return self.walk(kids[0], mode)
        current = self.walk(kids[0])
        i = 1
        while i + 1 < len(kids):
            name, line, col = name_pos(kids[i])
            right = self.walk(kids[i + 1])
            token = kids[i].start
            current = self.op_call(current, name, 1, token, args=(right,), symbol=False)
            i += 2
        return current

    def r_infixOperation(self, ctx, mode):
        """``x in c`` calls ``c.contains(x)``; ``x is T`` calls nothing."""
        kids = self._operands(ctx)
        if len(kids) == 1:
            return self.walk(kids[0], mode)
        current = self.walk(kids[0])
        i = 1
        while i < len(kids):
            if rule(kids[i]) == "inOperator" and i + 1 < len(kids):
                container = self.walk(kids[i + 1])
                current = self.op_call(container, "contains", 1, kids[i].start, args=(current,))
                i += 2
            else:                                   # `is` / `!is` and its type
                current = None
                self.note_type(kids[i + 1] if i + 1 < len(kids) and rule(kids[i + 1]) == "type_" else None)
                i += 2
        return current

    def r_rangeTest(self, ctx, mode):
        """``when (x) { in a..b -> }``: ``(a..b).contains(x)``."""
        operator = first(ctx, "inOperator")
        container = self.walk(first(ctx, "expression"))
        self.op_call(container, "contains", 1, operator.start)
        return None

    def note_type(self, type_ctx):
        """A qualified type written in an expression (``as a.b.C``, ``is Outer.Inner``) reads its qualifier."""
        user = None if type_ctx is None else type_ctx if rule(type_ctx) == "userType" else find(type_ctx, "userType")
        parts = children(user, "simpleUserType") if user is not None else []
        if parts:                       # `x as List<Point>`: an expression, so Java's `Use GenericArgument`
            self.c.argument_list(first(parts[-1], "typeArguments"), self.owner, self.scope, constructed=True)
        if len(parts) > 1:
            self.c.out.qualifiers.append(
                {"owner": self.owner, "name": ".".join(name_pos(first(p, "simpleIdentifier"))[0] for p in parts),
                 "enclosing": list(self.scope), "start": name_pos(first(parts[0], "simpleIdentifier"))[1:]}
            )

    def r_typeTest(self, ctx, mode):
        self.note_type(first(ctx, "type_"))
        return None

    def r_asExpression(self, ctx, mode):
        kids = [c for c in ctx.children or [] if rule(c) is not None]
        desc = self.walk(kids[0], mode if len(kids) == 1 else None)
        for c in kids[1:]:
            if rule(c) == "type_":
                self.note_type(c)
                user = find(c, "userType")
                named = name_of(c)
                if user is not None and named and not any(named in frame for frame in getattr(self.c, "_tp", ())):
                    start = name_pos(first(children(user, "simpleUserType")[0], "simpleIdentifier"))
                    self.c.out.casts.append(
                        {"owner": self.owner, "name": named, "line": start[1], "col": start[2],
                         "enclosing": list(self.scope)}
                    )
        if len(kids) > 1:
            named = name_of(kids[-1])
            return ("cast", named) if named else None
        return desc

    def r_lambdaLiteral(self, ctx, mode):
        outer = self.env
        self.env = outer.child()
        saved = (self.wowner, self.dscope)
        lambda_name = self.c.lambda_name(".".join(self.dscope))
        lambda_key = self.c.add(None, list(self.dscope), decl=K.LAMBDA, type_text=None, ctx=ctx, modifiers=(),
                                name=lambda_name)
        self.wowner, self.dscope = lambda_key, (*self.dscope, lambda_name)
        binding = self.pending_lambda          # (call id, argument position) this lambda is passed as
        if binding is not None:
            self.lambdas.append(binding)
            pushed = True
        else:
            pushed = False
        self.pending_lambda = None
        params = first(ctx, "lambdaParameters")
        if params is None:
            # `it` is the callee's first lambda parameter, typed by its signature
            self.env.names["it"] = ("lparam", binding[0], binding[1], 0, None) if binding else ("shadow",)
            lam_scope = list(self.dscope)
            self.env.lazy["it"] = lambda: self.c.add(      # declared when the body reads it: it is implicit
                None, lam_scope, decl=K.PARAMETER, type_text=None, ctx=ctx, modifiers=(), span=False,
                name="it", implicit=True)
        else:
            for position, p in enumerate(children(params, "lambdaParameter")):
                # `{ (k, v) -> }` is componentN on the parameter, whose type the callee's signature
                # (or an explicit `: Type`) gives
                declared = name_of(first(p, "type_")) if first(p, "type_") is not None else None
                value = ("lparam", binding[0] if binding else None, binding[1] if binding else None, position, declared)
                destructured = first(p, "multiVariableDeclaration") is not None
                for ident in _identifiers(p):
                    self.env.names[ident] = ("shadow",) if destructured or not (binding or declared) else value
                self.declare_lambda_parameters(p)
                if destructured and (binding is not None or declared):
                    self.components(p, value)
        result = None
        for child in ctx.children or []:
            if rule(child) == "statements":
                for statement in children(child, "statement"):
                    result = self.walk(statement)       # the last one is the lambda's value
            else:
                self.walk(child)
        self.lambda_result = result
        self.env = outer
        self.wowner, self.dscope = saved
        if pushed:
            self.lambdas.pop()
        return None

    def declare_lambda_parameters(self, p):
        """Each explicit lambda parameter (and each name it destructures) is a parameter of the lambda."""
        entries = [first(p, "variableDeclaration")] if first(p, "variableDeclaration") is not None else \
            [first(e, "variableDeclaration") for e in children(first(p, "multiVariableDeclaration"), "destructuringEntry")] \
            if first(p, "multiVariableDeclaration") is not None else []
        for variable in entries:
            ident = first(variable, "simpleIdentifier") if variable is not None else None
            if ident is None:
                continue
            type_ctx = first(variable, "type_")
            key = self.c.add(ident, list(self.dscope), decl=K.PARAMETER,
                             type_text=type_ctx.getText() if type_ctx is not None else None,
                             ctx=variable, modifiers=(), span=False)
            if type_ctx is not None:
                self.c.typed(key, type_ctx, list(self.dscope))
            self.env.pkeys[name_pos(ident)[0]] = key

    def r_objectLiteral(self, ctx, mode):
        """An anonymous object is declared by the collector; as a value it is of its own class."""
        return ("lit", self.c.anonymous(ctx, self))

    def r_anonymousFunction(self, ctx, mode):
        """``fun(x: Int): Int { ... }`` as a value: a scope like a lambda's, with typed parameters.

        Its parameters are shadows (never entities) but carry their written type, so ``x.foo()``
        resolves. It has no implicit receiver of its own unless it writes one (``fun Int.(): ...``),
        in which case the names inside may belong to that receiver and are left alone.
        """
        outer = self.env
        self.env = outer.child()
        saved = (self.wowner, self.dscope)
        lambda_name = self.c.lambda_name(".".join(self.dscope))
        lambda_key = self.c.add(None, list(self.dscope), decl=K.LAMBDA, type_text=None, ctx=ctx, modifiers=(),
                                name=lambda_name)
        self.wowner, self.dscope = lambda_key, (*self.dscope, lambda_name)
        self.pending_lambda = None
        own_receiver = False
        for c in ctx.children or []:
            if rule(c) == "anonymousFunctionParameters":
                break
            if rule(c) == "type_":
                own_receiver = True
        if own_receiver:
            self.lambdas.append((None, 0))
        params = first(ctx, "anonymousFunctionParameters")
        for position, p in enumerate(children(params, "anonymousFunctionParameter") if params is not None else []):
            declared = name_of(first(p, "type_")) if first(p, "type_") is not None else None
            default = first(p, "expression")
            if default is not None:
                self.walk(default)
            name = name_of_identifier(first(p, "simpleIdentifier"))
            self.env.names[name] = ("lparam", None, None, position, declared) if declared else ("shadow",)
            param_key = self.c.add(first(p, "simpleIdentifier"), list(self.dscope), decl=K.PARAMETER,
                                   type_text=first(p, "type_").getText() if first(p, "type_") is not None else None,
                                   ctx=p, modifiers=(), span=False)
            if first(p, "type_") is not None:
                self.c.typed(param_key, first(p, "type_"), list(self.dscope))
            self.env.pkeys[name] = param_key
        result = None
        body = first(ctx, "functionBody")
        for part in (body.children if body is not None else []) or []:
            if rule(part) == "expression":
                result = self.walk(part)
            else:
                self.walk(part)
        self.lambda_result = result
        self.env = outer
        self.wowner, self.dscope = saved
        if own_receiver:
            self.lambdas.pop()
        return None

    def r_constructorDelegationCall(self, ctx, mode):
        """``this(...)`` or ``super(...)`` after a secondary constructor's parameters."""
        keyword = ctx.children[0]
        token = keyword.symbol if isinstance(keyword, TerminalNode) else ctx.start
        occ = self.occurrence("call", "<" + token.text + ">", token.line, token.column)
        occ["init"] = True
        occ["a"], occ["args"] = self.arguments_of(first(ctx, "valueArguments"))
        return None

    def header_call(self, user_type, arguments):
        """``class A : Base(x)``: the superclass constructor the class header invokes."""
        token = user_type.start
        names = [name_pos(first(p, "simpleIdentifier")) for p in children(user_type, "simpleUserType")]
        name, line, col = names[-1]
        occ = self.occurrence("call", ".".join(n for n, _, _ in names), line, col)
        occ["init"] = True
        occ["a"], occ["args"] = self.arguments_of(arguments)

    def arguments_of(self, value_arguments):
        described = []
        for argument in children(value_arguments, "valueArgument") if value_arguments is not None else []:
            expression = first(argument, "expression")
            described.append(self.walk(expression))
        return len(described), described

    def r_block(self, ctx, mode):
        outer = self.env
        self.env = outer.child()
        self.generic(ctx)
        self.env = outer
        return None

    def r_propertyDeclaration(self, ctx, mode):
        head = first(ctx, "propertyDeclarationHead")
        descriptor = None
        # the initialiser first: it cannot see the variable it initialises
        for c in head.children or []:
            if rule(c) == "propertyDelegate":
                descriptor = self.delegate(c, is_var=any(
                    isinstance(t, TerminalNode) and t.getText() == "var" for t in head.children or []
                ))
            elif rule(c) == "expression":
                descriptor = self.expect(self.walk(c), first(first(head, "variableDeclaration") or head, "type_"))
        if self.lambda_depth > 0:
            for ident in _identifiers(head):
                self.env.names[ident] = ("shadow",)
        else:
            self.c.local(ctx, list(self.dscope), self.env, descriptor, self.components(head, descriptor))
        accessors = first(ctx, "propertyAccessors")
        if accessors is not None:
            self.generic(accessors)
        return None

    def delegate(self, ctx, is_var):
        """``val x by d``: ``d.getValue(thisRef, property)``, plus ``setValue`` for a ``var``.

        If the delegate's type declares ``provideDelegate``, the delegate that is read is what that
        returns, so the descriptor says "this, unless provideDelegate answers". The result stands
        for the property's value, so ``val x by lazy { ... }`` is typed by ``getValue``.
        """
        value = self.walk(first(ctx, "expression"))
        by = ctx.children[0].symbol
        if value is None:
            return None
        provided = self.op_call(value, "provideDelegate", 2, by, symbol=False, args=(None, None))
        holder = ("delegate", value, provided)
        getter = self.op_call(holder, "getValue", 2, by, symbol=False, args=(None, None))
        if is_var:
            self.op_call(holder, "setValue", 3, by, symbol=False, args=(None, None, None))
        return getter

    def r_equality(self, ctx, mode):
        """``a == b`` calls ``a.equals(b)``; ``===`` compares identity and calls nothing."""
        kids = self._operands(ctx)
        if len(kids) == 1:
            return self.walk(kids[0], mode)
        current = self.walk(kids[0])
        left_text = kids[0].getText()
        i = 1
        while i + 1 < len(kids):
            op, right_ctx = kids[i], kids[i + 1]
            right = self.walk(right_ctx)
            if op.getText().strip() in ("==", "!=") and "null" not in (left_text, right_ctx.getText()):
                self.op_call(current, "equals", 1, op.start, args=(right,))
            current, left_text = None, ""
            i += 2
        return current

    def components(self, holder, value):
        """``componentN`` calls for ``val (a, b) = value``: one per entry, or ``None`` for none.

        Positional entries, in parentheses or the newer brackets, are ``componentN`` at the opening
        token. A name-based entry, ``(val first = firstName)``, reads the property it names instead:
        a plain read of ``firstName`` on the value, at that name, and the new variable takes its type.
        """
        multi = first(holder, "multiVariableDeclaration")
        if multi is None or value is None:
            return None
        out = []
        # at the opening token, not on an entry's name: the name is where that variable is
        # defined, and one position carries one kind of reference
        for position, entry in enumerate(children(multi, "destructuringEntry"), 1):
            if has_equals(entry):
                prop = first(entry, "simpleIdentifier")
                name, line, col = name_pos(prop)
                self.occurrence("name", name, line, col, receiver=value)
                out.append(("member", value, name))
            else:
                out.append(self.op_call(value, f"component{position}", 0, multi.start, symbol=False))
        return out

    def r_forStatement(self, ctx, mode):
        outer = self.env
        self.env = outer.child()
        iterable = None
        for c in ctx.children or []:
            if rule(c) == "expression":
                iterable = self.walk(c)
        element, entries = None, None
        if iterable is not None:
            # `for (x in c)` is c.iterator(), then hasNext() and next() on what that returns
            keyword = next((c.symbol for c in ctx.children or [] if isinstance(c, TerminalNode) and c.getText() == "in"), ctx.start)
            iterator = self.op_call(iterable, "iterator", 0, keyword, loop=iterable)
            self.op_call(iterator, "hasNext", 0, keyword, loop=iterable)
            following = self.op_call(iterator, "next", 0, keyword, loop=iterable)
            element = ("element", iterable, following)
            entries = self.components(ctx, element)
        if self.lambda_depth > 0:
            for name in _identifiers_in(ctx, ("variableDeclaration", "multiVariableDeclaration")):
                self.env.names[name] = ("shadow",)
        else:
            self.c.for_variables(ctx, list(self.dscope), self.env, element, entries)
        for c in ctx.children or []:
            if rule(c) == "controlStructureBody":
                self.walk(c)
        self.env = outer
        return None

    def r_whenExpression(self, ctx, mode):
        outer = self.env
        self.env = outer.child()
        subject = first(ctx, "whenSubject")
        if subject is not None:
            for ident in _identifiers_in(subject, ("variableDeclaration",)):
                self.env.names[ident] = ("shadow",)
        self.generic(ctx)
        self.env = outer
        return None

    def r_catchBlock(self, ctx, mode):
        outer = self.env
        self.env = outer.child()
        ident = first(ctx, "simpleIdentifier")
        if ident is not None:
            self.env.names[name_of_identifier(ident)] = ("shadow",)
        self.note_type(first(ctx, "userType"))
        self.generic(ctx)
        self.env = outer
        return None

    # a local declaration inside a body
    def r_classDeclaration(self, ctx, mode):
        if self.lambda_depth == 0:
            self.c.klass(ctx, list(self.dscope), False, False)
        return None

    def r_objectDeclaration(self, ctx, mode):
        if self.lambda_depth == 0:
            self.c.obj(ctx, list(self.dscope), False)
        return None

    def r_functionDeclaration(self, ctx, mode):
        if self.lambda_depth == 0:
            key = self.c.function(ctx, list(self.dscope), False, False, None, env=self.env)
            if key is not None:
                self.env.declare_fun(key[0].rsplit(".", 1)[-1], key)
        return None

    def r_lineStringContent(self, ctx, mode):
        for c in ctx.children or []:
            if isinstance(c, TerminalNode) and c.symbol.text.startswith("$") and len(c.symbol.text) > 1:
                text = c.symbol.text.lstrip("$")
                token = c.symbol
                if text.isidentifier():
                    self.occurrence(
                        "name", text, token.line, token.column + len(token.text) - len(text),
                        binding=self.env.lookup(text),
                    )
        return None

    r_multiLineStringContent = r_lineStringContent

    def reference(self, ctx, receiver, at=None, chained=False, head_at=None, names=()):
        """``::f``, ``Type::f``, ``obj::f``: a read of the function, property or constructor named.

        Written as a ``ref`` occurrence at the name after ``::`` (``Type::class`` and ``::class``
        name no declaration). ``Type::f`` takes the type as an ordinary name receiver, which the
        resolver reads as a class (an unbound reference to an instance member) or an object.
        """
        ident = first(ctx, "simpleIdentifier")
        written = first(ctx, "receiverType") or first(ctx, "nullableType")
        if written is not None:
            dotted = name_of(written)
            user = find(written, "userType")
            if dotted and user is not None:
                parts = children(user, "simpleUserType")
                dot = dotted[:1].isupper() and not chained
                # a DotRef is to the head type at the head (as Java's `Outer.Inner.class`); a Use is
                # of the whole type at its last segment
                if len(parts) > 1 and not dot:
                    # a package-qualified type is an expression: one name per segment, as `a.b.C.f` is
                    walked = None
                    for p in parts:
                        seg, line, col = name_pos(first(p, "simpleIdentifier"))
                        self.occurrence("name", seg, line, col, receiver=walked,
                                        binding=self.env.lookup(seg) if walked is None else None)
                        walked = ("name", seg, None) if walked is None else ("member", walked, seg)
                else:
                    segment = name_pos(first(parts[0 if dot else -1], "simpleIdentifier"))
                    used = self.occurrence("ref", segment[0], segment[1], segment[2])
                    used["type_only"] = dotted.split(".")[0] if dot else dotted
                    used["dotref"] = dot
        elif at is not None and receiver is not None and receiver[0] in ("name", "member"):
            head = receiver
            while head[0] == "member":
                head = head[1]
            dot = head[0] == "name" and head[1][:1].isupper() and not chained and head_at is not None
            if dot:
                used = self.occurrence("ref", head[1], head_at[0], head_at[1])
                used["type_only"] = head
                for occ in names:                  # `Outer.Inner::class` reads its head only, as Java's does
                    occ["m"] = "skip"
            else:
                used = self.occurrence("ref", receiver[-1] if receiver[0] == "member" else receiver[1], at[0], at[1])
                used["type_only"] = receiver       # a class name when it is not a variable
            used["dotref"] = dot
        if ident is None:
            return
        if written is not None:
            receiver = UNKNOWN
            if dotted:
                head, *rest = dotted.split(".")
                receiver = ("name", head, self.env.lookup(head))
                for segment in rest:
                    receiver = ("member", receiver, segment)
        name, line, col = name_pos(ident)
        self.occurrence("ref", name, line, col, receiver=receiver,
                        binding=self.env.lookup(name) if receiver is None else None)

    # -- the chain `a.b(c).d` ---------------------------------------------
    def chain(self, primary, suffixes, mode):
        index = 0
        current = None
        final_mode = mode or "use"
        has_more = bool(suffixes)
        kind = rule(primary) if primary is not None else None
        recv_at = None                      # where the receiver's last name is written
        head_at = None                      # where its first name is written
        names_read = []                     # the name occurrences of this chain, in order
        if kind == "simpleIdentifier":
            name, line, col = name_pos(primary)
            recv_at = head_at = (line, col)
            call_at = _call_index(suffixes, 0)
            if call_at is not None:
                current, index = self.call(None, name, line, col, suffixes, call_at)
            else:
                occ = self.occurrence(
                    "name", name, line, col,
                    mode=final_mode if not has_more else "use",
                    binding=self.env.lookup(name),
                )
                self.last = occ
                occ["deref"] = _dereferenced(suffixes) and (final_mode if final_mode in ("set", "modify") else True)
                names_read.append(occ)
                current = ("name", name, occ["b"])
        elif kind == "thisExpression":
            current = ("this",)
        elif kind == "superExpression":
            current = ("super",)
        elif kind == "parenthesizedExpression":
            current = self.walk(first(primary, "expression"))
        elif kind == "literalConstant":
            token = primary.start
            current = ("lit", _LITERALS[_token_name(token)]) if _token_name(token) in _LITERALS else None
        elif kind == "stringLiteral":
            self.generic(primary)
            current = ("lit", "kotlin.String")
        elif kind == "callableReference":
            self.reference(primary, None, chained=bool(suffixes))
            return None
        elif kind == "objectLiteral":
            current = self.walk(primary)
        elif primary is not None:
            self.walk(primary)
        while index < len(suffixes):
            s = suffixes[index]
            sr = rule(s)
            last_one = index == len(suffixes) - 1
            if sr == "navigationSuffix":
                operator = s.children[0].getText().strip() if s.children else ""
                if operator == "::":
                    self.reference(s, current if current is not None else UNKNOWN, recv_at,
                                   chained=index < len(suffixes) - 1, head_at=head_at, names=names_read)
                    if first(s, "simpleIdentifier") is None and current is not None and current[0] in ("name", "member"):
                        rest = suffixes[index + 1:]       # `X::class` and `X::class.java`: a value of a known type
                        java = len(rest) == 1 and rule(rest[0]) == "navigationSuffix" and rest[0].getText() == ".java"
                        if not rest or java:
                            return ("classlit", current, java)
                    return None
                ident = first(s, "simpleIdentifier")
                if ident is None:  # `.class` or `.(expr)`
                    self.walk(first(s, "parenthesizedExpression"))
                    current = None
                    index += 1
                    continue
                name, line, col = name_pos(ident)
                recv_at = (line, col)
                # a receiver that is written but untyped must not look like "no receiver"
                if current is None:
                    current = UNKNOWN
                call_at = _call_index(suffixes, index + 1)
                if call_at is not None:
                    current, index = self.call(current, name, line, col, suffixes, call_at)
                    continue
                occ = self.occurrence(
                    "name", name, line, col, receiver=current,
                    mode=final_mode if last_one else "use",
                )
                self.last = occ
                occ["deref"] = _dereferenced(suffixes[index + 1:])
                names_read.append(occ)
                current = ("member", current, name)
            elif sr == "callSuffix":     # invoke: `f(x)(y)`
                current, index = self.call(current if current is not None else UNKNOWN, "invoke",
                                           s.start.line, s.start.column, suffixes, index)
                self.c.out.occurrences[current[4]]["op"] = True
                continue
            elif sr == "indexingSuffix":
                indices = [self.walk(e) for e in children(s, "expression")]
                count = len(indices)
                how = final_mode if last_one else "use"
                if how == "use":
                    current = self.op_call(current, "get", count, s.start, args=indices)
                elif how == "set":
                    self.op_call(current, "set", count + 1, s.start, args=[*indices, None])
                    current = None
                else:                     # `a[i] += x` reads and writes
                    current = self.op_call(current, "get", count, s.start, args=indices)
                    self.op_call(current[1], "set", count + 1, s.start, args=[*indices, None])
            elif sr == "postfixUnaryOperator":
                text = s.getText().strip()
                if text in ("++", "--"):
                    if self.last is not None:
                        self.last["m"] = "modify"
                        if len(names_read) > 1 and names_read[0].get("deref"):
                            names_read[0]["deref"] = "modify"      # `a.f++` partly modifies `a`
                    current = self.op_call(current, "inc" if text == "++" else "dec", 0, s.start)
            index += 1
        return current

    def call(self, receiver, name, line, col, suffixes, at):
        """Record a call; ``at`` indexes its callSuffix. Returns (descriptor, next index)."""
        occ = self.occurrence(
            "call", name, line, col, receiver=receiver,
            binding=self.env.lookup(name) if receiver is None else None,
        )
        end = at
        if at > 0 and rule(suffixes[at - 1]) == "typeArguments":     # `emptyList<Point>()`
            occ["targs"] = tuple(
                "*" if not children(a, "type_") else self.c.texpr(first(a, "type_"))
                for a in children(suffixes[at - 1], "typeProjection")
            )
            self.c.argument_list(suffixes[at - 1], self.owner, self.scope, constructed=True)
        nargs = self.arguments(suffixes[at], occ)
        # lambdas written after the call (`f(x) {} {}`) are further arguments
        while end + 1 < len(suffixes) and rule(suffixes[end + 1]) == "callSuffix" and first(suffixes[end + 1], "valueArguments") is None:
            end += 1
            nargs += self.arguments(suffixes[end], occ, base=nargs)
        occ["a"] = nargs
        return ("call", receiver, name, nargs, occ["id"]), end + 1

    def arguments(self, call_suffix, occ, base=0):
        """Walk a call's arguments; returns how many. A lambda is tagged with where it binds.

        A trailing lambda always binds to the *last* parameter (position ``-1``). One
        inside the parentheses binds by position, or to any parameter when the
        argument is named (``-2``); either way the resolver asks whether that
        parameter's type gives the lambda a receiver.
        """
        count = 0
        args = first(call_suffix, "valueArguments")
        if args is not None:
            for argument in children(args, "valueArgument"):
                expression = first(argument, "expression")
                named = any(rule(c) == "simpleIdentifier" for c in argument.children or [])
                spread = any(isinstance(c, TerminalNode) and c.getText() == "*" for c in argument.children or [])
                if occ is not None and _is_lambda(expression):
                    self.pending_lambda = (occ["id"], -2 if named else base + count)
                described = self.walk(expression)
                self.pending_lambda = None
                if occ is not None:
                    occ["args"].append(("lambda", self.lambda_result) if _is_lambda(expression) else described)
                    occ["argnames"].append(
                        name_of_identifier(first(argument, "simpleIdentifier")) if named else ("*" if spread else None))
                    occ["named"] = occ["named"] or named or spread
                    if described is not None and described[0] == "call" and not named and not spread:
                        self.c.out.occurrences[described[4]]["arg_of"] = (occ["id"], base + count)
                count += 1
        for c in call_suffix.children or []:
            if rule(c) in ("annotatedLambda", "labeledLambda"):
                lam = first(c, "lambdaLiteral")
                if occ is not None:
                    self.pending_lambda = (occ["id"], -1)
                self.walk(lam)
                self.pending_lambda = None
                if occ is not None:
                    occ["args"].append(("lambda", self.lambda_result))
                    occ["argnames"].append(None)
                count += 1
        return count


# -- helpers ---------------------------------------------------------------
def name_of_identifier(simple_identifier) -> str:
    return simple_identifier.start.text.strip("`")


def _token_name(token) -> str:
    from openunderstand.gen.kotlin.KotlinLexer import KotlinLexer

    names = KotlinLexer.symbolicNames
    return names[token.type] if 0 <= token.type < len(names) else ""


def _is_lambda(expression) -> bool:
    """Whether an argument expression is, directly, a lambda literal."""
    node = expression
    while node is not None and not isinstance(node, TerminalNode):
        if rule(node) in ("lambdaLiteral", "anonymousFunction"):
            return True
        kids = [c for c in node.children or [] if not (isinstance(c, TerminalNode) and not c.symbol.text.strip())]
        if len(kids) != 1:
            return False
        node = kids[0]
    return False


def _call_index(suffixes, at):
    """Index of the callSuffix at or after ``at`` if only type arguments lie between."""
    i = at
    while i < len(suffixes) and rule(suffixes[i]) == "typeArguments":
        i += 1
    if i < len(suffixes) and rule(suffixes[i]) == "callSuffix":
        return i
    return None


def _identifiers(ctx) -> list:
    """Names declared by a lambda parameter, a property head or a for variable."""
    names = []

    def visit(node):
        for c in node.children or []:
            if isinstance(c, TerminalNode):
                continue
            r = rule(c)
            if r == "variableDeclaration":
                ident = first(c, "simpleIdentifier")
                if ident is not None:
                    names.append(name_of_identifier(ident))
            elif r in ("type_", "expression", "propertyDelegate"):
                continue
            else:
                visit(c)

    visit(ctx)
    return names


def _identifiers_in(ctx, rules) -> list:
    names = []
    for c in ctx.children or []:
        if isinstance(c, TerminalNode):
            continue
        if rule(c) in rules:
            names.extend(_identifiers(c) if rule(c) == "multiVariableDeclaration" else [name_of_identifier(first(c, "simpleIdentifier"))])
        elif rule(c) not in ("expression", "controlStructureBody"):
            names.extend(_identifiers_in(c, rules))
    return names
