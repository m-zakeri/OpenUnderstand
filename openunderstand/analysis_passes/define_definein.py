"""


"""

import os
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties
from openunderstand.utils import kind_names as K


# Rules that carry the modifier list for a declaration nested inside them.
# A member's modifiers hang off classBodyDeclaration/interfaceBodyDeclaration,
# two levels above the declaration itself, so they have to be walked to.
_MODIFIER_ACCESSORS = ("modifier", "classOrInterfaceModifier", "variableModifier",
                       "interfaceMethodModifier")


def _modifiers_at(ctx):
    """Modifier keywords attached directly to `ctx`, lowercased.

    Annotations are skipped: `classOrInterfaceModifier` matches `annotation`
    too, and `@Override` is not a modifier.
    """
    for accessor in _MODIFIER_ACCESSORS:
        getter = getattr(ctx, accessor, None)
        if getter is None:
            continue
        try:
            nodes = getter()
        except TypeError:
            continue
        if not nodes:
            continue
        out = []
        for node in nodes:
            text = node.getText()
            if text.startswith("@"):
                continue
            out.append(text.lower())
        if out:
            return out
    return []


def _enclosing_modifiers(ctx, depth=3):
    """Modifiers of a declaration, searched up through its wrapper rules.

    `classDeclaration` sits under `typeDeclaration` (top level),
    `memberDeclaration7 -> classBodyDeclaration2` (nested), or
    `interfaceMemberDeclaration5 -> interfaceBodyDeclaration`. Rather than
    enumerate every wrapper, walk up a bounded number of levels and take the
    first that carries modifiers.
    """
    current = ctx.parentCtx
    for _ in range(depth):
        if current is None:
            return []
        found = _modifiers_at(current)
        if found:
            return found
        current = current.parentCtx
    return []


# Context class names (labelled alternatives get a numeric suffix, hence the
# prefix match) that wrap a declaration together with its modifier list.
_SPAN_WRAPPERS = (
    "TypeDeclarationContext", "ClassBodyDeclaration", "MemberDeclaration",
    "InterfaceBodyDeclarationContext", "InterfaceMemberDeclaration",
    "LocalTypeDeclarationContext", "GenericMethodDeclarationContext",
    "GenericConstructorDeclarationContext", "GenericInterfaceMethodDeclarationContext",
)


def _body_span(ctx):
    """(begin, end) positions of a declaration that has a braced body.

    Understand reports a Begin reference where the declaration starts -- at its
    first modifier, not at its name -- and an End reference at the matching
    closing brace. Returns None for declarations with no body (an abstract or
    interface method ends in `;`), which get neither reference.
    """
    stop = ctx.stop
    if stop is None or stop.text != "}":
        return None
    start = ctx.start
    current = ctx.parentCtx
    # Climb only through the rules that wrap a declaration together with its
    # modifiers. Climbing blindly reaches compilationUnit and reports every
    # method as beginning at line 1.
    while current is not None and type(current).__name__.startswith(_SPAN_WRAPPERS):
        if current.start is not None and current.start.tokenIndex < start.tokenIndex:
            start = current.start
        current = current.parentCtx
    return (start.line, start.column), (stop.line, stop.column)


def source_text(ctx):
    """The declaration's original source, whitespace and all.

    `ctx.getText()` concatenates token text, so a method comes back as
    `publicvoidmain(String[]args){...}` -- which is not Java and cannot be
    reparsed. Every metric that works by reparsing `ent.contents()`
    (Cyclomatic, CountStmt, CountLineCode, MaxNesting, …) was therefore
    returning 0. The input stream still holds the real characters.
    """
    start, stop = ctx.start, ctx.stop
    if start is None or stop is None:
        return ctx.getText()
    stream = start.getInputStream()
    if stream is None:
        return ctx.getText()
    try:
        return stream.getText(_doc_comment_start(stream, start.start), stop.stop)
    except Exception:
        return ctx.getText()


def _doc_comment_start(stream, begin):
    """Extend a declaration's start back over its documentation comment.

    Understand treats the comment block immediately above a declaration as part
    of it: on JSONObject that is 53 lines, which is exactly how far CountLine
    and CountLineComment were short. Only whitespace may separate the comment
    from the declaration, so a comment belonging to something else is not
    swallowed.
    """
    try:
        text = stream.strdata
    except AttributeError:
        return begin

    i = begin - 1
    while i >= 0 and text[i] in " \t\r\n":
        i -= 1
    if i < 1:
        return begin

    if text[i - 1:i + 1] == "*/":
        opening = text.rfind("/*", 0, i)
        return opening if opening != -1 else begin

    # A run of // lines directly above the declaration.
    end_of_run = i
    start_of_run = None
    while True:
        line_start = text.rfind("\n", 0, end_of_run) + 1
        if not text[line_start:end_of_run + 1].lstrip().startswith("//"):
            break
        start_of_run = line_start
        end_of_run = line_start - 1
        while end_of_run >= 0 and text[end_of_run] in " \t\r\n":
            end_of_run -= 1
        if end_of_run < 0:
            break
    return start_of_run if start_of_run is not None else begin


def _is_generic(ctx):
    getter = getattr(ctx, "typeParameters", None)
    try:
        return getter is not None and getter() is not None
    except TypeError:
        return False


class DefineListener(JavaParserLabeledListener):
    def __init__(self, file_address):
        self.defines = []
        self.package = ""
        self.lambda_expression_count = 0
        self.file_address = file_address

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.package = [str(i) for i in ctx.qualifiedName().IDENTIFIER()]

        ent_start = ctx.qualifiedName().IDENTIFIER()[0]
        ent_name = ctx.qualifiedName().IDENTIFIER()[-1].getText()
        # A package is identified by its dotted name. This used to join the
        # components with "/" and then prefix the source file path, producing
        # longnames like "/abs/path/CDL.java/org/json" that match nothing.
        ent_longname = ".".join(self.package)
        line = ent_start.symbol.line
        column = ent_start.symbol.column
        self.defines.append(
            {
                "contents": ctx.getText(),
                "type": "Package",
                "decl": K.PACKAGE,
                "modifiers": [],
                "span": None,
                "parent": self.file_address,
                "scope": None,
                "ent": ent_name,
                "scope_longname": None,
                "ent_longname": ent_longname,
                "line": line,
                "col": column,
            }
        )

    def add_define_info(
        self, ent, ent_parents, ent_name=None, type=None, contents=None,
        decl=None, modifiers=(), span=None,
    ):
        if ent_name is None:
            ent_name = ent.getText()
        line = ent.symbol.line
        column = ent.symbol.column
        # findParents() already includes the package components, so prefixing
        # self.package here produced it twice ("org.json" + "." + "org.json").
        scope_longname = ".".join(ent_parents)
        ent_longname = (scope_longname + "." + ent_name) if scope_longname else ent_name
        if len(ent_parents) == 0:
            scope_name = None
        else:
            scope_name = ent_parents[-1]

        self.defines.append(
            {
                "contents": contents,
                "type": type,
                "decl": decl,
                "modifiers": list(modifiers),
                "span": span,
                "parent": ".".join(self.package),
                "scope": scope_name,
                "ent": ent_name,
                "scope_longname": scope_longname,
                "ent_longname": ent_longname,
                "line": line,
                "col": column,
            }
        )

    @staticmethod
    def _type_modifiers(ctx):
        modifiers = _enclosing_modifiers(ctx)
        if _is_generic(ctx):
            modifiers = modifiers + ["generic"]
        return modifiers

    @staticmethod
    def _method_modifiers(ctx):
        # A generic method is `typeParameters methodDeclaration`, so the
        # `<T>` lives on the parent rule, not on the declaration itself.
        modifiers = _enclosing_modifiers(ctx)
        parent = ctx.parentCtx
        if parent is not None and _is_generic(parent):
            modifiers = modifiers + ["generic"]
        return modifiers

    @staticmethod
    def _variable_context(ctx):
        """Whether a variableDeclarator is a field or a local, and its modifiers.

        `variableDeclarator` is shared by `fieldDeclaration` and
        `localVariableDeclaration`; only the grandparent tells them apart, and
        they resolve to completely different kinds (`Java Variable Public
        Member` vs `Java Variable Local`).
        """
        declaration = ctx.parentCtx.parentCtx if ctx.parentCtx is not None else None
        if isinstance(declaration, JavaParserLabeled.LocalVariableDeclarationContext):
            return K.LOCAL, _modifiers_at(declaration)
        return K.FIELD, _enclosing_modifiers(declaration or ctx)

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent=ent,
            ent_parents=ent_parents,
            type="Class",
            contents=source_text(ctx),
            decl=K.CLASS,
            span=_body_span(ctx),
            modifiers=self._type_modifiers(ctx),
        )

    def enterInterfaceDeclaration(
        self, ctx: JavaParserLabeled.InterfaceDeclarationContext
    ):
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent=ent,
            ent_parents=ent_parents,
            type="Interface",
            contents=source_text(ctx),
            decl=K.INTERFACE,
            span=_body_span(ctx),
            modifiers=self._type_modifiers(ctx),
        )

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent=ent,
            ent_parents=ent_parents,
            type=ctx.typeTypeOrVoid().getText(),
            contents=source_text(ctx),
            decl=K.METHOD,
            span=_body_span(ctx),
            modifiers=self._method_modifiers(ctx),
        )

    def enterInterfaceMethodDeclaration(
        self, ctx: JavaParserLabeled.InterfaceMethodDeclarationContext
    ):
        """Interface methods do not go through `methodDeclaration`.

        `interfaceMethodDeclaration` is its own rule with its own modifier
        list, so without this callback no interface method was ever defined.
        They are implicitly public, and abstract unless declared `default`.
        """
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        modifiers = ["public"] + _modifiers_at(ctx)
        if "default" not in modifiers and "static" not in modifiers:
            modifiers.append("abstract")
        if ctx.typeParameters() is not None:
            modifiers.append("generic")
        self.add_define_info(
            ent=ent,
            ent_parents=ent_parents,
            type=ctx.typeTypeOrVoid().getText(),
            contents=source_text(ctx),
            decl=K.METHOD,
            span=_body_span(ctx),
            modifiers=modifiers,
        )

    def enterAnnotationTypeDeclaration(
        self, ctx: JavaParserLabeled.AnnotationTypeDeclarationContext
    ):
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent=ent,
            ent_parents=ent_parents,
            type="Annotation",
            contents=source_text(ctx),
            decl=K.ANNOTATION,
            span=_body_span(ctx),
            modifiers=self._type_modifiers(ctx),
        )

    def enterConstructorDeclaration(
        self, ctx: JavaParserLabeled.ConstructorDeclarationContext
    ):
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent=ent,
            ent_parents=ent_parents,
            type="Constructor",
            contents=source_text(ctx),
            decl=K.CONSTRUCTOR,
            span=_body_span(ctx),
            modifiers=_enclosing_modifiers(ctx),
        )

    def enterVariableDeclarator(self, ctx: JavaParserLabeled.VariableDeclaratorContext):
        ent = ctx.variableDeclaratorId().IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)

        decl, modifiers = self._variable_context(ctx)
        self.add_define_info(
            ent=ent,
            ent_parents=ent_parents,
            type=ctx.parentCtx.parentCtx.typeType().getText(),
            contents=source_text(ctx),
            decl=decl,
            modifiers=modifiers,
        )

    def enterEnumConstant(self, ctx: JavaParserLabeled.EnumConstantContext):
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent=ent,
            ent_parents=ent_parents,
            type="EnumConst",
            contents=source_text(ctx),
            decl=K.ENUM_CONSTANT,
        )

    def enterEnumDeclaration(self, ctx: JavaParserLabeled.EnumDeclarationContext):
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent, ent_parents, type="Enum", contents=source_text(ctx),
            decl=K.ENUM, modifiers=self._type_modifiers(ctx), span=_body_span(ctx),
        )
        # values()/valueOf() are compiler-generated statics on every enum.
        for synthetic in ("values", "valueOf"):
            self.add_define_info(
                ent,
                ent_parents + [ent.getText()],
                synthetic,
                type="Enum",
                contents=source_text(ctx),
                decl=K.METHOD,
            span=_body_span(ctx),
                modifiers=["public", "static"],
            )

    def enterFormalParameter(self, ctx: JavaParserLabeled.FormalParameterContext):
        ent = ctx.variableDeclaratorId().IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent, ent_parents, decl=K.PARAMETER, modifiers=_modifiers_at(ctx)
        )

    def enterLambdaParameters0(self, ctx: JavaParserLabeled.LambdaParameters0Context):
        self.lambda_expression_count += 1
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        ent_name = f"(lambda_expr_{self.lambda_expression_count})"
        self.add_define_info(ent, ent_parents, ent_name, decl=K.LAMBDA)
        self.add_define_info(ent, ent_parents + [ent_name], decl=K.PARAMETER)

    def enterLambdaParameters2(self, ctx: JavaParserLabeled.LambdaParameters2Context):
        self.lambda_expression_count += 1
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        ent_name = f"(lambda_expr_{self.lambda_expression_count})"
        identifiers = ctx.IDENTIFIER()
        self.add_define_info(identifiers[0], ent_parents, ent_name, decl=K.LAMBDA)
        for ent in identifiers:
            self.add_define_info(ent, ent_parents + [ent_name], decl=K.PARAMETER)

    def enterEnhancedForControl(self, ctx: JavaParserLabeled.EnhancedForControlContext):
        ent = ctx.variableDeclaratorId().IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent, ent_parents, decl=K.LOCAL, modifiers=_modifiers_at(ctx)
        )

    def enterCatchClause(self, ctx: JavaParserLabeled.CatchClauseContext):
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(ent, ent_parents, decl=K.CATCH_PARAMETER)

    def enterTypeParameter(self, ctx: JavaParserLabeled.TypeParameterContext):
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(ent, ent_parents, decl=K.TYPE_PARAMETER)

    def enterConstantDeclarator(self, ctx: JavaParserLabeled.ConstantDeclaratorContext):
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent=ent,
            ent_parents=ent_parents,
            type="Constant",
            contents=source_text(ctx),
            decl=K.CONSTANT,
        )

    def enterLastFormalParameter(
        self, ctx: JavaParserLabeled.LastFormalParameterContext
    ):
        ent = ctx.variableDeclaratorId().IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent, ent_parents, decl=K.PARAMETER, modifiers=_modifiers_at(ctx)
        )
