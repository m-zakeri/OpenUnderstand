from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
from openunderstand.analysis_passes import class_properties
from os.path import basename


def symbol_table_member_type(owner, field):
    """Declared type of `owner.field`, project or JDK.

    Imported inside the call: this module is loaded while symbol_table is
    still being built, and a module-level import would close the cycle.
    """
    from openunderstand.ounderstand import symbol_table

    return symbol_table.member_type(owner, field)


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
        #: Declared type (simple name) of each field of the enclosing class.
        self.field_types = {}
        #: Same for the parameters and locals of the method being walked.
        self.local_types = {}

    # ---- declared types, for resolving `receiver.field = ...` -------------
    #
    # Understand reports a Java Set against every member of a dereferenced
    # assignment target, resolved to the class that declares it: `x.p = temp`
    # sets DataStructures.Trees.RedBlackBST.Node.p, because x is declared
    # `Node x`. Naming that field needs the receiver's declared type, which
    # the database does not carry -- all 1206 parameters and 2552 of 4634
    # variables on TheAlgorithms have a null _type -- so the pass records it
    # while walking. 204 of the 290 Set references missing there are the first
    # member of such a chain.

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.ex_name = ctx.children[1].getText()
        # Parameters and locals belong to one method; fields outlive them.
        self.local_types = {}

    def enterConstructorDeclaration(
        self, ctx: JavaParserLabeled.ConstructorDeclarationContext
    ):
        self.local_types = {}

    def enterFormalParameter(self, ctx: JavaParserLabeled.FormalParameterContext):
        self._record_type(
            self.local_types, ctx.typeType(), [ctx.variableDeclaratorId()]
        )

    def enterLocalVariableDeclaration(
        self, ctx: JavaParserLabeled.LocalVariableDeclarationContext
    ):
        self._record_type(
            self.local_types,
            ctx.typeType(),
            ctx.variableDeclarators().variableDeclarator(),
        )

    def enterFieldDeclaration(self, ctx: JavaParserLabeled.FieldDeclarationContext):
        self._record_type(
            self.field_types,
            ctx.typeType(),
            ctx.variableDeclarators().variableDeclarator(),
        )

    @staticmethod
    def _record_type(target, type_ctx, declarators):
        if type_ctx is None:
            return
        # Generic arguments and array brackets are not part of the type's name:
        # a field declared `Node<Element> firstElement` has type Node.
        name = type_ctx.getText().split("<")[0].split("[")[0]
        for declarator in declarators or []:
            # `variableDeclarator: variableDeclaratorId ('=' variableInitializer)?`
            # -- getText() on an initialised one is "temp=null", so the name has
            # to come from the id. Keying on the whole text recorded a type for
            # "temp=null" and left `temp` itself untyped, which is why only the
            # uninitialised declarations resolved.
            declarator_id = getattr(declarator, "variableDeclaratorId", None)
            if callable(declarator_id):
                declarator = declarator_id() or declarator
            identifier = declarator.getText().split("[")[0]
            if identifier:
                target[identifier] = name

    def add_member_set(self, target, ctx, name_of_file):
        """Record `receiver.member = ...` as a Set against the member's field.

        Only the first member of the chain: naming the second would need the
        declared type of the first, which is a field of another class and not
        recorded anywhere this pass can see. On TheAlgorithms that first member
        is 204 of the 290 missing Set references, the rest being members two or
        more levels deep.
        """
        if target.children[1].getText() != ".":
            return  # `a[i] = x`: no member is named
        receiver = target.children[0].getText()
        if "." in receiver and all(
            part.split("[")[0].isidentifier() for part in receiver.split(".")
        ):
            # `head.a.b = v` sets a field of b's type. Each hop is a field whose
            # type the project index knows, so the chain resolves however deep
            # it goes -- DoublyLinkedList sets `position.next.previous` and this
            # pass stopped at the first member.
            parents = class_properties.ClassPropertiesListener.findParents(ctx)
            owner = self.owner_of_member(
                receiver.split(".")[0].split("[")[0], ".".join(parents)
            )
            for hop in receiver.split(".")[1:]:
                if owner is None:
                    break
                owner = symbol_table_member_type(owner, hop.split("[")[0])
            member = target.children[2]
            if owner and hasattr(member, "symbol"):
                self.add_set_by_entry(
                    member.getText(),
                    owner + "." + member.getText(),
                    name_of_file,
                    member.symbol.line,
                    member.symbol.column,
                    ctx,
                    resolve_override=owner,
                )
            return
        if not receiver.isidentifier():
            # `cursorSpace[os].next = x` sets a field of the *element*. The
            # head is still a name this pass can resolve; anything else -- a
            # chained call, a cast -- is not.
            head = receiver.split("[")[0]
            if "[" not in receiver or not head.isidentifier():
                return
            receiver = head
        member = target.children[2]
        if not hasattr(member, "symbol"):
            return  # `a.foo() = ...` cannot occur, but be safe
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        owner = self.owner_of_member(receiver, ".".join(parents))
        if owner is None:
            return  # receiver's type is unknown: no guess
        self.add_set_by_entry(
            member.getText(),
            owner + "." + member.getText(),
            name_of_file,
            member.symbol.line,
            member.symbol.column,
            ctx,
            resolve_override=owner,
        )

    def declared_type(self, name):
        """Simple name of `name`'s declared type: a local first, then a field."""
        return self.local_types.get(name) or self.field_types.get(name)

    def owner_of_member(self, receiver, scope_longname):
        """Long name of the class declaring the member accessed on `receiver`."""
        from openunderstand.ounderstand import symbol_table

        type_name = self.declared_type(receiver)
        if not type_name:
            # `ColumnarTranspositionCipher.keyword = x` -- the receiver is a
            # *type*, so the field is a static one on that type. Understand
            # reports these as an ordinary Java Set and this pass produced
            # none of them.
            return symbol_table.resolve_type(receiver, scope_longname)
        # An array's element type is what carries the member.
        return symbol_table.resolve_type(type_name.split("[")[0], scope_longname)

    def add_set_by_entry(
        self,
        set_short_name,
        set_long_name,
        name_of_file,
        line,
        column,
        ctx,
        scope_override=None,
        resolve_override=None,
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
        # A dereferenced member resolves inside the class that declares it, not
        # in the method doing the assigning; the reference's own scope is still
        # the method, which is what Understand reports as the Setby.
        if scope_override is not None:
            scope_longname = scope_override
        if resolve_override is not None:
            resolve_scope = resolve_override
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
                            # The dereferenced variable itself is a Set Deref
                            # Partial, but the *member* being written is a
                            # plain Set against the field's declaring class:
                            # `x.p = temp` sets RedBlackBST.Node.p.
                            self.add_member_set(target, ctx, name_of_file)
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
