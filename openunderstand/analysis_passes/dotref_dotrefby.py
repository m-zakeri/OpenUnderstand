from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties


class DotRef_DotRefBy(JavaParserLabeledListener):
    """Collect `Java DotRef`: a *type* used as the receiver of a dotted expression.

    `Character.forDigit(...)`, `JSONObject.testValidity(v)`, `Locale.ROOT` --
    Understand points at the receiver's identifier and scopes the reference to
    the enclosing method:

        Cookie.java:59:27  scope=org.json.Cookie.escape  ent=java.lang.Character

    A receiver that is a *variable* is not a DotRef -- `sb.append(...)` is a Use
    Deref Partial. This pass used to accept any receiver whose text appeared in
    a list of class names, which is why it needs the type test below.

    The state used to live in class attributes -- `implement = []` at class
    scope, mutated through `self.implement.append(...)`. Every instance shared
    one list, so each file re-emitted everything collected before it: the
    references for CookieList.java were written again against HTTP.java,
    HTTPTokener.java and every file after them. 2973 rows on TheAlgorithms, none
    of which matched Understand.
    """

    def __init__(self):
        self.package_name = ""
        self.imports = {}
        self.wildcards = []
        self.implement = []

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.package_name = ctx.qualifiedName().getText()

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        longname = ctx.qualifiedName().getText()
        if ctx.getText().rstrip(";").endswith(".*"):
            # `import java.util.*` names a package, so the last segment is not
            # an importable type -- registering it made `util` one. Kept as a
            # package instead: it is how `KeyboardFocusManager` is reached in
            # a file whose only mention of java.awt is `import java.awt.*`,
            # and jhotdraw writes 148 of its receivers that way.
            self.wildcards.append(longname)
            return
        self.imports[longname.split(".")[-1]] = longname

    def enterExpression1(self, ctx: JavaParserLabeled.Expression1Context):
        self._qualified_prefix(ctx)
        if not ctx.DOT() or ctx.expression() is None:
            return
        receiver = ctx.expression().getText()
        # Only a bare name can be a type here. Anything else is a chained call
        # or an indexed access -- `sb.append(x).append(y)`, `a[i].f` -- whose
        # receiver is a value, not a type.
        if not receiver.isidentifier():
            return
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        scope_longname = ".".join(parents)
        # Resolved from the asking scope: `Node` is declared in several
        # packages, and without it the name binds to whichever was indexed
        # first rather than the one this file would actually see.
        longname = self.resolve_type(receiver, scope_longname)
        if longname is None:
            return
        token = ctx.start
        self.implement.append(
            {
                "scope_longname": scope_longname,
                "refent_name": receiver,
                "refent_longname": longname,
                "line": token.line,
                "col": token.column,
            }
        )

    def enterPrimary5(self, ctx: JavaParserLabeled.Primary5Context):
        """`Integer.class`, `Map.Entry.class`: a DotRef to the head type at
        its token, scoped like any expression. 960 rows over eight fixtures.
        A lowercase head is a package -- `java.lang.String.class` -- which
        Understand walks as an expression instead, so it is left alone.
        A literal that is itself a receiver -- `Map.class.isAssignableFrom(t)`
        -- is a plain Use."""
        type_ctx = ctx.typeTypeOrVoid().typeType()
        named = type_ctx.classOrInterfaceType() if type_ctx is not None else None
        if named is None:
            return
        outer = getattr(ctx.parentCtx, "parentCtx", None)
        receiver = (
            isinstance(outer, JavaParserLabeled.Expression1Context)
            and outer.expression() is ctx.parentCtx
        )
        self._head_type(
            ctx, named.IDENTIFIER()[0].symbol, "Java Use" if receiver else None
        )

    def enterExpression23(self, ctx: JavaParserLabeled.Expression23Context):
        """`Objects::nonNull` -- a method reference on a type."""
        receiver = ctx.expression()
        if receiver.getText().isidentifier():
            self._head_type(ctx, receiver.start)

    def enterExpression24(self, ctx: JavaParserLabeled.Expression24Context):
        """`List<String>::size` -- the typeType form; `TreeMap::new` is a
        plain Use."""
        named = ctx.typeType().classOrInterfaceType()
        if named is not None:
            self._head_type(
                ctx,
                named.IDENTIFIER()[0].symbol,
                "Java Use" if ctx.NEW() is not None else None,
            )

    def _head_type(self, ctx, token, kind=None):
        name = token.text
        if not name[:1].isupper():
            return
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        scope_longname = ".".join(parents)
        longname = self.resolve_type(name, scope_longname)
        if longname is None:
            return
        self.implement.append(
            {
                "scope_longname": scope_longname,
                "refent_name": name,
                "refent_longname": longname,
                "line": token.line,
                "col": token.column,
                **({"kind": kind} if kind else {}),
            }
        )

    # ------------------------------------------- a name written out in full

    def _qualified_prefix(self, ctx):
        """The prefix of a qualified name used as an expression.

        Understand walks a dotted expression segment by segment and writes one
        reference per *entity* in it, each at the segment where that entity's
        own name ends. `java.lang.System.out.println(...)` is a Use of
        java.lang at the `lang`, a Use of java.lang.System at the `System`, a
        Use of java.lang.System.out at the `out` and the Call at the
        `println` -- and nothing at the `java`, because no entity is named
        that.

        What this adds is the package and the type. The member steps belong to
        the field and call passes, which already own them.

        The head segment is the exception: when the package *is* the head --
        `p.Helper.help()`, `p.R.shared` -- Understand writes `Java DotRef`
        there rather than `Java Use`, the same kind it writes for a receiver
        named by a simple name. Verified against Understand on a hand-written
        fixture covering both.

        Nothing is written when no prefix names a type this project or the JDK
        index knows. Understand invents an unresolved entity per segment
        instead; this project refuses bare simple names as targets, because
        merge_placeholder_entities() would fold them into whichever project
        entity happens to share the name.
        """
        if isinstance(getattr(ctx, "parentCtx", None), JavaParserLabeled.Expression1Context):
            return  # only the outermost link of the chain walks the whole of it
        tokens = self._dotted_chain(ctx)
        if tokens is None or len(tokens) < 3:
            return
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        scope_longname = ".".join(parents)
        names = [t.text for t in tokens]
        index = self._type_prefix(names)
        if index is None:
            self._external_chain(ctx, tokens, scope_longname)
            return
        for position, longname, kind in (
            (index - 1, ".".join(names[:index]), "Java DotRef" if index == 1 else "Java Use"),
            (index, ".".join(names[: index + 1]), "Java Use"),
        ):
            self.implement.append(
                {
                    "scope_longname": scope_longname,
                    "refent_name": longname.rsplit(".", 1)[-1],
                    "refent_longname": longname,
                    "line": tokens[position].line,
                    "col": tokens[position].column,
                    "kind": kind,
                }
            )

    def _external_chain(self, ctx, tokens, scope_longname):
        """A qualified name into a library outside the analysed source.

        `org.evosuite.runtime.RuntimeSettings.className = ...` names nothing
        the project or the JDK index knows. Understand still walks it segment
        by segment, read off its database for an EvoSuite scaffolding file:

        * the longest prefix the file has named as a *package* elsewhere -- in
          an import, or a qualified type -- is one `Java Use` of that Unknown
          Package at its last segment: `org.evosuite.runtime.thread` at the
          `thread`, because `org.evosuite.runtime.thread.ThreadStopper` is
          written as a type on the same line;
        * once a segment completes a class the file has named, nothing more is
          written for the chain: `org.evosuite.runtime.sandbox.Sandbox
          .SandboxMode.RECOMMENDED` is the package Use and nothing else;
        * every other segment, from the head when no package is known, is a
          `Java Use` of a bare-named Unknown Variable -- `org`, `evosuite`,
          `runtime`, `RuntimeSettings`, `className` -- up to the first call,
          which the call pass already writes as a bare Unknown Method.

        Only the shape a package name can have: at least two lower-case
        segments and then a capitalised one, with a head that is no variable,
        field or type in scope. `obj.field.method()` never qualifies, and a
        head the type table can resolve is someone else's reference. The
        bare names are safe from merge_placeholder_entities(), which leaves a
        bare Unknown Variable alone (see there).
        """
        names, lead = _external_shape(tokens)
        if names is None or _head_in_scope(ctx, names[0], scope_longname):
            return
        packages, classes = _named_externals(ctx)
        start = 0
        for end in range(lead, 0, -1):
            package = ".".join(names[:end])
            if package in packages:
                self._chain_ref(scope_longname, package, tokens[end - 1],
                                "Java DotRef" if end == 1 else "Java Use",
                                "Java Unknown Package")
                start = end
                break
        for position in range(start, len(names)):
            if start and ".".join(names[: position + 1]) in classes:
                return
            self._chain_ref(scope_longname, names[position], tokens[position],
                            "Java Use", "Java Unknown Variable Member")

    def _chain_ref(self, scope_longname, longname, token, kind, ent_kind):
        self.implement.append(
            {
                "scope_longname": scope_longname,
                "refent_name": longname.rsplit(".", 1)[-1],
                "refent_longname": longname,
                "line": token.line,
                "col": token.column,
                "kind": kind,
                "ent_kind": ent_kind,
            }
        )

    @staticmethod
    def _type_prefix(names):
        """Index of the segment completing the longest prefix naming a type.

        Longest first, so `a.b.Outer.Inner` binds to the nested class rather
        than to its enclosing one. None when the name is not written out in
        full: `Collections.emptyList()` has no qualified prefix, and its
        receiver is the head, which the simple-name handler above already
        turns into a DotRef.
        """
        from openunderstand.ounderstand import symbol_table

        for end in range(len(names) - 1, 0, -1):
            if symbol_table.is_type_longname(".".join(names[: end + 1])):
                return end
        return None

    @staticmethod
    def _dotted_chain(ctx):
        """The identifier tokens of `a.b.c` / `a.b.c(...)`, or None.

        Anything else in the chain -- an index, a cast, a call on a call --
        means the head is a value rather than a name, and the reference the
        expression carries is not this one.
        """
        tokens = []
        node = ctx
        while isinstance(node, JavaParserLabeled.Expression1Context):
            identifier = node.IDENTIFIER()
            is_call = False
            if identifier is None:
                call = node.methodCall()
                # `super(...)`/`this(...)` (methodCall1/2) carry no identifier.
                identifier = (
                    getattr(call, "IDENTIFIER", lambda: None)()
                    if call is not None
                    else None
                )
                if identifier is None:
                    return None
                is_call = True
            identifier.symbol._ou_call = is_call
            tokens.append(identifier.symbol)
            node = node.expression()
        if not isinstance(node, JavaParserLabeled.Expression0Context):
            return None
        primary = node.primary()
        if not isinstance(primary, JavaParserLabeled.Primary4Context):
            return None
        tokens.append(primary.IDENTIFIER().symbol)
        tokens.reverse()
        return tokens

    def resolve_type(self, name, scope_longname=""):
        """Long name if `name` denotes a type, else None.

        The shared ladder rather than a fourth copy of it. The copy this
        replaces knew the file's single-type imports, the project and
        java.lang, and nothing else -- so a receiver reached through
        `import java.awt.*` resolved to nothing and its `Java DotRef` was
        never written. That is 1,935 of jhotdraw's missing DotRef rows,
        148 of them java.awt alone.
        """
        # Deferred: openunderstand.ounderstand's __init__ reaches oudb.api ->
        # parsing_process -> the module that imports this pass.
        from openunderstand.ounderstand import symbol_table

        return symbol_table.resolve_type_name(
            name, self.imports, self.wildcards, scope_longname
        )


#: id(tree root) -> (packages, classes) the file names outside the project.
_EXTERNALS = {}


def _named_externals(ctx):
    """Packages and classes a file names in imports and qualified types.

    What Understand treats as known when it walks a chain into a library it
    cannot see: `import org.evosuite.runtime.sandbox.Sandbox` makes the
    package and the class known, and so does writing
    `org.evosuite.runtime.thread.ThreadStopper` as a type. Per file -- a
    package another file imports does not count, measured on the same chain
    in a file that does not.
    """
    root = ctx
    while root.parentCtx is not None:
        root = root.parentCtx
    key = id(root)
    if key in _EXTERNALS and _EXTERNALS[key][0] is root:
        return _EXTERNALS[key][1]
    packages, classes = set(), set()

    def name(parts):
        if len(parts) < 2 or not parts[0][:1].islower():
            return
        classes.add(".".join(parts))
        packages.add(".".join(parts[:-1]))

    stack = [root]
    while stack:
        node = stack.pop()
        if isinstance(node, JavaParserLabeled.ImportDeclarationContext):
            written = node.qualifiedName().getText()
            if node.getText().rstrip(";").endswith(".*"):
                packages.add(written)
            else:
                name(written.split("."))
            continue
        if isinstance(node, (JavaParserLabeled.ClassOrInterfaceTypeContext,
                             JavaParserLabeled.CreatedName0Context)):
            name([i.getText() for i in node.IDENTIFIER()])
        stack.extend(c for c in (getattr(node, "children", None) or ())
                     if hasattr(c, "getRuleIndex"))
    if len(_EXTERNALS) > 64:
        _EXTERNALS.clear()
    _EXTERNALS[key] = (root, (packages, classes))
    return packages, classes


def _external_shape(tokens):
    """`(member names, lower-case lead)` if the chain can be a package path.

    Members stop at the first call. At least two lower-case segments, then a
    capitalised one: `org.evosuite.runtime.RuntimeSettings`, never
    `obj.field.method()`. `(None, 0)` otherwise.
    """
    members = len(tokens)
    for position, token in enumerate(tokens):
        if position and getattr(token, "_ou_call", False):
            members = position
            break
    names = [t.text for t in tokens[:members]]
    lead = 0
    while lead < len(names) and names[lead][:1].islower():
        lead += 1
    if lead < 2 or lead >= len(names) or not names[lead][:1].isupper():
        return None, 0
    return names, lead


#: id(tree root) -> (root, TypeBinder): one type table per file, shared.
_BINDERS = {}


def _binder(ctx):
    from openunderstand.ounderstand.type_binding import TypeBinder

    root = ctx
    while root.parentCtx is not None:
        root = root.parentCtx
    cached = _BINDERS.get(id(root))
    if cached is None or cached[0] is not root:
        if len(_BINDERS) > 64:
            _BINDERS.clear()
        cached = _BINDERS[id(root)] = (root, TypeBinder(root, ""))
    return cached[1]


def _head_in_scope(ctx, head, scope_longname):
    """Whether a chain's head is a type, variable or field visible here."""
    from openunderstand.ounderstand import symbol_table

    binder = _binder(ctx)
    if symbol_table.resolve_type_name(head, binder.imports, binder.wildcards, scope_longname):
        return True
    if binder.name_type(head, ctx) is not None:
        return True
    owner = binder.enclosing_type(ctx)  # an inherited field the file does not declare
    return bool(owner) and symbol_table.member_type(owner, head) is not None


def starts_external_chain(receiver_ctx):
    """Whether this head identifier begins a chain `_external_chain` writes.

    use_variants asks before writing `Use Deref Partial` on a receiver: for
    `org.evosuite.runtime.GuiSupport.initialize()` the head `org` is not a
    variable being dereferenced, and the chain's own references -- written by
    this pass -- are the whole of what Understand reports there.
    """
    outer = receiver_ctx.parentCtx
    if not isinstance(outer, JavaParserLabeled.Expression1Context):
        return False
    while isinstance(outer.parentCtx, JavaParserLabeled.Expression1Context):
        outer = outer.parentCtx
    tokens = DotRef_DotRefBy._dotted_chain(outer)
    if tokens is None or len(tokens) < 3:
        return False
    if DotRef_DotRefBy._type_prefix([t.text for t in tokens]) is not None:
        return False
    names, _ = _external_shape(tokens)
    if names is None:
        return False
    parents = class_properties.ClassPropertiesListener.findParents(receiver_ctx)
    return not _head_in_scope(receiver_ctx, names[0], ".".join(parents))
