import os
from antlr4 import *
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


PRJ_INDEX = 0


def get_parse_tree(file_path):
    file = FileStream(file_path, encoding="utf-8")
    lexer = JavaLexer(file)
    tokens = CommonTokenStream(lexer)
    parser = JavaParserLabeled(tokens)
    return parser.compilationUnit()


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


class StatementListener(JavaParserLabeledListener):
    def __init__(self, files):
        self.repository = []
        self.files = files
        self.counter = 0

    def enterPackageDeclaration(self, ctx:JavaParserLabeled.PackageDeclarationContext):
        line = ctx.children[0].symbol.line
        self.counter += 1
        self.save_result(line)

    def enterImportDeclaration(self, ctx:JavaParserLabeled.ImportDeclarationContext):
        line = ctx.children[0].symbol.line
        self.counter += 1
        self.save_result(line)

    def enterStatement15(self, ctx:JavaParserLabeled.Statement15Context):
        line = ctx.children[0].symbol.line
        self.counter += 1
        self.save_result(line)

    def enterLocalVariableDeclaration(self, ctx: JavaParserLabeled.LocalVariableDeclarationContext):
        line = ctx.children[0].symbol.line
        self.counter += 1
        self.save_result(line)

    def save_result(self, line):
        self.repository.append({
            'line': line,
        })


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


def main():
    info = get_project_info(PRJ_INDEX)
    p = Project(info['PROJECT_PATH'], info['PROJECT_NAME'])
    p.get_java_files()

    for file_name, file_path in p.files:
        tree = get_parse_tree(file_path)
        listener = StatementListener(p.files)
        walker = ParseTreeWalker()
        walker.walk(listener, tree)

        for i in listener.repository:
            print(i)


if __name__ == '__main__':
    main()
