from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
import openunderstand.analysis_passes.class_properties as class_properties
from db.api import open as db_open, create_db
from db.models import KindModel, EntityModel, ReferenceModel
from db.fill import main

class ClassEntities:
    def __init__(self,name, parent , kind , content , longname  , modifiers):
        self.modifiers = modifiers
        self.name = name
        self.parent = parent
        self.kind = kind
        self.content = content
        self.longname = longname
        self.type = None
        self.value = None

class implementListener(JavaParserLabeledListener):
    classes = []
    def __init__(self , classes):
        self.classes = classes

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        name = ctx.IDENTIFIER().getText()
        scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if len(scope_parents) == 1:
            scope_longname = scope_parents[0]
        else:
            scope_longname = ".".join(scope_parents)

        EntityClass = ClassEntities(name, scope_parents[-2] if len(scope_parents) > 2 else None, "Class", ctx.getText(),
                                    scope_longname , class_properties.ClassPropertiesListener.findClassOrInterfaceModifiers(
                                                   ctx))
        self.classes.append(EntityClass)

class CastAndCastBy(JavaParserLabeledListener):
    classes = []
    def __init__(self , classes):
        self.classes = classes

            # for myType in ctx.typeList().typeType():
            #     if myType.classOrInterfaceType():
            #         myType_longname = ".".join([x.getText() for x in myType.classOrInterfaceType().IDENTIFIER()])
            #         EntityClass = ClassEntities(scope_parents[-2] if len(scope_parents) > 2 else None,"Class",ctx.getText(),scope_longname)
            #         self.classes.append(EntityClass)

    def enterExpression5(self, ctx:JavaParserLabeled.Expression5Context):
        name = ctx.typeType().getText()
        scope_parents = class_properties.ClassPropertiesListener.findParents(ctx)
        [line, col] = str(ctx.start).split(",")[3].split(":")  # line, column
        if (len(scope_parents) >= 2):
            parent = scope_parents[-2]
        else:
            parent = None
        print(name)
        for ent in self.classes:
            if(ent.name == name):
                print(ent.parent)
                print("name : " + ent.name)
                print("Longname : "+ent.longname)
                print("Kind : "+ent.kind)
                print("Content : "+ ent.content)
                print(ent.modifiers)
            if(parent is not None):
                if(ent.name == parent):
                    print(ent.parent)
                    print("name : " + ent.name)
                    print("Longname : " + ent.longname)
                    print("Kind : " + ent.kind)
                    print("Content : " + ent.content)
                    print(ent.modifiers)
    # cast = []
    # name = ""
    # @staticmethod
    # def findClassOrInterfaceModifiers(c):
    #     m = ""
    #     modifiers = []
    #     current = c
    #     while current is not None:
    #         if "typeDeclaration" in type(current.parentCtx).__name__:
    #             m = (current.parentCtx.classOrInterfaceModifier())
    #             break
    #         current = current.parentCtx
    #     for x in m:
    #         modifiers.append(x.getText())
    #     return modifiers

    # def enterExpression5(self, ctx:JavaParserLabeled.Expression5Context):
    #     self.name = ctx.typeType().getText()
    #     kindId = ""
    #     print("name : "+ self.name)
    #     parents = class_properties.ClassPropertiesListener.findParents(ctx)
    #     if len(parents) == 1:
    #         longname = parents[0]
    #     else:
    #         longname = ".".join(parents)
    #
    #     print("longname : "+longname)
    #     #self.SearchInDB(name=self.name)
    #     Value = None
    #     print("Value : ")
    #     type = None
    #     print("Type : ")

    # def SearchInDB(self, name):
    #     create_db("C:/Users/98910/university/Term6/Courses/Compiler/Project/Compiler_OpneUnderstand/OpenUnderstand-8b69f877f175bf4ccd6c58ec3601be655157d8ca/benchmark2_database.db",
    #               project_dir="C:/Users/98910/university/Term6/Courses/Compiler/Project/Compiler_OpneUnderstand/OpenUnderstand-8b69f877f175bf4ccd6c58ec3601be655157d8ca/benchmark")
    #     db = db_open("C:/Users/98910/university/Term6/Courses/Compiler/Project/Compiler_OpneUnderstand/OpenUnderstand-8b69f877f175bf4ccd6c58ec3601be655157d8ca/benchmark2_database.db")
    #
    #     obj = EntityModel.get_or_none("c2")
    #     print("3")
    #     print(obj)
    #     # for entitiy in castedToClass:
    #     #     print("4")
    #     #     print("Parent : "+entitiy._parent)
    #     #     print("Kind : " + entitiy._kind)
    #     #     print("Content : "+entitiy._contents)
    #
    #
    # def enterExpression5(self, ctx:JavaParserLabeled.Expression5Context):
    #     kind_id = "174"


