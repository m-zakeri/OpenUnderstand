"""Typed source spans from the OpenUnderstand Kotlin parse tree, in the PSI
vocabulary, so the two can be compared set against set.

The grammar is flat per precedence level (`a + b + c` is one additiveExpression)
where PSI nests left, so chains are unrolled here: that unrolling is exactly the
claim being tested (associativity and grouping)."""
import sys
sys.path.insert(0, __import__("os").path.join(__import__("os").path.dirname(__file__), "pyparser"))
from antlr4 import InputStream, CommonTokenStream
from antlr4.tree.Tree import TerminalNode
from KotlinLexer import KotlinLexer
from KotlinParser import KotlinParser

NL = KotlinLexer.NL
CHAINS = {  # rule -> operand rule
    "disjunction": "conjunction", "conjunction": "equality", "equality": "comparison",
    "comparison": "infixOperation", "elvisExpression": "infixFunctionCall",
    "infixFunctionCall": "rangeExpression", "rangeExpression": "additiveExpression",
    "additiveExpression": "multiplicativeExpression", "multiplicativeExpression": "asExpression",
}
SIMPLE = {  # rule -> PSI kind
    "functionDeclaration": "FUNCTION", "propertyDeclaration": "PROPERTY", "classDeclaration": "CLASS",
    "objectDeclaration": "OBJECT_DECLARATION", "typeAlias": "TYPEALIAS", "ifExpression": "IF",
    "whenExpression": "WHEN", "tryExpression": "TRY", "forStatement": "FOR", "whileStatement": "WHILE",
    "doWhileStatement": "DO_WHILE", "lambdaLiteral": "LAMBDA_EXPRESSION", "parenthesizedExpression": "PARENTHESIZED",
    "valueArgument": "VALUE_ARGUMENT", "valueArguments": "VALUE_ARGUMENT_LIST", "typeArguments": "TYPE_ARGUMENT_LIST",
    "functionType": "FUNCTION_TYPE", "typeParameter": "TYPE_PARAMETER", "stringLiteral": "STRING_TEMPLATE",
    "collectionLiteral": "COLLECTION_LITERAL_EXPRESSION",
    "functionValueParameter": "VALUE_PARAMETER", "classParameter": "VALUE_PARAMETER",
    "enumEntry": "ENUM_ENTRY", "secondaryConstructor": "SECONDARY_CONSTRUCTOR",
    "getter": "PROPERTY_ACCESSOR", "setter": "PROPERTY_ACCESSOR", "whenEntry": "WHEN_ENTRY",
    "catchBlock": "CATCH", "companionObject": "OBJECT_DECLARATION", "anonymousFunction": "FUNCTION", "finallyBlock": "FINALLY",
}

class Ex:
    def __init__(self, tokens, names, src):
        self.tokens, self.names, self.out, self.src, self.fn_fix = tokens, names, [], src, {}

    def rule(self, n):
        return self.names[n.getRuleIndex()] if hasattr(n, "getRuleIndex") else None

    def span(self, n):
        """(start, end) chars, ignoring NL tokens at both edges."""
        if isinstance(n, TerminalNode):
            t = n.symbol
            return t.start, t.stop + 1
        a, b = n.start.tokenIndex, n.stop.tokenIndex if n.stop else n.start.tokenIndex
        toks = self.tokens.tokens
        skip = lambda t: t.type == NL or t.channel != 0
        while a < b and skip(toks[a]): a += 1
        while b > a and skip(toks[b]): b -= 1
        e = toks[b].stop + 1
        while e > toks[a].start and self.src[e - 1].isspace(): e -= 1   # `?` lexes with its trailing blank
        return toks[a].start, e

    def kids(self, n):
        return [c for c in (n.children or []) if not (isinstance(c, TerminalNode) and c.symbol.type == NL)]

    def add(self, kind, a, b):
        self.out.append((kind, a, b))

    def visit(self, n):
        if isinstance(n, TerminalNode):
            return
        r = self.rule(n)
        if n.stop is None and n.start is not None and n.children is None:
            return
        if r in SIMPLE:
            self.add(SIMPLE[r], *self.span(n))
        if r in CHAINS or r in ("infixOperation", "asExpression"):
            self.chain(n, r)
        elif r == "expressionStatement":
            k = self.kids(n)
            if len(k) > 1:
                self.add("BINARY_EXPRESSION", *self.span(n))
        elif r == "destructuringAssignment":
            par = [c for c in self.kids(n.parentCtx) if self.rule(c) == "annotation"] if self.rule(n.parentCtx) in ("statement", "controlStatement") else []
            self.add("DESTRUCTURING_DECLARATION", self.span(par[0])[0] if par else self.span(n)[0], self.span(n)[1])
        elif r == "variableDeclaration" and self.rule(n.parentCtx) == "lambdaParameter":
            self.add("VALUE_PARAMETER", *self.span(n))
        elif r == "whenSubject" and any(c.getText() == "val" for c in self.kids(n)):
            self.add("PROPERTY", self.span([c for c in self.kids(n) if c.getText() == "val"][0])[0], self.span(n)[1])
        elif r == "valueArgument" and any(self.rule(c) == "annotation" for c in self.kids(n)):
            a0 = [c for c in self.kids(n) if self.rule(c) == "annotation"][0]
            self.add("ANNOTATED_EXPRESSION", self.span(a0)[0], self.span(n)[1])
        elif r in ("annotatedLambda", "labeledLambda"):
            k = self.kids(n); lab = [c for c in k if self.rule(c) == "label"]; ann = [c for c in k if self.rule(c) == "annotation"]
            if lab: self.add("LABELED_EXPRESSION", self.span(lab[0])[0], self.span(n)[1])
            if ann: self.add("ANNOTATED_EXPRESSION", self.span(ann[0])[0], self.span(n)[1])
        elif r == "type_" and self.rule(n.parentCtx) == "functionTypeParameters":
            self.add("VALUE_PARAMETER", *self.span(n))      # unnamed parameter of a function type
        elif r == "setter" and any(self.rule(c) == "setterParameter" for c in self.kids(n)):
            k = self.kids(n); sp = [c for c in k if self.rule(c) == "setterParameter"][0]
            first = [c for c in k if self.rule(c) in ("annotation", "parameterModifier") or c is sp][0]
            self.add("VALUE_PARAMETER", self.span(first)[0], self.span(sp)[1])   # annotations belong to the parameter
        elif r == "catchBlock":
            k = self.kids(n); ut = [c for c in k if self.rule(c) == "userType"][0]
            first = [c for c in k if self.rule(c) in ("annotation", "simpleIdentifier")][0]
            self.add("VALUE_PARAMETER", self.span(first)[0], self.span(ut)[1])
        elif r == "contextParameter" and any(c.getText() == ":" for c in self.kids(n)):
            self.add("VALUE_PARAMETER", *self.span(n))      # named; an unnamed one is a CONTEXT_RECEIVER
        elif r == "lambdaParameter" and any(self.rule(c) == "multiVariableDeclaration" for c in self.kids(n)):
            self.add("VALUE_PARAMETER", *self.span(n))
        elif r in ("variableDeclaration", "multiVariableDeclaration") and self.rule(n.parentCtx) == "forStatement":
            self.add("VALUE_PARAMETER", *self.span(n))
            if r == "multiVariableDeclaration": self.add("DESTRUCTURING_DECLARATION", *self.span(n))
        elif r == "anonymousFunctionParameter":
            self.add("VALUE_PARAMETER", *self.span(n))
        elif r == "parameter" and self.rule(n.parentCtx) != "functionValueParameter":
            self.add("VALUE_PARAMETER", *self.span(n))
        elif r == "identifier":
            ks = [c for c in self.kids(n) if self.rule(c) == "simpleIdentifier"]
            for i in range(1, len(ks)):
                self.add("DOT_QUALIFIED_EXPRESSION", self.span(ks[0])[0], self.span(ks[i])[1])
        elif r == "multiVariableDeclaration" and self.rule(n.parentCtx) in ("forStatement", "lambdaParameter"):
            self.add("DESTRUCTURING_DECLARATION", *self.span(n))
        elif r in ("statement", "controlStatement"):
            k = self.kids(n); end = self.span(n)[1]
            sa = [c for c in k if self.rule(c) == "statementAnnotation"]
            if sa: self.add("ANNOTATED_EXPRESSION", self.span(sa[0])[0], end)
            ann = [c for c in k if self.rule(c) == "annotation"]
            if ann and any(self.rule(c) == "loopStatement" for c in k):
                self.add("ANNOTATED_EXPRESSION", self.span(ann[0])[0], end)
            for c in k:
                if self.rule(c) == "label": self.add("LABELED_EXPRESSION", self.span(c)[0], end)
        elif r == "controlStatement" or r == "statement":
            pass
        elif r == "functionType":
            ctx = [c for c in (n.parentCtx.children or []) if self.rule(c) == "typeModifiers"] if n.parentCtx is not None else []
            for tm in ctx:
                for m in self.kids(tm):
                    cp = [x for x in self.kids(m) if self.rule(x) == "contextParameters"]
                    if cp:
                        self.out = [o for o in self.out if not (o[0] == "FUNCTION_TYPE" and o[1] == self.span(n)[0] and o[2] == self.span(n)[1])]
                        self.add("FUNCTION_TYPE", self.span(cp[0])[0], self.span(n)[1])
        elif r == "prefixUnaryExpression":
            self.prefix(n)
        elif r == "postfixUnaryExpression":
            self.postfix(n)
        elif r == "jumpExpression":
            first = self.kids(n)[0].getText()
            kind = {"throw": "THROW", "return": "RETURN", "continue": "CONTINUE", "break": "BREAK"}.get(
                first, "RETURN" if first.startswith("return") else "CONTINUE" if first.startswith("continue") else "BREAK")
            self.add(kind, *self.span(n))
        elif r == "callableReference":
            k = self.kids(n)
            self.add("CLASS_LITERAL_EXPRESSION" if k[-1].getText() == "class" else "CALLABLE_REFERENCE_EXPRESSION", *self.span(n))
        elif r == "propertyDeclaration" and any(self.rule(x) == "multiVariableDeclaration" for x in self.kids(self.kids(n)[0])):
            self.out = [o for o in self.out if not (o[0] == "PROPERTY" and (o[1], o[2]) == self.span(n))]
            self.add("DESTRUCTURING_DECLARATION", *self.span(n))
        elif r == "objectLiteral":
            self.add("OBJECT_LITERAL", *self.span(n)); self.add("OBJECT_DECLARATION", *self.span(n))
        elif r == "userType":
            ks = [c for c in self.kids(n) if self.rule(c) == "simpleUserType"]
            for i in range(len(ks)):
                self.add("USER_TYPE", self.span(ks[0])[0], self.span(ks[i])[1])
        elif r == "nullableType" and self.rule(n.parentCtx) != "callableReference":
            k = self.kids(n)
            q = [c for c in n.getChildren() if isinstance(c, TerminalNode) or self.rule(c) == "quest"]
            qs = [c for c in k if self.rule(c) == "quest"]
            s0 = self.span(k[0])[0]
            for c in qs:
                self.add("NULLABLE_TYPE", s0, self.span(c)[1])
        if (r == "receiverType" or r == "nullableType") and self.rule(n.parentCtx) == "callableReference":
            self.receiver(n)
            return
        mark = len(self.out)
        for c in n.children or []:
            self.visit(c)
        if r in ("statement", "controlStatement"):
            self.bind_label(n, mark)

    def receiver(self, n):
        """PSI reads a callable reference's receiver as an expression: `a.b<c>` is a
        dot of `a` and a call `b<c>` with no arguments, and `?` just extends it."""
        ut = None
        def find(x):
            nonlocal ut
            if ut is None and self.rule(x) == "userType": ut = x
            for c in getattr(x, "children", None) or []:
                if not isinstance(c, TerminalNode): find(c)
        find(n)
        if ut is None: return
        segs = [c for c in self.kids(ut) if self.rule(c) == "simpleUserType"]
        first = self.span(segs[0])[0]
        for i, sg in enumerate(segs):
            ta = [c for c in self.kids(sg) if self.rule(c) == "typeArguments"]
            if ta: self.add("CALL_EXPRESSION", self.span(sg)[0], self.span(sg)[1])
            if i: self.add("DOT_QUALIFIED_EXPRESSION", first, self.span(sg)[1])
            for t in ta: self.visit(t)

    def bind_label(self, n, mark):
        """A statement label belongs to the first operand: `l@ a + b` is (l@ a) + b."""
        k = self.kids(n)
        labels = [c for c in k if self.rule(c) == "label"]
        es = [c for c in k if self.rule(c) == "expressionStatement"]
        if not labels or not es:
            return
        x = es[0]
        while self.rule(x) in ("expressionStatement", "expression") or self.rule(x) in CHAINS or self.rule(x) in ("infixOperation", "asExpression"):
            x = self.kids(x)[0]
        a, b = self.span(x)
        ls = self.span(labels[0])[0]
        for idx in range(mark, len(self.out)):
            kd, s0, e0 = self.out[idx]
            if s0 == a and e0 > b and not kd.startswith("LABEL"):
                self.out[idx] = (kd, ls, e0)
        self.out = [o for o in self.out if not (o[0] == "LABELED_EXPRESSION" and o[1] == ls and o[2] == self.span(n)[1])]
        self.add("LABELED_EXPRESSION", ls, b)

    def chain(self, n, r):
        k = self.kids(n)
        if len(k) < 2: return
        operand = CHAINS.get(r)
        s0 = self.span(k[0])[0]
        i = 1
        while i < len(k):
            # collect the operator group up to the next operand (or type for is/as)
            j = i
            ops = []
            while j < len(k):
                c = k[j]
                rc = self.rule(c)
                if r in ("infixOperation", "asExpression"):
                    ops.append(c)
                    if rc in ("type_",) or (r == "infixOperation" and rc == "elvisExpression"):
                        break
                else:
                    if rc == operand and j > i - 1 and not (rc is None):
                        break
                    ops.append(c)
                j += 1
            end = self.span(k[min(j, len(k) - 1)])[1]
            if r == "asExpression": kind = "BINARY_WITH_TYPE"
            elif r == "infixOperation": kind = "IS_EXPRESSION" if self.rule(ops[0]) == "isOperator" else "BINARY_EXPRESSION"
            else: kind = "BINARY_EXPRESSION"
            self.add(kind, s0, end)
            i = j + 1

    def is_anon_fun(self, post):
        x = self.kids(post)[0]
        while x is not None and self.rule(x) in ("primaryExpression", "functionLiteral"):
            x = self.kids(x)[0]
        return self.rule(x) == "anonymousFunction"

    def prefix(self, n):
        k = self.kids(n)
        end = self.span(n)[1]
        prev = None
        for c in k[:-1]:
            if self.rule(c) != "unaryPrefix": continue
            inner = self.kids(c)[0]
            ri = self.rule(inner)
            if ri == "annotation" and prev == "annotation":   # PSI keeps adjacent annotations in one node
                continue
            prev = ri
            last = k[-1]
            if ri == "annotation" and self.rule(last) == "postfixUnaryExpression" and len(self.kids(last)) == 1 and self.is_anon_fun(last):
                self.fn_fix[self.span(last)] = self.span(c)[0]
                continue
            kind = "ANNOTATED_EXPRESSION" if ri == "annotation" else "LABELED_EXPRESSION" if ri == "label" else "PREFIX_EXPRESSION"
            self.add(kind, self.span(c)[0], end)

    def postfix(self, n):
        k = self.kids(n)
        prim = k[0]
        start = self.span(prim)[0]
        cur_end = self.span(prim)[1]
        sfx = [self.kids(c)[0] for c in k[1:]]  # postfixUnarySuffix -> its single child
        i = 0
        while i < len(sfx):
            s = sfx[i]; rs = self.rule(s)
            if rs == "postfixUnaryOperator":
                cur_end = self.span(s)[1]; self.add("POSTFIX_EXPRESSION", start, cur_end)
            elif rs == "navigationSuffix":
                kids = self.kids(s)
                op = kids[0]; opt = op.getText()
                name_start = self.span(kids[1])[0] if len(kids) > 1 else self.span(s)[1]
                sel_end = self.span(s)[1]
                j = i + 1
                if opt == "::":
                    self.add("CLASS_LITERAL_EXPRESSION" if kids[-1].getText() == "class" else "CALLABLE_REFERENCE_EXPRESSION", start, sel_end); cur_end = sel_end
                else:
                    # the first call suffix (with its type arguments) joins the selector
                    if j < len(sfx) and self.rule(sfx[j]) == "typeArguments" and j + 1 < len(sfx) and self.rule(sfx[j + 1]) == "callSuffix":
                        j += 1
                    if j < len(sfx) and self.rule(sfx[j]) == "typeArguments":   # `b<c>` before `::`
                        sel_end = self.span(sfx[j])[1]
                        self.add("CALL_EXPRESSION", name_start, sel_end)
                        i = j
                    elif j < len(sfx) and self.rule(sfx[j]) == "callSuffix":
                        while j + 1 < len(sfx) and self.rule(sfx[j + 1]) == "callSuffix" and not any(self.rule(x) == "valueArguments" for x in self.kids(sfx[j + 1])):
                            j += 1
                        sel_end = self.span(sfx[j])[1]
                        self.add("CALL_EXPRESSION", name_start, sel_end)
                        i = j
                    cur_end = sel_end
                    self.add("SAFE_ACCESS_EXPRESSION" if opt == "?." else "DOT_QUALIFIED_EXPRESSION", start, cur_end)
            elif rs == "typeArguments":
                if i + 1 < len(sfx) and self.rule(sfx[i + 1]) == "callSuffix":
                    i += 1
                    while i + 1 < len(sfx) and self.rule(sfx[i + 1]) == "callSuffix" and not any(self.rule(x) == "valueArguments" for x in self.kids(sfx[i + 1])):
                        i += 1
                    cur_end = self.span(sfx[i])[1]
                    self.add("CALL_EXPRESSION", start, cur_end)
                else:
                    cur_end = self.span(s)[1]
                    self.add("CALL_EXPRESSION", start, cur_end)   # `a<b>` before `::`
            elif rs == "callSuffix":
                cur_end = self.span(s)[1]
                while i + 1 < len(sfx) and self.rule(sfx[i + 1]) == "callSuffix" and not any(self.rule(x) == "valueArguments" for x in self.kids(sfx[i + 1])):
                    i += 1; cur_end = self.span(sfx[i])[1]
                self.add("CALL_EXPRESSION", start, cur_end)
            elif rs == "indexingSuffix":
                cur_end = self.span(s)[1]; self.add("ARRAY_ACCESS_EXPRESSION", start, cur_end)
            i += 1

def spans(text, script=False):
    lx = KotlinLexer(InputStream(text)); lx.removeErrorListeners()
    ts = CommonTokenStream(lx)
    ps = KotlinParser(ts); ps.removeErrorListeners()
    errs = []
    from antlr4.error.ErrorListener import ErrorListener
    class L(ErrorListener):
        def syntaxError(self, *a): errs.append(a[4])
    ps.addErrorListener(L())
    tree = ps.script() if script else ps.kotlinFile()
    ex = Ex(ts, ps.ruleNames, text); ex.visit(tree)
    ex.out = [(k, ex.fn_fix.get((a, b), a) if k == 'FUNCTION' else a, b) for k, a, b in ex.out]
    return ex.out, errs
