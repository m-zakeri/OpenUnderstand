from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.analysis_passes import class_properties
from os.path import basename


class SetAndSetByListener(JavaParserLabeledListener):
    def __init__(self, file_name):
        self.ex_name = ""
        self.in_expression_21 = False
        self.has_primary_3 = False
        self.in_variable_initializer = False
        self.initializer_identifier_number = 0
        self.number_of_primary_4 = 0
        self.file_name = basename(file_name)
        self.package_name = ""
        self.setBy = []
        self.entered_expression = False
        self.call_function = False
        self.create_object = False
        self.method_name = ""
        self.class_name = ""
        self.for_loop_counter = 0
        self.stream = ""
        self.ent_type = None
        self.ent_value = None
        self.ent_name = None
        self.ss = ""

    def add_set_by_entry(
        self, set_short_name, set_long_name, name_of_file, line, column, ctx
    ):
        if self.call_function:
            set_value = self.method_name
        elif self.create_object:
            set_value = self.class_name
        else:
            if (
                ("this" in ctx.children[0].getText())
                or (ctx.children[2].getChildCount() <= 1)
            ) and (ctx.getRuleIndex() == 83):
                set_value = None
            else:
                set_value = "String"

        sss = self.ss + "." + self.ex_name
        # The long names above are assembled by walking to a parent by rule
        # index and taking children[1]. In the plain `x = ...` branch that
        # parent is the assignment expression itself, so children[1] is the
        # `=` token: every one of those 150 references on the JSON benchmark
        # was scoped to `org.json.CDL.=`. findParents() answers the question
        # the index-chasing was approximating -- which scopes enclose this
        # node -- and it is right for nested classes and methods alike.
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(parents)
        # `this.x` names a field of the enclosing class, never a local. The
        # constructors here take a parameter of the same name as the field they
        # assign -- `JSONPointer(List<String> refTokens) { this.refTokens = ...
        # }` -- so resolving from the constructor outwards found the parameter
        # first and produced org.json.JSONPointer.JSONPointer.refTokens.
        # Resolution for a `this.` target starts one scope out; the reference's
        # own scope stays the constructor, which is what Understand reports.
        target = ctx.children[0].getText() if ctx.getChildCount() else ""
        resolve_scope = (
            ".".join(parents[:-1])
            if target.startswith("this.") and len(parents) > 1
            else scope_longname
        )
        self.setBy.append(
            (
                set_short_name,
                set_long_name,
                name_of_file,
                set_value,
                line,
                column,
                self.package_name,
                self.ex_name,
                self.stream,
                self.ent_type,
                sss,
                scope_longname,
                resolve_scope,
            )
        )

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.ex_name = ctx.children[1].getText()
        long_name = self.file_name.replace(".java", "") + "." + self.ex_name
        line = ctx.children[0].symbol.line
        col = ctx.children[0].symbol.column

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.ex_name = ctx.children[1].getText()

    def enterExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        self.entered_expression = True
        self.create_object = False
        self.call_function = False

    def exitExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        try:
            name_of_file = self.file_name
            set_long_name = (
                self.package_name + "." + self.ex_name + "." + ctx.children[0].getText()
            )
            set_short_name = ctx.children[0].getText()
            if int(ctx.children[0].getChildCount()) > 1:
                node = ctx
                if (
                    ctx.children[1].getText()
                    and ctx.children[0].children[1].getText() == "="
                ):
                    line = ctx.children[0].children[2].symbol.line
                    column = ctx.children[0].children[2].symbol.column
                    self.add_set_by_entry(
                        set_short_name, set_long_name, name_of_file, line, column, ctx
                    )
                else:
                    if ctx.children[1].getText() == "=":
                        # `a[i] = x` and `obj.field = x` set only part of
                        # what a / obj refer to. Understand reports those as
                        # Java Set Deref Partial against the dereferenced
                        # variable and emits no plain Java Set at all, so they
                        # belong to setpartial_setpartialby. Emitting them here
                        # too was 580 of this pass's 627 false positives on the
                        # TheAlgorithms benchmark.
                        target = ctx.children[0]
                        dereferenced = target.children[1].getText() == "[" or (
                            target.children[1].getText() == "."
                            and target.children[0].getText() != "this"
                        )
                        if dereferenced:
                            pass
                        else:
                            node = self.get_parent_node(ctx, (7, 25, 20))
                            self.ss = node.children[0].getText()
                            if node.getRuleIndex() == 25:
                                set_short_name = (
                                    node.children[0].getText()
                                    + "."
                                    + ctx.children[0].children[2].getText()
                                )
                                self.stream = node.parentCtx.parentCtx.getText()
                                self.scope_kind = (
                                    node.parentCtx.parentCtx.children[0].getText()
                                    + "."
                                    + node.children[0].getText()
                                )
                            set_long_name = (
                                self.package_name
                                + "."
                                + node.children[0].getText()
                                + "."
                                + ctx.children[0].children[2].getText()
                            )
                            # `this.myArrayList = ...`: the reference belongs to
                            # the field, so it sits on the field's identifier.
                            # Drilling to the leftmost token landed on `this`,
                            # putting all 64 of these exactly len("this.") = 5
                            # columns to the left of where Understand has them.
                            field = ctx.children[0].children[2]
                            line = field.symbol.line
                            column = field.symbol.column
                            self.add_set_by_entry(
                                set_short_name,
                                set_long_name,
                                name_of_file,
                                line,
                                column,
                                ctx,
                            )

            else:
                if ctx.children[1].getText() == "=":
                    node = ctx
                    node1 = self.get_parent_node(node, (7,))
                    line = ctx.children[0].children[0].children[0].symbol.line
                    if node.getRuleIndex() == 25:
                        self.stream = node.parentCtx.parentCtx.getText()
                        set_long_name = (
                            self.package_name
                            + "."
                            + node.children[0].getText()
                            + "."
                            + node1.children[1].getText()
                            + "."
                            + ctx.children[0].getText()
                        )
                    else:
                        set_long_name = (
                            self.package_name
                            + "."
                            + node1.children[1].getText()
                            + "."
                            + node.children[1].getText()
                            + "."
                            + ctx.children[0].getText()
                        )
                    column = ctx.children[0].children[0].children[0].symbol.column
                    self.add_set_by_entry(
                        set_short_name, set_long_name, name_of_file, line, column, ctx
                    )

        except Exception as e:
            print(f"Error occurred: {e}")

        self.entered_expression = False
        self.call_function = False
        self.create_object = False
        self.method_name = ""
        self.class_name = ""

    # A variable declared with an initializer -- `char c = ' '` -- is a
    # Java Set Init, not a Java Set. Understand reports Define/Definein and
    # Set Init/Setby Init there and no plain Set, and setinit_setinitby
    # already emits exactly those 310 references on the JSON benchmark. The
    # exitVariableDeclarator handler that used to live here duplicated all of
    # them as Java Set, which was 310 of this pass's 537 rows.

    def exitPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        try:
            self.package_name = ctx.children[1].getText()

        except Exception as e:
            print(f"Error occurred: {e}")

    def exitMethodCall0(self, ctx: JavaParserLabeled.MethodCall0Context):
        self.ent_value = ctx.children[0]

    def get_parent_node(self, node, indices):
        while node.getRuleIndex() not in indices:
            node = node.parentCtx
        return node
