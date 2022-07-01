"""
## Description
This module find all OpenUnderstand call and callby references in a Java project

## References

"""

__author__ = 'Navid Mousavizade, Amir Mohammad Sohrabi, Sara Younesi, Deniz Ahmadi'
__version__ = '0.1.0'

from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled


class UseModuleUseModuleByListener(JavaParserLabeledListener):
    """
    #Todo: Implementing the ANTLR listener pass for Java Call and Java Callby reference kind
    """
    useModules = []
    useUnknownModules = []
    useUnresolvedModules = []
    methods = []

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.methods.append(ctx.IDENTIFIER().getText())

    def enterAnnotation(self, ctx:JavaParserLabeled.AnnotationContext):
        line_col = str(ctx.start).split(",")[3][:-1].split(':')
        self.useModules.append({
            "scope": None, "ent": None, "name": ctx.children[1].IDENTIFIER()[0].getText(),
            "line": line_col[0], "col": line_col[1]
        })
        self.useUnresolvedModules.append({
            "scope": None, "ent": None, "name": ctx.children[1].IDENTIFIER()[0].getText(),
            "line": line_col[0], "col": line_col[1]
        })

    def enterPackageDeclaration(self, ctx:JavaParserLabeled.PackageDeclarationContext):
        package_name_array = ctx.getText().replace('package', '').split('.')
        if len(package_name_array) == 4 and package_name_array[0] == 'com':
            self.useUnknownModules.append({
                "scope": None, "ent": ctx.getChild(1).IDENTIFIER()[3].getText(), "name":ctx.getChild(1).IDENTIFIER()[2].getText(),
                "line": 1, "col": 1
            })
            self.useUnresolvedModules.append({
                "scope": None, "ent": ctx.getChild(1).IDENTIFIER()[3].getText(),
                "name": ctx.getChild(1).IDENTIFIER()[2].getText(),
                "line": 1, "col": 1
            })
