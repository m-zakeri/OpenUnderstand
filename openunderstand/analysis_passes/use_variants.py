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


class UseVariantListener(JavaParserLabeledListener):
    def __init__(self, file_address=""):
        self.file_address = file_address
        self.uses = []

    def _add(self, kind, name, ctx, token, suffix=None):
        if not name:
            return
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if suffix:
            # The reference belongs to the declaration the construct attaches
            # to, which findParents() stops short of.
            parents = parents + [suffix]
        self.uses.append({
            "kind": kind,
            "name": name,
            "scope_longname": ".".join(parents),
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
        declared = _declared_owner(ctx)
        kind = ("Java Typed GenericArgument" if declared
                else "Java Use GenericArgument")
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
            self._add(kind, _simple_type_name(type_ctx), ctx, type_ctx.start,
                      suffix=declared)


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