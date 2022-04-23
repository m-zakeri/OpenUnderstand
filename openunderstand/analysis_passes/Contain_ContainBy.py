from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties
from db.api import open as db_open, create_db
from db.models import KindModel, EntityModel, ReferenceModel
from db.fill import main

class ContainAndContainBy(JavaParserLabeledListener):
    contain = []
    def enterPackageDeclaration(self, ctx:JavaParserLabeled.PackageDeclarationContext):
        print(ctx.qualifiedName().IDENTIFIER()[0])

    def enterClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        print(ctx.IDENTIFIER().getText())
        [line, col] = str(ctx.start).split(",")[3].split(":")  # line, column
        col = col[:-1]
        print("line : "+line)
        print("col :" +col)


