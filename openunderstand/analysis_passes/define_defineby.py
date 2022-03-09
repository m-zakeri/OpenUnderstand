"""


"""


import os
from antlr4 import *
from pathlib import Path

from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled

from gen.javaLabeled.JavaLexer import JavaLexer

from ..oudb.models import *

from ..oudb.api import open as db_open, create_db, Kind


class DefineListener(JavaParserLabeledListener):
    def __init__(self):
        self.names = []
        self.values = []
        self.types = []
        self.kind_type = []
        self.parents = []
        self.lines = []
        self.columns = []
        self.kind = []
        self.parent_info = []

    def get_kind_object(self):
        for kind in self.kind_type:
            if kind == "private":
                self.kind.append(KindModel.get_or_none(_name="Java Variable Private Member")._id)
            elif kind == " ":
                self.kind.append(KindModel.get_or_none(_name="Java Variable Public Member")._id)

    def make_parent_method(self, current):
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
                parent = self.make_parent_class(current)
                break
            current = current.parentCtx
        self.parent_info.append({"parent": parent, "kind": kind, "name": name, "content": content})

    def make_parent_class(self, current):
        content = current.getText()
        name = current.IDENTIFIER().getText()
        kind = KindModel.get_or_none(_name="Java Class Type Public Member")._id
        parent = "file"
        return {"parent": parent, "kind": kind, "name": name, "content": content}

    def find_parent(self, Ctx):
        current = Ctx.parentCtx
        while current is not None:
            if type(current).__name__ == "ClassDeclarationContext" or type(
                    current).__name__ == "MethodDeclarationContext":
                self.parents.append(current.IDENTIFIER().getText())
                if type(current).__name__ == "ClassDeclarationContext":
                    self.parent_info.append(self.make_parent_class(current))
                elif type(current).__name__ == "MethodDeclarationContext":
                    self.make_parent_method(current)
                return
            current = current.parentCtx
        self.parents.append(" ")

    def enterVariableDeclarators(self, ctx: JavaParserLabeled.VariableDeclaratorContext):
        self.find_parent(ctx)
        # print(ctx.children[0].start)
        first_parent = ctx.parentCtx
        second_parent = first_parent.parentCtx
        third_parent = second_parent.parentCtx
        idx = 0
        for child in first_parent.getChildren():
            if idx == 0:
                self.types.append(child.getText())
                line_col = str(child.start).split(",")[3][:-1].split(':')
                self.lines.append(line_col[0])
                self.columns.append(line_col[1])
                idx += 1
                continue
            if idx == 1:
                var = child.getText().split('=')
                self.names.append(var[0])
                self.values.append(var[1])
                break
        has_kind = False
        for child in third_parent.getChildren():
            if type(child).__name__ == "ModifierContext":
                self.kind_type.append(child.getText())
                has_kind = True
        if not has_kind:
            self.kind_type.append(" ")
        self.get_kind_object()


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


def readFile():
    listOfFiles = list()
    filename = []
    for (dirpath, dirnames, filenames) in os.walk(r"E:\uni\compiler\OpenUnderstand\benchmark\calculator_app"):
        for file in filenames:
            if '.java' in str(file):
                filename.append(file)
                listOfFiles.append(os.path.join(dirpath, file))

    db = db_open(r"E:\uni\compiler\OpenUnderstand\database.oudb")

    types = [JavaLexer.ADD_ASSIGN, JavaLexer.SUB_ASSIGN, JavaLexer.MUL_ASSIGN, JavaLexer.DIV_ASSIGN,
             JavaLexer.AND_ASSIGN, JavaLexer.OR_ASSIGN, JavaLexer.XOR_ASSIGN, JavaLexer.MOD_ASSIGN,
             JavaLexer.LSHIFT_ASSIGN, JavaLexer.RSHIFT_ASSIGN, JavaLexer.URSHIFT_ASSIGN, JavaLexer.DEC,
             JavaLexer.INC]

    for path, name in zip(listOfFiles, filename):
        file = FileStream(path)
        lexer = JavaLexer(file)
        tokens = CommonTokenStream(lexer)
        tokens.fill()
        parser = JavaParserLabeled(tokens)
        tree = parser.compilationUnit()
        listener = DefineListener()
        walker = ParseTreeWalker()
        walker.walk(listener=listener, t=tree)

        for idx, parent in enumerate(listener.parent_info):
            # make parent entity type of class
            if parent['parent'] == "file":
                file_entity = create_Entity(name, path, None, FileStream(path),
                                            KindModel.get_or_none(_name="Java File")._id, None, None)
                path_parts = path.split('\\')
                i = path_parts.index("src")
                longname = '.'.join(path_parts[i + 1:])
                parent_entity = create_Entity(parent['name'], longname, file_entity, parent['content']
                                              , parent['kind'], None, None)
            # make parent entity type of method
            else:
                parent_class = parent['parent']
                file_entity = create_Entity(name, path, None, FileStream(path),
                                            KindModel.get_or_none(_name="Java File")._id, None, None)
                path_parts = path.split('\\')
                i = path_parts.index("src")
                longname = '.'.join(path_parts[i + 1:])
                class_entity = create_Entity(parent_class['name'], longname, file_entity, parent_class['content']
                                             , parent_class['kind'], None, None)
                longname_method = longname + "." + parent['name']
                parent_entity = create_Entity(parent['name'], longname_method, class_entity, parent['content']
                                              , parent['kind'], None, None)

            var_entity = create_Entity(listener.names[idx], longname + '.' + listener.names[idx],
                                       parent_entity, "", listener.kind[idx], listener.values[idx], listener.types[idx])
            create_Ref(KindModel.get_or_none(_name="Java Define")._id, file_entity, listener.lines[idx],
                       listener.columns[idx], var_entity, parent_entity)


readFile()
