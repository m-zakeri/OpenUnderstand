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
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.analysis_passes import class_properties

class CoupleAndCoupleBy(JavaParserLabeledListener):
    """
    #Todo: Implementing the ANTLR listener pass for Java Couple and Java Coupleby reference kind
    """
    def __init__(self):
        self.Couple = []
        self.packageName = ''
        self.Imports = {}
        self.Modifiers = []
        self.dic = {}
        self.file =None
        self.classes = {}
        self.classlongname = ''
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




    def set_file(self , filex):
        self.file = filex


    def set_classesx(self, classesx):
        self.classes = classesx


    def set_couples(self , couples):
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


    def enterClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        self.push_scope(ctx, "Class")

    def enterInterfaceDeclaration(self, ctx:JavaParserLabeled.InterfaceDeclarationContext):
        self.push_scope(ctx, "Interface")

    def enterAnnotationTypeDeclaration(self, ctx:JavaParserLabeled.AnnotationTypeDeclarationContext):
        self.push_scope(ctx, "Annotation")

    def push_scope(self, ctx, scope_kind):
        """Open a couple frame for a type declaration.

        Only classes used to get one, so `interface JSONString` and
        `@interface JSONPropertyName` collected nothing at all -- four scopes
        Understand reports couples for produced none.
        """
        scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        # findParents() stops at the enclosing scopes, so the type's own
        # name has to be appended -- otherwise a class's longname is its
        # package ("org.json" for class CDL) and matches nothing.
        scope_longname = ".".join(scope_parents + [ctx.IDENTIFIER().__str__()])
        line, col = ctx.start.line, ctx.start.column
        self.classlongname = scope_longname
        self.dic = {"scope_kind": scope_kind, "scope_name": ctx.IDENTIFIER().__str__(),
                                       "scope_longname": scope_longname,
                                       "scope_parent": scope_parents[-2] if len(scope_parents) >= 2 else None,
                                       "scope_contents": self.extract_original_text(ctx),
                                       "scope_modifiers": self.Modifiers , 'File' : self.file , 'line':line ,  'col' : col }

        # A nested class exits before the class that encloses it, so with a
        # single shared couple list `class JSONObject { ... static class
        # Null {} ... }` handed everything JSONObject had collected so far
        # to Null, and JSONObject kept only what came after. Each type
        # gets its own frame.
        self.stack.append((self.dic, []))
        self.couplebyrefrences = self.stack[-1][1]

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
        if ctx.getText().rstrip(';').endswith('.*'):
            # `import java.util.*` names a package, not a type. Taking the last
            # segment registered 'util' -> 'java.util' as though util were a
            # class; the package is what an unqualified name falls back to.
            self.wildcard_imports.append(imported_class_longname)
            return
        imported_class_name = imported_class_longname.split('.')[-1]
        self.Imports[imported_class_name] = imported_class_longname


    def exitClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        self.pop_scope()

    def exitInterfaceDeclaration(self, ctx:JavaParserLabeled.InterfaceDeclarationContext):
        self.pop_scope()

    def exitAnnotationTypeDeclaration(self, ctx:JavaParserLabeled.AnnotationTypeDeclarationContext):
        self.pop_scope()

    def pop_scope(self):
        if not self.stack:
            return
        dic, refs = self.stack.pop()
        dic["type_ent_longname"] = refs
        self.Couple.append(dic)
        self.classes[dic["scope_longname"]] = dic

        # Back to the enclosing class, if there is one.
        self.dic = self.stack[-1][0] if self.stack else {}
        self.couplebyrefrences = self.stack[-1][1] if self.stack else []
        self.classlongname = self.dic.get("scope_longname", "")







    def enterClassOrInterfaceModifier(self, ctx:JavaParserLabeled.ClassOrInterfaceModifierContext):
        parent = ctx.parentCtx
        if( type(parent).__name__ == 'TypeDeclarationContext'):
            self.Modifiers.append(ctx.getText())



    def enterClassOrInterfaceType(self, ctx:JavaParserLabeled.ClassOrInterfaceTypeContext):
        """Collect the types this class is coupled to.

        Understand's Java Couple is purely type-level: every one of the 260
        couples it reports on the JSON benchmark targets a type. This pass used
        to also harvest expression receivers (enterExpression1) and constructor
        names (enterExpression4), which put local variables (`sb`, `jo`),
        string literals (`"name"`) and member paths
        (`JSONObject.quote.hhhh`) into the couple set -- 322 of our 364 rows
        had no Understand counterpart. Those two handlers are gone.
        """
        if type(ctx.parentCtx).__name__ != 'TypeTypeContext':
            return
        # `class X extends Y` (parent ClassDeclaration) and `implements Z`
        # (parent typeList): inheritance is carried by Java Extend Couple, and
        # Understand emits no Java Couple for a supertype -- JSONException
        # extends RuntimeException produces none.
        grandparent = type(ctx.parentCtx.parentCtx).__name__
        if grandparent == 'ClassDeclarationContext':
            return
        if grandparent == 'TypeListContext' and \
                type(ctx.parentCtx.parentCtx.parentCtx).__name__ == 'ClassDeclarationContext':
            # `implements Z` is its own relation, not a plain Couple.
            self.record_relation('Java Implement Couple', ctx, self.classlongname)
            return
        bound = self.constrained_parameter(ctx)
        if bound is not None:
            # `<T extends Comparable<T>>` -- scoped to the type parameter
            # itself, which is how Understand names it: Searches.BinarySearch
            # .find.T -> java.lang.Comparable.
            self.record_relation('Java Use Constrains Couple', ctx, bound)
            return

        self.add(self.resolve_type_longname(ctx))

    def constrained_parameter(self, ctx):
        """Long name of the type parameter this type bounds, or None."""
        node = ctx.parentCtx
        while node is not None:
            if type(node).__name__.startswith('TypeParameter'):
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
                return '.'.join(parents + [identifier.getText()])
            if type(node).__name__.startswith(('ClassBody', 'Block')):
                return None
            node = node.parentCtx
        return None

    @staticmethod
    def generic_owner(node):
        """Name of the method a type parameter list belongs to, if any."""
        current = node.parentCtx
        while current is not None:
            name = type(current).__name__
            if name.startswith(('GenericMethodDeclaration',
                                'GenericConstructorDeclaration')):
                for attribute in ('methodDeclaration', 'constructorDeclaration'):
                    inner = getattr(current, attribute, None)
                    inner = inner() if callable(inner) else None
                    if inner is not None and inner.IDENTIFIER() is not None:
                        return inner.IDENTIFIER().getText()
                return None
            if name.startswith(('ClassBody', 'ClassDeclaration')):
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
        self.relations.append({
            'kind': kind,
            'scope_longname': scope_longname,
            'ent_longname': longname,
            'name': longname.rsplit('.', 1)[-1],
            'line': token.line,
            'col': token.column,
        })

    def enterAnnotation(self, ctx:JavaParserLabeled.AnnotationContext):
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

    def enterExpression1(self, ctx:JavaParserLabeled.Expression1Context):
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

    def enterCreatedName0(self, ctx:JavaParserLabeled.CreatedName0Context):
        """`new JSONTokener(...)` -- createdName is not a classOrInterfaceType."""
        self.add(self.lookup(".".join(i.getText() for i in ctx.IDENTIFIER())))

    def enterCatchType(self, ctx:JavaParserLabeled.CatchTypeContext):
        """`catch (JSONException e)` -- catchType holds qualifiedNames."""
        for qualified_name in ctx.qualifiedName():
            self.add(self.lookup(qualified_name.getText()))

    def add(self, keyname):
        """Record one coupled type, applying the exclusions Understand applies."""
        if not keyname or not self.stack:
            return
        # Understand never couples a class to itself, nor to an ancestor: it
        # reports no JSONException -> java.lang.Throwable even though the
        # constructors take one. Object is every class's ancestor.
        # ponytail: only the universal ancestor is excluded here. Catching
        # java.lang.Throwable for exception subclasses needs the JDK hierarchy,
        # which this pass has no access to -- 2 false positives on JSON.
        if keyname == self.classlongname or keyname == "java.lang.Object":
            return
        if keyname not in self.couplebyrefrences:
            self.couplebyrefrences.append(keyname)

    def enterTypeParameter(self, ctx:JavaParserLabeled.TypeParameterContext):
        """`<E>` declares a name that looks like a type but denotes none.

        Understand couples to no type parameter on the JSON benchmark; without
        this the java.lang fallback below turned every `<E>` into a coupling to
        a non-existent java.lang.E. Names are kept for the whole file rather
        than per-declaration: a type parameter is never a real type anywhere,
        so the coarser scope costs nothing.
        """
        self.type_parameters.add(ctx.IDENTIFIER().getText())

    def enterQualifiedNameList(self, ctx:JavaParserLabeled.QualifiedNameListContext):
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
        if name in self.Imports:
            return self.Imports[name]
        if "." in name:
            return name
        # Scoped: `Node` is declared in several packages, and without the
        # asking class it binds to whichever was indexed first.
        in_project = symbol_table.resolve_type(name, self.classlongname)
        if in_project:
            return in_project
        # java.lang is imported implicitly, and a name that lives there beats a
        # wildcard: `Integer` is java.lang.Integer even under `import
        # java.util.*`.
        if name in symbol_table.JAVA_LANG_TYPES:
            return "java.lang." + name
        # Otherwise a single `import x.y.*` is the only place left it can come
        # from. This used to fall straight through to java.lang, which named 41
        # of TheAlgorithms' couples java.lang.Map, java.lang.ArrayList,
        # java.lang.FileInputStream -- a false positive and a missed true
        # positive each time.
        # ponytail: only when exactly one wildcard is in scope. 15 of the 19
        # files that use one have exactly one; with two or more there is no
        # evidence here to choose between them, so those keep the old guess.
        if len(self.wildcard_imports) == 1:
            return self.wildcard_imports[0] + "." + name
        # An unqualified name that is neither imported nor declared here is
        # implicitly java.lang -- String, Object, Throwable. This used to be
        # `self.packageName + '.' + name`, which produced org.json.String for
        # every one of them: a false positive and a missed true positive at the
        # same time.
        return "java.lang." + name


