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

#: A dotted path of identifiers and nothing else -- `java.util.Objects`. Any
#: other receiver text is an expression, and reading it as a type name is what
#: put local variables and string literals in the couple set.
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
        # getInputStream() rather than getTokenSource().inputStream: both return
        # the same stream under the Python parser, but the C++ accelerator
        # leaves the token-source slot empty, so the indirect route is None.
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
        # Every enum has an implicit `public static E valueOf(String)`, and
        # Understand couples the enum to java.lang.String for it: all four of
        # JSON's enums carry it, including `enum MyEnum { VAL1, VAL2, VAL3; }`,
        # which names no type at all.
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
        # findParents() stops at the enclosing scopes, so the type's own
        # name has to be appended -- otherwise a class's longname is its
        # package ("org.json" for class CDL) and matches nothing.
        # An anonymous class has no IDENTIFIER and is named by its caller, and
        # its declaration is the body rather than the whole creator.
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

        # A nested class exits before the class that encloses it, so with a
        # single shared couple list `class JSONObject { ... static class
        # Null {} ... }` handed everything JSONObject had collected so far
        # to Null, and JSONObject kept only what came after. Each type
        # gets its own frame.
        from openunderstand.ounderstand import symbol_table

        ancestors = symbol_table.ancestors(scope_longname) | {"java.lang.Object"}
        self.stack.append((self.dic, [], ancestors))
        self.couplebyrefrences = self.stack[-1][1]
        self.ancestors = ancestors

        # `@Target(...) public @interface JSONPropertyName` puts the annotation
        # in the *typeDeclaration*'s modifier list, so enterAnnotation fires
        # before this frame exists. Those are held aside and land here.
        pending, self.pending_annotations = self.pending_annotations, []
        for keyname in pending:
            self.add(keyname)

        self.Modifiers = []

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.packageName = ctx.qualifiedName().getText()

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        imported_class_longname = ctx.qualifiedName().getText()
        if ctx.getText().rstrip(";").endswith(".*"):
            # `import java.util.*` names a package, not a type. Taking the last
            # segment registered 'util' -> 'java.util' as though util were a
            # class; the package is what an unqualified name falls back to.
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
            # A type argument counts only where it is *written in an
            # expression* -- `new HashMap<String, XMLXsiTypeConverter<?>>()` --
            # and not where it decorates a declared type. Understand's own
            # split says so: it writes `Java Use GenericArgument` for the first
            # and only `Java Typed GenericArgument` for the second, and the
            # couple set follows the Use. `Map<String, List<Integer>>
            # integerMap` couples CustomClassH to java.util.Map alone and
            # `List<CustomClassC>` couples CustomClassE to java.util.List
            # alone, while XMLParserConfiguration, which constructs the map,
            # couples to org.json.XMLXsiTypeConverter it names nowhere else.
            if not self._inside_creator(ctx):
                return
        # `class X extends Y` (parent ClassDeclaration) and `implements Z`
        # (parent typeList): inheritance is carried by Java Extend Couple, and
        # Understand emits no Java Couple for a supertype -- JSONException
        # extends RuntimeException produces none.
        grandparent = type(ctx.parentCtx.parentCtx).__name__
        if grandparent == "ClassDeclarationContext":
            return
        if (
            grandparent == "TypeListContext"
            and type(ctx.parentCtx.parentCtx.parentCtx).__name__
            == "ClassDeclarationContext"
        ):
            # `implements Z` is its own relation, not a plain Couple.
            self.record_relation("Java Implement Couple", ctx, self.classlongname)
            return
        bound = self.constrained_parameter(ctx)
        if bound is not None:
            # `<T extends Comparable<T>>` -- scoped to the type parameter
            # itself, which is how Understand names it: Searches.BinarySearch
            # .find.T -> java.lang.Comparable.
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
    def _inside_creator(cls, ctx):
        """Whether this type argument is written inside a `new X<...>()`."""
        node = ctx.parentCtx
        while node is not None:
            name = type(node).__name__
            if name.startswith("CreatedName"):
                # Not for `new XMLXsiTypeConverter<Boolean>() { ... }`: the
                # whole created type, arguments included, belongs to the
                # anonymous class as its supertype and couples the class
                # holding it to nothing -- the same rule enterCreatedName0
                # applies to the name itself.
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
                parents = class_properties.ClassPropertiesListener.findParents(node)
                owner = self.generic_owner(node)
                if owner:
                    # `<T extends Comparable<T>> int find(...)`: the type
                    # parameter list is a *sibling* of the method declaration
                    # inside genericMethodDeclaration, so findParents() stops at
                    # the class and the scope came out Searches.BinarySearch.T
                    # where Understand says Searches.BinarySearch.find.T.
                    parents = parents + [owner]
                return ".".join(parents + [identifier.getText()])
            if type(node).__name__.startswith(("ClassBody", "Block")):
                return None
            node = node.parentCtx
        return None

    @staticmethod
    def generic_owner(node):
        """Name of the method a type parameter list belongs to, if any."""
        current = node.parentCtx
        while current is not None:
            name = type(current).__name__
            if name.startswith(
                ("GenericMethodDeclaration", "GenericConstructorDeclaration")
            ):
                for attribute in ("methodDeclaration", "constructorDeclaration"):
                    inner = getattr(current, attribute, None)
                    inner = inner() if callable(inner) else None
                    if inner is not None and inner.IDENTIFIER() is not None:
                        return inner.IDENTIFIER().getText()
                return None
            if name.startswith(("ClassBody", "ClassDeclaration")):
                return None
            current = current.parentCtx
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
        token = ctx.start
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
        owner = self.lookup_receiver(receiver)
        self.add(owner)
        self.add(self.field_type(owner, ctx))

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

    def lookup_receiver(self, name):
        """Long name if `name` denotes a type, else None. No guessing."""
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
            # A bare `f()` is a call on `this`, which is the enclosing class or
            # one of its supertypes -- neither is a coupling.
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
            # A fully qualified static call -- `java.util.Objects.hash(...)`.
            # The receiver is a type path rather than a value, so the binder
            # has nothing to bind; accepted only when the name is one the JDK
            # index or the project actually declares.
            text = receiver_ctx.getText()
            if _QUALIFIED_NAME.fullmatch(text) and (
                jdk_index.known(text) or symbol_table.is_project_type(text)
            ):
                owner = text
        if not owner:
            return

        member = identifier.getText()
        # The declaring type only. What the call *returns* is not a coupling:
        # Understand reports no org.json.Cookie -> java.util.Set for
        # `jo.keySet()` and no JSONObjectLocaleTest -> java.lang.String for
        # `jsonen.getString("i")`. Adding return types put 17 pairs on classes
        # that have none.
        # No fallback to the receiver's own type. `jsonArray.write(w,0,0)`
        # returns a java.io.Writer and `.toString()` on it is
        # java.lang.Object's, which is not a coupling -- falling back put
        # java.io.Writer on three classes Understand does not couple to it.
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
        self.add(self.lookup(".".join(i.getText() for i in ctx.IDENTIFIER())))

    def enterCatchType(self, ctx: JavaParserLabeled.CatchTypeContext):
        """`catch (JSONException e)` -- catchType holds qualifiedNames."""
        for qualified_name in ctx.qualifiedName():
            self.add(self.lookup(qualified_name.getText()))

    def add(self, keyname):
        """Record one coupled type, applying the exclusions Understand applies."""
        if not keyname or not self.stack:
            return
        # Understand never couples a class to itself, nor to an ancestor: it
        # reports no JSONException -> java.lang.Throwable even though the
        # constructors take one, and no JSONMLParserConfiguration ->
        # ParserConfiguration. The whole chain is excluded, not just the
        # universal ancestor -- that left six of these on JSON.
        if keyname == self.classlongname or keyname in self.ancestors:
            return
        if keyname not in self.couplebyrefrences:
            self.couplebyrefrences.append(keyname)

    def enterTypeParameter(self, ctx: JavaParserLabeled.TypeParameterContext):
        """`<E>` declares a name that looks like a type but denotes none.

        Understand couples to no type parameter on the JSON benchmark; without
        this the java.lang fallback below turned every `<E>` into a coupling to
        a non-existent java.lang.E. Names are kept for the whole file rather
        than per-declaration: a type parameter is never a real type anywhere,
        so the coarser scope costs nothing.
        """
        self.type_parameters.add(ctx.IDENTIFIER().getText())

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
        # Imported here, not at module scope: openunderstand.ounderstand's
        # __init__ reaches oudb.api -> parsing_process -> the module that
        # imports this pass, so a top-level import is circular.
        from openunderstand.ounderstand import symbol_table

        if not name or name in self.type_parameters:
            return None
        # One ladder, not a near-copy of it. This one ended in an
        # unconditional `java.lang.` + name, which named java.lang.Map,
        # java.lang.List and java.lang.Set for types that live in java.util --
        # a wrong coupling and a missed right one each time, 4 classes apiece
        # on JSON. resolve_type_name asks the JDK index instead, and refuses
        # when nothing settles it.
        return symbol_table.resolve_type_name(
            name, self.Imports, self.wildcard_imports, self.classlongname
        )
