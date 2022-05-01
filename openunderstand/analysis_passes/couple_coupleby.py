"""
## Description
This module find all OpenUnderstand call and callby references in a Java project


## References


"""

__author__ = 'Shaghayegh Mobasher , Setayesh kouloubandi ,Parisa Alaie'
__version__ = '0.1.0'

from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled


class CoupleAndCoupleBy(JavaParserLabeledListener):
    class_names = []
    implement = []
    def __init__(self,class_names):
        self.class_names = class_names
        self.implement = []

    def enterClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        for item in ctx.classBody().classBodyDeclaration():
            member = item.memberDeclaration()
            if type(item) == JavaParserLabeled.ClassBodyDeclaration2Context and type(member) == JavaParserLabeled.MemberDeclaration2Context:
                field = member.fieldDeclaration()
                variable = field.variableDeclarators().variableDeclarator()

                variable = variable[0].variableDeclaratorId().IDENTIFIER()
                typeType = field.typeType()
                targetClass = typeType.classOrInterfaceType()

                if targetClass is not None:
                    if targetClass.getText() in self.class_names:
                        print("Couple", [
                            ctx.IDENTIFIER().getText(),
                            str(targetClass.IDENTIFIER()[0]),
                        ])

                        line = ctx.children[0].symbol.line
                        col = ctx.children[0].symbol.column

                        self.implement.append({"scope_kind": "Class", "scope_name": ctx.IDENTIFIER().getText(),
                                               "scope_longname": ctx.IDENTIFIER().getText(),
                                               "scope_parent": None,
                                               "scope_contents": ctx.getText(),
                                               "scope_modifiers": [],
                                               "line": line,
                                               "col": col,
                                               "type_ent_longname": str(targetClass.IDENTIFIER()[0])})
            elif type(item) == JavaParserLabeled.ClassBodyDeclaration2Context and type(member) == JavaParserLabeled.MemberDeclaration0Context:
                block = member.methodDeclaration().methodBody().block()
                for blockStatement in block.blockStatement():
                    if type(blockStatement) == JavaParserLabeled.BlockStatement0Context:
                        variable = blockStatement.localVariableDeclaration()
                        targetClass = variable.typeType().classOrInterfaceType()
                        if targetClass is not None and targetClass.getText() in self.class_names:
                            print("Couple", [
                                ctx.IDENTIFIER().getText(),
                                str(targetClass.IDENTIFIER()[0]),
                            ])
                            line = ctx.children[0].symbol.line
                            col = ctx.children[0].symbol.column

                            self.implement.append({"scope_kind": "Class", "scope_name": ctx.IDENTIFIER().getText(),
                                                   "scope_longname": ctx.IDENTIFIER().getText(),
                                                   "scope_parent": None,
                                                   "scope_contents": ctx.getText(),
                                                   "scope_modifiers": [],
                                                   "line": line,
                                                   "col": col,
                                                   "type_ent_longname": str(targetClass.IDENTIFIER()[0])})
