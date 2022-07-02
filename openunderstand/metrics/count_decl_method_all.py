import os
from oudb.api import open
from oudb.models import EntityModel, KindModel
from antlr4 import *
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaLexer import JavaLexer
from analysis_passes.extend_listener_g6 import ExtendListener


def Walk(reference_listener, parse_tree):
    walker = ParseTreeWalker()
    walker.walk(listener=reference_listener, t=parse_tree)

def count_decl_method_all(dbname):
    open(dbname)
    class_methods = {}
    files = []
    extends_class_names = {}
    # get files names
    for ent_model in EntityModel.select():
        if ent_model._kind_id == 1:
            files.append(ent_model._longname)
        if "Class" in ent_model._kind._name:
            class_methods[ent_model._name]=0


    # get parent names
    for file_address in files:
        try:
            file_stream = FileStream(file_address, encoding='utf8')
            lexer = JavaLexer(file_stream)
            tokens = CommonTokenStream(lexer)
            parser = JavaParserLabeled(tokens)
            parse_tree = parser.compilationUnit();
        except Exception as e:
            print("An Error occurred in file:" + file_address + "\n" + str(e))
            continue
        try:
            listener = ExtendListener()
            Walk(listener,parse_tree)
            extends_class_names.update(listener.get_refers())
        except Exception as e:
            print("An Error occurred for reference implement in file:" + file_address + "\n" + str(e))


        # get class methods number
    for ent_model in EntityModel.select():

        if "Method" in ent_model._kind._name:
            exists = class_methods.get(ent_model._parent._name, -1)
            if exists == -1:
                class_methods[ent_model._parent._name] = 1
            else:
                class_methods[ent_model._parent._name] += 1

    for cm in class_methods:
        stack=[]
        visited=[]
        temp = cm
        while extends_class_names.__contains__(temp):
            for t in extends_class_names[temp]:
                if not visited.__contains__(t):
                    stack.append(t)
                    visited.append(t)
            temp = stack.pop()
        for v in visited:
            class_methods[cm] += class_methods[v]


    return class_methods


if __name__ == '__main__':
    print(count_decl_method_all("../../benchmark2_database.oudb"))
