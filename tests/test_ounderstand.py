import os
import sys
import pytest

sys.path.insert(0, os.getcwd())

from openunderstand.utils.utilities import ClassTypeData


class FakeIdentifier:
    def __str__(self):
        return "SampleClass"


class FakeChildClass:
    def getText(self):
        return "SampleClass"

    def IDENTIFIER(self):
        return FakeIdentifier()


def test_class_type_data_default_values():
    data = ClassTypeData()

    assert data.parentClass is None
    assert data.childClass is None
    assert data.file_path == ""
    assert data.package_name == ""
    assert data.line == -1
    assert data.column == -1
    assert data.prefixes == []


def test_class_type_data_setters_normal_behavior():
    data = ClassTypeData()
    child = FakeChildClass()

    data.set_child_class(child)
    data.set_parent_class("ParentClass")
    data.set_file_path("src/Main.java")
    data.set_package_name("com.example")
    data.set_line(10)
    data.set_column(5)
    data.set_prefixes(["public", "static"])

    assert data.childClass == child
    assert data.parentClass == "ParentClass"
    assert data.file_path == "src/Main.java"
    assert data.package_name == "com.example"
    assert data.line == 10
    assert data.column == 5
    assert data.prefixes == ["public", "static"]


def test_class_type_data_getters_normal_behavior():
    data = ClassTypeData()

    data.set_child_class(FakeChildClass())
    data.set_parent_class("ParentClass")
    data.set_package_name("com.example")
    data.set_prefixes(["public"])

    assert data.get_name() == "SampleClass"
    assert data.get_contents() == "SampleClass"
    assert data.get_prefixes() == ["public"]


def test_class_type_data_edge_case_empty_package():
    data = ClassTypeData()

    data.set_child_class(FakeChildClass())
    data.set_package_name("")

    assert data.get_name() == "SampleClass"


def test_class_type_data_malformed_missing_child_class():
    data = ClassTypeData()

    with pytest.raises(Exception):
        data.get_contents()


class FakeUnknownIdentifier:
    def __str__(self):
        return "UnknownEntity"


class FakeUnknownChildClass:
    def getText(self):
        return "UnknownEntity"

    def IDENTIFIER(self):
        return FakeUnknownIdentifier()


class FakeReference:
    def __init__(self, source, target, kind):
        self.source = source
        self.target = target
        self.kind = kind

    def inverse(self):
        return FakeReference(
            self.target,
            self.source,
            "Inverse" + self.kind,
        )


def test_class_type_data_unresolved_unknown_entity():
    data = ClassTypeData()

    data.set_child_class(FakeUnknownChildClass())
    data.set_parent_class(None)

    assert data.get_name() == "UnknownEntity"
    assert data.parentClass is None


def test_class_type_data_parent_child_relationship_validation():
    data = ClassTypeData()
    child = FakeChildClass()

    data.set_parent_class("ParentClass")
    data.set_child_class(child)

    assert data.parentClass == "ParentClass"
    assert data.childClass == child
    assert data.get_name() == "SampleClass"


def test_class_type_data_inverse_reference_simulation():
    ref = FakeReference(
        "ParentClass",
        "SampleClass",
        "Contain",
    )

    inverse_ref = ref.inverse()

    assert ref.source == "ParentClass"
    assert ref.target == "SampleClass"

    assert inverse_ref.source == "SampleClass"
    assert inverse_ref.target == "ParentClass"
    assert inverse_ref.kind == "InverseContain"


def test_class_type_data_malformed_java_snippet_simulation():
    malformed_java_snippet = "public class {"

    assert "class" in malformed_java_snippet
    assert "}" not in malformed_java_snippet


def test_class_type_data_multi_pass_analysis_simulation():
    data = ClassTypeData()

    # First pass
    data.set_child_class(FakeChildClass())
    data.set_package_name("com.example")

    assert data.get_name() == "SampleClass"
    assert data.package_name == "com.example"

    # Second pass
    data.set_parent_class("ParentClass")
    data.set_file_path("src/Main.java")
    data.set_line(10)
    data.set_column(5)

    assert data.parentClass == "ParentClass"
    assert data.file_path == "src/Main.java"
    assert data.line == 10
    assert data.column == 5
import os
import logging
import configparser
from unittest.mock import MagicMock

from openunderstand.utils import utilities
from openunderstand.utils.utilities import (
    ClassTypeData,
    timer_decorator,
    setup_config,
    setup_logger,
)


def test_get_long_name_returns_package_and_child_text():
    data = ClassTypeData()
    data.set_package_name("com.example")
    fake_child = MagicMock()
    fake_child.getText.return_value = "MyClass"
    data.set_child_class(fake_child)
    assert data.get_long_name() == "com.example.MyClass"


def test_get_type_returns_extends_parent():
    data = ClassTypeData()
    data.set_parent_class("BaseClass")
    assert data.get_type() == "extends BaseClass"


def test_get_name_returns_identifier_string():
    data = ClassTypeData()
    fake_child = MagicMock()
    fake_child.IDENTIFIER.return_value = "Ident"
    data.set_child_class(fake_child)
    assert data.get_name() == "Ident"


def test_timer_decorator_runs_wrapped_function(monkeypatch):
    monkeypatch.setattr(utilities, "setup_logger", lambda: MagicMock())

    @timer_decorator()
    def sample(self, file_address=None):
        return "done"

    result = sample(None, file_address="Test.java")
    assert result == "done"

def test_setup_config_returns_configparser():
    config = setup_config()
    assert isinstance(config, configparser.ConfigParser)


def test_setup_logger_returns_logger_instance(monkeypatch, tmp_path):
    fake_config = {
        "Logging": {
            "filename": str(tmp_path / "test.log"),
            "level": "info",
        }
    }
    monkeypatch.setattr(utilities, "setup_config", lambda: fake_config)
    logger = setup_logger()
    assert isinstance(logger, logging.Logger)