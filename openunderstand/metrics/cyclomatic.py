from openunderstand.ounderstand.project import Project
from collections import Counter
from antlr4 import *
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
from openunderstand.metrics.utils import get_method_prefixes
from openunderstand.metrics import context
from openunderstand.gen.javaLabeled.JavaLexer import JavaLexer


def make_enum_scope():
    return [
        {
            "kind": "Java Method Public Member",
            "name": "values",
            "longname": "",
            "cyclomatic": 1,
        },
        {
            "kind": "Java Method Public Member",
            "name": "valueOf",
            "longname": "",
            "cyclomatic": 1,
        },
    ]


def make_method_scope(ctx):
    prefixes = get_method_prefixes(ctx)
    name = ""
    kind = ""
    if type(ctx).__name__ == "MethodDeclarationContext":
        name = ctx.IDENTIFIER().getText()
        if name == "main":
            is_main = True
        else:
            is_main = False
        kind = get_kind_name(prefixes, is_main=is_main)
    elif type(ctx).__name__ == "GenericMethodDeclarationContext":
        name = ctx.children[1].IDENTIFIER().getText()
        kind = get_kind_name(prefixes, is_generic=True)
    elif type(ctx).__name__ == "ConstructorDeclarationContext":
        name = ctx.IDENTIFIER().getText()
        kind = get_kind_name(prefixes, is_constructor=True)
    elif type(ctx).__name__ == "GenericConstructorDeclarationContext":
        name = ctx.children[1].IDENTIFIER().getText()
        kind = get_kind_name(prefixes, is_constructor=True, is_generic=True)
    elif type(ctx).__name__ == "LambdaExpressionContext":
        name = "(lambda_expr)"
        kind = get_kind_name(prefixes, is_lambda=True)

    return {"kind": kind, "name": name, "longname": ""}


def get_kind_name(
    prefixes, is_constructor=False, is_lambda=False, is_generic=False, is_main=False
):
    p_static = ""
    p_final = ""
    p_generic = ""
    p_main = ""

    if "static" in prefixes:
        p_static = "Static"

    if "final" in prefixes:
        p_final = "Final"

    if is_generic:
        p_generic = "Generic"

    if "private" in prefixes:
        p_visibility = "Private"
    elif "public" in prefixes:
        p_visibility = "Public"
    elif "protected" in prefixes:
        p_visibility = "Protected"
    else:
        p_visibility = "Default"

    if is_main:
        p_main = "Main"

    if is_constructor:
        s = f"Java Method Constructor Member {p_visibility}"
        s = " ".join(s.split())
        return s

    elif is_lambda:
        s = f"Java Method Lambda"
        s = " ".join(s.split())
        return s

    else:
        s = f"Java {p_static} {p_final} {p_generic} Method {p_visibility} {p_main} Member"
        s = " ".join(s.split())
        return s


def get_method_ctx(ctx):
    # Traverse bottom up until reaching a method
    current = ctx.parentCtx
    while current is not None:
        type_name = type(current).__name__
        if type_name in [
            "MethodDeclarationContext",
            "GenericMethodDeclarationContext",
            "ConstructorDeclarationContext",
            "GenericConstructorDeclarationContext",
            # A lambda is a scope of its own: a decision inside one counted
            # for the method around it (ClientBodyPublisher 3 against 2).
            "LambdaExpressionContext",
            "InterfaceMethodDeclarationContext",
        ]:
            return current
        current = current.parentCtx
    return None


def in_switch_expression(label):
    """Whether a case label belongs to a switch expression, not a statement."""
    node = label.parentCtx
    while node is not None:
        if isinstance(node, JavaParserLabeled.SwitchExpressionContext):
            return True
        if isinstance(node, (JavaParserLabeled.Statement8Context,
                             JavaParserLabeled.Statement18Context)):
            return False
        node = node.parentCtx
    return False


class CyclomaticListener(JavaParserLabeledListener):
    def __init__(self):
        # repository of ctx
        self.repository = []
        self.project_cyclomatic = 0

    def update_repository(self, ctx, kind=None):
        if kind:
            scope_ctx = ctx

        else:
            scope_ctx = get_method_ctx(ctx)
            if scope_ctx is None:
                return

            parent_scope_ctx = scope_ctx.parentCtx
            if type(parent_scope_ctx).__name__ in [
                "GenericMethodDeclarationContext",
                "GenericConstructorDeclarationContext",
            ]:
                scope_ctx = parent_scope_ctx

        prefixes = get_method_prefixes(scope_ctx)
        if "abstract" not in prefixes:
            self.repository.append(scope_ctx)
            self.project_cyclomatic += 1

    def enterGenericMethodDeclaration(
        self, ctx: JavaParserLabeled.GenericMethodDeclarationContext
    ):
        self.update_repository(ctx, kind="GenericMethodDeclarationContext")

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        # Parent can be genericMethodDeclaration
        if type(ctx.parentCtx).__name__ == "GenericMethodDeclarationContext":
            return
        self.update_repository(ctx, kind="MethodDeclarationContext")

    def enterGenericConstructorDeclaration(
        self, ctx: JavaParserLabeled.GenericConstructorDeclarationContext
    ):
        self.update_repository(ctx, kind="GenericConstructorDeclarationContext")

    def enterConstructorDeclaration(
        self, ctx: JavaParserLabeled.ConstructorDeclarationContext
    ):
        # Parent can be genericConstructorDeclaration
        if type(ctx.parentCtx).__name__ == "GenericConstructorDeclarationContext":
            return
        self.update_repository(ctx, kind="ConstructorDeclarationContext")

    def enterEnumDeclaration(self, ctx: JavaParserLabeled.EnumDeclarationContext):
        # valueOf and values for Enums
        self.repository.append(ctx)
        self.project_cyclomatic += 2

    def enterInterfaceMethodDeclaration(
        self, ctx: JavaParserLabeled.InterfaceMethodDeclarationContext
    ):
        """A `default` or `static` interface method with a body is a scope."""
        body = ctx.methodBody()
        if body is not None and body.block() is not None:
            self.repository.append(ctx)
            self.project_cyclomatic += 1

    def enterLambdaExpression(self, ctx: JavaParserLabeled.LambdaExpressionContext):
        self.repository.append(ctx)
        self.project_cyclomatic += 1

    # while
    def enterStatement4(self, ctx: JavaParserLabeled.Statement4Context):
        self.update_repository(ctx)

    # ternary
    def enterExpression20(self, ctx: JavaParserLabeled.Expression20Context):
        self.update_repository(ctx)

    # if
    def enterStatement2(self, ctx: JavaParserLabeled.Statement2Context):
        self.update_repository(ctx)

    # for
    def enterStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        self.update_repository(ctx)

    # do
    def enterStatement5(self, ctx: JavaParserLabeled.Statement5Context):
        self.update_repository(ctx)

    # catch
    def enterCatchClause(self, ctx: JavaParserLabeled.CatchClauseContext):
        self.update_repository(ctx)

    # case: one per label, however many constants it lists, and only in a
    # switch *statement*. Understand counts nothing for a switch expression,
    # colon or arrow form alike, and counts `case X ->` in a statement exactly
    # as it counts `case X:`.
    def enterSwitchLabel(self, ctx: JavaParserLabeled.SwitchLabelContext):
        if ctx.CASE() is not None and not in_switch_expression(ctx):
            self.update_repository(ctx)

    def enterSwitchRuleLabel(self, ctx: JavaParserLabeled.SwitchRuleLabelContext):
        if ctx.CASE() is not None and not in_switch_expression(ctx):
            self.update_repository(ctx)


def cyclomatic(ent_model):
    """Cyclomatic complexity of one entity.

    Understand reports this per method: decision points plus one.

    Counted from the entity's *own* source, not by finding its name in the
    file. Overloads share a simple name, so the name search answered every one
    of JSONArray's twelve constructors with the first one's number -- right for
    each name the parity harness scores, and 197 against Understand's 227 the
    moment a class sums them.
    """
    if context.is_file(ent_model):
        listener = context.walk_file(ent_model, CyclomaticListener())
        return listener.project_cyclomatic

    return _own_count(context.walk_entity(ent_model, CyclomaticListener()))


def _own_count(listener):
    """The count of the entity's own declaration -- the first one walked that
    is not the parse wrapper. Taking the *largest* count let an anonymous
    class's method speak for the method holding it: KSubset.iterator is 1 to
    Understand and was 4. A method with no branches still has complexity 1."""
    counts = Counter(listener.repository)
    for ctx in dict.fromkeys(listener.repository):
        if context.declared_name(ctx) != context._WRAPPER:
            return counts[ctx]
    return max(counts.values(), default=1)


class CyclomaticModifiedListener(CyclomaticListener):
    """Cyclomatic, with a whole `switch` counted as one decision rather than
    one per case. The separate listener this replaces crashed on any method
    that misparsed, never counted inside a constructor, and counted a `try`
    once instead of once per `catch` -- SalaryCalculator's three *Modified
    metrics went 0.75-0.87 to 1.000 on this."""

    def enterSwitchLabel(self, ctx):
        pass

    def enterSwitchRuleLabel(self, ctx):
        pass

    def enterStatement8(self, ctx):
        self.update_repository(ctx)

    def enterStatement18(self, ctx):
        self.update_repository(ctx)


def cyclomatic_modified(ent_model=None):
    """CyclomaticModified: as Cyclomatic, a switch counting once."""
    if ent_model is None:
        return None
    if context.is_file(ent_model):
        return context.walk_file(ent_model, CyclomaticModifiedListener()).project_cyclomatic
    return _own_count(context.walk_entity(ent_model, CyclomaticModifiedListener()))
