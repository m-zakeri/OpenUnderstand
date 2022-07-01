import os
from antlr4 import *
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled


# Common Helper Functions

class Project:
    def __init__(self, project_dir, project_name=None):
        self.project_dir = project_dir
        self.project_name = project_name
        self.files = []

    def get_java_files(self):
        for dir_path, _, file_names in os.walk(self.project_dir):
            for file in file_names:
                lowercase_file = str(file).lower()
                if lowercase_file.endswith('.java'):
                    path = os.path.join(dir_path, file)
                    path = path.replace("/", "\\")
                    path = os.path.abspath(path)
                    self.files.append((file, path))


def get_project_info(index, ref_name=None):
    project_names = [
        'calculator_app',       # 0
        'JSON',                 # 1
        'testing_legacy_code',  # 2
        'TheAlgorithms',        # 3*
        'jhotdraw-develop',     # 4
        'xerces2j',             # 5
        'jvlt-1.3.2',           # 6
        'jfreechart',           # 7
        'ganttproject',         # 8*
        '105_freemind',         # 9*
        'custom'                # 10
    ]
    project_name = project_names[index]
    db_path = f"../../../databases/{ref_name}/{project_name}"
    if ref_name == "origin":
        db_path = db_path + ".udb"
    else:
        db_path = db_path + ".oudb"
    project_path = f"../../../benchmarks/{project_name}"

    db_path = os.path.abspath(db_path)
    project_path = os.path.abspath(project_path)

    return {
        'PROJECT_NAME': project_name,
        'DB_PATH': db_path,
        'PROJECT_PATH': project_path,
    }


def get_parse_tree(file_path):
    file = FileStream(file_path, encoding="utf-8")
    lexer = JavaLexer(file)
    tokens = CommonTokenStream(lexer)
    parser = JavaParserLabeled(tokens)
    return parser.compilationUnit()


def get_parent(parent_file_name, files):
    file_names, file_paths = zip(*files)
    parent_file_index = file_names.index(parent_file_name)
    parent_file_path = file_paths[parent_file_index]
    return parent_file_path


# Prefix producers

def get_class_prefixes(ctx, ctx_type):
    branches = ctx.parentCtx.children
    prefixes = ""
    for branch in branches:
        if type(branch).__name__ == ctx_type:
            break
        prefixes += branch.getText() + " "
    return prefixes


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


# Cyclomatic Helper Functions

def report_cyclomatic(project_cyclomatic, ent_kind_set, cyclomatic_list):
    sorted_cyclomatic_list = sorted(cyclomatic_list, key=lambda d: (d['cyclomatic'], d['name']))
    for e in sorted_cyclomatic_list:
        print({
            'val': e['cyclomatic'],
            'name': e['name'],
            'kind': e['kind'],
            # 'ln': e['longname']
        })
    print("-" * 25)

    print(f"Entities with cyclomatic: {len(ent_kind_set)}")
    for i in sorted(ent_kind_set):
        print(i)
    print("-" * 25)

    print("Project Cyclomatic Summary")
    print(f"Project total cyclomatic: {project_cyclomatic}")


# Scope makers

def make_scope_interface(ctx):
    prefixes = get_class_prefixes(ctx, "InterfaceDeclarationContext")
    kind_name = get_kind_name(prefixes, kind="Class")
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


def make_scope_Lambda(ctx):
    prefixes = get_class_prefixes(ctx, "LambdaExpressionContext")
    kind_name = get_kind_name(prefixes, kind="Class", is_lambda=True)
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


def make_scope_class(ctx):
    prefixes = get_class_prefixes(ctx, "ClassDeclarationContext")
    kind_name = get_kind_name(prefixes, kind="Class")
    class_name = ctx.children[1].getText()
    return_type = ctx.children[0].getText()
    access_type = ctx.parentCtx.parentCtx.children[0].getText()
    static_type = ''
    if len(ctx.parentCtx.parentCtx.children) > 1:
        if ctx.parentCtx.parentCtx.children[1].getText() == 'static':
            static_type = ctx.parentCtx.parentCtx.children[1].getText()
    return {
        'kind_name': kind_name,
        'method_name': class_name,
        'return_type': return_type,
        'access_type': access_type,
        'static_type': static_type
    }


def make_scope_method(ctx):
    prefixes = get_method_prefixes(ctx)
    kind_name = get_kind_name(prefixes, kind="Method")
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


def make_scope_constructor(ctx):
    prefixes = get_method_prefixes(ctx)
    kind_name = get_kind_name(prefixes, kind="Method", is_constructor=True)
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


# Scope finders

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


def find_scope(ctx):
    scope = []
    if str(ctx.children[0]) == 'package':
        return [{
            'kind_name': 'Java Package',
            'method_name': ctx.children[1].getText(),
            'return_type': '',
            'access_type': '',
            'static_type': ''
        }]
    scope_ctx = search_scope(ctx, ["ClassDeclarationContext", "MethodDeclarationContext",
                                   "InterfaceDeclarationContext", "AnnotationTypeDeclarationContext",
                                   "ConstructorDeclarationContext", "LambdaExpressionContext"])
    for item in scope_ctx:
        if type(item).__name__ == "ClassDeclarationContext":
            scope.append(make_scope_class(item))
        elif type(item).__name__ == "ConstructorDeclarationContext":
            scope.append(make_scope_constructor(item))
        elif type(item).__name__ == "MethodDeclarationContext":
            scope.append(make_scope_method(item))
        elif type(item).__name__ == "InterfaceDeclarationContext":
            scope.append(make_scope_interface(item))
        elif type(ctx).__name__ == "LambdaExpressionContext":
            scope.append(make_scope_lambda(item))
    return scope


def get_kind_name(prefixes, kind, is_constructor=False, is_lambda=False):
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

    if is_constructor:
        s = f"Java Method Constructor Member {p_visibility}"
        s = " ".join(s.split())
        return s

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

    elif is_lambda:
        s = f"Java Method Lambda"
        s = " ".join(s.split())
        return s

    s = f"Java {p_static} {p_abstract} {p_generic} {kind} {p_type} {p_visibility} {p_member}"
    s = " ".join(s.split())
    return s
