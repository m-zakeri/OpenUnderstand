import os
from antlr4 import *
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.oudb.models import KindModel, EntityModel, ReferenceModel, col_1based
from openunderstand.oudb.models import kind_id
import openunderstand.analysis_passes.class_properties as class_properties

PRJ_INDEX = 8
REF_NAME = "import"


def get_project_info(index, ref_name):
    project_names = [
        "calculator_app",
        "JSON",
        "testing_legacy_code",
        "jhotdraw-develop",
        "xerces2j",
        "jvlt-1.3.2",
        "jfreechart",
        "ganttproject",
        "105_freemind",
    ]
    project_name = project_names[index]
    db_path = f"../databases/{ref_name}/{project_name}"
    if ref_name == "origin":
        db_path = db_path + ".udb"
    else:
        db_path = db_path + ".oudb"
    project_path = f"../benchmark/{project_name}"
    return {
        "PROJECT_NAME": project_name,
        "DB_PATH": db_path,
        "PROJECT_PATH": project_path,
    }


def get_parse_tree(file_path):
    file = FileStream(file_path, encoding="utf-8")
    lexer = JavaLexer(file)
    tokens = CommonTokenStream(lexer)
    parser = JavaParserLabeled(tokens)
    return parser.compilationUnit()


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

    def get_java_files(self):
        for dir_path, _, file_names in os.walk(self.project_dir):
            for file in file_names:
                if ".java" in str(file):
                    path = os.path.join(dir_path, file)
                    self.files.append((file, path))
                    # add java file entity to database
                    # add_java_file_entity(path, file)


class OpenListener(JavaParserLabeledListener):
    def __init__(self, files):
        self.repository = []
        self.files = files

    @staticmethod
    def _qualified_name(ctx):
        """Package-qualified dotted name of a type declaration.

        These three helpers used to return the declaration *signature* --
        "public class print_fail extends X" -- as the entity's longname, so
        nothing this pass created could ever join to the entity the define
        pass created for the same class.
        """
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        return ".".join(parents + [ctx.IDENTIFIER().getText()])

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        class_longname = self._qualified_name(ctx)
        class_name = ctx.IDENTIFIER().getText()
        line = ctx.children[0].symbol.line
        col = ctx.children[0].symbol.column

        self.repository.append(
            {
                "name": class_name,
                "longname": class_longname,
                "line": line,
                "column": col,
                "kind": "Class",
                "body": ctx.getText(),
            }
        )

    def enterEnumDeclaration(self, ctx: JavaParserLabeled.EnumDeclarationContext):
        enum_longname = self._qualified_name(ctx)
        enum_name = enum_longname.split(".")[-1]
        line = ctx.children[0].symbol.line
        col = ctx.children[0].symbol.column

        self.repository.append(
            {
                "name": enum_name,
                "longname": enum_longname,
                "line": line,
                "column": col,
                "kind": "Enum",
                "body": ctx.getText(),
            }
        )

    def enterInterfaceDeclaration(
        self, ctx: JavaParserLabeled.InterfaceDeclarationContext
    ):
        interface_longname = self._qualified_name(ctx)
        interface_name = ctx.IDENTIFIER().getText()
        line = ctx.children[0].symbol.line
        col = ctx.children[0].symbol.column
        self.repository.append(
            {
                "name": interface_name,
                "longname": interface_longname,
                "line": line,
                "column": col,
                "kind": "Interface",
                "body": ctx.getText(),
            }
        )


def get_parent(parent_file_name, files):
    file_names, file_paths = zip(*files)
    parent_file_index = file_names.index(parent_file_name)
    parent_file_path = file_paths[parent_file_index]
    parent_entity = EntityModel.get_or_none(
        _kind=kind_id("Java File"),
        _name=parent_file_name,
        _longname=parent_file_path,
    )
    return parent_entity, parent_file_path


def add_imported_entity(entity, files):
    entity_kind = get_kind_name(entity["longname"], entity["kind"])
    imported_entity, _ = EntityModel.get_or_create(
        _kind=KindModel.get_or_none(_name=entity_kind).get_id(),
        # _parent=parent_entity.get_id(),
        _parent=None,
        _name=entity["name"],
        _longname=entity["longname"],
        _contents=entity["body"],
    )
    return imported_entity


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
        p_static = ""

    if kind == "Method":
        p_type = ""

    s = f"Java {p_static} {p_abstract} {p_generic} {kind} {p_type} {p_visibility} {p_member}"
    s = " ".join(s.split())
    return s


def add_java_file_entity(file_path, file_name):
    obj, _ = EntityModel.get_or_create(
        _kind=kind_id("Java File"),
        _name=file_name,
        _longname=file_path,
        _contents=FileStream(file_path, encoding="utf-8"),
    )
    return obj


def add_references(importing_ent, imported_ent, ref_dict):
    ref, _ = ReferenceModel.get_or_create(
        _kind=kind_id("Java Open"),
        _file=importing_ent.get_id(),
        _line=ref_dict["line"],
        _column=col_1based(ref_dict["column"]),
        _ent=imported_ent.get_id(),
        _scope=importing_ent.get_id(),
    )
    inverse_ref, _ = ReferenceModel.get_or_create(
        _kind=kind_id("Java Openby"),
        _file=importing_ent.get_id(),
        _line=ref_dict["line"],
        _column=col_1based(ref_dict["column"]),
        _ent=importing_ent.get_id(),
        _scope=imported_ent.get_id(),
    )


def main():
    info = get_project_info(PRJ_INDEX, REF_NAME)
    p = Project(info["DB_PATH"], info["PROJECT_PATH"], info["PROJECT_NAME"])
    p.init_db()
    p.get_java_files()

    for file_name, file_path in p.files:
        importing_entity = add_java_file_entity(file_path, file_name)

        tree = get_parse_tree(file_path)
        listener = OpenListener(p.files)
        walker = ParseTreeWalker()
        walker.walk(listener, tree)

        for i in listener.repository:
            imported_entity = add_imported_entity(i, p.files)
            add_references(importing_entity, imported_entity, i)
