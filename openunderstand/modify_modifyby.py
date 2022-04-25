import os
from antlr4 import *
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from oudb.fill import main as db_fill
from oudb.api import create_db, open as db_open
from oudb.models import KindModel, EntityModel, ReferenceModel


DB_PATH = "../../database/calculator_app_modify.oudb"
PROJECT_PATH = "../../benchmarks_projects/calculator_app"
PROJECT_NAME = "Calculator App"


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
        imported_entity, _ = EntityModel.get_or_create(
            _kind=KindModel.get_or_none(_name="Java Class Type Public Member")._id,
            # _parent=None,
            _name='modified_class_name',
            _longname='modified_class_longname',
        )
        return imported_entity


class ClassEntityListener(JavaParserLabeledListener):
    def __init__(self):
        self.class_body = None

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.class_body = ctx.getText()


class ModifyListener(JavaParserLabeledListener):
    def __init__(self):
        self.repository = []
        self.scopes = []
        self.scope_info = []

    def enterImportDeclaration(self, ctx: JavaParserLabeled.Expression6Context):
        operations = ['+=', '-=', '/=', '*=', '&=', '|=', '^=', '%=']
        line = None
        col = None
        if ctx.children[1].getText() in operations:
            line_col = str(ctx.children[0].start).split(",")[3][:-1].split(':')
            line = line_col[0]
            col = line_col[1]

        self.repository.append({
            'line': line,
            'column': col,
        })


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


def add_references(importing_ent, imported_ent, ref_dict):
    ref, _ = ReferenceModel.get_or_create(
        _kind=KindModel.get_or_none(_name="Java Modify")._id,
        _file=importing_ent._id,
        _line=ref_dict['line'],
        _column=ref_dict['column'],
        _ent=imported_ent._id,
        _scope=importing_ent._id,
    )
    inverse_ref, _ = ReferenceModel.get_or_create(
        _kind=KindModel.get_or_none(_name="Java Modifyby")._id,
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
        listener = ModifyListener()
        walker = ParseTreeWalker()
        walker.walk(listener, tree)
        for i in listener.repository:
            imported_entity = p.imported_entity_factory(i)
            add_references(importing_entity, imported_entity, i)


if __name__ == '__main__':
    main()
