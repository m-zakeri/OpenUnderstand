"""
The helper module for couple_coupleby.py, create_createby.py, declare_declareby.py modules

Todo: Must be document well
"""

__author__ = "Shaghayegh Mobasher , Setayesh kouloubandi ,Parisa Alaie, Zakeri"
__version__ = "0.1.1"


from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
from antlr4 import *
from functools import lru_cache


#: Two entries: the per-file walk asks about one tree at a time, and a metric
#: that reparses a snippet alternates between two. Keyed on the root context
#: itself, so a freed tree cannot have its id reused under a live cache entry.
@lru_cache(maxsize=2)
def _anonymous_names(root):
    """{id(classCreatorRest): "(Anon_N)"} for every anonymous class in a tree.

    Understand numbers them over the file in source order, which a pre-order
    walk visits them in. Numbering cannot be done while walking *up* from a
    declaration -- the nth anonymous class is only knowable from the whole file
    -- so it is computed once per tree and cached.

    ponytail: numbered per file, not per outer class. The two differ only in a
    file holding more than one top-level type, which none of the eleven
    benchmark subjects does.
    """
    names, count = {}, 0

    def walk(node):
        nonlocal count
        if (
            isinstance(node, JavaParserLabeled.ClassCreatorRestContext)
            and node.classBody() is not None
        ):
            count += 1
            names[id(node)] = "(Anon_%d)" % count
        for i in range(node.getChildCount()):
            child = node.getChild(i)
            if isinstance(child, ParserRuleContext):
                walk(child)

    walk(root)
    return names


@lru_cache(maxsize=2)
def _lambda_names(root):
    """{id(lambdaExpression): "(lambda_expr_N)"} for every lambda in a tree.

    Numbered from 1 within the method that encloses it, in source order, which
    is Understand's naming: `testOptBigDecimalVariousTypes` holds
    `(lambda_expr_1)` through `(lambda_expr_3)`.
    """
    names, counts = {}, {}

    def enclosing(node):
        node = node.parentCtx
        while node is not None:
            if node.getRuleIndex() in ClassPropertiesListener._SCOPE_RULES:
                return id(node)
            node = node.parentCtx
        return None

    def walk(node):
        if isinstance(node, JavaParserLabeled.LambdaExpressionContext):
            key = enclosing(node)
            counts[key] = counts.get(key, 0) + 1
            names[id(node)] = "(lambda_expr_%d)" % counts[key]
        for i in range(node.getChildCount()):
            child = node.getChild(i)
            if isinstance(child, ParserRuleContext):
                walk(child)

    walk(root)
    return names


@lru_cache(maxsize=2)
def _catch_names(root):
    """{id(catchClause): "(catch_N)"} for every catch clause in a tree.

    Numbered over the *file* in source order, which is Understand's naming:
    JSONTokener.java runs `more.(catch_1)` through `skipTo.(catch_7)`. Each
    clause is a scope, so two `catch (X e)` in one method are two `e` entities
    -- `more.(catch_1).e` and `more.(catch_2).e` -- where a single `more.e`
    counted one, and CountInput was short by one on every method with two.
    """
    names, count = {}, 0

    def walk(node):
        nonlocal count
        if isinstance(node, JavaParserLabeled.CatchClauseContext):
            count += 1
            names[id(node)] = "(catch_%d)" % count
        for i in range(node.getChildCount()):
            child = node.getChild(i)
            if isinstance(child, ParserRuleContext):
                walk(child)

    walk(root)
    return names


def lambda_name(ctx):
    """`(lambda_expr_N)` for a lambda expression."""
    root = ctx
    while root.parentCtx is not None:
        root = root.parentCtx
    return _lambda_names(root).get(id(ctx))


def anonymous_name(ctx):
    """`(Anon_N)` for a classCreatorRest that carries a body, else None."""
    if ctx.classBody() is None:
        return None
    root = ctx
    while root.parentCtx is not None:
        root = root.parentCtx
    return _anonymous_names(root).get(id(ctx))


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

    _SCOPE_RULES = frozenset(
        {
            JavaParserLabeled.RULE_classDeclaration,
            JavaParserLabeled.RULE_methodDeclaration,
            JavaParserLabeled.RULE_enumDeclaration,
            JavaParserLabeled.RULE_interfaceDeclaration,
            JavaParserLabeled.RULE_constructorDeclaration,
            JavaParserLabeled.RULE_annotationTypeDeclaration,
            JavaParserLabeled.RULE_genericInterfaceMethodDeclaration,
        }
    )

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
        chain, root = [], None
        current = c.parentCtx
        while current is not None:
            chain.append(current)
            root = current
            current = current.parentCtx

        anonymous = _anonymous_names(root) if root is not None else {}
        lambdas = _lambda_names(root) if root is not None else {}
        catches = _catch_names(root) if root is not None else {}
        parents = []
        for current in chain:
            rule = current.getRuleIndex()
            if rule in ClassPropertiesListener._SCOPE_RULES:
                identifier = current.IDENTIFIER()
                if identifier is not None:
                    parents.append(identifier.getText())
            elif rule == JavaParserLabeled.RULE_classCreatorRest:
                name = anonymous.get(id(current))
                if name is not None:
                    parents.append(name)
            elif rule == JavaParserLabeled.RULE_lambdaExpression:
                name = lambdas.get(id(current))
                if name is not None:
                    parents.append(name)
            elif rule == JavaParserLabeled.RULE_catchClause:
                # A catch clause is a scope of its own, so its parameter is not
                # the method's: two `catch (X e)` in one method are two `e`.
                name = catches.get(id(current))
                if name is not None:
                    parents.append(name)
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
