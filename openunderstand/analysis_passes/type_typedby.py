"""Java Typed / Java Typedby: what a declaration is declared as.

Understand records the reference against the *declared entity* and points it at
the type, positioned on the type's own token:

    CDL.java:55:30  scope=org.json.CDL.getValue.x   ent=org.json.JSONTokener
    CDL.java:58:9   scope=org.json.CDL.getValue.sb  ent=java.lang.StringBuilder
    CDL.java:55:14  scope=org.json.CDL.getValue     ent=java.lang.String

This pass used to emit both ends as simple names and let the write layer glue
the package on the front, which produced `org.json.x` for a local of
`CDL.getValue` and `org.json.String` for java.lang.String -- 24 of 1062
references matched Understand on JSON, 31 of 3717 on TheAlgorithms.

Understand emits no Typed for a primitive or for `void`; those were
`org.json.char` rows here.
"""

from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
import openunderstand.analysis_passes.class_properties as class_properties
from openunderstand.analysis_passes.cast_castby import _declaring_generic

#: A declaration of one of these is not a reference to anything.
PRIMITIVES = frozenset("byte short int long float double boolean char void var".split())


class TypedAndTypedByListener(JavaParserLabeledListener):
    def __init__(self):
        self.package_name = ""
        self.imports = {}
        self.wildcards = []
        self.typedBy = []
        self.dotrefs = []

    @property
    def get_type(self):
        d = {}
        d["typedBy"] = self.typedBy
        d["dotrefs"] = self.dotrefs
        return d

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.package_name = ctx.qualifiedName().getText()

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        longname = ctx.qualifiedName().getText()
        if ctx.getText().rstrip(";").endswith(".*"):
            # Kept, not discarded. `import java.util.*` is how TheAlgorithms
            # reaches Scanner, Map and HashMap, and dropping it left 273
            # Java Typed references unresolved.
            self.wildcards.append(longname)
            return
        self.imports[longname.split(".")[-1]] = longname

    # ---------------------------------------------------------------- helpers

    def resolve_type(self, name, scope_longname):
        """Long name of a type's simple name, or None if it names no type."""
        from openunderstand.ounderstand import symbol_table

        if not name or name in PRIMITIVES:
            return None
        # The shared ladder: imports, then already-qualified, then the project,
        # then java.lang, then a package the file wildcard-imports. Refusing
        # beats guessing -- a package-glued guess is what produced
        # org.json.String.
        return symbol_table.resolve_type_name(
            name, self.imports, self.wildcards, scope_longname
        )

    def record(
        self, ctx, declared_name, type_ctx, kind=None, scope_kind=None,
        scope_longname=None, type_longname=None,
    ):
        """Record `declared_name is of type_ctx`, positioned on the type.

        kind/scope_kind/scope_longname are for a record's components, where
        one name is three entities (see enterRecordComponent).
        """
        if type_ctx is None or not declared_name:
            return
        # findParents() stops at the enclosing scopes, so the declared entity's
        # own name has to be appended: a local of CDL.getValue is
        # org.json.CDL.getValue.sb, not org.json.sb.
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        enclosing = ".".join(parents)
        # Generic arguments are their own reference kind (Typed
        # GenericArgument); the raw type is what Typed points at.
        type_name = type_ctx.getText().split("<")[0].split("[")[0]
        # A type parameter is declared by the method or class it belongs to,
        # and must be resolved before the import ladder: with `import
        # java.util.*` the lone-wildcard rule turned DynamicArray's `E` into
        # java.util.E.
        if type_longname is not None:
            type_name = type_longname.rsplit(".", 1)[-1]  # inferred: `var`
        else:
            declaring = _declaring_generic(ctx, type_name)
            if declaring:
                type_longname = f"{declaring}.{type_name}"
            else:
                type_longname = self.resolve_type(type_name, enclosing)
        if type_longname is None:
            return
        # Understand anchors a reference at the segment carrying the entity's
        # own name, so a `Java Typed` on `java.util.Map field` sits on `Map`
        # and not on `java`. Measured on a hand-written fixture: the field's
        # Typed is at column 20 of `  public java.util.Map<...> field`, which
        # is `Map`, and this pass put it at 10. Reading the rule off the
        # benchmark was not possible -- almost every fixture imports its types
        # and writes them unqualified, so the two columns coincide; the
        # EvoSuite scaffolding in testing_legacy_code, which qualifies
        # everything, is the one place it shows.
        token = class_properties.type_anchor(type_ctx, type_ctx.start)
        entry = {}
        if kind is not None:
            entry["kind"] = kind
        if scope_kind is not None:
            entry["scope_kind"] = scope_kind
        self.typedBy.append(
            {
                **entry,
                "name": declared_name,
                "scope_longname": scope_longname or f"{enclosing}.{declared_name}",
                "type_name": type_name,
                "type_longname": type_longname,
                "line": token.line,
                "col": token.column,
            }
        )

    # ------------------------------------------------- the qualifying package

    def enterClassOrInterfaceType(
        self, ctx: JavaParserLabeled.ClassOrInterfaceTypeContext
    ):
        """`Java DotRef` on the package a type was written out in full with.

        A qualified type name carries two references, one at each end:
        `java.util.Map<...> field` is a DotRef to java.util at the `java` and
        a Typed to java.util.Map at the `Map`. Understand writes the pair in
        every type position -- a field, a local, a parameter, a return type,
        a cast, a `new`, a `throws`, an `extends`, an `implements`, an
        `instanceof` and every generic argument of each -- so this is walked
        for itself rather than hung off the Typed pass, which sees only some
        of them.

        Only a name written out in full. `Outer.Inner` also has two
        identifiers and its prefix is a type, not a package; refusing it is
        cheaper than being wrong about which, and `resolve_type` returning the
        written name unchanged is what tells the two apart.
        """
        # `java.lang.String.class` parses as a type too, and Understand reads
        # it as an expression instead: three `Java Use` rows walking the name,
        # no DotRef. primary5 is that shape and the only one to exclude.
        node, hops = getattr(ctx, "parentCtx", None), 0
        while node is not None and hops < 3:
            if isinstance(node, JavaParserLabeled.Primary5Context):
                return
            node, hops = getattr(node, "parentCtx", None), hops + 1
        self._qualified_dotref(list(ctx.IDENTIFIER()), ctx)

    def enterCreatedName0(self, ctx: JavaParserLabeled.CreatedName0Context):
        """`new java.util.ArrayList<...>()` -- a created name is not a typeType."""
        self._qualified_dotref(list(ctx.IDENTIFIER()), ctx)

    def enterQualifiedNameList(
        self, ctx: JavaParserLabeled.QualifiedNameListContext
    ):
        """`throws java.io.IOException` -- a throws clause is not one either."""
        for name in ctx.qualifiedName() or ():
            self._qualified_dotref(list(name.IDENTIFIER()), name)

    def _qualified_dotref(self, identifiers, ctx):
        if len(identifiers) < 2:
            return
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        enclosing = ".".join(parents)
        written = ".".join(i.getText() for i in identifiers)
        if self.resolve_type(written, enclosing) != written:
            return
        self.dotrefs.append(
            {
                "package_longname": written.rsplit(".", 1)[0],
                "scope_longname": self._declaration_scope(ctx, enclosing),
                "line": identifiers[0].symbol.line,
                "col": identifiers[0].symbol.column,
            }
        )

    @staticmethod
    def _declaration_scope(ctx, enclosing):
        """What Understand scopes a type reference to.

        The declared entity when the type introduces one -- java.util is
        DotRef'd from `p.Q.field`, not from `p.Q` -- and the enclosing method
        otherwise. The walk stops at the first expression on the way up,
        because a type inside an initialiser belongs to the method and not to
        the variable being initialised: the `new java.util.ArrayList<...>()`
        of `List<String> made = new ArrayList<>()` is scoped to `p.Q.go`
        while the declaration's own `java.util.List` is scoped to
        `p.Q.go.made`.
        """
        node = getattr(ctx, "parentCtx", None)
        while node is not None:
            name = type(node).__name__
            if name.startswith(("Expression", "VariableInitializer", "Creator")):
                return enclosing
            if name in ("FieldDeclarationContext", "LocalVariableDeclarationContext"):
                declarators = node.variableDeclarators()
                first = (declarators.variableDeclarator() or [None])[0] if declarators else None
                identifier = first.variableDeclaratorId() if first is not None else None
                if identifier is not None:
                    return f"{enclosing}.{identifier.getText().split('[')[0]}"
                return enclosing
            if name == "FormalParameterContext":
                identifier = node.variableDeclaratorId()
                if identifier is not None:
                    return f"{enclosing}.{identifier.getText().split('[')[0]}"
                return enclosing
            node = getattr(node, "parentCtx", None)
        return enclosing

    @staticmethod
    def _declared_names(declarators):
        for declarator in declarators or []:
            identifier = declarator.variableDeclaratorId()
            if identifier is not None:
                yield identifier.getText().split("[")[0]

    # ------------------------------------------------------------- the shapes

    def enterFieldDeclaration(self, ctx: JavaParserLabeled.FieldDeclarationContext):
        for name in self._declared_names(
            ctx.variableDeclarators().variableDeclarator()
        ):
            self.record(ctx, name, ctx.typeType())

    def enterLocalVariableDeclaration(
        self, ctx: JavaParserLabeled.LocalVariableDeclarationContext
    ):
        if ctx.typeType().getText() == "var":
            self._typed_var(ctx)
            return
        for name in self._declared_names(
            ctx.variableDeclarators().variableDeclarator()
        ):
            self.record(ctx, name, ctx.typeType())

    def _typed_var(self, ctx):
        """`var tasks = new ArrayList<Task>()` (Java 10): Understand types the
        variable by the initialiser's type, positioned on the variable's
        *name* -- there is no written type to sit on."""
        binder = self._binder_for(ctx)
        for declarator in ctx.variableDeclarators().variableDeclarator():
            initializer = declarator.variableInitializer()
            expression = getattr(initializer, "expression", lambda: None)()
            inferred = binder.type_of(expression)
            if not inferred or "." not in inferred:
                continue
            identifier = declarator.variableDeclaratorId()
            name = identifier.getText().split("[")[0]
            self.record(ctx, name, identifier, type_longname=inferred)

    def _binder_for(self, ctx):
        if getattr(self, "_binder", None) is None:
            from openunderstand.ounderstand.type_binding import TypeBinder

            root = ctx
            while root.parentCtx is not None:
                root = root.parentCtx
            self._binder = TypeBinder(root)
        return self._binder

    def enterLastFormalParameter(
        self, ctx: JavaParserLabeled.LastFormalParameterContext
    ):
        """`String... columns` types columns by String, as a plain parameter."""
        identifier = ctx.variableDeclaratorId()
        if identifier is not None:
            self.record(ctx, identifier.getText().split("[")[0], ctx.typeType())

    def enterInterfaceMethodDeclaration(
        self, ctx: JavaParserLabeled.InterfaceMethodDeclarationContext
    ):
        """An interface method is typed by its return type, as a class's is."""
        returns = ctx.typeTypeOrVoid()
        if returns is None or ctx.IDENTIFIER() is None:
            return
        self.record(ctx, ctx.IDENTIFIER().getText(), returns.typeType())

    def enterFormalParameter(self, ctx: JavaParserLabeled.FormalParameterContext):
        identifier = ctx.variableDeclaratorId()
        if identifier is not None:
            self.record(ctx, identifier.getText().split("[")[0], ctx.typeType())

    def enterEnhancedForControl(self, ctx: JavaParserLabeled.EnhancedForControlContext):
        """`for (Object item : table)` types item, exactly as a local does."""
        identifier = ctx.variableDeclaratorId()
        if identifier is not None:
            self.record(ctx, identifier.getText().split("[")[0], ctx.typeType())

    def enterCatchClause(self, ctx: JavaParserLabeled.CatchClauseContext):
        """`catch (InputMismatchException e)` types e.

        The caught type is a qualifiedName rather than a typeType, which is
        why this needed its own handler; a multi-catch names several, and
        Understand types the variable by each of them.
        """
        identifier = ctx.IDENTIFIER()
        caught = ctx.catchType()
        if identifier is None or caught is None:
            return
        for qualified in caught.qualifiedName():
            self.record(ctx, identifier.getText(), qualified)

    def enterRecordComponent(self, ctx: JavaParserLabeled.RecordComponentContext):
        """`record R(T c)`: the field R.c is Typed T, and unless the record
        declares an ordinary constructor, the parameter R.c and R itself are
        each Typed Implicit T -- for a compact constructor too. Understand
        writes all three at the type."""
        name = ctx.IDENTIFIER().getText()
        record_ctx = ctx.parentCtx.parentCtx
        self.record(ctx, name, ctx.typeType(), scope_kind="Java Variable Private Member")
        if class_properties.record_constructor(record_ctx) == "explicit":
            return
        self.record(
            ctx, name, ctx.typeType(), kind="Java Typed Implicit",
            scope_kind="Java Parameter",
        )
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.record(
            ctx, record_ctx.IDENTIFIER().getText(), ctx.typeType(),
            kind="Java Typed Implicit",
            scope_longname=".".join(parents),
        )

    def _typed(self, scope_longname, name, type_longname, token, kind=None, scope_kind=None):
        """One Typed row whose type is already known."""
        entry = {"kind": kind} if kind else {}
        if scope_kind:
            entry["scope_kind"] = scope_kind
        self.typedBy.append(
            {
                **entry,
                "name": name,
                "scope_longname": scope_longname,
                "type_name": type_longname.rsplit(".", 1)[-1],
                "type_longname": type_longname,
                "line": token.line,
                "col": token.column,
            }
        )

    def enterEnumDeclaration(self, ctx: JavaParserLabeled.EnumDeclarationContext):
        """Understand types an enum's constants by the enum, at each constant,
        and its implicit members at the enum's name: values() and valueOf()
        Typed Implicit the enum, valueOf's `s` Typed Implicit String."""
        identifier = ctx.IDENTIFIER()
        enum = ".".join(
            class_properties.ClassPropertiesListener.findParents(ctx) + [identifier.getText()]
        )
        token = identifier.symbol
        for member in ("values", "valueOf"):
            self._typed(f"{enum}.{member}", member, enum, token,
                        kind="Java Typed Implicit", scope_kind="Java Static Method Public Member")
        self._typed(f"{enum}.valueOf.s", "s", "java.lang.String", token,
                    kind="Java Typed Implicit", scope_kind="Java Parameter")
        constants = ctx.enumConstants()
        for constant in constants.enumConstant() if constants is not None else ():
            name = constant.IDENTIFIER()
            self._typed(f"{enum}.{name.getText()}", name.getText(), enum, name.symbol,
                        scope_kind="Java Variable EnumConstant Public Member")

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        """A method is typed by its return type."""
        returns = ctx.typeTypeOrVoid()
        if returns is None:
            return
        self.record(ctx, ctx.IDENTIFIER().getText(), returns.typeType())
