""" """

import os
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties
from openunderstand.utils import kind_names as K

# Rules that carry the modifier list for a declaration nested inside them.
# A member's modifiers hang off classBodyDeclaration/interfaceBodyDeclaration,
# two levels above the declaration itself, so they have to be walked to.
_MODIFIER_ACCESSORS = (
    "modifier",
    "classOrInterfaceModifier",
    "variableModifier",
    "interfaceMethodModifier",
)


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
    "TypeDeclarationContext",
    "ClassBodyDeclaration",
    "MemberDeclaration",
    "InterfaceBodyDeclarationContext",
    "InterfaceMemberDeclaration",
    "LocalTypeDeclarationContext",
    "GenericMethodDeclarationContext",
    "GenericConstructorDeclarationContext",
    "GenericInterfaceMethodDeclarationContext",
)


def _declaration_start(ctx):
    """First token of a declaration, including its modifiers.

    `ctx.start` on a methodDeclaration is the return type -- the modifiers sit
    on the wrapper rule -- so anything measured from it starts too late.
    """
    start = ctx.start
    current = ctx.parentCtx
    # Climb only through the rules that wrap a declaration together with its
    # modifiers. Climbing blindly reaches compilationUnit.
    while current is not None and type(current).__name__.startswith(_SPAN_WRAPPERS):
        if current.start is not None and current.start.tokenIndex < start.tokenIndex:
            start = current.start
        current = current.parentCtx
    return start


def _body_span(ctx):
    """(begin, end) positions of a declaration.

    Understand reports a Begin reference where the declaration starts -- at its
    first modifier, not at its name -- and an End reference at the matching
    closing brace. A declaration with no body (an abstract or interface method)
    ends at its `;` and gets both too: all 14 of JSON's abstract methods carry
    a Begin and an End, which this used to deny them.
    """
    stop = ctx.stop
    if stop is None or stop.text not in ("}", ";"):
        return None
    start = _declaration_start(ctx)
    return (start.line, start.column), (stop.line, stop.column)


def source_text(ctx):
    """The declaration's original source, whitespace and all.

    `ctx.getText()` concatenates token text, so a method comes back as
    `publicvoidmain(String[]args){...}` -- which is not Java and cannot be
    reparsed. Every metric that works by reparsing `ent.contents()`
    (Cyclomatic, CountStmt, CountLineCode, MaxNesting, ...) was therefore
    returning 0. The input stream still holds the real characters.
    """
    start, stop = _declaration_start(ctx), ctx.stop
    if start is None or stop is None:
        return ctx.getText()
    stream = start.getInputStream()
    if stream is None:
        return ctx.getText()
    try:
        return stream.getText(
            _doc_comment_start(stream, start.start), _line_end(stream, stop.stop)
        )
    except Exception:
        return ctx.getText()


def _line_end(stream, stop):
    """Extend to include the newline terminating the declaration's last line.

    Understand counts line *terminators*: a class whose closing brace is the
    last character of a file with no trailing newline reports one line fewer
    than its brace-to-brace span. Carrying the terminator in the entity's own
    text makes that fall out of a plain count instead of needing a special
    case -- every entity in calculator_app matches once it does.
    """
    try:
        text = stream.strdata
    except AttributeError:
        return stop
    i = stop + 1
    while i < len(text) and text[i] == "\r":
        i += 1
    if i < len(text) and text[i] == "\n":
        return i
    return stop


def _doc_comment_start(stream, begin):
    """Extend a declaration's start back over its Javadoc block.

    Understand counts a `/** ... */` block above a declaration as part of it,
    and a `//` comment above it as not. Both halves are measured: `Main.main`
    is preceded by a `//` line and Understand reports CountLine 13 -- its
    declaration through its closing brace -- while org.json's members are
    preceded by Javadoc and Understand's line counts include it.

    Only whitespace may separate the block from the declaration, so one
    documenting something else is not swallowed.
    """
    try:
        text = stream.strdata
    except AttributeError:
        return begin

    i = begin - 1
    while i >= 0 and text[i] in " \t\r\n":
        i -= 1
    if i < 1 or text[i - 1 : i + 1] != "*/":
        return begin

    opening = text.rfind("/*", 0, i)
    # `/*` alone is an ordinary block comment; only `/**` is documentation.
    if opening == -1 or not text.startswith("/**", opening):
        return begin
    return opening


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
        self,
        ent,
        ent_parents,
        ent_name=None,
        type=None,
        contents=None,
        decl=None,
        modifiers=(),
        span=None,
    ):
        if ent_name is None:
            ent_name = ent.getText()
        # `ent` is an IDENTIFIER node for a named declaration and a bare Token
        # for an anonymous class, which has no identifier to hang a name on.
        symbol = getattr(ent, "symbol", ent)
        line = symbol.line
        column = symbol.column
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
        # `sealed`/`non-sealed` and any modifier written after it are inside
        # the declaration itself (grammar: sealedModifier), not the wrapper.
        sealed = getattr(ctx, "sealedModifier", None)
        sealed = sealed() if callable(sealed) else None
        if sealed is not None:
            modifiers = modifiers + [sealed.getText()] + [
                m.getText() for m in ctx.classOrInterfaceModifier()
            ]
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

    def enterClassCreatorRest(self, ctx: JavaParserLabeled.ClassCreatorRestContext):
        """`new Iterable<Integer>() { ... }` declares a class of its own.

        Nothing declared one before, so the anonymous class's members hung off
        the enclosing method and the class itself was simply absent -- which is
        the whole of CountDeclClass's gap: org.json reported 28 against
        Understand's 30, the two missing being the pair in
        `XML.codePointIterator`.

        Understand names it `(Anon_N)`, numbered over the *file* in source
        order, and positions it on the body's opening brace -- Define, Definein
        and Begin all sit at 79:40 for the first one, which is the `{`.

        The name comes from class_properties, which is also what puts the
        segment into every scope chain running through the body: one numbering,
        so an entity and its declaring scope cannot disagree about it.
        """
        name = class_properties.anonymous_name(ctx)
        if name is None:
            return  # `new Foo(...)` with no body creates nothing
        body = ctx.classBody()
        self.add_define_info(
            ent=body.start,
            ent_parents=class_properties.ClassPropertiesListener.findParents(ctx),
            ent_name=name,
            type="Class",
            contents=source_text(body),
            decl=K.ANONYMOUS_CLASS,
            span=_body_span(body),
        )

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        ent = ctx.IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        is_record = ctx.recordKeyword() is not None
        modifiers = self._type_modifiers(ctx)
        if is_record and not isinstance(ctx.parentCtx, JavaParserLabeled.TypeDeclarationContext):
            modifiers = modifiers + ["nested"]
        self.add_define_info(
            ent=ent,
            ent_parents=ent_parents,
            type="Class",
            contents=source_text(ctx),
            decl=K.RECORD if is_record else K.CLASS,
            span=_body_span(ctx),
            modifiers=modifiers,
        )
        if is_record:
            self._record_components(ctx, ent_parents)

    def _record_components(self, ctx, ent_parents):
        """What `record R(T c)` declares beyond R itself.

        Understand's long names, read off its database: the field is R.c, the
        implicit canonical constructor is R -- the *record's* long name -- and
        its parameter is R.c again. Field and parameter stay two rows because
        a parameter and a member never share an identity (models.py).

        * the field: Define R -> R.c at the component's name, a private member;
        * an implicit constructor: Define Implicit R -> R at the record's name,
          and Define Implicit R -> R.c for each parameter, at the same place;
        * a compact constructor `R { }` is declared by enterConstructorDeclaration
          as R.R; its parameters are still R.c, Define Implicit from R.R, at
          the record's name.
        """
        record_name = ctx.IDENTIFIER()
        record_longname = ".".join(ent_parents + [record_name.getText()])
        components = ctx.recordHeader().recordComponent()
        for component in components:
            self.add_define_info(
                ent=component.IDENTIFIER(),
                ent_parents=ent_parents + [record_name.getText()],
                type=component.typeType().getText(),
                contents=source_text(component),
                decl=K.FIELD,
                modifiers=["private"],
            )
        how = class_properties.record_constructor(ctx)
        if how == "explicit":
            return  # an ordinary constructor, declared by its own handler
        implicit = how == "implicit"
        if implicit:
            self._append_record_part(
                record_name, record_name.getText(), record_longname,
                ent_parents[-1] if ent_parents else None,
                record_longname, K.CONSTRUCTOR, ["public"], "Constructor",
                implicit=True, scope_family="type",
            )
        constructor_longname = (
            record_longname if implicit else f"{record_longname}.{record_name.getText()}"
        )
        for component in components:
            name = component.IDENTIFIER().getText()
            self._append_record_part(
                record_name, name, f"{record_longname}.{name}",
                record_name.getText(), constructor_longname, K.PARAMETER, [],
                component.typeType().getText(),
                implicit=True, scope_family="method",
            )

    def _append_record_part(
        self, at, name, longname, scope, scope_longname, decl, modifiers,
        type_text, implicit, scope_family,
    ):
        symbol = getattr(at, "symbol", at)
        self.defines.append(
            {
                "contents": "",
                "type": type_text,
                "decl": decl,
                "modifiers": list(modifiers),
                "span": None,
                "parent": ".".join(self.package),
                "scope": scope,
                "ent": name,
                "scope_longname": scope_longname,
                "ent_longname": longname,
                "line": symbol.line,
                "col": symbol.column,
                "implicit": implicit,
                "scope_family": scope_family,
            }
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

    def enterAnnotationMethodRest(
        self, ctx: JavaParserLabeled.AnnotationMethodRestContext
    ):
        """`String value();` inside an `@interface` declares a method.

        It is `annotationMethodRest`, not a methodDeclaration, so nothing
        created it and JSONPropertyName reported CountDeclMethod 0 against
        Understand's 1 -- and CountDeclMethodAll with it, for every annotation
        in the project.
        """
        ent = ctx.IDENTIFIER()
        if ent is None:
            return
        element = ctx.parentCtx
        while element is not None and not type(element).__name__.startswith(
            "AnnotationTypeElementRest"
        ):
            element = element.parentCtx
        declared = element.typeType() if element is not None else None
        # Begin at the element's first token (its modifiers included), End at
        # its `;`, which belongs to the wrapping element rule -- as for any
        # other body-less method.
        span = None
        if element is not None and element.stop is not None and element.stop.text == ";":
            first = element.parentCtx.start if element.parentCtx is not None else element.start
            span = ((first.line, first.column), (element.stop.line, element.stop.column))
        self.add_define_info(
            ent=ent,
            ent_parents=class_properties.ClassPropertiesListener.findParents(ctx),
            type=declared.getText() if declared is not None else "",
            contents=source_text(ctx),
            decl=K.METHOD,
            # An annotation member is implicitly public and abstract.
            modifiers=["public", "abstract"],
            span=span,
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
            ent,
            ent_parents,
            type="Enum",
            contents=source_text(ctx),
            decl=K.ENUM,
            modifiers=self._type_modifiers(ctx),
            span=_body_span(ctx),
        )
        # values()/valueOf() are compiler-generated statics on every enum.
        # No span: they have no source, and Understand writes no Begin or End
        # for them -- these carried the enum's own, 8 false rows on JSON.
        for synthetic in ("values", "valueOf"):
            self.add_define_info(
                ent,
                ent_parents + [ent.getText()],
                synthetic,
                type="Enum",
                contents=source_text(ctx),
                decl=K.METHOD,
                span=None,
                modifiers=["public", "static"],
            )

    def enterFormalParameter(self, ctx: JavaParserLabeled.FormalParameterContext):
        ent = ctx.variableDeclaratorId().IDENTIFIER()
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        self.add_define_info(
            ent, ent_parents, decl=K.PARAMETER, modifiers=_modifiers_at(ctx)
        )

    @staticmethod
    def _lambda_scope(ctx):
        """(scope chain above the lambda, its name), or (None, None).

        `ctx` is the parameter list, which is *inside* the lambda, so
        `findParents(ctx)` already ends with the lambda's own segment -- asking
        from here and then appending the name again produced
        `go.(lambda_expr_1).(lambda_expr_1)`, an entity parented to itself.
        Ask from the lambda expression instead, whose chain stops above it.

        The name comes from `class_properties` rather than from a counter of
        this listener's own. Two numberings over the same file cannot be
        relied on to agree, and the one that decides an entity's *scope* is
        that one.
        """
        node = ctx
        while node is not None and not isinstance(
            node, JavaParserLabeled.LambdaExpressionContext
        ):
            node = node.parentCtx
        if node is None:
            return None, None
        return (
            class_properties.ClassPropertiesListener.findParents(node),
            class_properties.lambda_name(node),
        )

    def enterLambdaParameters0(self, ctx: JavaParserLabeled.LambdaParameters0Context):
        ent_parents, ent_name = self._lambda_scope(ctx)
        if ent_name is None:
            return
        ent = ctx.IDENTIFIER()
        self.add_define_info(ent, ent_parents, ent_name, decl=K.LAMBDA)
        self.add_define_info(ent, ent_parents + [ent_name], decl=K.PARAMETER)

    def enterLambdaParameters2(self, ctx: JavaParserLabeled.LambdaParameters2Context):
        ent_parents, ent_name = self._lambda_scope(ctx)
        if ent_name is None:
            return
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
