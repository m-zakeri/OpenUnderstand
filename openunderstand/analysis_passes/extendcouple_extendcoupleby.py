"""
## Description
This module find all OpenUnderstand call and callby references in a Java project


## References


"""

__author__ = "Shaghayegh Mobasher , Setayesh kouloubandi ,Parisa Alaie"
__version__ = "0.1.0"

from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties


class ExtendCoupleAndExtendCoupleBy(JavaParserLabeledListener):
    """
    #Todo: Implementing the ANTLR listener pass for Java Call and Java Callby reference kind
    """

    def __init__(self):
        self.implement = []
        self.relations = []
        self.imports = {}
        self.wildcards = []

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        longname = ctx.qualifiedName().getText()
        if ctx.getText().rstrip(";").endswith(".*"):
            self.wildcards.append(longname)
            return
        self.imports[longname.split(".")[-1]] = longname

    def enterEnumDeclaration(self, ctx: JavaParserLabeled.EnumDeclarationContext):
        """`enum MyEnum implements JSONString` -- plus the implicit parent.

        Every enum extends java.lang.Enum, and Understand records it the way it
        records an implicit java.lang.Object: `Java Extend Couple Implicit
        External` on the enum's line at no column. All four of JSON's enums
        carry one and this pass emitted none, so CountClassBase answered 0 for
        them and CountDeclMethodAll stopped at the project boundary.
        """
        from openunderstand.ounderstand import symbol_table

        scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(scope_parents + [ctx.IDENTIFIER().__str__()])
        self.relations.append(
            {
                "kind": "Java Extend Couple Implicit External",
                "scope_longname": scope_longname,
                "ent_longname": "java.lang.Enum",
                "name": "Enum",
                "line": ctx.start.line,
                "col": 0,
                "column_is_absolute": True,
            }
        )
        if ctx.typeList() is None:
            return
        for type_ctx in ctx.typeList().typeType():
            written = type_ctx.getText().split("<")[0]
            longname = symbol_table.resolve_type_name(
                written, self.imports, self.wildcards, scope_longname
            )
            if longname is None:
                continue
            token = type_ctx.start
            self.relations.append(
                {
                    "kind": "Java Implement Couple",
                    "scope_longname": scope_longname,
                    "ent_longname": longname,
                    "name": longname.rsplit(".", 1)[-1],
                    "line": token.line,
                    "col": token.column,
                }
            )

    def enterClassCreatorRest(self, ctx: JavaParserLabeled.ClassCreatorRestContext):
        """`new Iterable<Integer>() { ... }` -- what an anonymous class inherits.

        Understand gives it two bases when the created type is an interface:
        `Java Implement Couple` on the interface at its own token, and
        java.lang.Object implicitly, because an anonymous class implementing an
        interface extends Object. When the created type is a *class* it gives
        one -- `Java Extend Couple External` on java.io.StringReader for
        `new StringReader(...) { ... }` -- and no Object, which is then not
        immediate. 11 of JSON's 12 anonymous classes are the first shape.

        Nothing recorded either before, because nothing declared the anonymous
        class at all; with the class declared and its supertype missing,
        CountClassBase answered 0 for all twelve.
        """
        name = class_properties.anonymous_name(ctx)
        if name is None:
            return
        created = self._created_name(ctx)
        if created is None:
            return
        from openunderstand.oudb import jdk_index
        from openunderstand.ounderstand import symbol_table

        scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(scope_parents + [name])
        written = created.getText().split("<")[0]
        longname = symbol_table.resolve_type_name(
            written, self.imports, self.wildcards, scope_longname
        )
        if longname is None:
            return  # a wrong supertype is worse than a missing one
        in_project = (
            symbol_table.resolve_type(written.rsplit(".", 1)[-1], scope_longname)
            is not None
        )
        interface = (
            symbol_table.is_interface(longname)
            if in_project
            else jdk_index.is_interface(longname)
        )
        if interface:
            kind = "Java Implement Couple"
        else:
            kind = "Java Extend Couple" if in_project else "Java Extend Couple External"
        token = created.start
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
        if interface:
            self.relations.append(
                {
                    "kind": "Java Extend Couple Implicit External",
                    "scope_longname": scope_longname,
                    "ent_longname": "java.lang.Object",
                    "name": "Object",
                    "line": ctx.classBody().start.line,
                    "col": 0,
                    "column_is_absolute": True,
                }
            )

    @staticmethod
    def _created_name(ctx):
        """The `createdName` a classCreatorRest hangs off, or None.

        Three producers: `creator0` puts explicit type arguments before it,
        `creator1` is the plain `new X()`, and `innerCreator` is `o.new X()`,
        which names the type with a bare IDENTIFIER instead.
        """
        parent = ctx.parentCtx
        getter = getattr(parent, "createdName", None)
        if getter is None:
            return None
        try:
            return getter()
        except TypeError:
            return None

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        """`class X extends Y`.

        Understand positions this on Y's own token and names Y in full, and
        splits the kind by where Y lives: a supertype inside the project is a
        Java Extend Couple, one outside it is Java Extend Couple External --
        `EmptyHeapException extends Exception` is the External kind pointing at
        java.lang.Exception. This recorded the bare text `Exception` at the
        `class` keyword's column under the non-External kind, so none of the
        three on TheAlgorithms matched.
        """
        if not ctx.EXTENDS():
            return
        scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(scope_parents + [ctx.IDENTIFIER().__str__()])
        type_ctx = ctx.typeType()
        if type_ctx is None:
            return
        from openunderstand.ounderstand import symbol_table

        written = type_ctx.getText()
        longname = symbol_table.resolve_type_name(
            written, self.imports, self.wildcards, scope_longname
        )
        if longname is None:
            return
        in_project = (
            symbol_table.resolve_type(written.split("<")[0], scope_longname) is not None
        )
        token = type_ctx.start
        self.relations.append(
            {
                "kind": (
                    "Java Extend Couple"
                    if in_project
                    else "Java Extend Couple External"
                ),
                "scope_longname": scope_longname,
                "ent_longname": longname,
                "name": longname.rsplit(".", 1)[-1],
                "line": token.line,
                "col": token.column,
            }
        )
