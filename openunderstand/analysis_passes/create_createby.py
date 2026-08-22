# expression -> NEW creator


"""
## Description
This module find all OpenUnderstand call and callby references in a Java project


## References


"""

__author__ = "zahra habibolah, G4"
# __version__ = "0.1.0"

# Omitted imports and other code for brevity
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties


class CreateAndCreateBy(JavaParserLabeledListener):
    def __init__(self):
        self.package_long_name = ""
        self.create = []
        self.imports = {}
        self.wildcard_imports = []
        # Initialize new flags for blockStatement and variableInitializer
        self.isBlockStatement1 = False
        self.isVariableInitializer1 = False
        self.isStatement15 = False  # New flag
        self.file_address = ""
        #: Resolved-type table for this file, built on first use.
        self._binder = None

    def findmethodreturntype(self, c):
        parents = ""
        context = ""
        current = c
        while current is not None:
            if type(current.parentCtx).__name__ == "MethodDeclarationContext":
                parents = current.parentCtx.typeTypeOrVoid().getText()
                context = current.parentCtx.getText()
                break
            current = current.parentCtx

        return parents, context

    # def findmethodaccess(self, c):
    #     parents = ""
    #     modifiers=[]
    #     current = c
    #     while current is not None:
    #         if "ClassBodyDeclaration" in type(current.parentCtx).__name__:
    #             parents=(current.parentCtx.modifier())
    #             break
    #         current = current.parentCtx
    #     for x in parents:
    #         if x.classOrInterfaceModifier():
    #             modifiers.append(x.classOrInterfaceModifier().getText())
    #     return modifiers

    def findmethodaccess(self, ctx):
        modifiers_list = [
            "Default",
            "Private",
            "Public",
            "Protected",
            "Static",
            "Generic",
            "Abstract",
            "Final",
        ]
        parent_modifiers = ""
        modifiers = []
        parent_type = ""
        current = ctx
        while current is not None:
            if "ClassBodyDeclaration2" in type(current.parentCtx).__name__:
                parent_modifiers = current.parentCtx.modifier()
                if "MethodDeclaration" in type(current.children[0]).__name__:
                    parent_type = "Method"
                elif "ConstructorDeclaration" in type(current.children[0]).__name__:
                    parent_type = "Constructor"
                # elif "FieldDeclaration" in type(current.children[0]).__name__:
                #     parent_type = "Method"
                elif "ClassDeclaration" in type(current.children[0]).__name__:
                    parent_type = "Class"
                elif "EnumDeclaration" in type(current.children[0]).__name__:
                    parent_type = "Enum"
                else:
                    parent_type = "Unresolved"
                break
            current = current.parentCtx

        for modifier in parent_modifiers:
            if modifier.classOrInterfaceModifier():
                if (
                    modifier.classOrInterfaceModifier().getText().title()
                    in modifiers_list
                ):
                    modifiers.append(modifier.classOrInterfaceModifier().getText())

        return modifiers, parent_type

    create = []

    # Add new method for statement15
    def enterStatement15(self, ctx):
        if self.isBlockStatement1:
            # Set flag if we are within blockStatement1
            self.isStatement15 = True

    # Override for blockStatement1
    def enterBlockStatement1(self, ctx):
        # Set context to blockStatement1
        self.isBlockStatement1 = True
        # Reset other flags
        self.isVariableInitializer1 = False
        self.isStatement15 = False

    # Override for variableInitializer1
    def enterVariableInitializer1(self, ctx):
        # Set context to variableInitializer1
        self.isVariableInitializer1 = True
        # Reset blockStatement1 context
        self.isBlockStatement1 = False
        # We do not reset isStatement15 because it's not related to variable initialization

    # Override exit methods to reset the flags when the context ends
    def exitBlockStatement1(self, ctx):
        self.isBlockStatement1 = False

    def exitVariableInitializer1(self, ctx):
        self.isVariableInitializer1 = False

    def exitStatement15(self, ctx):
        self.isStatement15 = False

    def enterExpression4(self, ctx: JavaParserLabeled.Expression4Context):
        """Every `new X(...)`, wherever it is written.

        This used to fire only inside a block statement or a variable
        initialiser, which is two of the places a creator can appear: `throw
        new JSONException(...)` is statement11 and `return new X(...)` is
        statement10, and a creator in an argument list is neither. Understand
        records a Create for all of them, and the constructor call with it --
        `org.json.JSONException.JSONException` alone was missing from 33
        methods' callee sets.
        """
        if True:
            modifiers, parent_type = self.findmethodaccess(ctx)
            methodreturn, methodcontext = self.findmethodreturntype(ctx)

            # First check to ensure we're working with creator1
            creator = ctx.creator()
            rest = creator.classCreatorRest()
            # `new ActionListener() { ... }` declares an anonymous class rather
            # than creating a named one, and Understand reports no Java Create
            # for it -- 4 of Hanoi's rows, and the entity each left behind was
            # the bare name `ActionListener`.
            anonymous = rest is not None and rest.classBody() is not None
            if not anonymous and (creator.arrayCreatorRest() or rest):
                createdName = creator.createdName()
                all_parents = class_properties.ClassPropertiesListener.findParents(ctx)
                scope_name = all_parents[-1]
                # findParents() already includes the package components.
                scope_longname = ".".join(all_parents)
                # The token carries its own position. Scraping it out of the
                # token's repr broke on tokens whose text contains a comma or
                # a colon -- `new int[24]` yielded the column "24]", which went
                # straight into an integer column as text.
                # The reference belongs on the *type* being created, not on
                # the `new` keyword: Understand puts `new StringBuilder()`
                # at the S, four columns right of where ctx.start is.
                line = createdName.start.line
                col = createdName.start.column

                # if creator.arrayCreatorRest() or creator.classCreatorRest():
                # If we're in the correct context for creator1, then check for createdName0
                # createdName = creator.createdName()
                # if isinstance(createdName, JavaParserLabeled.CreatedName0Context):
                # all_parents = class_properties.ClassPropertiesListener.findParents(ctx)
                # scope_name = all_parents[-1]
                # scope_longname = self.package_long_name + "." + ".".join(all_parents)
                # [line, col] = str(ctx.start).split(",")[3].split(":")

                self.create.append(
                    {
                        "scopename": scope_name,
                        "scopelongname": scope_longname,
                        "scopemodifiers": modifiers,
                        "parent_type": parent_type,
                        "scopereturntype": methodreturn,
                        "scopecontent": methodcontext,
                        "line": line,
                        "col": col,
                        # An array creation runs no constructor, so it is a Create and not a Call.
                        "is_array": creator.arrayCreatorRest() is not None,
                        "arguments": self.constructor_arguments(creator),
                        "refent": createdName.getText(),
                        # Resolved here rather than left bare: a bare
                        # `StringBuilder` is folded by
                        # merge_placeholder_entities() into whatever
                        # project entity shares the name, where Understand
                        # reports java.lang.StringBuilder.
                        "refent_longname": self.resolve_created_type(
                            createdName.getText(), scope_longname
                        ),
                        "scope_parent": (
                            all_parents[-2] if len(all_parents) > 1 else None
                        ),
                        "potential_refent": ".".join(all_parents[:-1])
                        + "."
                        + createdName.getText(),
                    }
                )

        # Reset the flags whether context condition was met or not
        self.isBlockStatement1 = False
        self.isVariableInitializer1 = False

    def binder(self, ctx):
        """The resolved-type table for this file, built from the tree's root."""
        if self._binder is None:
            from openunderstand.ounderstand.type_binding import TypeBinder

            root = ctx
            while root.parentCtx is not None:
                root = root.parentCtx
            self._binder = TypeBinder(root, self.file_address)
        return self._binder

    def constructor_arguments(self, creator):
        """Types of the arguments `new X(...)` passes, for overload selection.

        org.json.JSONObject has fifteen constructors and org.json.JSONArray
        twelve, so `new JSONObject(map)` and `new JSONObject(string)` are two
        callees to Understand and were one here.
        """
        from openunderstand.ounderstand import type_binding

        rest = creator.classCreatorRest()
        arguments = rest.arguments() if rest is not None else None
        listed = arguments.expressionList() if arguments is not None else None
        if arguments is None:
            return None  # an array creation runs no constructor
        return tuple(
            type_binding.argument_type(self.binder(expression), expression)
            for expression in (listed.expression() if listed else [])
        )

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        longname = ctx.qualifiedName().getText()
        if ctx.getText().rstrip(";").endswith(".*"):
            self.wildcard_imports.append(longname)
            return  # a package, not a type
        self.imports[longname.split(".")[-1]] = longname

    def resolve_created_type(self, name, scope_longname):
        """Long name of the type being created, or None if it cannot be placed."""
        from openunderstand.ounderstand import symbol_table

        # The same ladder every other pass climbs. This used to be a private
        # near-copy; the shared one also resolves a type reached through one of
        # several `import x.y.*`, which is most of what Hanoi.java constructs.
        return symbol_table.resolve_type_name(
            name, self.imports, self.wildcard_imports, scope_longname
        )

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.package_long_name = ctx.qualifiedName().getText()


# This code does not show the parts related to THROW, i.e. statement11
# the code below is the version that shows it, but the outputs are more in Linux.

# Omitted imports and other code for brevity
# from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
# from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
# import analysis_passes.class_properties as class_properties
#
# class CreateAndCreateBy(JavaParserLabeledListener):
#     def __init__(self):
#         self.package_long_name = ""
#         self.create = []
#         # Initialize new flags for blockStatement and variableInitializer
#         self.isBlockStatement1 = False
#         self.isVariableInitializer1 = False
#         self.isStatement15 = False
#         self.isStatement11 = False
#
#     def findmethodreturntype(self, c):
#         parents = ""
#         context = ""
#         current = c
#         while current is not None:
#             if type(current.parentCtx).__name__ == "MethodDeclarationContext":
#                 parents = current.parentCtx.typeTypeOrVoid().getText()
#                 context = current.parentCtx.getText()
#                 break
#             current = current.parentCtx
#
#         return parents, context
#
#     # def findmethodaccess(self, c):
#     #     parents = ""
#     #     modifiers=[]
#     #     current = c
#     #     while current is not None:
#     #         if "ClassBodyDeclaration" in type(current.parentCtx).__name__:
#     #             parents=(current.parentCtx.modifier())
#     #             break
#     #         current = current.parentCtx
#     #     for x in parents:
#     #         if x.classOrInterfaceModifier():
#     #             modifiers.append(x.classOrInterfaceModifier().getText())
#     #     return modifiers
#
#     def findmethodaccess(self, ctx):
#         modifiers_list = [
#             "Default",
#             "Private",
#             "Public",
#             "Protected",
#             "Static",
#             "Generic",
#             "Abstract",
#             "Final",
#         ]
#         parent_modifiers = ""
#         modifiers = []
#         parent_type = ""
#         current = ctx
#         while current is not None:
#             if "ClassBodyDeclaration2" in type(current.parentCtx).__name__:
#                 parent_modifiers = current.parentCtx.modifier()
#                 if "MethodDeclaration" in type(current.children[0]).__name__:
#                     parent_type = "Method"
#                 elif "ConstructorDeclaration" in type(current.children[0]).__name__:
#                     parent_type = "Constructor"
#                 # elif "FieldDeclaration" in type(current.children[0]).__name__:
#                 #     parent_type = "Method"
#                 elif "ClassDeclaration" in type(current.children[0]).__name__:
#                     parent_type = "Class"
#                 elif "EnumDeclaration" in type(current.children[0]).__name__:
#                     parent_type = "Enum"
#                 else:
#                     parent_type = "Unresolved"
#                 break
#             current = current.parentCtx
#
#         for modifier in parent_modifiers:
#             if modifier.classOrInterfaceModifier():
#                 if (
#                     modifier.classOrInterfaceModifier().getText().title()
#                     in modifiers_list
#                 ):
#                     modifiers.append(modifier.classOrInterfaceModifier().getText())
#
#         return modifiers, parent_type
#
#     create = []
#
#     # Add new method for statement15
#     def enterStatement15(self, ctx):
#         if self.isBlockStatement1:
#             # Set flag if we are within blockStatement1
#             self.isStatement15 = True
#
#     # Override for blockStatement1
#     def enterBlockStatement1(self, ctx):
#         # Set context to blockStatement1
#         self.isBlockStatement1 = True
#         # Reset other flags
#         self.isVariableInitializer1 = False
#         self.isStatement15 = False
#
#     # Override for variableInitializer1
#     def enterVariableInitializer1(self, ctx):
#         # Set context to variableInitializer1
#         self.isVariableInitializer1 = True
#         # Reset blockStatement1 context
#         self.isBlockStatement1 = False
#         # We do not reset isStatement15 because it's not related to variable initialization
#
#     # Override exit methods to reset the flags when the context ends
#     def exitBlockStatement1(self, ctx):
#         self.isBlockStatement1 = False
#
#     def exitVariableInitializer1(self, ctx):
#         self.isVariableInitializer1 = False
#
#     def exitStatement15(self, ctx):
#         self.isStatement15 = False
#
#     def enterStatement11(self, ctx):
#         self.isStatement11 = True
#
#     def exitStatement11(self, ctx):
#         self.isStatement11 = False
#
#     def enterExpression4(self, ctx: JavaParserLabeled.Expression4Context):
#         # Check for specific sequences
#         if self.isBlockStatement1 or self.isVariableInitializer1:
#             if self.isBlockStatement1 and self.isStatement15 or self.isStatement11:
#                 # Process Expression4 only if followed by statement15 in a blockStatement1
#                 self.processExpression4(ctx)
#             elif self.isVariableInitializer1:
#                 # Process Expression4 only if it follows a variableInitializer1
#                 # Assuming you are 'throwing away' variable declarators before this
#                 self.processExpression4(ctx)
#             # Reset flags after checking for the specific sequence
#         self.isBlockStatement1 = False
#         self.isVariableInitializer1 = False
#         self.isStatement15 = False
#
#     def processExpression4(self, ctx):
#         # Perform the context check before processing the expression4
#         #if self.isBlockStatement1 or self.isVariableInitializer1:
#             modifiers, parent_type = self.findmethodaccess(ctx)
#             methodreturn, methodcontext = self.findmethodreturntype(ctx)
#
#             # First check to ensure we're working with creator1
#             creator = ctx.creator()
#             if creator.arrayCreatorRest() or creator.classCreatorRest():
#                 createdName = creator.createdName()
#                 all_parents = class_properties.ClassPropertiesListener.findParents(ctx)
#                 scope_name = all_parents[-1]
#                 scope_longname = self.package_long_name + "." + ".".join(all_parents)
#                 [line, col] = str(ctx.start).split(",")[3].split(":")
#
#             #if creator.arrayCreatorRest() or creator.classCreatorRest():
#                 # If we're in the correct context for creator1, then check for createdName0
#                 #createdName = creator.createdName()
#                 #if isinstance(createdName, JavaParserLabeled.CreatedName0Context):
#                     #all_parents = class_properties.ClassPropertiesListener.findParents(ctx)
#                     #scope_name = all_parents[-1]
#                     #scope_longname = self.package_long_name + "." + ".".join(all_parents)
#                     #[line, col] = str(ctx.start).split(",")[3].split(":")
#
#
#                 self.create.append(
#                     {
#                         "scopename": scope_name,
#                         "scopelongname": scope_longname,
#                         "scopemodifiers": modifiers,
#                         "parent_type": parent_type,
#                         "scopereturntype": methodreturn,
#                         "scopecontent": methodcontext,
#                         "line": line.strip(),
#                         "col": col.strip(),
#                         "refent": createdName.getText(),
#                         "scope_parent": all_parents[-2] if len(all_parents) > 1 else None,
#                         "potential_refent": ".".join(all_parents[:-1]) + "." + createdName.getText(),
#                     }
#                 )
#
#         # Reset the flags whether context condition was met or not
#             self.isBlockStatement1 = False
#             self.isVariableInitializer1 = False
#
#     def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
#         self.package_long_name = ctx.qualifiedName().getText()
