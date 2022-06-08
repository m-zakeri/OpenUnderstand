import os
from antlr4 import *
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener

PRJ_INDEX = 0
REF_NAME = "import"


def get_project_info(index):
    project_names = [
        'calculator_app',
        'JSON',
        'testing_legacy_code',
        'jhotdraw-develop',
        'xerces2j',
        'jvlt-1.3.2',
        'jfreechart',
        'ganttproject',
        '105_freemind',
    ]
    project_name = project_names[index]
    project_path = f"../../../benchmarks/{project_name}"

    project_path = os.path.abspath(project_path)

    return {
        'PROJECT_NAME': project_name,
        'PROJECT_PATH': project_path,
    }


def get_parse_tree(file_path):
    file = FileStream(file_path, encoding="utf-8")
    lexer = JavaLexer(file)
    tokens = CommonTokenStream(lexer)
    parser = JavaParserLabeled(tokens)
    return parser.compilationUnit()


class Project:
    def __init__(self, project_dir, project_name=None):
        self.project_dir = project_dir
        self.project_name = project_name
        self.files = []

    def get_java_files(self):
        for dir_path, _, file_names in os.walk(self.project_dir):
            for file in file_names:
                if '.java' in str(file):
                    path = os.path.join(dir_path, file)
                    path = path.replace("/", "\\")
                    path = os.path.abspath(path)
                    self.files.append((file, path))


class CyclomaticComplexityListener(JavaParserLabeledListener):
    def __init__(self):
        pass

    # if, else
    def enterStatement2(self, ctx: JavaParserLabeled.Statement2Context):
        pass

    # for
    def enterStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        pass

    # while
    def enterStatement4(self, ctx: JavaParserLabeled.Statement4Context):
        pass

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        pass

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        pass

    def enterConstructorDeclaration(self, ctx: JavaParserLabeled.ConstructorDeclarationContext):
        pass

    def enterEnumDeclaration(self, ctx: JavaParserLabeled.EnumDeclarationContext):
        pass


def main():
    info = get_project_info(PRJ_INDEX)
    p = Project(info['PROJECT_PATH'], info['PROJECT_NAME'])
    p.get_java_files()

    for file_name, file_path in p.files:
        tree = get_parse_tree(file_path)
        listener = CyclomaticComplexityListener()
        walker = ParseTreeWalker()
        walker.walk(listener, tree)


if __name__ == '__main__':
    main()
