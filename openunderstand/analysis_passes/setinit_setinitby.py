# Group 13
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
import openunderstand.analysis_passes.class_properties as class_properties


class SetInitAndSetByInitListener(JavaParserLabeledListener):
    def __init__(self, file_name):
        self.ex_name = ""
        self.in_expreession_21 = False
        self.has_primary_3 = False
        self.in_variable_initializer = False
        self.initializer_identifier_number = 0
        self.number_of_primary_4 = 0
        self.file_name = file_name
        self.package_name = ""
        self.set_init_by = []
        self.enterd_initialization = False
        self.call_function = False
        self.create_object = False
        self.method_name = ""
        self.class_name = ""
        self.ent_type = None
        self.stream = ""
        self.ss = ""

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        # IDENTIFIER, not children[1]: a record's or a sealed class's first
        # child is a sub-rule, not the `class` keyword.
        self.ex_name = ctx.IDENTIFIER().getText()

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):

        name_of_file = self.file_name.split("\\")[
            self.file_name.split("\\").count(0) - 1
        ]
        self.ex_name = ctx.children[1].getText()

    def enterVariableInitializer1(
        self, ctx: JavaParserLabeled.VariableInitializer1Context
    ):
        self.enterd_initialization = True
        self.create_object = False
        self.call_function = False

    def exitVariableInitializer1(
        self, ctx: JavaParserLabeled.VariableInitializer1Context
    ):
        """One `Java Set Init` per initialised declaration.

        Everything the writer reads comes from the declarator and from
        findParents(). The long names this used to build by climbing to a
        method or class rule *by index* are kept only as best-effort extras:
        inside an interface -- a default method, a constant, an anonymous class
        in either -- the climb ran off the root, the bare except swallowed it,
        and 66 of jenetics' initialisers had no Set Init at all.
        """
        declarator = ctx.parentCtx
        identifier = declarator.children[0] if declarator.children else None
        if identifier is None:
            self._reset()
            return
        # variableDeclarator: a variableDeclaratorId rule; constantDeclarator
        # (an interface constant): the IDENTIFIER token itself.
        token = getattr(identifier, "symbol", None)
        if token is None:
            first = identifier.children[0] if identifier.children else None
            token = getattr(first, "symbol", None)
        if token is None:
            self._reset()
            return
        declared = token.text
        name_of_file = self.file_name.split("\\")[
            self.file_name.split("\\").count(0) - 1
        ]
        short_name = long_name = declared
        try:
            node = ctx
            while node.getRuleIndex() not in (20, 7, 25):
                node = node.parentCtx
            self.stream = node.parentCtx.parentCtx.getText()
            self.ss = node.children[0].getText()
        except AttributeError:
            self.stream = self.ss = ""
        if self.call_function:
            value = self.method_name
        elif self.create_object:
            value = self.class_name
        else:
            value = ctx.getText()
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        enclosing = ".".join(parents)
        self.set_init_by.append(
            (
                short_name,
                long_name,
                name_of_file,
                value,
                declared,
                token.line,
                token.column,
                self.ex_name,
                self.ent_type,
                self.stream,
                self.ss + "." + self.ex_name,
                enclosing,
                f"{enclosing}.{declared}",
            )
        )
        self._reset()

    def _reset(self):
        self.enterd_initialization = False
        self.call_function = False
        self.create_object = False
        self.method_name = ""
        self.class_name = ""

    def enterPattern(self, ctx: JavaParserLabeled.PatternContext):
        """`x instanceof T name` and `case T name`: the match sets `name`.

        Understand writes a Set Init at the name although nothing is written
        after an `=`, so this does not go through exitVariableInitializer1.
        """
        declaration = ctx.localVariableDeclaration()
        if declaration is None:
            return  # a record pattern; its components are patterns themselves
        enclosing = ".".join(
            class_properties.ClassPropertiesListener.findParents(ctx)
        )
        type_text = declaration.typeType().getText()
        for declarator in declaration.variableDeclarators().variableDeclarator():
            token = declarator.variableDeclaratorId().IDENTIFIER().symbol
            name = token.text
            self.set_init_by.append(
                (
                    name,
                    f"{enclosing}.{name}",
                    self.file_name,
                    "",
                    type_text,
                    token.line,
                    token.column,
                    self.ex_name,
                    type_text,
                    "",
                    "",
                    enclosing,
                    f"{enclosing}.{name}",
                )
            )

    def exitPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.package_name = ctx.children[1].getText()
