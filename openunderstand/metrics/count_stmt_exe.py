import os
import sys
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from utils_g10 import get_keys, stmt_main

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)


PRJ_INDEX = 0
METRIC_NAME = 'CountStmtExe'


class StatementListener(JavaParserLabeledListener):
    def __init__(self, files):
        self.repository = {'$$$Java Import-': 0}
        self.files = files
        self.counter = 0

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.update_repository(ctx, 1)

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        self.repository['$$$Java Import-'] += 1
        self.counter += 1

    def enterAnnotationMethodOrConstantRest0(self, ctx: JavaParserLabeled.AnnotationMethodOrConstantRest0Context):
        self.update_repository(ctx, 1)

    def enterInterfaceMethodDeclaration(self, ctx: JavaParserLabeled.InterfaceMethodDeclarationContext):
        self.update_repository(ctx, 1)

    # return
    def enterStatement10(self, ctx: JavaParserLabeled.Statement10Context):
        self.update_repository(ctx, 1)

    # for
    def enterStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        self.update_repository(ctx, 2)

    # break
    def enterStatement12(self, ctx: JavaParserLabeled.Statement12Context):
        self.update_repository(ctx, 1)

    # throw
    def enterStatement11(self, ctx: JavaParserLabeled.Statement11Context):
        self.update_repository(ctx, 1)

    # continue
    def enterStatement13(self, ctx: JavaParserLabeled.Statement13Context):
        self.update_repository(ctx, 1)

    def update_repository(self, ctx, increment):
        self.counter += increment
        keys = get_keys(ctx)
        for key in keys:
            if key in self.repository:
                self.repository[key] += increment
            else:
                new_dict = {key: 0}
                new_dict[key] += increment
                self.repository.update(new_dict)


if __name__ == '__main__':
    stmt_main(PRJ_INDEX, StatementListener, METRIC_NAME)
