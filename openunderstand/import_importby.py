import os
from antlr4 import *
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from oudb.fill import main as db_fill
from oudb.api import create_db, open as db_open
from oudb.models import EntityModel, ReferenceModel

PRJ_INDEX = 1
REF_NAME = "import"


def get_project_info(index, ref_name):
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
    db_path = f"../../databases/{ref_name}/{project_name}"
    if ref_name == "origin":
        db_path = db_path + ".udb"
    else:
        db_path = db_path + ".oudb"
    project_path = f"../../benchmarks/{project_name}"

    return {
        'PROJECT_NAME': project_name,
        'DB_PATH': db_path,
        'PROJECT_PATH': project_path,
    }


class Project:
    def __init__(self, db_name, project_dir, project_name=None):
        self.db_name = db_name
        self.project_dir = project_dir
        self.project_name = project_name
        self.files = []

    def init_db(self):
        create_db(self.db_name, self.project_dir, self.project_name)
        db_fill()
        db_open(self.db_name)

    def get_java_files(self, add_to_db=True):
        for dir_path, _, file_names in os.walk(self.project_dir):
            for file in file_names:
                if '.java' in str(file):
                    path = os.path.join(dir_path, file)
                    path = path.replace("/", "\\")
                    self.files.append((file, path))
                    if add_to_db:
                        add_java_file_entity(path, file)


class ClassEntityListener(JavaParserLabeledListener):
    def __init__(self):
        self.class_body = None

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        self.class_body = ctx.getText()


class ImportListener(JavaParserLabeledListener):
    def __init__(self, files):
        self.repository = []
        self.files = files

    def enterImportDeclaration(self, ctx: JavaParserLabeled.CompilationUnitContext):
        imported_class_longname = ctx.qualifiedName().getText()
        imported_class_name = imported_class_longname.split('.')[-1]

        is_built_in = False
        imported_class_file_name = imported_class_name + ".java"
        if imported_class_file_name not in [file[0] for file in self.files]:
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


def get_parent(parent_file_name, files):
    file_names, file_paths = zip(*files)
    parent_file_index = file_names.index(parent_file_name)
    parent_file_path = file_paths[parent_file_index]
    parent_entity = EntityModel.get_or_none(
        _kind=1,  # Java File
        _name=parent_file_name,
        _longname=parent_file_path,
    )
    return parent_entity, parent_file_path


def imported_entity_factory(i, files):
    if i['is_built_in']:
        imported_entity, _ = EntityModel.get_or_create(
            _kind=84,  # Java Unknown Class Type Member
            _parent=None,
            _name=i['imported_class_name'],
            _longname=i['imported_class_longname'],
        )
    else:
        parent_entity, parent_file_path = get_parent(i['imported_class_file_name'], files)
        imported_entity, _ = EntityModel.get_or_create(
            _kind=98,  # Java Class Type Public Member
            _parent=parent_entity.get_id(),
            _name=i['imported_class_name'],
            _longname=i['imported_class_longname'],
            _contents=get_class_body(parent_file_path),
        )
    return imported_entity


def add_java_file_entity(file_path, file_name):
    kind_id = 1  # Java File
    obj, _ = EntityModel.get_or_create(
        _kind=kind_id,
        _name=file_name,
        _longname=file_path,
        _contents=FileStream(file_path, encoding="utf-8"),
    )
    return obj


def add_references(importing_ent, imported_ent, ref_dict):
    ref, _ = ReferenceModel.get_or_create(
        _kind=206,  # Java Import
        _file=importing_ent.get_id(),
        _line=ref_dict['line'],
        _column=ref_dict['column'],
        _ent=imported_ent.get_id(),
        _scope=importing_ent.get_id(),
    )
    inverse_ref, _ = ReferenceModel.get_or_create(
        _kind=207,  # Java Importby
        _file=importing_ent.get_id(),
        _line=ref_dict['line'],
        _column=ref_dict['column'],
        _ent=importing_ent.get_id(),
        _scope=imported_ent.get_id(),
    )


def get_class_body(file_path):
    tree = get_parse_tree(file_path)
    listener = ClassEntityListener()
    walker = ParseTreeWalker()
    walker.walk(listener=listener, t=tree)
    return listener.class_body


def main():
    info = get_project_info(PRJ_INDEX, REF_NAME)
    p = Project(info['DB_PATH'], info['PROJECT_PATH'], info['PROJECT_NAME'])
    p.init_db()
    p.get_java_files()

    for file_name, file_path in p.files:
        importing_entity = add_java_file_entity(file_path, file_name)

        tree = get_parse_tree(file_path)
        listener = ImportListener(p.files)
        walker = ParseTreeWalker()
        walker.walk(listener, tree)

        for i in listener.repository:
            imported_entity = imported_entity_factory(i, p.files)
            add_references(importing_entity, imported_entity, i)


if __name__ == '__main__':
    main()
