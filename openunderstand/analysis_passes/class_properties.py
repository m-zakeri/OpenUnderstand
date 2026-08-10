"""
The helper module for couple_coupleby.py, create_createby_g11.py, declare_declareby.py modules

Todo: Must be document well
"""

__author__ = "Shaghayegh Mobasher , Setayesh kouloubandi ,Parisa Alaie, Zakeri"
__version__ = "0.1.1"


from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from antlr4 import *


class ClassPropertiesListener(JavaParserLabeledListener):
    def __init__(self):
        self.class_longname = []
        self.class_properties = None

    def checkParents(self, c):
        # reversed(self.class_longname)
        # myList = []
        # myList.append(".".join(self.class_longname))
        return set(ClassPropertiesListener.findParents(c)) & set(
            list(reversed(self.class_longname))
        )

    # Rules that name an enclosing scope. Each one carries an IDENTIFIER.
    #
    # RULE_typeDeclaration is deliberately absent: it is only a wrapper around
    # classDeclaration / interfaceDeclaration / enumDeclaration, it has no
    # IDENTIFIER of its own, and the rule it wraps already contributes the
    # name. While it was listed here it fell through to the package branch
    # below and appended the entire class body as a name component, producing
    # longnames like "org.json.classJSONML{privatestaticObjectparse(...".
    _SCOPE_RULES = frozenset({
        JavaParserLabeled.RULE_classDeclaration,
        JavaParserLabeled.RULE_methodDeclaration,
        JavaParserLabeled.RULE_enumDeclaration,
        JavaParserLabeled.RULE_interfaceDeclaration,
        JavaParserLabeled.RULE_constructorDeclaration,
        JavaParserLabeled.RULE_annotationTypeDeclaration,
        JavaParserLabeled.RULE_genericInterfaceMethodDeclaration,
    })

    @staticmethod
    def _package_components(compilation_unit):
        """Dotted components of the file's package declaration, or []."""
        try:
            pkg = compilation_unit.packageDeclaration()
        except AttributeError:
            return []
        if pkg is None:
            return []
        try:
            return [str(i) for i in pkg.qualifiedName().IDENTIFIER()]
        except AttributeError:
            return []

    @staticmethod
    def findParents(c: ParserRuleContext):
        """Names of the scopes enclosing ``c``, outermost first.

        Starts at ``c.parentCtx``, so the result does NOT include ``c``'s own
        identifier -- callers wanting a fully qualified name must append it.

        The package contributes each of its dotted components as a separate
        entry, so a method in class ``CDL`` in ``package org.json`` yields
        ``["org", "json", "CDL"]``.

        Note the package is read from the compilation unit at the end rather
        than found during the walk: ``packageDeclaration`` is a *sibling* of
        ``typeDeclaration`` under ``compilationUnit``, never an ancestor, so
        walking up from a declaration never reaches it. This previously worked
        only by accident -- ``typeDeclaration`` has no IDENTIFIER, so it raised
        and a fallback re-parsed ``parentCtx.getChild(0)`` as package text.
        That fallback also fired for contexts where child 0 was not the package
        declaration, splicing whole class bodies into longnames.
        """
        parents = []
        current = c.parentCtx
        root = None
        while current is not None:
            if current.getRuleIndex() in ClassPropertiesListener._SCOPE_RULES:
                identifier = current.IDENTIFIER()
                if identifier is not None:
                    parents.append(identifier.getText())
            root = current
            current = current.parentCtx
        parents.reverse()
        return ClassPropertiesListener._package_components(root) + parents

    @staticmethod
    def findClassOrInterfaceModifiers(c):
        m = ""
        modifiers = []
        current = c
        while current is not None:
            if "typeDeclaration" in type(current.parentCtx).__name__:
                m = current.parentCtx.classOrInterfaceModifier()
                break
            current = current.parentCtx
        for x in m:
            modifiers.append(x.getText())
        return modifiers

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        if self.class_properties:  # already found the class
            return
        if self.class_longname[-1] == ctx.IDENTIFIER().getText():
            if self.checkParents(ctx):
                # this is the exact class we wanted.
                self.class_properties = {}
                self.class_properties["name"] = self.class_longname[-1]
                self.class_properties["longname"] = ".".join(self.class_longname)

                if len(self.class_longname) == 1:
                    self.class_properties["parent"] = None
                else:
                    self.class_properties["parent"] = self.class_longname[-2]
                self.class_properties["modifiers"] = (
                    ClassPropertiesListener.findClassOrInterfaceModifiers(ctx)
                )
                self.class_properties["contents"] = ctx.getText()


class InterfacePropertiesListener(JavaParserLabeledListener):
    interface_longname = []
    interface_properties = None

    def checkParents(self, c):
        return set(ClassPropertiesListener.findParents(c)) & set(
            list(reversed(self.interface_longname))
        )

    def enterInterfaceDeclaration(
        self, ctx: JavaParserLabeled.InterfaceDeclarationContext
    ):
        if self.interface_properties:  # already found the interface
            return
        if self.interface_longname[-1] == ctx.IDENTIFIER().getText():
            if self.checkParents(ctx):
                # this is the exact class we wanted.
                self.interface_properties = {}
                self.interface_properties["name"] = self.interface_longname[-1]
                self.interface_properties["longname"] = ".".join(
                    self.interface_longname
                )

                if len(self.interface_longname) == 1:
                    self.interface_properties["parent"] = None
                else:
                    self.interface_properties["parent"] = self.interface_longname[-2]
                self.interface_properties["modifiers"] = (
                    ClassPropertiesListener.findClassOrInterfaceModifiers(ctx)
                )
                self.interface_properties["contents"] = ctx.getText()
