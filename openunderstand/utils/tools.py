import os
from pathlib import Path

from antlr4 import FileStream, CommonTokenStream, ParseTreeWalker
from antlr4.TokenStreamRewriter import TokenStreamRewriter

from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled


def get_filenames_in_dir(directory_name: str, file_filter=lambda x: x.endswith(".java")) -> list:
    result = []
    for (root, dirs, files) in os.walk(directory_name):
        result.extend([Path(root) / name for name in files if file_filter(name)])
    result.sort()
    return result


def walk_tree(tree, listener_class, **kwargs):
    listener = listener_class(**kwargs)
    ParseTreeWalker().walk(
        listener,
        tree
    )
    return listener


def get_tree(file_path: str, *args, **kwargs):
    stream = FileStream(file_path)
    lexer = JavaLexer(stream)
    tokens = CommonTokenStream(lexer)
    parser = JavaParserLabeled(tokens)
    tree = parser.compilationUnit()
    return tree


def get_parent_long_name(long_name: str) -> str:
    return ".".join(long_name.split(".")[:-1])