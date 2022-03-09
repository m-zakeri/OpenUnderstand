"""


"""

import os
from pathlib import Path

from antlr4 import *

from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener

from ..oudb.models import *
from ..oudb.api import open as db_open, create_db, Kind
from ..oudb.fill import main
from ..analysis_passes.define_defineby import *


class ModifyListener(JavaParserLabeledListener):
    def __init__(self):
        self.scopes = []
        self.scope_info = []
        self.line = []
        self.column = []

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
        self.scope_info.append({"parent": parent, "kind": kind, "name": name, "content": content})

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
                self.scopes.append(current.IDENTIFIER().getText())
                if type(current).__name__ == "ClassDeclarationContext":
                    self.scope_info.append(self.make_scope_class(current))
                elif type(current).__name__ == "MethodDeclarationContext":
                    self.make_scope_method(current)
                return
            current = current.parentCtx
        self.scopes.append(" ")

    def enterExpression6(self, ctx: JavaParserLabeled.Expression6Context):
        line_col = str(ctx.children[0].start).split(",")[3][:-1].split(':')
        self.line.append(line_col[0])
        self.column.append(line_col[1])
        self.search_scope(ctx)

    def enterExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        operations = ['+=', '-=', '/=', '*=', '&=', '|=', '^=', '%=']
        if ctx.children[1].getText() in operations:
            self.search_scope(ctx)
            line_col = str(ctx.children[0].start).split(",")[3][:-1].split(':')
            self.line.append(line_col[0])
            self.column.append(line_col[1])


def ent_scope(parent, name, path):
    # create entity for reference
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
    return (parent_entity, longname, file_entity)


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

        previous_token = None
        modified_vars = []
        for token in tokens.tokens:
            if token.type == JavaLexer.WS:
                continue
            if token.type in types:
                modified_vars.append(previous_token.text)
            previous_token = token

        # if the file doesn't contain any modifying variable, then continue
        if len(modified_vars) == 0:
            continue

        parser = JavaParserLabeled(tokens)

        tree = parser.compilationUnit()

        listener = DefineListener()
        scope_listener = ModifyListener()

        walker = ParseTreeWalker()
        walker.walk(listener=listener, t=tree)
        walker.walk(listener=scope_listener, t=tree)

        idx = 0
        idx2 = 0
        for n, parent in zip(listener.names, listener.parent_info):
            if n not in modified_vars:
                idx += 1
                continue

            parent_entity, longname, _ = ent_scope(parent, name, path)

            var_entity = create_Entity(listener.names[idx], longname + '.' + listener.names[idx],
                                       parent_entity, "", listener.kind[idx], listener.values[idx],
                                       listener.types[idx])

            scope, longname, file_ent = ent_scope(scope_listener.scope_info[idx2], name, path)

            ref = create_Ref(KindModel.get_or_none(_name="Java Modify")._id, file_ent, scope_listener.line[idx2],
                             scope_listener.column[idx2], var_entity, scope)
            idx += 1
            idx2 += 1


readFile()
