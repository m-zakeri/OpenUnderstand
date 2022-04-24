from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties
from db.api import open as db_open, create_db
from db.models import KindModel, EntityModel, ReferenceModel
from db.fill import main

class ContainAndContainBy(JavaParserLabeledListener):
    contain = []
    packageInfo = []


    def enterPackageDeclaration(self, ctx:JavaParserLabeled.PackageDeclarationContext):
        print(ctx.qualifiedName().IDENTIFIER()[0])
        self.packageInfo.append({"name":ctx.qualifiedName().IDENTIFIER()[0]})

    def enterClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        name = ctx.IDENTIFIER().getText()
        print(ctx.IDENTIFIER().getText())
        [line, col] = str(ctx.start).split(",")[3].split(":")  # line, column
        col = col[:-1]
        scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if len(scope_parents) == 1:
            scope_longname = scope_parents[0]
        else:
            scope_longname = ".".join(scope_parents)


        scope_longname = "."+ scope_longname
        packageName = self.packageInfo[0]["name"]
        scope_longname = packageName.getText() + scope_longname


        parent = scope_parents[-2] if len(scope_parents) > 2 else None
        kind ="Class"
        modifiers = class_properties.ClassPropertiesListener.findClassOrInterfaceModifiers(
            ctx)
        content = ctx.getText()

        self.contain.append({
                             "package_name":packageName.getText(),
                             "name":name ,
                             "longname" : scope_longname,
                             "parent" : parent,
                             "kind" : kind,
                             "line" :line,
                             "col" : col,
                             "modifiers" : modifiers,
                             "content":content
                             })
        print(self.contain)





