import os
from antlr4 import *
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from oudb.fill import main as db_fill
from oudb.api import create_db, open as db_open
from oudb.models import KindModel, EntityModel, ReferenceModel

PRJ_INDEX = 0
PROJECTS_NAME = [
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
PROJECT_NAME = PROJECTS_NAME[PRJ_INDEX]
DB_PATH = f"../../databases/modify/{PROJECT_NAME}.oudb"
PROJECT_PATH = f"../../benchmarks/{PROJECT_NAME}"


class Project:
    def __init__(self, db_name, project_dir, project_name=None):
        self.db_name = db_name
        self.project_dir = project_dir
        self.project_name = project_name
        self.file_paths = []
        self.file_names = []

    def init_db(self):
        create_db(self.db_name, self.project_dir, self.project_name)
        db_fill()
        db_open(self.db_name)

    def get_java_files(self):
        for dir_path, _, file_names in os.walk(self.project_dir):
            for file in file_names:
                if '.java' in str(file):
                    path = os.path.join(dir_path, file)
                    path = path.replace("/", "\\")
                    self.file_paths.append(path)
                    self.file_names.append(file)
                    add_java_file_entity(path, file)

    def get_parent(self, parent_file_name):
        parent_file_index = self.file_names.index(parent_file_name)
        parent_file_path = self.file_paths[parent_file_index]
        parent_entity = EntityModel.get_or_none(
            _kind=KindModel.get_or_none(_name="Java File")._id,
            _name=parent_file_name,
            _longname=parent_file_path,
        )
        return parent_entity


class ClassEntityListener(JavaParserLabeledListener):
    def __init__(self):
        self.class_body = None

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.class_body = ctx.getText()


class ModifyListener(JavaParserLabeledListener):
    def __init__(self, file_names):
        self.repository = []
        self.scope = None
        self.scope_info = []
        self.line = None
        self.column = None
        self.file_names = file_names
        self.ent = None

    def make_scope_method(self, current):
        content = current.getText()
        name = current.IDENTIFIER().getText()
        if type(current).__name__ == "MethodDeclarationContext":
            if "static" in current.getText():
                kind = KindModel.get_or_none(_name="Java Static Method Public Member")._id
            else:
                kind = KindModel.get_or_none(_name="Java Method Public Member")._id
        current = current.parentCtx
        while current is not None:
            if type(current).__name__ == "ClassDeclarationContext":
                parent = self.make_scope_class(current)
                break
            current = current.parentCtx
        self.scope_info.append({"parent": parent, "kind": kind, "line": self.line, "column": self.column,
                                "name": name, "content": content, "scope": self.scope})

    def make_scope_class(self, current):
        content = current.getText()
        name = current.IDENTIFIER().getText()
        kind = KindModel.get_or_none(_name="Java Class Type Public Member")._id
        parent = "file"
        return {"parent": parent, "kind": kind, "name": name, "content": content}

    def search_scope(self, ctx):
        current = ctx.parentCtx
        while current is not None:
            if type(current).__name__ == "ClassDeclarationContext" or type(
                    current).__name__ == "MethodDeclarationContext":
                self.scope = current.IDENTIFIER().getText()
                if type(current).__name__ == "ClassDeclarationContext":
                    self.scope_info.append(self.make_scope_class(current))
                elif type(current).__name__ == "MethodDeclarationContext":
                    self.make_scope_method(current)
                return
            current = current.parentCtx
        self.scope = " "

    def enterExpression6(self, ctx: JavaParserLabeled.Expression6Context):
        line_col = str(ctx.children[0].start).split(",")[3][:-1].split(':')
        self.line = line_col[0]
        self.column = line_col[1]
        self.search_scope(ctx)

    def enterExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        operations = ['+=', '-=', '/=', '*=', '&=', '|=', '^=', '%=']
        if ctx.children[1].getText() in operations:
            self.search_scope(ctx)
            line_col = str(ctx.children[0].start).split(",")[3][:-1].split(':')
            self.line = line_col[0]
            self.column = line_col[1]


def create_Entity(name, longname, parent, contents, kind, value, entity_type):
    obj, has_created = EntityModel.get_or_create(_kind=kind,
                                                 _parent=parent,
                                                 _name=name,
                                                 _longname=longname,
                                                 _value=value,
                                                 _type=entity_type,
                                                 _contents=contents
                                                 )
    return obj


def create_Ref(kind, file, line, column, ent, scope):
    obj, has_created = ReferenceModel.get_or_create(_kind=kind,
                                                    _file=file,
                                                    _line=line,
                                                    _column=column,
                                                    _ent=ent,
                                                    _scope=scope
                                                    )
    return obj


def get_parse_tree(file_path):
    file = FileStream(file_path)
    lexer = JavaLexer(file)
    tokens = CommonTokenStream(lexer)
    parser = JavaParserLabeled(tokens)
    return parser.compilationUnit()


def add_java_file_entity(file_path, file_name):
    kind_id = KindModel.get_or_none(_name="Java File")._id
    obj, _ = EntityModel.get_or_create(
        _kind=kind_id,
        _name=file_name,
        _longname=file_path,
        _contents=FileStream(file_path),
    )
    return obj


def add_references(modifying_ent, ref_dict):
    ref, _ = ReferenceModel.get_or_create(
        _kind=KindModel.get_or_none(_name="Java Modify")._id,
        _file=modifying_ent._id,
        _line=ref_dict['line'],
        _column=ref_dict['column'],
        _ent=modifying_ent._id,
        _scope=ref_dict['scope'],
    )
    inverse_ref, _ = ReferenceModel.get_or_create(
        _kind=KindModel.get_or_none(_name="Java Modifyby")._id,
        _file=modifying_ent._id,
        _line=ref_dict['line'],
        _column=ref_dict['column'],
        _ent=ref_dict['scope'],
        _scope=modifying_ent._id,
    )


def main():
    p = Project(DB_PATH, PROJECT_PATH, PROJECT_NAME)
    p.init_db()
    p.get_java_files()
    for file_path, file_name in zip(p.file_paths, p.file_names):
        modifying_entity = add_java_file_entity(file_path, file_name)

        tree = get_parse_tree(file_path)
        listener = ModifyListener(p.file_names)
        walker = ParseTreeWalker()
        walker.walk(listener, tree)
        for i in listener.scope_info:
            add_references(modifying_entity, i)


if __name__ == '__main__':
    main()
