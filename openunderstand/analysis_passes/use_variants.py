"""Collect the qualified Use/Typed reference variants.

Understand does not label every use the same way -- on the JSON benchmark it
emits 788 ``Java Use Deref Partial``, 120 ``Java Use
Return``, 93 ``Java Typed GenericArgument`` and 32 ``Java Use Annotation``
alongside the plain ``Java Use``. None of them had a producer here, which is
why they showed up in the comparison as reference kinds that exist in the
vocabulary but never get a row.

Each variant is a syntactic position, so each one is a single grammar
alternative:

  Use Deref Partial   the receiver of ``a.b``      (expression1)
  Use Return          an identifier in ``return x``(statement10)
  Use Annotation      ``@Override``                (annotation)
  Typed GenericArgument / Use GenericArgument
                      the ``T`` of ``List<T>``     (typeArguments)

``Java Use Cast`` is *not* here. It shares expression5 with this pass but needs
a primitive filter and type-parameter resolution that none of the others do, so
it lives in ``cast_cast_by.py`` -- and while both emitted it, every cast got
two rows and every ``(int) x`` got one it should not have.

The listener only collects; resolving a name to an entity is the write
layer's job.
"""

from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
import openunderstand.analysis_passes.class_properties as class_properties


#: Java's keyword literals are valid Python identifiers, so the isidentifier()
#: guard each handler uses lets them through. `return true;` named an entity
#: `false`/`true`/`null` and pointed 114 references at it on TheAlgorithms.
#: Checked once here rather than in each handler, which is where the bug got in.
LITERALS = frozenset(("true", "false", "null"))


class UseVariantListener(JavaParserLabeledListener):
    def __init__(self, file_address=""):
        self.file_address = file_address
        self.uses = []

    def _add(self, kind, name, ctx, token, suffix=None, ent_longname=None):
        if not name or name in LITERALS:
            return
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if suffix:
            # The reference belongs to the declaration the construct attaches
            # to, which findParents() stops short of.
            parents = parents + [suffix]
        scope_longname = ".".join(parents)
        self.uses.append({
            "kind": kind,
            "name": name,
            "scope_longname": scope_longname,
            # Set when the pass already knows which entity is meant and the
            # writer must not go looking by name. `<E extends Enum<E>>` reads
            # its own type parameter, so entity and scope are the same thing;
            # resolving "E" by name instead found an arbitrary other E.
            "ent_longname": scope_longname if ent_longname is True else ent_longname,
            "line": token.line,
            "col": token.column,
        })

    def enterExpression1(self, ctx: JavaParserLabeled.Expression1Context):
        # `a.b` -- `a` is used by dereference. Only a bare identifier receiver
        # names an entity; `f().b` dereferences a value, not a named thing.
        receiver = ctx.expression()
        if receiver is None or type(receiver).__name__ != "Expression0Context":
            return
        text = receiver.getText()
        if not text.isidentifier():
            return
        self._add("Java Use Deref Partial", text, ctx, receiver.start)

    def enterStatement10(self, ctx: JavaParserLabeled.Statement10Context):
        expression = ctx.expression()
        if expression is None:
            return
        text = expression.getText()
        if not text.isidentifier():
            return
        self._add("Java Use Return", text, ctx, expression.start)

    def enterAnnotation(self, ctx: JavaParserLabeled.AnnotationContext):
        """`@Override` is used *by the thing it annotates*, not by its class.

        Understand scopes it to the annotated member -- a method, or even a
        local: `@SuppressWarnings` on `E myE = ...` inside optEnum is scoped to
        org.json.JSONArray.optEnum.myE. Scoping it to the enclosing class, and
        positioning it on the `@` rather than the name, meant none of the 31
        references on JSON matched.
        """
        qualified = ctx.qualifiedName()
        if qualified is None:
            return
        annotated = _annotated_name(ctx)
        self._add("Java Use Annotation",
                  qualified.IDENTIFIER()[-1].getText(), ctx, qualified.start,
                  suffix=annotated)

    def enterTypeArguments(self, ctx: JavaParserLabeled.TypeArgumentsContext):
        """`List<T>` -- the T, labelled by where the list is written.

        Understand splits these two ways, and on one line of
        SimpleSubstitutionCipher both appear:

            Map<Character, Character> cipherMap = new HashMap<Character, ...>();
            ^ Typed GenericArgument, scoped to ...decode.cipherMap
                                                 ^ Use GenericArgument, scoped
                                                   to ...decode

        A type argument in a *declaration's type* belongs to the thing being
        declared; one in an *expression* belongs to the method containing it.
        Emitting every one as Typed GenericArgument scoped to the method gave
        19% precision and left Use GenericArgument with no producer at all.
        """
        # `class Graph<E extends Comparable<E>>` -- the inner E sits inside the
        # *declaration of E*, and Understand scopes it to the type parameter,
        # not to Graph: scope and entity are both Graph.E. Checked first
        # because such an argument is never part of a declaration's type.
        bound = _type_parameter_scope(ctx)
        declared = None if bound else _declared_owner(ctx)
        kind = ("Java Typed GenericArgument" if declared
                else "Java Use GenericArgument")
        declared = declared or bound
        for argument in ctx.typeArgument():
            # A wildcard is an entity in its own right: Understand names it "?"
            # and reports 46 of JSON's 93 Typed GenericArgument references
            # against one. Skipping any argument without a concrete type left
            # exactly those unproduced.
            if argument.getText().startswith("?"):
                self._add(kind, "?", ctx, argument.start, suffix=declared)
                continue
            type_ctx = argument.typeType() if hasattr(argument, "typeType") else None
            if type_ctx is None:
                continue
            argument_name = _simple_type_name(type_ctx)
            self._add(kind, argument_name, ctx, type_ctx.start, suffix=declared,
                      # The bound of a type parameter naming that parameter.
                      ent_longname=bool(
                          bound and argument_name == bound.rsplit(".", 1)[-1]) or None)


def _type_parameter_scope(ctx):
    """Scope suffix when this sits inside a type parameter's bound, else None.

    `<T extends Comparable<T>>` on a *method* is a further trap: typeParameters
    is a sibling of the methodDeclaration under the genericMethodDeclaration
    wrapper, so findParents() walking up from the bound reaches the class and
    never sees the method name. The result is the method's own name has to be
    fetched back down off the wrapper -- `find.T`, not `T`.
    """
    node = ctx.parentCtx
    parameter = None
    while node is not None:
        name = type(node).__name__
        if name == "TypeParameterContext" and parameter is None:
            identifier = node.IDENTIFIER()
            if identifier is not None:
                parameter = identifier.getText()
        elif parameter and name.startswith("Generic") and "Method" in name:
            for attribute in ("methodDeclaration", "interfaceMethodDeclaration"):
                declaration = getattr(node, attribute, None)
                declaration = declaration() if callable(declaration) else None
                if declaration is not None and declaration.IDENTIFIER() is not None:
                    return f"{declaration.IDENTIFIER().getText()}.{parameter}"
        node = node.parentCtx
    return parameter


def _annotated_name(ctx):
    """Simple name of the declaration an annotation attaches to, or None.

    An annotation is a *sibling* of the declaration it modifies, not an
    ancestor of it, so walking up alone never reaches the name -- the search
    has to go up to the declaration node and then back down to its identifier.
    """
    node = ctx.parentCtx
    while node is not None:
        name = type(node).__name__
        if name.startswith("ClassBodyDeclaration"):
            member = getattr(node, "memberDeclaration", None)
            member = member() if callable(member) else None
            if member is not None:
                # genericMethodDeclaration and its constructor twin wrap the
                # real declaration: `@Override public <T> int find(...)` is a
                # generic method, and leaving them out left 24 of
                # TheAlgorithms' annotations scoped to the class instead of the
                # method.
                for attribute in ("methodDeclaration", "fieldDeclaration",
                                  "constructorDeclaration", "classDeclaration",
                                  "interfaceDeclaration",
                                  "genericMethodDeclaration",
                                  "genericConstructorDeclaration"):
                    inner = getattr(member, attribute, None)
                    inner = inner() if callable(inner) else None
                    if inner is not None:
                        return _first_declared_name(inner)
            return None
        if name.startswith("LocalVariableDeclaration"):
            return _first_declared_name(node)
        node = node.parentCtx
    return None


def _declared_owner(ctx):
    """Name of the declaration whose *type* these arguments are part of.

    None when they belong to an expression instead -- `new HashMap<K,V>()` --
    which is what separates Understand's Typed GenericArgument from its Use
    GenericArgument.
    """
    node = ctx.parentCtx
    while node is not None:
        name = type(node).__name__
        if name.startswith(("Creator", "CreatedName", "Expression",
                            "MethodCall", "Block")):
            return None
        if name.startswith(("TypeList", "ClassDeclaration",
                            "InterfaceDeclaration")):
            # `class Vertex implements Comparable<Vertex>` -- the arguments
            # belong to the class, which findParents() already names. Walking
            # past this reached the class again and appended it twice, so the
            # scope came out as Others.Graph.Vertex.Vertex.
            return None
        if name.startswith(("LocalVariableDeclaration", "FieldDeclaration")):
            return _first_declared_name(node)
        if name.startswith("FormalParameter"):
            identifier = node.variableDeclaratorId()
            return identifier.getText().split("[")[0] if identifier else None
        if name.startswith("MethodDeclaration"):
            # The return type's arguments belong to the method itself.
            return _first_declared_name(node)
        node = node.parentCtx
    return None


def _first_declared_name(node):
    # A generic declaration wraps the real one: its own IDENTIFIER() is the
    # type parameter list's, not the member's.
    for wrapper in ("methodDeclaration", "constructorDeclaration"):
        if type(node).__name__.startswith("Generic"):
            inner = getattr(node, wrapper, None)
            inner = inner() if callable(inner) else None
            if inner is not None:
                node = inner
                break
    identifier = getattr(node, "IDENTIFIER", None)
    if callable(identifier):
        try:
            token = identifier()
        except TypeError:
            token = None
        if token is not None and not isinstance(token, list):
            return token.getText()
    declarators = getattr(node, "variableDeclarators", None)
    declarators = declarators() if callable(declarators) else None
    if declarators is not None:
        first = declarators.variableDeclarator()
        if first:
            return first[0].variableDeclaratorId().getText().split("[")[0]
    return None


def _simple_type_name(type_ctx):
    """Last identifier of a type, without generics or array brackets."""
    holder = type_ctx.classOrInterfaceType() if hasattr(
        type_ctx, "classOrInterfaceType") else None
    if holder is not None:
        identifiers = holder.IDENTIFIER()
        if identifiers:
            return identifiers[-1].getText()
    text = type_ctx.getText().split("<")[0].replace("[]", "")
    return text.rsplit(".", 1)[-1] if text else ""