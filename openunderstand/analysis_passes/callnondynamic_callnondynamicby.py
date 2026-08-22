"""
## Description
This module find all OpenUnderstand call and callby references in a Java project


## References


"""

from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties


class CallNonDynamicAndCallNonDynamicBy(JavaParserLabeledListener):
    """
    #Todo: Implementing the ANTLR listener pass for Java Call and Java Callby reference kind
    """

    def __init__(self):
        self.implement = []

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        bodies = ctx.classBody().classBodyDeclaration()
        if bodies is not None:
            if ctx.EXTENDS():
                extendedBy = ctx.typeType().classOrInterfaceType().IDENTIFIER(i=0)
                for body in bodies:
                    member = getattr(body, "memberDeclaration", None)
                    if member is not None:
                        member = member()
                        method = getattr(member, "methodDeclaration", None)
                        if method is not None:
                            method = method()
                            body_ctx = method.methodBody()
                            block = body_ctx.block() if body_ctx else None
                            if block is not None:
                                self.dfs(block, method, ctx, extendedBy)

    @staticmethod
    def scope_of(method, line, col, called):
        """The call site's scope: the method the `super.x()` call sits in.

        `dfs` calls its parameters (ctx, cls, context) but passes
        (block, methodDeclaration, classDeclaration), so `cls` here is a
        *method*. This used to take the long name from
        `findParents(classDeclaration)`, which -- as that function's docstring
        says -- excludes the context's own identifier, so the class name never
        made it in and the long name was the bare package. The scope was then
        written as a *class* entity called `org.json.junit.data` holding the
        method's `getText()`, and the four references scoped to it could never
        match Understand, which scopes a call to the calling method.

        `findParents(method)` walks up through the class, so appending the
        method's own name gives package.Class.method -- the same shape
        `method_calls.py` produces for every other call.
        """
        parents = class_properties.ClassPropertiesListener.findParents(method)
        name = method.IDENTIFIER().getText()
        return {
            "scope_kind": "Method",
            "scope_name": name,
            "scope_longname": ".".join(parents + [name]),
            "scope_parent": parents[-1] if parents else None,
            "scope_contents": "",
            "scope_modifiers": class_properties.ClassPropertiesListener.findClassOrInterfaceModifiers(
                method
            ),
            "line": line,
            "col": col,
            "type_ent_longname": str(called),
        }

    def dfs(self, ctx, cls, context, extendedBy):
        bStatements = ctx.blockStatement()
        for bStatement in bStatements:
            kk = str(type(bStatement)).split(".")[-1][:-2]
            kk2 = "BlockStatement1Context"
            if kk == kk2:

                statement = bStatement.statement()

                s = getattr(statement, "statement", None)

                if s is not None:
                    s = s()
                    bb = getattr(s, "block", None)
                    if bb is not None:
                        bb = bb()
                        self.dfs(bb, cls, context, extendedBy)
                else:
                    exp = statement
                    if hasattr(statement, "expression"):
                        exp = statement.expression()
                    exp2 = getattr(exp, "expression", None)
                    if exp2 is not None:
                        exp2 = exp2()
                        primary = getattr(exp2, "primary", None)
                        if primary is not None:
                            primary = primary()
                            super = getattr(primary, "SUPER", None)
                            if super is not None:
                                super = super()

                                if type(exp) == list:

                                    for exp3 in exp:
                                        methodCall = getattr(exp3, "methodCall", None)
                                        if methodCall is not None:
                                            methodCall = methodCall()
                                            if methodCall is not None:
                                                called = methodCall.IDENTIFIER()
                                                self.implement.append(
                                                    self.scope_of(
                                                        cls,
                                                        context.children[0].symbol.line,
                                                        context.children[
                                                            0
                                                        ].symbol.column,
                                                        called,
                                                    )
                                                )

                                else:
                                    methodCall = getattr(exp, "methodCall", None)
                                    if methodCall is not None:
                                        methodCall = methodCall()
                                        if methodCall is not None:
                                            called = methodCall.IDENTIFIER()
                                            self.implement.append(
                                                self.scope_of(
                                                    cls,
                                                    methodCall.start.line,
                                                    methodCall.start.column,
                                                    called,
                                                )
                                            )
