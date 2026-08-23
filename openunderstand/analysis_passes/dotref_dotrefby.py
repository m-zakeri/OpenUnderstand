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
            if identifier is None:
                call = node.methodCall()
                identifier = call.IDENTIFIER() if call is not None else None
                if identifier is None:
                    return None
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
