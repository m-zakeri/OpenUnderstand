import os
from antlr4 import *
from setuptools import glob

from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener

import argparse

class CyclomaticListener(JavaParserLabeledListener):
    def __init__(self):
        self.count = 0
        self.methods = 0
        self.avg = 0
        self.dict = {}
        self.name = ""
        self.cycle=[]
        self.symbols = ['if', 'for', 'while', 'and', 'or', '?', 'do']

    @property
    def get_dict(self):
        return self.dict

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        try:
            self.name = ctx.IDENTIFIER().getText()
            self.dict[self.name] = 0
            self.count = 1
            self.methods = 0
            self.avg = 0
            self.cycle = []
        except:
            pass    

    def enterStatement12(self, ctx:JavaParserLabeled.Statement12Context):
        try:
            arr = []
            temp = ctx
            while type(temp) != 'gen.JavaParserLabeled.JavaParserLabeled.MethodBodyContext':

                if not hasattr(temp,'parentCtx'):
                    break
                child = temp
                temp = temp.parentCtx

                if not hasattr(temp, 'start'):
                    continue


                if not hasattr(temp,'children'):
                    continue
                x=temp.children[0]
                if len(temp.children)>=5:
                    if child.getText() == temp.children[4].getText():
                        y = temp.children[3]
                        if y.getText() in self.symbols:

                            if hasattr(y, 'symbol'):
                                if y.symbol in self.cycle:
                                    continue
                                arr.append(y.symbol)
                                if arr[0].text != 'if':
                                    return
                                self.count += 1
                                self.cycle.append(y.symbol)
                                continue


                if x.getText() in self.symbols:

                    if hasattr(x, 'symbol'):
                        if x.symbol in self.cycle:
                            continue
                        arr.append(x.symbol)
                        if arr[0].text != 'if':
                            return
                        self.count += 1
                        self.cycle.append(x.symbol)
                        continue
                if not hasattr(x,'children'):
                    continue
                if x.children[0].getText() in self.symbols:

                    if hasattr(x.children[0], 'symbol'):
                        if x.children[0].symbol in self.cycle:
                            continue

                        arr.append(x.children[0].symbol)
                        if arr[0].text != 'if':
                            return
                        self.count += 1
                        self.cycle.append(x.children[0].symbol)
                        continue

        except:
            pass

    def enterStatement10(self, ctx:JavaParserLabeled.Statement12Context):
        try:
            arr = []
            temp = ctx
            while type(temp) != 'gen.JavaParserLabeled.JavaParserLabeled.MethodBodyContext':

                if not hasattr(temp,'parentCtx'):

                    break
                child = temp
                temp = temp.parentCtx

                if not hasattr(temp, 'start'):
                    continue


                if not hasattr(temp,'children'):
                    continue
                x=temp.children[0]
                if len(temp.children)>=5:
                    if child.getText() == temp.children[4].getText():
                        y = temp.children[3]
                        if y.getText() in self.symbols:

                            if hasattr(y, 'symbol'):
                                if y.symbol in self.cycle:
                                    continue
                                arr.append(y.symbol)
                                if arr[0].text != 'if':
                                    return
                                self.count += 1
                                self.cycle.append(y.symbol)
                                continue


                if x.getText() in self.symbols:

                    if hasattr(x, 'symbol'):
                        if x.symbol in self.cycle:
                            continue
                        arr.append(x.symbol)
                        if arr[0].text != 'if':
                            return
                        self.count += 1
                        self.cycle.append(x.symbol)
                        continue
                if not hasattr(x,'children'):
                    continue
                if x.children[0].getText() in self.symbols:

                    if hasattr(x.children[0], 'symbol'):
                        if x.children[0].symbol in self.cycle:
                            continue
                        arr.append(x.children[0].symbol)
                        if arr[0].text != 'if':
                            return
                        self.count += 1
                        self.cycle.append(x.children[0].symbol)
                        continue
        except:
            pass

    def enterMethodDeclaration(self, ctx:JavaParserLabeled.MethodDeclarationContext):
        try:
            self.methods+=1
        except:
            pass        

    def exitClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        try:
            self.avg = self.count / self.methods
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

    with open('Results.txt', 'a') as f:
        f.write(f"Average Cyclomatic Essential:{my_listener.get_dict}")
        f.write('\n')


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