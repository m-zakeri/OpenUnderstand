from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties
from db.api import open as db_open, create_db
from db.models import KindModel, EntityModel, ReferenceModel
from db.fill import main

class CastAndCastBy(JavaParserLabeledListener):
    cast = []
    name = ""

    @staticmethod
    def findParents(c):  # includes the ctx identifier
        parents = []
        current = c
        while current is not None:
            if type(current).__name__ == "ClassDeclarationContext" or type(
                    current).__name__ == "MethodDeclarationContext" \
                    or type(current).__name__ == "EnumDeclarationContext" \
                    or type(current).__name__ == "InterfaceDeclarationContext" \
                    or type(current).__name__ == "AnnotationTypeDeclarationContext":
                parents.append(current.IDENTIFIER().getText())
            current = current.parentCtx
        return list(reversed(parents))

    @staticmethod
    def findClassOrInterfaceModifiers(c):
        m = ""
        modifiers = []
        current = c
        while current is not None:
            if "typeDeclaration" in type(current.parentCtx).__name__:
                m = (current.parentCtx.classOrInterfaceModifier())
                break
            current = current.parentCtx
        for x in m:
            modifiers.append(x.getText())
        return modifiers

    def enterExpression5(self, ctx:JavaParserLabeled.Expression5Context):
        self.name = ctx.typeType().getText()
        kindId = ""
        print("name : "+ self.name)
        parents = self.findParents(ctx)
        longname = ""
        if len(parents) == 1:
            longname = parents[0]
        else:
            longname = ".".join(parents)

        print("longname : "+longname)
        self.SearchInDB(self.name)
        Value = None
        print("Value : ")
        type = None
        print("Type : ")

    def SearchInDB(self, name):
        print("1")
        db = db_open("C:/Users/98910/university/Term6/Courses/Compiler/Project/Compiler_OpneUnderstand/OpenUnderstand-8b69f877f175bf4ccd6c58ec3601be655157d8ca/benchmark2_database.db")
        print("2")
        castedToClass = EntityModel.select().where(EntityModel._name == name)
        print("3")
        for entitiy in castedToClass:
            print("4")
            print("Parent : "+entitiy._parent)
            print("Kind : " + entitiy._kind)
            print("Content : "+entitiy._contents)