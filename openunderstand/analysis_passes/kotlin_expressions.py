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

Not walked: anonymous objects and anonymous functions, callable references
(``::f``), annotations, types. Not resolved: ``==`` (``equals``), the name-based and
bracketed destructuring forms, a lambda parameter's destructuring, and property
delegates' ``getValue``.
"""

from __future__ import annotations

from antlr4.tree.Tree import TerminalNode

from openunderstand.analysis_passes.kotlin_tree import (
    children,
    first,
    has_equals,
    name_of,
    name_pos,
    rule,
)

_SKIPPED = {
    "objectLiteral",
    "anonymousFunction",
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

    def lookup(self, name: str):
        env = self
        while env is not None:
            if name in env.names:
                return env.names[name]
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


class ExprWalker:
    """One owner's code. ``collector`` supplies declarations for locals."""

    def __init__(self, collector, owner, scope, env: Env, receiver_lambda: bool = False):
        self.c = collector
        self.owner = owner
        self.scope = tuple(scope)
        self.env = env
        self.lambdas: list = []  # (call id, argument position) enclosing the code
        self.lambda_depth = 0
        self.receiver_lambda_next = receiver_lambda
        self.pending_lambda = None  # (call id, position) of the lambda being entered
        self.last = None  # the occurrence a following `++` may turn into a modify

    # -- recording ---------------------------------------------------------
    def occurrence(self, kind, name, line, col, receiver=None, nargs=0, mode="use", binding=None,
                   op=False, alt=None):
        occ = {
            "id": len(self.c.out.occurrences),
            "o": self.owner,
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
            "sym": False,    # an operator written as a symbol (see op_call)
            "loop": None,    # for `iterator`/`hasNext`/`next`: the loop's iterable
        }
        self.c.out.occurrences.append(occ)
        return occ

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
                i += 2
        return current

    def r_rangeTest(self, ctx, mode):
        """``when (x) { in a..b -> }``: ``(a..b).contains(x)``."""
        operator = first(ctx, "inOperator")
        container = self.walk(first(ctx, "expression"))
        self.op_call(container, "contains", 1, operator.start)
        return None

    def r_asExpression(self, ctx, mode):
        kids = [c for c in ctx.children or [] if rule(c) is not None]
        desc = self.walk(kids[0], mode if len(kids) == 1 else None)
        if len(kids) > 1:
            named = name_of(kids[-1])
            return ("cast", named) if named else None
        return desc

    def r_lambdaLiteral(self, ctx, mode):
        outer, depth = self.env, self.lambda_depth
        self.env = outer.child()
        self.lambda_depth += 1
        if self.pending_lambda is not None:
            self.lambdas.append(self.pending_lambda)
            pushed = True
        else:
            pushed = False
        self.pending_lambda = None
        params = first(ctx, "lambdaParameters")
        if params is None:
            self.env.names["it"] = ("shadow",)
        else:
            for p in children(params, "lambdaParameter"):
                for ident in _identifiers(p):
                    self.env.names[ident] = ("shadow",)
        self.generic(ctx)
        self.env, self.lambda_depth = outer, depth
        if pushed:
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
            if rule(c) in ("propertyDelegate",):
                descriptor = None
                self.walk(c)
            elif rule(c) == "expression":
                descriptor = self.walk(c)
        if self.lambda_depth > 0:
            for ident in _identifiers(head):
                self.env.names[ident] = ("shadow",)
        else:
            self.c.local(ctx, self.scope, self.env, descriptor, self.components(head, descriptor))
        accessors = first(ctx, "propertyAccessors")
        if accessors is not None:
            self.generic(accessors)
        return None

    def components(self, holder, value):
        """``componentN`` calls for ``val (a, b) = value``: one per entry, or ``None`` for none.

        Only the positional form with parentheses and no ``= name`` entries is the ordinary
        destructuring; the name-based and bracketed forms are newer and left alone.
        """
        multi = first(holder, "multiVariableDeclaration")
        if multi is None or value is None or not multi.getText().startswith("("):
            return None
        entries = children(multi, "destructuringEntry")
        if any(has_equals(e) for e in entries):
            return None
        out = []
        # at the opening parenthesis, not on an entry's name: the name is where that variable is
        # defined, and one position carries one kind of reference
        for position, entry in enumerate(entries, 1):
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
            self.c.for_variables(ctx, self.scope, self.env, element, entries)
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
        self.generic(ctx)
        self.env = outer
        return None

    # a local declaration inside a body
    def r_classDeclaration(self, ctx, mode):
        if self.lambda_depth == 0:
            self.c.klass(ctx, list(self.scope), False, False)
        return None

    def r_objectDeclaration(self, ctx, mode):
        if self.lambda_depth == 0:
            self.c.obj(ctx, list(self.scope), False)
        return None

    def r_functionDeclaration(self, ctx, mode):
        if self.lambda_depth == 0:
            key = self.c.function(ctx, list(self.scope), False, False, None, env=self.env)
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

    # -- the chain `a.b(c).d` ---------------------------------------------
    def chain(self, primary, suffixes, mode):
        index = 0
        current = None
        final_mode = mode or "use"
        has_more = bool(suffixes)
        kind = rule(primary) if primary is not None else None
        if kind == "simpleIdentifier":
            name, line, col = name_pos(primary)
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
        elif kind in ("callableReference",):
            return None
        elif primary is not None:
            self.walk(primary)
        while index < len(suffixes):
            s = suffixes[index]
            sr = rule(s)
            last_one = index == len(suffixes) - 1
            if sr == "navigationSuffix":
                operator = s.children[0].getText().strip() if s.children else ""
                if operator == "::":
                    return None
                ident = first(s, "simpleIdentifier")
                if ident is None:  # `.class` or `.(expr)`
                    self.walk(first(s, "parenthesizedExpression"))
                    current = None
                    index += 1
                    continue
                name, line, col = name_pos(ident)
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
                    occ["args"].append(("lambda",) if _is_lambda(expression) else described)
                    occ["named"] = occ["named"] or named or spread
                count += 1
        for c in call_suffix.children or []:
            if rule(c) in ("annotatedLambda", "labeledLambda"):
                lam = first(c, "lambdaLiteral")
                if occ is not None:
                    self.pending_lambda = (occ["id"], -1)
                self.walk(lam)
                self.pending_lambda = None
                if occ is not None:
                    occ["args"].append(("lambda",))
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
        if rule(node) == "lambdaLiteral":
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
