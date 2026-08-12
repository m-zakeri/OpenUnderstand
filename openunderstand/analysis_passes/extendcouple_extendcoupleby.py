"""
## Description
This module find all OpenUnderstand call and callby references in a Java project


## References


"""

__author__ = "Shaghayegh Mobasher , Setayesh kouloubandi ,Parisa Alaie"
__version__ = "0.1.0"

from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
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
            written, self.imports, self.wildcards, scope_longname)
        if longname is None:
            return
        in_project = symbol_table.resolve_type(
            written.split("<")[0], scope_longname) is not None
        token = type_ctx.start
        self.relations.append({
            "kind": ("Java Extend Couple" if in_project
                     else "Java Extend Couple External"),
            "scope_longname": scope_longname,
            "ent_longname": longname,
            "name": longname.rsplit(".", 1)[-1],
            "line": token.line,
            "col": token.column,
        })
