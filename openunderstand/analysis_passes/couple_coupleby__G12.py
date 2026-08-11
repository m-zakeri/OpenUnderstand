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
            return

        self.add(self.resolve_type_longname(ctx))

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
        self.add(self.lookup_receiver(receiver))

    def lookup_receiver(self, name):
        """Long name if `name` denotes a type, else None. No guessing."""
        from openunderstand.ounderstand import symbol_table

        if not name or name in self.type_parameters:
            return None
        if name in self.Imports:
            return self.Imports[name]
        in_project = symbol_table.resolve_type(name)
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
        in_project = symbol_table.resolve_type(name)
        if in_project:
            return in_project
        # An unqualified name that is neither imported nor declared here is
        # implicitly java.lang -- String, Object, Integer, Throwable. This used
        # to be `self.packageName + '.' + name`, which produced org.json.String
        # for every one of them: a false positive and a missed true positive at
        # the same time.
        # ponytail: wildcard imports (`import java.util.*`) also land here and
        # get mislabelled java.lang. Revisit if parity shows it matters.
        return "java.lang." + name


