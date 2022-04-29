"""
The helper module for couple_coupleby.py, create_createby.py, declare_declareby.py modules

Todo: Must be document well
"""


__author__ = 'Shaghayegh Mobasher , Setayesh kouloubandi ,Parisa Alaie, Zakeri'
__version__ = '0.1.1'


from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled


class ClassPropertiesListener(JavaParserLabeledListener):
    class_longname = []
    class_properties = None

    def checkParents(self, c):
        return set(ClassPropertiesListener.findParents(c)) & set(list(reversed(self.class_longname)))

    @staticmethod
    def findParents(c):  # includes the ctx identifier
        parents = []
        current = c
        while current is not None:
            if type(current).__name__ == "ClassDeclarationContext" or type(current).__name__ == "MethodDeclarationContext"\
                    or type(current).__name__ == "EnumDeclarationContext"\
                    or type(current).__name__ == "InterfaceDeclarationContext"\
                    or type(current).__name__ == "AnnotationTypeDeclarationContext":
                parents.append(current.IDENTIFIER().getText())
            current = current.parentCtx
        return list(reversed(parents))

    @staticmethod
    def findClassOrInterfaceModifiers(c):
        m = ""
        modifiers=[]
        current = c
        while current is not None:
            if "typeDeclaration" in type(current.parentCtx).__name__:
                m=(current.parentCtx.classOrInterfaceModifier())
                break
            current = current.parentCtx
        for x in m:
            modifiers.append(x.getText())
        return modifiers

    def enterClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        if self.class_properties:  # already found the class
            return
        if self.class_longname[-1] == ctx.IDENTIFIER().getText():
            if self.checkParents(ctx):
                # this is the exact class we wanted.
                self.class_properties = {}
                self.class_properties["name"] = self.class_longname[-1]
                self.class_properties["longname"] = ".".join(self.class_longname)

                if len(self.class_longname) == 1:
                    self.class_properties["parent"] = None
                else:
                    self.class_properties["parent"] = self.class_longname[-2]
                self.class_properties["modifiers"] = ClassPropertiesListener.findClassOrInterfaceModifiers(ctx)
                self.class_properties["contents"] = ctx.getText()


class InterfacePropertiesListener(JavaParserLabeledListener):
    interface_longname = []
    interface_properties = None

    def checkParents(self, c):
        return set(ClassPropertiesListener.findParents(c)) & set(list(reversed(self.interface_longname)))

    def enterInterfaceDeclaration(self, ctx:JavaParserLabeled.InterfaceDeclarationContext):
        if self.interface_properties:  # already found the interface
            return
        if self.interface_longname[-1] == ctx.IDENTIFIER().getText():
            if self.checkParents(ctx):
                # this is the exact class we wanted.
                self.interface_properties = {}
                self.interface_properties["name"] = self.interface_longname[-1]
                self.interface_properties["longname"] = ".".join(self.interface_longname)

                if len(self.interface_longname) == 1:
                    self.interface_properties["parent"] = None
                else:
                    self.interface_properties["parent"] = self.interface_longname[-2]
                self.interface_properties["modifiers"] = ClassPropertiesListener.findClassOrInterfaceModifiers(ctx)
                self.interface_properties["contents"] = ctx.getText()




