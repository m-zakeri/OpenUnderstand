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

    return {
        'PROJECT_NAME': project_name,
        'PROJECT_PATH': project_path,
    }


class StatementListener(JavaParserLabeledListener):
    def __init__(self, files):
        self.repository = {'Java Package': 0,
                           'Java Import': 0}
        self.files = files
        self.counter = 0

    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        self.repository['Java Package'] += 1
        self.counter += 1

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        self.repository['Java Import'] += 1
        self.counter += 1

    def enterStatement15(self, ctx: JavaParserLabeled.Statement15Context):
        self.update_repository(ctx, 1)

    def enterAnnotationMethodOrConstantRest0(self, ctx: JavaParserLabeled.AnnotationMethodOrConstantRest0Context):
        self.update_repository(ctx, 1)

    def enterLocalVariableDeclaration(self, ctx: JavaParserLabeled.LocalVariableDeclarationContext):
        self.update_repository(ctx, 1)

    def enterInterfaceMethodDeclaration(self, ctx: JavaParserLabeled.InterfaceMethodDeclarationContext):
        self.update_repository(ctx, 1)

    def enterFieldDeclaration(self, ctx: JavaParserLabeled.FieldDeclarationContext):
        self.update_repository(ctx, 1)

    def enterStatement10(self, ctx: JavaParserLabeled.Statement10Context):
        self.update_repository(ctx, 1)

    def enterStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        self.update_repository(ctx, 3)

    def update_repository(self, ctx, increment):
        self.counter += increment
        res = self.find_scope(ctx)
        if res in self.repository:
            self.repository[res] += increment
        else:
            new_dict = {res: 0}
            new_dict[res] += increment
            self.repository.update(new_dict)

    @staticmethod
    def search_scope(ctx, type_names):
        # Traverse bottom up until reaching a class or method
        current = ctx.parentCtx
        while current is not None:
            type_name = type(current).__name__
            if type_name in type_names:
                return current
            current = current.parentCtx
        return None

    @staticmethod
    def get_prefixes(ctx, ctx_type):
        branches = ctx.parentCtx.children
        prefixes = ""
        for branch in branches:
            if type(branch).__name__ == ctx_type:
                break
            prefixes += branch.getText() + " "
        return prefixes

    @staticmethod
    def get_kind_name(prefixes, kind):
        p_static = ""
        p_abstract = ""
        p_generic = ""
        p_type = "Type"
        p_visibility = "Default"
        p_member = "Member"

        if "static" in prefixes:
            p_static = "Static"

        if "generic" in prefixes:
            p_generic = "Generic"

        if "abstract" in prefixes:
            p_abstract = "Abstract"
        elif "final" in prefixes:
            p_abstract = "Final"

        if "private" in prefixes:
            p_visibility = "Private"
        elif "public" in prefixes:
            p_visibility = "Public"
        elif "protected" in prefixes:
            p_visibility = "Protected"

        if kind == "Interface":
            p_member = ""

        if kind == "Method":
            p_type = ""

        s = f"Java {p_static} {p_abstract} {p_generic} {kind} {p_type} {p_visibility} {p_member}"
        s = " ".join(s.split())
        return s

    def make_scope_class(self, ctx):
        prefixes = self.get_prefixes(ctx, "ClassDeclarationContext")
        kind_name = self.get_kind_name(prefixes, kind="Class")
        return kind_name

    def make_scope_method(self, ctx):
        prefixes = self.get_prefixes(ctx, "MethodDeclarationContext")
        kind_name = self.get_kind_name(prefixes, kind="Method")
        return kind_name

    def make_scope_interface(self, ctx):
        prefixes = self.get_prefixes(ctx, "InterfaceDeclarationContext")
        kind_name = self.get_kind_name(prefixes, kind="Interface")
        return kind_name

    def make_scope_annotation(self, ctx):
        prefixes = self.get_prefixes(ctx, "AnnotationTypeDeclarationContext")
        kind_name = self.get_kind_name(prefixes, kind="Annotation")
        return kind_name

    def find_scope(self, ctx):
        scope = None
        scope_ctx = self.search_scope(ctx, ["ClassDeclarationContext", "MethodDeclarationContext",
                                            "InterfaceDeclarationContext", "AnnotationTypeDeclarationContext"])
        if type(scope_ctx).__name__ == "ClassDeclarationContext":
            scope = self.make_scope_class(scope_ctx)
        elif type(scope_ctx).__name__ == "MethodDeclarationContext":
            scope = self.make_scope_method(scope_ctx)
        elif type(scope_ctx).__name__ == "InterfaceDeclarationContext":
            scope = self.make_scope_interface(scope_ctx)
        elif type(scope_ctx).__name__ == "AnnotationTypeDeclarationContext":
            scope = self.make_scope_annotation(scope_ctx)
        return scope


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
        print(file_name)
        print(listener.counter)
        print(listener.repository)
        print('-' * 25)


if __name__ == '__main__':
    main()
