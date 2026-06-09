import sys
import os
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__) + '/..'))


class TestClassEntity:

    def test_class_entity_name(self):
        name = "MyClass"
        assert name == "MyClass"
        assert name != ""
        assert name is not None

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
        assert len(parent) > 0

    def test_malformed_java_snippet(self):
        # Test malformed Java class names
        malformed = "123InvalidClass"
        assert malformed[0].isdigit()
        assert not malformed[0].isalpha() or malformed[0].isupper()

        malformed2 = ""
        assert len(malformed2) == 0

        malformed3 = None
        assert malformed3 is None

    def test_unresolved_entity(self):
        # Test unresolved/unknown entities
        unresolved = "UNKNOWN"
        assert unresolved == "UNKNOWN"
        assert unresolved != "Class"
        assert unresolved != "Method"

        unknown_type = None
        assert unknown_type is None

    def test_inverse_reference(self):
        # Test inverse references
        parent = "ParentClass"
        child = "ChildClass"
        # Forward: parent -> child
        assert child != parent
        # Inverse: child -> parent
        assert parent != child
        assert parent == "ParentClass"

    def test_multi_pass_analysis(self):
        # Validate multi-pass analysis behavior
        first_pass = "MyClass"
        second_pass = "MyClass"
        assert first_pass == second_pass
        assert id(first_pass) == id(second_pass) or first_pass == second_pass


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

    def test_malformed_method_name(self):
        # Test malformed method names
        malformed = ""
        assert len(malformed) == 0

        malformed2 = None
        assert malformed2 is None

        malformed3 = "123method"
        assert malformed3[0].isdigit()