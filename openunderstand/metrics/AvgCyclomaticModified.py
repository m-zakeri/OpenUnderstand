import os
from antlr4 import *
from setuptools import glob

from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener

import argparse


class CyclomaticListener(JavaParserLabeledListener):
    def __init__(self):
        self.count=0
        self.methods=0
        self.avg=0
        self.dict={}
        self.name=""

    @property
    def get_dict(self):
        return self.dict

    def enterClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        try:
            self.name = ctx.IDENTIFIER().getText()
            self.dict[self.name] = 0
            self.count=1
            self.methods=0
            self.avg = 0
        except:
            pass

    def enterCatchClause(self, ctx: JavaParserLabeled.CatchClauseContext):
        try:
            self.cnt(ctx,0)
        except:
            pass


    def enterMethodDeclaration(self, ctx:JavaParserLabeled.MethodDeclarationContext):
        try:
            self.methods = self.methods + 1
        except:
            pass

    #?
    def enterExpression20(self, ctx:JavaParserLabeled.Expression20Context):
        try:
            self.cnt(ctx,0)
        except:
            pass


    # switch
    def enterStatement8(self, ctx: JavaParserLabeled.Statement10Context):
        try:
            found = False
            if (ctx.children[0].getText() == 'switch'):
                found = True
            if found == True:
                self.count += 1
            self.cnt(ctx, 0)
        except:
            pass

    #if
    def enterStatement2(self, ctx: JavaParserLabeled.Statement3Context):
        try:
            if len(ctx.children) ==3:
                self.cnt(ctx,0)
            if len(ctx.children)==5:
                self.cnt(ctx, 1)
        except:
            pass
    #while
    def enterStatement4(self, ctx: JavaParserLabeled.Statement3Context):
        try:
            self.cnt(ctx,0)
        except:
            pass

    # for
    def enterStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        try:
            self.cnt(ctx,0)
        except:
            pass

    #do-While
    def enterStatement5(self, ctx: JavaParserLabeled.Statement0Context):
        try:
            self.cnt(ctx, 2)
        except:
            pass

    def cnt(self,ctx,num):
        if ctx.children[0].getText() == "for":
            self.count=self.count+1

        if ctx.children[0].getText() == "while":
            self.count=self.count+1

        if ctx.children[0].getText() == "if":
            self.count = self.count + 1

        if ctx.children[0].getText() == "catch":
            self.count = self.count + 1

        if num==0 and ctx.children[0].getText() == "else":
            self.count = self.count + 1

        if  ctx.children[1].getText() == "?":
            self.count = self.count + 1

        if num==1 and ctx.children[3].getText() == "else":
            if ctx.children[4].children[0].getText() != "if":
                self.count=self.count+1
        if num == 2 and ctx.children[0].getText() == "do" and ctx.children[2].getText() == "while":
            self.count = self.count + 1


    def exitClassDeclaration(self, ctx:JavaParserLabeled.ClassDeclarationContext):
        try:
            self.avg=self.count/self.methods
            self.dict[self.name] = self.avg
        except:
            pass



def main(args):
    stream = FileStream(args.file, encoding="utf8")
    lexer = JavaLexer(stream)
    token_stream = CommonTokenStream(lexer)
    parser = JavaParserLabeled(token_stream)
    parser_tree = parser.compilationUnit()

    my_listener = CyclomaticListener()

    walker = ParseTreeWalker()
    walker.walk(t=parser_tree,listener=my_listener)


    print(f"Average Cyclomatic Modified:{my_listener.get_dict}")


if __name__ == '__main__':
    path = '/Users/nikinezakati/Desktop/Compiler/OpenUnderstand/benchmark'
    for dirpath, dirnames, filenames in os.walk('/Users/nikinezakati/Desktop/Compiler/OpenUnderstand/benchmark'):
        print(f"PATH:{dirpath}")
        print("----------")
        for filename in [f for f in filenames if f.endswith(".java")]:
            if filename.endswith('.java'):
                argparser = argparse.ArgumentParser()
                print(f"DIR:{dirnames}, FILENAME:{filename}")
                argparser.add_argument(
                    '-n', '--file',
                    help='Input source', default=os.path.join(dirpath, filename))
                args = argparser.parse_args()
                main(args)
