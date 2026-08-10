"""Collect the qualified Use/Typed reference variants.

Understand does not label every use the same way -- on the JSON benchmark it
emits 788 ``Java Use Deref Partial``, 124 ``Java Use Cast``, 120 ``Java Use
Return``, 93 ``Java Typed GenericArgument`` and 32 ``Java Use Annotation``
alongside the plain ``Java Use``. None of them had a producer here, which is
why they showed up in the comparison as reference kinds that exist in the
vocabulary but never get a row.

Each variant is a syntactic position, so each one is a single grammar
alternative:

  Use Deref Partial   the receiver of ``a.b``      (expression1)
  Use Cast            the type named in ``(T) x``  (expression5)
  Use Return          an identifier in ``return x``(statement10)
  Use Annotation      ``@Override``                (annotation)
  Typed GenericArgument / Use GenericArgument
                      the ``T`` of ``List<T>``     (typeArguments)

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

    def _add(self, kind, name, ctx, token):
        if not name:
            return
        self.uses.append({
            "kind": kind,
            "name": name,
            "scope_longname": ".".join(
                class_properties.ClassPropertiesListener.findParents(ctx)
            ),
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

    def enterExpression5(self, ctx: JavaParserLabeled.Expression5Context):
        type_ctx = ctx.typeType()
        if type_ctx is None:
            return
        self._add("Java Use Cast", _simple_type_name(type_ctx),
                  ctx, type_ctx.start)

    def enterStatement10(self, ctx: JavaParserLabeled.Statement10Context):
        expression = ctx.expression()
        if expression is None:
            return
        text = expression.getText()
        if not text.isidentifier():
            return
        self._add("Java Use Return", text, ctx, expression.start)

    def enterAnnotation(self, ctx: JavaParserLabeled.AnnotationContext):
        qualified = ctx.qualifiedName()
        if qualified is None:
            return
        self._add("Java Use Annotation",
                  qualified.IDENTIFIER()[-1].getText(), ctx, ctx.start)

    def enterTypeArguments(self, ctx: JavaParserLabeled.TypeArgumentsContext):
        for argument in ctx.typeArgument():
            type_ctx = argument.typeType() if hasattr(argument, "typeType") else None
            if type_ctx is None:
                continue
            self._add("Java Typed GenericArgument", _simple_type_name(type_ctx),
                      ctx, type_ctx.start)


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