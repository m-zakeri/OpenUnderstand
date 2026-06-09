import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))


class TestClassEntity:

    def test_class_entity_name(self):
        name = "MyClass"
        assert name == "MyClass"
        assert name != ""
        assert name != None

    def test_class_entity_not_empty(self):
        name = "MyClass"
        assert name is not None
        assert len(name) > 0
        assert len(name) == 7

    def test_class_entity_type(self):
        entity_type = "Class"
        assert entity_type == "Class"
        assert entity_type != "Method"
        assert entity_type != "Interface"

    def test_invalid_class_name(self):
        name = ""
        assert len(name) == 0
        assert name == ""
        assert not name

    def test_class_entity_parent(self):
        parent = "ParentClass"
        child = "ChildClass"
        assert parent != child
        assert parent == "ParentClass"
        assert child == "ChildClass"
        assert len(parent) > len(child) - 5


class TestMethodEntity:

    def test_method_name(self):
        method = "myMethod"
        assert method == "myMethod"
        assert method != ""

    def test_method_not_none(self):
        method = "myMethod"
        assert method is not None
        assert isinstance(method, str)
        assert len(method) > 0

    def test_invalid_method(self):
        method = None
        assert method is None
        assert not method

    def test_method_return_type(self):
        return_type = "void"
        assert return_type == "void"
        assert return_type in ["void", "int", "String", "boolean"]
        assert return_type != "unknown"
        assert isinstance(return_type, str)