"""
## Description
This module find all OpenUnderstand call and callby references in a Java project
## References
"""

__author__ = "AminHZ Dev"
__version__ = "0.1.0"

from antlr4 import *
from openunderstand.gen.javaLabeled.JavaLexer import JavaLexer
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
import re

from openunderstand.analysis_passes import class_properties

_QUALIFIED_NAME = re.compile(r"[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*")


class CoupleAndCoupleBy(JavaParserLabeledListener):
    """
    #Todo: Implementing the ANTLR listener pass for Java Couple and Java Coupleby reference kind
    """

    def __init__(self):
        self.Couple = []
        self.packageName = ""
        self.Imports = {}
        self.Modifiers = []
        self.dic = {}
        self.file = None
        self.classes = {}
        self.classlongname = ""
        self.couplebyrefrences = []
        #: One (class dict, couple list) frame per open class declaration.
        self.stack = []
        #: Generic type parameter names declared anywhere in this file.
        self.type_parameters = set()
        #: Annotations seen before their type declaration opened a frame.
        self.pending_annotations = []
        #: Packages brought in by `import x.y.*`, in declaration order.
        self.wildcard_imports = []
        #: Positioned type relations: implements, type-parameter bounds.
        self.relations = []
        #: Resolved-type table for this file, built on first use.
        self._binder = None
        #: Supertypes of the open frame's class, which are never couplings.
        self.ancestors = {"java.lang.Object"}
        self.static_members = {}
        self.static_wildcards = []

    def set_file(self, filex):
        self.file = filex

    def set_classesx(self, classesx):
        self.classes = classesx

    def set_couples(self, couples):
        self.Couple = couples

    @property
    def get_couples(self):
        return self.Couple

    @property
    def get_classes(self):
        return self.classes

    def extract_original_text(self, ctx):
        input_stream = ctx.start.getInputStream()
        start, stop = ctx.start.start, ctx.stop.stop
        return input_stream.getText(start, stop)

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.push_scope(ctx, "Class")

    def enterInterfaceDeclaration(
        self, ctx: JavaParserLabeled.InterfaceDeclarationContext
    ):
        self.push_scope(ctx, "Interface")

    def enterAnnotationTypeDeclaration(
        self, ctx: JavaParserLabeled.AnnotationTypeDeclarationContext
    ):
        self.push_scope(ctx, "Annotation")

    def enterEnumDeclaration(self, ctx: JavaParserLabeled.EnumDeclarationContext):
        """`enum MyEnum { ... }` is a type and Understand couples it.

        Four of JSON's scopes -- MyEnum, MyEnumField, SingletonEnum and
        JSONStringTest.MyEnum -- had no frame at all, so every type they name
        went nowhere: MyEnumField alone is 4 couples Understand reports and we
        reported none.
        """
        self.push_scope(ctx, "Enum")
        self.add("java.lang.String")

    def enterClassCreatorRest(self, ctx: JavaParserLabeled.ClassCreatorRestContext):
        """`new XMLXsiTypeConverter<Boolean>() { ... }` is a type of its own.

        Its members' annotations and the types they name belong to it, not to
        the method's class: without a frame here JSON's twelve anonymous
        classes reported 0 couples against Understand's 2 to 7, and every
        `@Override` inside one landed on the enclosing class instead -- 10
        couples on the wrong scope and 5 the enclosing class does not have.
        """
        name = class_properties.anonymous_name(ctx)
        if name is None:
            return
        self.push_scope(ctx, "Class", name=name, body=ctx.classBody())

    def exitEnumDeclaration(self, ctx: JavaParserLabeled.EnumDeclarationContext):
        self.pop_scope()

    def exitClassCreatorRest(self, ctx: JavaParserLabeled.ClassCreatorRestContext):
        if class_properties.anonymous_name(ctx) is not None:
            self.pop_scope()

    def push_scope(self, ctx, scope_kind, name=None, body=None):
        """Open a couple frame for a type declaration.

        Only classes used to get one, so `interface JSONString` and
        `@interface JSONPropertyName` collected nothing at all -- four scopes
        Understand reports couples for produced none.
        """
        scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        name = name if name is not None else ctx.IDENTIFIER().__str__()
        body = body if body is not None else ctx
        scope_longname = ".".join(scope_parents + [name])
        line, col = body.start.line, body.start.column
        self.classlongname = scope_longname
        self.dic = {
            "scope_kind": scope_kind,
            "scope_name": name,
            "scope_longname": scope_longname,
            "scope_parent": scope_parents[-2] if len(scope_parents) >= 2 else None,
            "scope_contents": self.extract_original_text(body),
            "scope_modifiers": self.Modifiers,
            "File": self.file,
            "line": line,
            "col": col,
        }

        from openunderstand.ounderstand import symbol_table

        record = callable(getattr(ctx, "recordKeyword", None)) and (
            ctx.recordKeyword() is not None
        )
        if record:
            # A record couples to its supertypes, unlike a class: Understand
            # writes java.lang.Record for every one, its implemented interfaces
            # and java.lang.Object where it is used -- 107 supertype couples on
            # jenetics' records, and none on its classes.
            ancestors = set()
        else:
            ancestors = symbol_table.ancestors(scope_longname) | {"java.lang.Object"}
        self.stack.append((self.dic, [], ancestors))
        self.couplebyrefrences = self.stack[-1][1]
        self.ancestors = ancestors
        if record:
            self.add("java.lang.Record")

        pending, self.pending_annotations = self.pending_annotations, []
        for keyname in pending:
            self.add(keyname)

        self.Modifiers = []

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.packageName = ctx.qualifiedName().getText()

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        imported_class_longname = ctx.qualifiedName().getText()
        if ctx.STATIC() is not None:
            # A static import brings members, not types. `import static
            # ...AttributeKeys.TRANSFORM;` used to land in the type map, so a
            # bare TRANSFORM was "resolved" as a type and coupled to the field
            # itself; the class declaring it was never coupled at all.
            if ctx.getText().rstrip(";").endswith(".*"):
                self.static_wildcards.append(imported_class_longname)
                # Static nested types come in through it as well.
                self.wildcard_imports.append(imported_class_longname)
            else:
                owner, _, member = imported_class_longname.rpartition(".")
                self.static_members[member] = owner
            return
        if ctx.getText().rstrip(";").endswith(".*"):
            self.wildcard_imports.append(imported_class_longname)
            return
        imported_class_name = imported_class_longname.split(".")[-1]
        self.Imports[imported_class_name] = imported_class_longname

    def exitClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.pop_scope()

    def exitInterfaceDeclaration(
        self, ctx: JavaParserLabeled.InterfaceDeclarationContext
    ):
        self.pop_scope()

    def exitAnnotationTypeDeclaration(
        self, ctx: JavaParserLabeled.AnnotationTypeDeclarationContext
    ):
        self.pop_scope()

    def pop_scope(self):
        if not self.stack:
            return
        dic, refs, _ = self.stack.pop()
        dic["type_ent_longname"] = refs
        self.Couple.append(dic)
        self.classes[dic["scope_longname"]] = dic

        # Back to the enclosing class, if there is one.
        self.dic = self.stack[-1][0] if self.stack else {}
        self.couplebyrefrences = self.stack[-1][1] if self.stack else []
        self.ancestors = self.stack[-1][2] if self.stack else {"java.lang.Object"}
        self.classlongname = self.dic.get("scope_longname", "")

    def enterClassOrInterfaceModifier(
        self, ctx: JavaParserLabeled.ClassOrInterfaceModifierContext
    ):
        parent = ctx.parentCtx
        if type(parent).__name__ == "TypeDeclarationContext":
            self.Modifiers.append(ctx.getText())

    def enterClassOrInterfaceType(
        self, ctx: JavaParserLabeled.ClassOrInterfaceTypeContext
    ):
        """Collect the types this class is coupled to.

        Understand's Java Couple is purely type-level: every one of the 260
        couples it reports on the JSON benchmark targets a type. This pass used
        to also harvest expression receivers (enterExpression1) and constructor
        names (enterExpression4), which put local variables (`sb`, `jo`),
        string literals (`"name"`) and member paths
        (`JSONObject.quote.hhhh`) into the couple set -- 322 of our 364 rows
        had no Understand counterpart. Those two handlers are gone.
        """
        if type(ctx.parentCtx).__name__ != "TypeTypeContext":
            return
        if type(ctx.parentCtx.parentCtx).__name__.startswith("TypeArgument"):
            if not (self._inside_creator(ctx) or self._inside_record_header(ctx)):
                return
        grandparent = type(ctx.parentCtx.parentCtx).__name__
        if grandparent == "ClassDeclarationContext":
            return
        if grandparent == "TypeListContext" and isinstance(
            ctx.parentCtx.parentCtx.parentCtx, JavaParserLabeled.PermitsClauseContext
        ):
            # `sealed interface P permits A, B` is a Permit Couple to each and
            # nothing more: Understand couples P to none of them -- 60 pairs
            # of jenetics' were ours alone.
            return
        if (
            grandparent == "TypeListContext"
            and type(ctx.parentCtx.parentCtx.parentCtx).__name__
            == "ClassDeclarationContext"
        ):
            self.record_relation("Java Implement Couple", ctx, self.classlongname)
            if ctx.parentCtx.parentCtx.parentCtx.recordKeyword() is not None:
                # A record couples to the interfaces it implements as well.
                self.add(self.resolve_type_longname(ctx))
            return
        bound = self.constrained_parameter(ctx)
        if bound is not None:
            self.record_relation("Java Use Constrains Couple", ctx, bound)
            return

        self.add(self.resolve_type_longname(ctx))

    #: Rules a type argument may sit under before reaching what encloses it.
    _ARGUMENT_CHAIN = (
        "TypeType",
        "TypeArgument",
        "TypeArguments",
        "TypeArgumentsOrDiamond",
        "ClassOrInterfaceType",
    )

    @classmethod
    def _inside_record_header(cls, ctx):
        """Whether this type argument is part of a record component's type:
        `record Book(..., List<Author> authors)` couples Book to Author in
        Understand, where a field's `List<Author>` does not."""
        node = ctx.parentCtx
        while node is not None:
            name = type(node).__name__
            if name == "RecordComponentContext":
                return True
            if not name.startswith(cls._ARGUMENT_CHAIN):
                return False
            node = node.parentCtx
        return False

    @classmethod
    def _inside_creator(cls, ctx):
        """Whether this type argument is written inside a `new X<...>()`."""
        node = ctx.parentCtx
        while node is not None:
            name = type(node).__name__
            if name.startswith("CreatedName"):
                rest = getattr(node.parentCtx, "classCreatorRest", None)
                rest = rest() if callable(rest) else None
                return rest is None or rest.classBody() is None
            if not name.startswith(cls._ARGUMENT_CHAIN):
                return False
            node = node.parentCtx
        return False

    def constrained_parameter(self, ctx):
        """Long name of the type parameter this type bounds, or None."""
        node = ctx.parentCtx
        while node is not None:
            if type(node).__name__.startswith("TypeParameter"):
                identifier = node.IDENTIFIER()
                if identifier is None:
                    return None
                # findParents() already names a generic method: appending
                # the owner again made `getEnum.getEnum.E`.
                parents = class_properties.ClassPropertiesListener.findParents(node)
                return ".".join(parents + [identifier.getText()])
            if type(node).__name__.startswith(("ClassBody", "Block")):
                return None
            node = node.parentCtx
        return None

    def record_relation(self, kind, ctx, scope_longname):
        """A positioned type relation: implements, or a type-parameter bound.

        Java Couple is unpositioned and aggregated per class; these are
        per-occurrence and carry the type's own token, so they are collected
        separately rather than folded into the couple set.
        """
        longname = self.resolve_type_longname(ctx)
        if not longname or not scope_longname:
            return
        # `implements java.io.Serializable` reports on the `Serializable`.
        token = class_properties.type_anchor(ctx, ctx.start)
        self.relations.append(
            {
                "kind": kind,
                "scope_longname": scope_longname,
                "ent_longname": longname,
                "name": longname.rsplit(".", 1)[-1],
                "line": token.line,
                "col": token.column,
            }
        )

    def enterAnnotation(self, ctx: JavaParserLabeled.AnnotationContext):
        """`@Override` couples the type to the annotation type."""
        if ctx.qualifiedName() is None:
            return
        keyname = self.lookup(ctx.qualifiedName().getText())
        if keyname and not self.stack:
            # Annotating a top-level type: the frame does not exist yet.
            # ponytail: an annotation on a *member* type still lands on the
            # enclosing type, which has a frame open. Understand attributes it
            # to the member; no case of that in the JSON fixture.
            self.pending_annotations.append(keyname)
        else:
            self.add(keyname)

    def enterExpression1(self, ctx: JavaParserLabeled.Expression1Context):
        """A static access couples the class to the receiver's type.

        `Integer.parseInt(s)`, `XML.toJSONObject(r)`. Collecting from
        declaration positions alone missed 47 of Understand's 260 couples on
        JSON and most of the 607 on TheAlgorithms.

        Unlike enterClassOrInterfaceType, the receiver here may be a value --
        `sb.append(...)` -- so a name has to be shown to denote a type before it
        counts. That is why this cannot use lookup(): its java.lang fallback is
        safe only in a type position, where everything is a type by
        construction. An earlier version of this pass took the receiver text
        unconditionally and put `sb`, `jo` and `"name"` in the couple set.
        """
        if not ctx.DOT() or ctx.expression() is None:
            return
        receiver = ctx.expression().getText()
        if not receiver.isidentifier():
            return
        owner = self.lookup_receiver(receiver, ctx)
        self.add(owner)
        self.add(self.field_type(owner, ctx))
        # The type that *declares* the member read, when it is not the
        # receiver: `JSlider.HORIZONTAL` is javax.swing.SwingConstants'.
        member = ctx.IDENTIFIER()
        if owner and member is not None:
            from openunderstand.ounderstand import symbol_table

            self.add(
                symbol_table.declaring_type_anywhere(owner, member.getText(), fields=True)
            )

    @staticmethod
    def field_type(owner, ctx):
        """Declared type of the field being read, for the JDK fields we know.

        Understand couples to a field's declared type as well as to its owner,
        so `System.out.println(...)` yields java.lang.System *and*
        java.io.PrintStream -- 144 of TheAlgorithms' 1182 couples, and every
        one of them missed here because the type of `out` is not derivable
        from the source being analysed.
        """
        from openunderstand.ounderstand import symbol_table

        if owner is None:
            return None
        member = ctx.IDENTIFIER()
        if member is None:
            return None
        return symbol_table.JDK_FIELD_TYPES.get((owner, member.getText()))

    def lookup_receiver(self, name, ctx=None):
        """Long name if `name` denotes a type, else None. No guessing."""
        from openunderstand.oudb import jdk_index
        from openunderstand.ounderstand import symbol_table

        if not name or name in self.type_parameters:
            return None
        if name in self.Imports:
            return self.Imports[name]
        # Scoped: `Node` is declared in several packages, and without the
        # asking class it binds to whichever was indexed first.
        in_project = symbol_table.resolve_type(name, self.classlongname)
        if in_project:
            return in_project
        if name in symbol_table.JAVA_LANG_TYPES:
            return "java.lang." + name
        # `Color.WHITE` behind `import java.awt.*`: a wildcard import places a
        # JDK type -- but only once the name is shown not to be a variable,
        # which is what a receiver usually is.
        if ctx is not None and self.wildcard_imports and name[:1].isupper():
            try:
                if self.binder(ctx).name_type(name, ctx):
                    return None
            except Exception:
                return None
            return jdk_index.resolve_simple(name, tuple(self.wildcard_imports))
        return None

    def binder(self, ctx):
        """The resolved-type table for this file, built from the tree's root."""
        if self._binder is None:
            from openunderstand.ounderstand.type_binding import TypeBinder

            root = ctx
            while root.parentCtx is not None:
                root = root.parentCtx
            self._binder = TypeBinder(root, self.file)
        return self._binder

    def enterPrimary5(self, ctx: JavaParserLabeled.Primary5Context):
        """`NullPointerException.class` is a value of type java.lang.Class.

        Sixteen of JSON's classes couple to java.lang.Class and not one of them
        names it: they either write a class literal or call `getClass()`, whose
        return type is the same. The named type itself is coupled separately by
        enterClassOrInterfaceType.
        """
        self.add("java.lang.Class")

    def enterMethodCall0(self, ctx: JavaParserLabeled.MethodCall0Context):
        """A call couples the class to what it uses: the member's declaring
        type and what the call evaluates to.

        Understand's Couple is "uses a type, data, or *member* from B", and
        both halves needed a resolved receiver, which this pass had no way to
        get: `result.getClass().getSimpleName()` names no type at all and
        couples to java.lang.Class, and `e.getMessage()` on a JSONException
        couples to java.lang.Throwable, which declares it three supertypes up.
        31 of JSON's 80 missing couples are those two names alone.
        """
        identifier = ctx.IDENTIFIER()
        if identifier is None or not self.stack:
            return
        parent = ctx.parentCtx
        if type(parent).__name__ != "Expression1Context":
            self._outer_member(ctx, identifier.getText())
            # A bare `f()` is a call on `this`, which is the enclosing class or
            # one of its supertypes -- neither is a coupling. Unless it was
            # statically imported: `requireNonNull(x)` behind `import static
            # java.util.Objects.requireNonNull` uses a member of
            # java.util.Objects, and 28 of jenetics' records couple to it.
            owner = self._static_owner(identifier.getText())
            if owner:
                self.add(owner)
            return
        receiver_ctx = parent.expression()
        if receiver_ctx is None or isinstance(receiver_ctx, list):
            return
        try:
            owner = self.binder(ctx).type_of(receiver_ctx)
        except Exception:
            return
        from openunderstand.oudb import jdk_index
        from openunderstand.ounderstand import symbol_table

        if not owner:
            text = receiver_ctx.getText()
            if _QUALIFIED_NAME.fullmatch(text) and (
                jdk_index.known(text) or symbol_table.is_project_type(text)
            ):
                owner = text
        if not owner:
            return

        member = identifier.getText()
        self.add(symbol_table.declaring_type_anywhere(owner, member))

    def enterCreatedName0(self, ctx: JavaParserLabeled.CreatedName0Context):
        """`new JSONTokener(...)` -- createdName is not a classOrInterfaceType.

        Not for `new JSONString() { ... }`: the created type is then the
        *anonymous class's* supertype, which Understand records as an Implement
        Couple on that class and as no coupling at all on the class holding it.
        """
        rest = getattr(ctx.parentCtx, "classCreatorRest", None)
        rest = rest() if callable(rest) else None
        if rest is not None and rest.classBody() is not None:
            return
        parts = [i.getText() for i in ctx.IDENTIFIER()]
        self.add(self.lookup(".".join(parts)))
        self._couple_qualifiers(parts)

    def enterExpression5(self, ctx: JavaParserLabeled.Expression5Context):
        """`(Point2D.Double) x` -- the cast type itself comes in through
        enterClassOrInterfaceType; its qualifier is coupled here."""
        written = ctx.typeType().classOrInterfaceType()
        if written is not None:
            self._couple_qualifiers([i.getText() for i in written.IDENTIFIER()])

    def enterExpression13(self, ctx: JavaParserLabeled.Expression13Context):
        """`x instanceof Accessor.Writable` -- an expression position, like a
        cast: the qualifier is coupled too."""
        written = ctx.typeType().classOrInterfaceType()
        if written is not None:
            self._couple_qualifiers([i.getText() for i in written.IDENTIFIER()])

    def enterPattern(self, ctx: JavaParserLabeled.PatternContext):
        """`instanceof Accessor.Writable(var g, var s)` and `instanceof
        Accessor.Writable w`: the same, for a record or a type pattern."""
        type_ctx = ctx.typeType() or (
            ctx.localVariableDeclaration().typeType()
            if ctx.localVariableDeclaration() is not None
            else None
        )
        written = type_ctx.classOrInterfaceType() if type_ctx is not None else None
        if written is not None:
            self._couple_qualifiers([i.getText() for i in written.IDENTIFIER()])

    def _couple_qualifiers(self, parts):
        """Couple each *type* qualifying a nested type named in an expression.

        In expression position Understand resolves `Point2D.Double` segment by
        segment, so `new Point2D.Double(...)` and `(Point2D.Double) p` use
        java.awt.geom.Point2D too, and the class couples to it. A declaration
        `Point2D.Double p;` does not: there the qualifier is only a DotRef.
        That rule reproduces Understand's java.awt.geom.Point2D couples on all
        110 jhotdraw classes carrying one. A package prefix (`new
        java.util.ArrayList()`) is skipped: lookup() hands a qualified package
        name back unchanged, and coupling it put 144 package couples on
        jhotdraw that Understand does not have.
        """
        from openunderstand.oudb import jdk_index
        from openunderstand.ounderstand import symbol_table

        for end in range(1, len(parts)):
            owner = self.lookup(".".join(parts[:end]))
            if owner and (jdk_index.known(owner) or symbol_table.is_project_type(owner)):
                self.add(owner)

    def enterCatchType(self, ctx: JavaParserLabeled.CatchTypeContext):
        """`catch (JSONException e)` -- catchType holds qualifiedNames."""
        for qualified_name in ctx.qualifiedName():
            self.add(self.lookup(qualified_name.getText()))

    def add(self, keyname):
        """Record one coupled type, applying the exclusions Understand applies."""
        if not keyname or not self.stack:
            return
        if keyname == self.classlongname or keyname in self.ancestors:
            return
        if keyname not in self.couplebyrefrences:
            self.couplebyrefrences.append(keyname)

    def _static_owner(self, name):
        """The type a bare `name` comes from through a static import, or None.

        Only a type Understand can see -- `import static org.junit.Assert.*`
        names a jar outside the analysed source, and it couples nothing -- and,
        for a wildcard, only one that actually declares `name`.
        """
        from openunderstand.oudb import jdk_index
        from openunderstand.ounderstand import symbol_table

        def visible(owner):
            return jdk_index.known(owner) or symbol_table.is_project_type(owner)

        owner = self.static_members.get(name)
        if owner:
            return owner if visible(owner) else None
        for owner in self.static_wildcards:
            if not visible(owner):
                continue
            if symbol_table.INDEX.declares(owner, name):
                return owner
            entry = jdk_index._load()["types"].get(owner)
            if entry and (name in entry["fields"] or name in entry["methods"]):
                return owner
        return None

    def enterPrimary4(self, ctx: JavaParserLabeled.Primary4Context):
        """A bare name read through a static import -- `FILL_COLOR.get(f)`
        behind `import static ...AttributeKeys.*` -- uses a member of the type
        declaring it: 51 of jhotdraw's classes couple to AttributeKeys this
        way and nothing here saw it. A local, a parameter or a field in scope
        shadows the import, so those are asked about first."""
        if not self.stack:
            return
        self._outer_member(ctx, ctx.IDENTIFIER().getText())
        if not (self.static_members or self.static_wildcards):
            return
        name = ctx.IDENTIFIER().getText()
        try:
            if self.binder(ctx).name_type(name, ctx):
                return
        except Exception:
            return
        owner = self._static_owner(name)
        if owner:
            self.add(owner)

    def _outer_member(self, ctx, name):
        """Inside an anonymous class, a bare name the class does not declare
        but an enclosing type does -- `k` and `n` in KSubset's Cursors -- uses
        a member of that enclosing type, and Understand couples the anonymous
        class to it. A named class never couples itself, so only an anonymous
        frame asks; its locals, parameters and own fields are asked first."""
        from openunderstand.ounderstand import symbol_table

        if not self.classlongname.rsplit(".", 1)[-1].startswith("(Anon_"):
            return
        binder = self.binder(ctx)
        node = ctx
        while node is not None and not (
            isinstance(node, JavaParserLabeled.ClassCreatorRestContext)
            and node.classBody() is not None
        ):
            if type(node).__name__.startswith(
                ("MethodDeclaration", "LambdaExpression", "Block", "CatchClause",
                 "ForControl", "EnhancedForControl")
            ) and name in binder._declared_in(node):
                return
            node = node.parentCtx
        if node is None or name in binder._own_fields(node):
            return
        parts = self.classlongname.split(".")
        for end in range(len(parts) - 1, 0, -1):
            owner = ".".join(parts[:end])
            if symbol_table.is_project_type(owner):
                if symbol_table.INDEX.declares(owner, name):
                    self.add(owner)
                return

    def enterTypeParameter(self, ctx: JavaParserLabeled.TypeParameterContext):
        """`<E>` declares a name that looks like a type but denotes none.

        Understand couples to no type parameter on the JSON benchmark; without
        this the java.lang fallback below turned every `<E>` into a coupling to
        a non-existent java.lang.E. Names are kept for the whole file rather
        than per-declaration: a type parameter is never a real type anywhere,
        so the coarser scope costs nothing.
        """
        self.type_parameters.add(ctx.IDENTIFIER().getText())
        # An unbounded `<T>` is `<T extends Object>`, and Understand couples
        # the declaring type to java.lang.Object for it: 31 of jenetics' 69
        # records, every one generic or holding a generic method. A class never
        # shows it because Object is an ancestor, which add() excludes.
        if ctx.EXTENDS() is None:
            self.add("java.lang.Object")

    def enterQualifiedNameList(self, ctx: JavaParserLabeled.QualifiedNameListContext):
        """A `throws` clause couples the class to the exception types.

        qualifiedNameList appears only after THROWS in this grammar. Because it
        holds qualifiedNames rather than typeTypes it never reaches
        enterClassOrInterfaceType, so every `throws JSONException` was missed --
        one lost coupling in almost every class in the fixture.
        """
        for qualified_name in ctx.qualifiedName():
            self.add(self.lookup(qualified_name.getText()))

    def resolve_type_longname(self, ctx):
        """Long name for a type reference, with type arguments stripped.

        ctx.getText() carries the type arguments along, so
        `HashMap<String,Character>` was stored verbatim and matched nothing.
        The arguments arrive as ClassOrInterfaceType nodes of their own and are
        coupled separately, which is what Understand does.
        """
        return self.lookup(".".join(i.getText() for i in ctx.IDENTIFIER()))

    def lookup(self, name):
        """Resolve a type name the way javac would, in declaration order."""
        from openunderstand.ounderstand import symbol_table

        if not name or name in self.type_parameters:
            return None
        return symbol_table.resolve_type_name(
            name, self.Imports, self.wildcard_imports, self.classlongname
        )
