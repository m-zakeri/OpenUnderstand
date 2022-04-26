"""


"""

import os
from antlr4 import *

from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaLexer import JavaLexer

from oudb.models import *
from oudb.api import open as db_open

from analysis_passes.class_properties import ClassPropertiesListener


class OpenListener(JavaParserLabeledListener):
    def __init__(self):
        self.interfaces = []
        self.classes = []
        self.files = []
        self.functions = []
        self.loops = []
        self.conditions = []
        self.switch = []
        self.enums = []
        self.parents = []
        self.parent_info = []
        self.entities = []
        self.open = []

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        scope_parents = ClassPropertiesListener.findParents(ctx)
        if len(scope_parents) == 1:
            scope_longname = scope_parents[0]
        else:
            scope_longname = ".".join(scope_parents)

        [line, col] = str(ctx.start).split(",")[3].split(":")
        for ent_type in ctx.typeList().typeType():
            if ent_type.classOrInterfaceType():
                ent_long_name = ".".join([x.getText() for x in ent_type.classOrInterfaceType().IDENTIFIER()])
                self.entities.append({
                    "scope_kind": "Class", "scope_name": ctx.IDENTIFIER().__str__(),
                    ''"scope_longname": scope_longname,
                    "scope_parent": scope_parents[-2] if len(scope_parents) > 2 else None,
                    "scope_contents": ctx.getText(),
                    "scope_modifiers": ClassPropertiesListener.findClassOrInterfaceModifiers(ctx),
                    "line": line,
                    "col": col[:-1],
                    "type_ent_longname": ent_long_name
                })

    def enterEnumDeclaration(self, ctx: JavaParserLabeled.EnumDeclarationContext):
        scope_parents = ClassPropertiesListener.findParents(ctx)
        if len(scope_parents) == 1:
            scope_longname = scope_parents[0]
        else:
            scope_longname = ".".join(scope_parents)

        [line, col] = str(ctx.start).split(",")[3].split(":")  # line, column
        for ent_type in ctx.typeList().typeType():
            if ent_type.classOrInterfaceType():
                ent_long_name = ".".join([x.getText() for x in ent_type.classOrInterfaceType().IDENTIFIER()])
                self.entities.append({
                    "scope_kind": "Enum", "scope_name": ctx.IDENTIFIER().__str__(),
                    "scope_longname": scope_longname,
                    "scope_parent": scope_parents[-2] if len(scope_parents) > 2 else None,
                    "scope_contents": ctx.getText(),
                    "scope_modifiers": ClassPropertiesListener.findClassOrInterfaceModifiers(ctx),
                    "line": line,
                    "col": col[:-1],
                    "type_ent_longname": ent_long_name
                })

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        pass


def create_entity(name, longname, parent, contents, kind, value, entity_type):
    obj, has_created = EntityModel.get_or_create(_kind=kind,
                                                 _parent=parent,
                                                 _name=name,
                                                 _longname=longname,
                                                 _value=value,
                                                 _type=entity_type,
                                                 _contents=contents
                                                 )
    return obj


def create_ref(kind, file, line, column, ent, scope):
    obj, has_created = ReferenceModel.get_or_create(_kind=kind,
                                                    _file=file,
                                                    _line=line,
                                                    _column=column,
                                                    _ent=ent,
                                                    _scope=scope
                                                    )
    return obj


def read_files():
    files = list()
    filename = []
    for (dir_path, dir_names, file_names) in os.walk("../../benchmark/105_freemind"):
        for file in file_names:
            if '.java' in str(file):
                filename.append(file)
                files.append(os.path.join(dir_path, file))

    db_open("../benchmark2_database.oudb")

    for path, name in zip(files, filename):
        file = FileStream(path)
        lexer = JavaLexer(file)
        tokens = CommonTokenStream(lexer)
        tokens.fill()
        parser = JavaParserLabeled(tokens)
        tree = parser.compilationUnit()
        listener = OpenListener()
        walker = ParseTreeWalker()
        walker.walk(listener=listener, t=tree)

        for idx, parent in enumerate(listener.parent_info):
            # make parent entity type of class
            if parent['parent'] == "file":
                file_entity = create_entity(name, path, None, FileStream(path),
                                            KindModel.get_or_none(_name="Java File")._id, None, None)
                path_parts = path.split('\\')
                i = path_parts.index("src")
                longname = '.'.join(path_parts[i + 1:])
                parent_entity = create_entity(parent['name'], longname, file_entity, parent['content']
                                              , parent['kind'], None, None)
            # make parent entity type of method
            else:
                parent_class = parent['parent']
                file_entity = create_entity(name, path, None, FileStream(path),
                                            KindModel.get_or_none(_name="Java File")._id, None, None)
                path_parts = path.split('\\')
                i = path_parts.index("src")
                longname = '.'.join(path_parts[i + 1:])
                class_entity = create_entity(parent_class['name'], longname, file_entity, parent_class['content']
                                             , parent_class['kind'], None, None)
                longname_method = longname + "." + parent['name']
                parent_entity = create_entity(parent['name'], longname_method, class_entity, parent['content']
                                              , parent['kind'], None, None)

            var_entity = create_entity(listener.names[idx], longname + '.' + listener.names[idx],
                                       parent_entity, "", listener.kind[idx], listener.values[idx], listener.types[idx])
            create_ref(KindModel.get_or_none(_name="Java Define")._id, file_entity, listener.lines[idx],
                       listener.columns[idx], var_entity, parent_entity)


read_files()
