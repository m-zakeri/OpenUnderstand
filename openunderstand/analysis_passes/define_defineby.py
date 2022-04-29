"""


"""

from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import analysis_passes.class_properties as class_properties

class DefineListener(JavaParserLabeledListener):
    def __init__(self):
        self.defines = []
        self.package = ""

    def enterPackageDeclaration(self, ctx:JavaParserLabeled.PackageDeclarationContext):
        self.package = [str(i) for i in ctx.qualifiedName().IDENTIFIER()]

    def enterClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        ent = ctx.IDENTIFIER()
        ent_name = ent.getText()
        line = ent.symbol.line
        column = ent.symbol.column
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(self.package + ent_parents[:-1])
        ent_longname = scope_longname + "." + ent_name
        if len(ent_parents) == 1:
            scope_name = None
        else:
            scope_name = ent_parents[-2]

        self.defines.append({
            "scope": scope_name, "ent": ent_name,
            "scope_longname": scope_longname, "ent_longname": ent_longname,
            "line": line, "col": column
        })

    def enterInterfaceDeclaration(self, ctx:JavaParserLabeled.InterfaceDeclarationContext):
        ent = ctx.IDENTIFIER()
        ent_name = ent.getText()
        line = ent.symbol.line
        column = ent.symbol.column
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(self.package + ent_parents[:-1])
        ent_longname = scope_longname + "." + ent_name
        if len(ent_parents) == 1:
            scope_name = None
        else:
            scope_name = ent_parents[-2]

        self.defines.append({
            "scope": scope_name, "ent": ent_name,
            "scope_longname": scope_longname, "ent_longname": ent_longname,
            "line": line, "col": column
        })

    def enterMethodDeclaration(self, ctx:JavaParserLabeled.MethodDeclarationContext):
        ent = ctx.IDENTIFIER()
        ent_name = ent.getText()
        line = ent.symbol.line
        column = ent.symbol.column
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(self.package + ent_parents[:-1])
        ent_longname = scope_longname + "." + ent_name
        if len(ent_parents) == 1:
            scope_name = None
        else:
            scope_name = ent_parents[-2]

        self.defines.append({
            "scope": scope_name, "ent": ent_name,
            "scope_longname": scope_longname, "ent_longname": ent_longname,
            "line": line, "col": column
        })

    def enterConstructorDeclaration(self, ctx:JavaParserLabeled.ConstructorDeclarationContext):
        ent = ctx.IDENTIFIER()
        ent_name = ent.getText()
        line = ent.symbol.line
        column = ent.symbol.column
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(self.package + ent_parents)
        ent_longname = scope_longname + "." + ent_name
        if len(ent_parents) == 0:
            scope_name = None
        else:
            scope_name = ent_parents[-1]

        self.defines.append({
            "scope": scope_name, "ent": ent_name,
            "scope_longname": scope_longname, "ent_longname": ent_longname,
            "line": line, "col": column
        })

    def enterVariableDeclarator(self, ctx:JavaParserLabeled.VariableDeclaratorContext):
        ent = ctx.variableDeclaratorId().IDENTIFIER()
        ent_name = ent.getText()
        line = ent.symbol.line
        column = ent.symbol.column
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(self.package + ent_parents)
        ent_longname = scope_longname + "." + ent_name
        if len(ent_parents) == 0:
            scope_name = None
        else:
            scope_name = ent_parents[-1]

        self.defines.append({
            "scope": scope_name, "ent": ent_name,
            "scope_longname": scope_longname, "ent_longname": ent_longname,
            "line": line, "col": column
        })



    def enterEnumConstant(self, ctx:JavaParserLabeled.EnumConstantContext):
        ent = ctx.IDENTIFIER()
        ent_name = ent.getText()
        line = ent.symbol.line
        column = ent.symbol.column
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(self.package + ent_parents)
        ent_longname = scope_longname + "." + ent_name
        if len(ent_parents) == 0:
            scope_name = None
        else:
            scope_name = ent_parents[-1]

        self.defines.append({
            "scope": scope_name, "ent": ent_name,
            "scope_longname": scope_longname, "ent_longname": ent_longname,
            "line": line, "col": column
        })

    def enterFormalParameter(self, ctx:JavaParserLabeled.FormalParametersContext):
        ent = ctx.variableDeclaratorId().IDENTIFIER()
        ent_name = ent.getText()
        line = ent.symbol.line
        column = ent.symbol.column
        ent_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        scope_longname = ".".join(self.package + ent_parents)
        ent_longname = scope_longname + "." + ent_name
        if len(ent_parents) == 0:
            scope_name = None
        else:
            scope_name = ent_parents[-1]

        self.defines.append({
            "scope": scope_name, "ent": ent_name,
            "scope_longname": scope_longname, "ent_longname": ent_longname,
            "line": line, "col": column
        })