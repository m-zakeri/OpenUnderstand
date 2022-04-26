import os
from antlr4 import *
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from oudb.fill import main as db_fill
from oudb.api import create_db, open as db_open
from oudb.models import KindModel, EntityModel, ReferenceModel

PRJ_INDEX = 4
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
DB_PATH = f"../../databases/import/{PROJECT_NAME}.oudb"
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

    def imported_entity_factory(self, i):
        if i['is_built_in']:
            imported_entity, _ = EntityModel.get_or_create(
                _kind=KindModel.get_or_none(_name="Java Unknown Class Type Member")._id,
                _parent=None,
                _name=i['imported_class_name'],
                _longname=i['imported_class_longname'],
            )
        else:
            parent_entity = self.get_parent(i['imported_class_file_name'])
            imported_entity, _ = EntityModel.get_or_create(
                _kind=KindModel.get_or_none(_name="Java Class Type Public Member")._id,
                _parent=parent_entity._id,
                _name=i['imported_class_name'],
                _longname=i['imported_class_longname'],
                _contents=get_class_body(parent_entity._longname),
            )
        return imported_entity


class ClassEntityListener(JavaParserLabeledListener):
    def __init__(self):
        self.class_body = None

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.class_body = ctx.getText()


class ImportListener(JavaParserLabeledListener):
    def __init__(self, file_names):
        self.repository = []
        self.file_names = file_names

    def enterImportDeclaration(self, ctx: JavaParserLabeled.CompilationUnitContext):
        imported_class_longname = ctx.qualifiedName().getText()
        imported_class_name = imported_class_longname.split('.')[-1]

        is_built_in = False
        imported_class_file_name = imported_class_name + ".java"
        if imported_class_file_name not in self.file_names:
            is_built_in = True
            imported_class_file_name = None

        line = ctx.children[0].symbol.line
        col = ctx.children[0].symbol.column

        self.repository.append({
            'imported_class_name': imported_class_name,
            'imported_class_longname': imported_class_longname,
            'is_built_in': is_built_in,
            'imported_class_file_name': imported_class_file_name,
            'line': line,
            'column': col,
        })


def get_parse_tree(file_path):
    file = FileStream(file_path, encoding="utf-8")
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
        _contents=FileStream(file_path, encoding="utf-8"),
    )
    return obj


def add_references(importing_ent, imported_ent, ref_dict):
    ref, _ = ReferenceModel.get_or_create(
        _kind=KindModel.get_or_none(_name="Java Import")._id,
        _file=importing_ent._id,
        _line=ref_dict['line'],
        _column=ref_dict['column'],
        _ent=imported_ent._id,
        _scope=importing_ent._id,
    )
    inverse_ref, _ = ReferenceModel.get_or_create(
        _kind=KindModel.get_or_none(_name="Java Importby")._id,
        _file=importing_ent._id,
        _line=ref_dict['line'],
        _column=ref_dict['column'],
        _ent=importing_ent._id,
        _scope=imported_ent._id,
    )


def get_class_body(file_path):
    tree = get_parse_tree(file_path)
    listener = ClassEntityListener()
    walker = ParseTreeWalker()
    walker.walk(listener=listener, t=tree)
    return listener.class_body


def main():
    p = Project(DB_PATH, PROJECT_PATH, PROJECT_NAME)
    p.init_db()
    p.get_java_files()
    for file_path, file_name in zip(p.file_paths, p.file_names):
        importing_entity = add_java_file_entity(file_path, file_name)

        tree = get_parse_tree(file_path)
        listener = ImportListener(p.file_names)
        walker = ParseTreeWalker()
        walker.walk(listener, tree)

        for i in listener.repository:
            imported_entity = p.imported_entity_factory(i)
            add_references(importing_entity, imported_entity, i)


if __name__ == '__main__':
    main()
