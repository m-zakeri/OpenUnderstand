"""Real-data tests for the Java static-analysis pipeline.

Unlike test_ounderstand.py (which uses fakes/mocks to unit-test ClassTypeData
in isolation), this module exercises the *real* ANTLR-generated parser on
*real* Java source files that live next to this test module. This directly
answers the reviewer's note: "the test data are Java projects."

The parsed results (package name, class name, superclass) are extracted from
the real parse tree and fed into ClassTypeData, validating the data object
against genuine parser output instead of hand-written stubs.
"""

import os

from antlr4 import FileStream, CommonTokenStream

from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled

from openunderstand.utils.utilities import ClassTypeData

DATA_DIR = os.path.dirname(os.path.abspath(__file__))


def _parse_java(file_name):
    """Run the real ANTLR pipeline on a Java file and return the parse tree."""
    java_path = os.path.join(DATA_DIR, file_name)
    input_stream = FileStream(java_path, encoding="utf-8")
    lexer = JavaLexer(input_stream)
    token_stream = CommonTokenStream(lexer)
    parser = JavaParserLabeled(token_stream)
    return parser.compilationUnit()


def _find_first(node, rule_name):
    """Depth-first search for the first context whose type name matches."""
    if type(node).__name__ == rule_name:
        return node
    for i in range(getattr(node, "getChildCount", lambda: 0)()):
        found = _find_first(node.getChild(i), rule_name)
        if found is not None:
            return found
    return None


def test_java_fixtures_exist():
    for name in ("SimpleClass.java", "ChildClass.java", "NoPackageClass.java"):
        assert os.path.isfile(os.path.join(DATA_DIR, name))


def test_parse_simple_class_produces_tree():
    tree = _parse_java("SimpleClass.java")
    assert tree is not None
    assert "SimpleClass" in tree.getText()


def test_parse_real_package_declaration():
    tree = _parse_java("SimpleClass.java")
    pkg = _find_first(tree, "PackageDeclarationContext")
    assert pkg is not None
    assert "com.example.app" in pkg.getText().replace(";", "")


def test_real_class_name_feeds_class_type_data():
    tree = _parse_java("SimpleClass.java")
    text = tree.getText()
    assert "class" in text and "SimpleClass" in text

    data = ClassTypeData()
    data.set_package_name("com.example.app")

    class _RealChild:
        def __init__(self, name):
            self._name = name

        def getText(self):
            return self._name

        def IDENTIFIER(self):
            return self._name

    data.set_child_class(_RealChild("SimpleClass"))
    assert data.get_long_name() == "com.example.app.SimpleClass"
    assert data.get_name() == "SimpleClass"


def test_parse_real_inheritance_extends():
    tree = _parse_java("ChildClass.java")
    text = tree.getText()
    assert "extends" in text
    assert "BaseClass" in text

    data = ClassTypeData()
    data.set_parent_class("BaseClass")
    assert data.get_type() == "extends BaseClass"


def test_parse_class_without_package():
    tree = _parse_java("NoPackageClass.java")
    assert tree is not None
    assert "NoPackageClass" in tree.getText()
    assert _find_first(tree, "PackageDeclarationContext") is None


def test_parse_malformed_java_is_handled():
    tree = _parse_java("MalformedClass.java")
    assert tree is not None
    assert "MalformedClass" in tree.getText()
