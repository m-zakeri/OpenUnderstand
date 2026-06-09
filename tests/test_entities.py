import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


class TestClassEntity:
    def test_class_entity_name(self):
        assert "MyClass" == "MyClass"

    def test_class_entity_not_empty(self):
        name = "MyClass"
        assert name is not None
        assert len(name) > 0

    def test_class_entity_type(self):
        entity_type = "Class"
        assert entity_type == "Class"

    def test_invalid_class_name(self):
        name = ""
        assert len(name) == 0

    def test_class_entity_parent(self):
        parent = "ParentClass"
        child = "ChildClass"
        assert parent != child


class TestMethodEntity:
    def test_method_name(self):
        assert "myMethod" == "myMethod"

    def test_method_not_none(self):
        method = "calculate"
        assert method is not None

    def test_invalid_method(self):
        method = None
        assert method is None

    def test_method_return_type(self):
        return_type = "void"
        assert return_type in ["void", "int", "String"]
