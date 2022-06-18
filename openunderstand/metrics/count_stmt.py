import os, sys
from antlr4 import *

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)
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
        result = self.find_scope(ctx)
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

    @staticmethod
    def search_scope(ctx, type_names):
        # Traverse bottom up until reaching a class or method
        scope_list = []
        current = ctx.parentCtx
        while current is not None:
            type_name = type(current).__name__
            if type_name in type_names:
                scope_list.append(current)
            current = current.parentCtx
        return scope_list

    @staticmethod
    def get_parent(parent_file_name, files):
        file_names, file_paths = zip(*files)
        parent_file_index = file_names.index(parent_file_name)
        parent_file_path = file_paths[parent_file_index]
        return parent_file_path

    @staticmethod
    def get_class_prefixes(ctx, ctx_type):
        branches = ctx.parentCtx.children
        prefixes = ""
        for branch in branches:
            if type(branch).__name__ == ctx_type:
                break
            prefixes += branch.getText() + " "
        return prefixes

    @staticmethod
    def get_method_prefixes(ctx):
        access_branches = ctx.parentCtx.parentCtx.children
        type_branches = ctx.children
        prefixes = []

        for branch in access_branches:
            if type(branch).__name__ == "ModifierContext":
                prefixes.append(branch.getText())

        for branch in type_branches:
            if type(branch).__name__ == "TypeTypeOrVoidContext":
                prefixes.append(branch.getText())

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
        prefixes = self.get_class_prefixes(ctx, "ClassDeclarationContext")
        kind_name = self.get_kind_name(prefixes, kind="Class")
        class_name = ctx.children[1]
        return_type = ctx.children[0].getText()
        access_type = ctx.parentCtx.parentCtx.children[0].getText()
        if ctx.parentCtx.parentCtx.children[1].getText() == 'static':
            static_type = ctx.parentCtx.parentCtx.children[1].getText()
        else:
            static_type = ''
        return {
            'kind_name': kind_name,
            'method_name': class_name,
            'return_type': return_type,
            'access_type': access_type,
            'static_type': static_type
        }

    def make_scope_method(self, ctx):
        prefixes = self.get_method_prefixes(ctx)
        kind_name = self.get_kind_name(prefixes, kind="Method")
        method_name = ctx.children[1]
        return_type = ctx.children[0].getText()
        access_type = ctx.parentCtx.parentCtx.children[0].getText()
        static_type = ''
        if len(ctx.parentCtx.parentCtx.children) > 1:
            if ctx.parentCtx.parentCtx.children[1].getText() == 'static':
                static_type = ctx.parentCtx.parentCtx.children[1].getText()
        return {
            'kind_name': kind_name,
            'method_name': method_name,
            'return_type': return_type,
            'access_type': access_type,
            'static_type': static_type
        }

    def make_scope_interface(self, ctx):
        prefixes = self.get_class_prefixes(ctx, "InterfaceDeclarationContext")
        kind_name = self.get_kind_name(prefixes, kind="Class")
        class_name = ctx.children[1]
        return_type = ctx.children[0].getText()
        access_type = ctx.parentCtx.parentCtx.children[0].getText()
        if ctx.parentCtx.parentCtx.children[1].getText() == 'static':
            static_type = ctx.parentCtx.parentCtx.children[1].getText()
        else:
            static_type = ''
        return {
            'kind_name': kind_name,
            'method_name': class_name,
            'return_type': return_type,
            'access_type': access_type,
            'static_type': static_type
        }

    def make_scope_annotation(self, ctx):
        prefixes = self.get_class_prefixes(ctx, "AnnotationTypeDeclarationContext")
        kind_name = self.get_kind_name(prefixes, kind="Class")
        class_name = ctx.children[1]
        return_type = ctx.children[0].getText()
        access_type = ctx.parentCtx.parentCtx.children[0].getText()
        if ctx.parentCtx.parentCtx.children[1].getText() == 'static':
            static_type = ctx.parentCtx.parentCtx.children[1].getText()
        else:
            static_type = ''
        return {
            'kind_name': kind_name,
            'method_name': class_name,
            'return_type': return_type,
            'access_type': access_type,
            'static_type': static_type
        }

    def find_scope(self, ctx):
        scope = []
        if str(ctx.children[0]) == 'package':
            return[{
                'kind_name': 'Java Package',
                'method_name': ctx.children[1].getText(),
                'return_type': '',
                'access_type': '',
                'static_type': ''
            }]
        scope_ctx = self.search_scope(ctx, ["ClassDeclarationContext", "MethodDeclarationContext",
                                            "InterfaceDeclarationContext", "AnnotationTypeDeclarationContext"])
        for item in scope_ctx:
            if type(item).__name__ == "ClassDeclarationContext":
                scope.append(self.make_scope_class(item))
            elif type(item).__name__ == "MethodDeclarationContext":
                scope.append(self.make_scope_method(item))
            elif type(item).__name__ == "InterfaceDeclarationContext":
                scope.append(self.make_scope_interface(item))
            elif type(item).__name__ == "AnnotationTypeDeclarationContext":
                scope.append(self.make_scope_annotation(item))
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
