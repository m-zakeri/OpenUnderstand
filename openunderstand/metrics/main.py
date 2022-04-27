from antlr4 import *
from openunderstand.gen.javaLabeled.JavaLexer import JavaLexer
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from metric import DSCmetric
from pathlib import Path
import argparse
import os.path
import json


def main(args):
    stream = FileStream(args.file, encoding='utf8')
    lexer = JavaLexer(stream)
    token_stream = CommonTokenStream(lexer)
    parser = JavaParserLabeled(token_stream)
    parse_tree = parser.compilationUnit()

    my_listener = DSCmetric()

    walker = ParseTreeWalker()
    walker.walk(t=parse_tree, listener=my_listener)

    res2 = my_listener.get_arr
    res3 = my_listener.get_tmp
    print(res2, res3)
    print("Number of returned variables:"+str(len(res3))+"\n")


if __name__ == '__main__':
    inp = str(input("Enter the path to the Java project:"))
    # C:\Users\Roozbeh\PycharmProjects\pythonProject\Software Metrics

    try:
        dir = os.listdir(inp)

    except:
        print("Invalid Path")

    for dirpath, dirnames, filenames in os.walk(inp):
        for filename in [f for f in filenames if f.endswith(".java")]:
            argparser = argparse.ArgumentParser()
            print(filename)
            argparser.add_argument(
                '-n', '--file',
                help='Input source', default=os.path.join(dirpath, filename))
            args = argparser.parse_args()
            main(args)
