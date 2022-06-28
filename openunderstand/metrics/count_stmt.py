import os
import sys
from antlr4 import *
from utils_g10 import Project, get_project_info, get_parse_tree, find_scope
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)


PRJ_INDEX = 0


class StatementListener(JavaParserLabeledListener):
    def __init__(self, files):
        self.repository = {'Java Import': 0}
        self.files = files
        self.counter = 0

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.update_repository(ctx, 1)

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        self.repository['Java Import'] += 1
        self.counter += 1

    def enterAnnotationMethodOrConstantRest0(self, ctx: JavaParserLabeled.AnnotationMethodOrConstantRest0Context):
        self.update_repository(ctx, 1)

    def enterLocalVariableDeclaration(self, ctx: JavaParserLabeled.LocalVariableDeclarationContext):
        self.update_repository(ctx, 1)

    def enterInterfaceMethodDeclaration(self, ctx: JavaParserLabeled.InterfaceMethodDeclarationContext):
        self.update_repository(ctx, 1)

    def enterFieldDeclaration(self, ctx: JavaParserLabeled.FieldDeclarationContext):
        self.update_repository(ctx, 1)

    # return
    def enterStatement10(self, ctx: JavaParserLabeled.Statement10Context):
        self.update_repository(ctx, 1)

    # for
    def enterStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        self.update_repository(ctx, 3)
        for i in ctx.children:
            if i == ';':
                self.update_repository(ctx, 1)

    # break
    def enterStatement12(self, ctx: JavaParserLabeled.Statement12Context):
        self.update_repository(ctx, 1)
        
    # throw
    def enterStatement11(self, ctx: JavaParserLabeled.Statement11Context):
        self.update_repository(ctx, 1)

    # continue
    def enterStatement13(self, ctx: JavaParserLabeled.Statement13Context):
        self.update_repository(ctx, 1)

    def enterStatement14(self, ctx: JavaParserLabeled.Statement14Context):
        self.update_repository(ctx, 1)

    # call
    def enterStatement15(self, ctx: JavaParserLabeled.Statement15Context):
        self.update_repository(ctx, 1)

    def update_repository(self, ctx, increment):
        self.counter += increment
        result = find_scope(ctx)
        for res in result:
            if res['kind_name'] == "Java Package":
                key = str(res['kind_name']) + '-' + str(res['method_name'])
            elif res['static_type'] != '':
                key = str(res['kind_name']) + '-' + str(res['access_type']) + ' ' + str(res['static_type']) + ' ' \
                    + str(res['return_type']) + ' ' + str(res['method_name'])
            else:
                key = str(res['kind_name']) + '-' + str(res['access_type']) + ' ' \
                    + str(res['return_type']) + ' ' + str(res['method_name'])
            if key in self.repository:
                self.repository[key] += increment
            else:
                new_dict = {key: 0}
                new_dict[key] += increment
                self.repository.update(new_dict)


def main():
    info = get_project_info(PRJ_INDEX)
    p = Project(info['PROJECT_PATH'], info['PROJECT_NAME'])
    p.get_java_files()
    for file_name, file_path in p.files:
        tree = get_parse_tree(file_path)
        listener = StatementListener(p.files)
        walker = ParseTreeWalker()
        walker.walk(listener, tree)
        print('Java File')
        print(file_name)
        print(file_path)
        print(listener.counter)
        print('-' * 20)
        for item in listener.repository:
            key = item.split('-')
            if key[0] == 'Java Import':
                continue
            print(key[0])
            print(key[1])
            if key[0] == 'Java Package':
                print(listener.counter)
            else:
                print(listener.repository[item])
            print('-' * 20)
        print('\n!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n')


if __name__ == '__main__':
    main()
