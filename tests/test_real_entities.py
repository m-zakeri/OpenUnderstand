"""
Real Unit Tests for OpenUnderstand
Student: Mohammad Abdulmunim - 404131069
"""

import pytest
import sys
import os

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

OUDB_PATH = os.path.join(PROJECT_ROOT, "openunderstand", "oudb")
PASSES_PATH = os.path.join(PROJECT_ROOT, "openunderstand", "analysis_passes")

from openunderstand.oudb.models import (
    EntityModel,
    ReferenceModel,
    KindModel,
)


class TestKindModel:

    def test_kind_model_has_name_field(self):
        fields = list(KindModel._meta.fields.keys())
        assert "_name" in fields

    def test_kind_model_has_is_ent_kind_field(self):
        fields = list(KindModel._meta.fields.keys())
        assert "is_ent_kind" in fields

    def test_kind_model_is_a_class(self):
        assert isinstance(KindModel, type)
        assert KindModel is not None

    def test_kind_model_table_name(self):
        table = KindModel._meta.table_name
        assert table is not None
        assert isinstance(table, str)
        assert len(table) > 0

    def test_kind_model_fields_are_not_empty(self):
        fields = list(KindModel._meta.fields.keys())
        assert len(fields) >= 2

    def test_kind_model_is_ent_kind_is_boolean(self):
        from peewee import BooleanField
        field = KindModel._meta.fields.get("is_ent_kind")
        assert field is not None
        assert isinstance(field, BooleanField)

    def test_kind_model_not_same_as_entity_model(self):
        assert KindModel is not EntityModel

    def test_kind_model_meta_exists(self):
        assert hasattr(KindModel, "_meta")
        assert KindModel._meta is not None

    def test_kind_model_has_inv_field(self):
        fields = list(KindModel._meta.fields.keys())
        assert "_inv" in fields


class TestEntityModel:

    def test_entity_model_exists(self):
        assert EntityModel is not None

    def test_entity_model_is_class(self):
        assert isinstance(EntityModel, type)

    def test_entity_model_has_name_field(self):
        fields = list(EntityModel._meta.fields.keys())
        assert "_name" in fields

    def test_entity_model_has_kind_field(self):
        fields = list(EntityModel._meta.fields.keys())
        assert "_kind" in fields

    def test_entity_model_has_longname_field(self):
        fields = list(EntityModel._meta.fields.keys())
        assert "_longname" in fields

    def test_entity_model_has_type_field(self):
        fields = list(EntityModel._meta.fields.keys())
        assert "_type" in fields

    def test_entity_model_fields_count(self):
        fields = list(EntityModel._meta.fields.keys())
        assert len(fields) >= 5

    def test_entity_model_table_name_not_empty(self):
        table = EntityModel._meta.table_name
        assert table is not None
        assert len(table) > 0

    def test_entity_model_different_table_than_kind(self):
        assert EntityModel._meta.table_name != KindModel._meta.table_name

    def test_entity_model_has_parent_field(self):
        fields = list(EntityModel._meta.fields.keys())
        assert "_parent" in fields

    def test_entity_model_has_value_field(self):
        fields = list(EntityModel._meta.fields.keys())
        assert "_value" in fields

    def test_entity_model_has_contents_field(self):
        fields = list(EntityModel._meta.fields.keys())
        assert "_contents" in fields


class TestReferenceModel:

    def test_reference_model_exists(self):
        assert ReferenceModel is not None

    def test_reference_model_is_class(self):
        assert isinstance(ReferenceModel, type)

    def test_reference_model_has_kind_field(self):
        fields = list(ReferenceModel._meta.fields.keys())
        assert "_kind" in fields

    def test_reference_model_has_line_field(self):
        fields = list(ReferenceModel._meta.fields.keys())
        assert "_line" in fields

    def test_reference_model_has_entity_fields(self):
        fields = list(ReferenceModel._meta.fields.keys())
        has_entity = any("ent" in f for f in fields)
        assert has_entity

    def test_reference_model_table_different_from_entity(self):
        assert ReferenceModel._meta.table_name != EntityModel._meta.table_name

    def test_reference_model_table_different_from_kind(self):
        assert ReferenceModel._meta.table_name != KindModel._meta.table_name

    def test_reference_model_has_col_field(self):
        fields = list(ReferenceModel._meta.fields.keys())
        assert "_column" in fields

    def test_reference_model_has_file_field(self):
        fields = list(ReferenceModel._meta.fields.keys())
        assert "_file" in fields

    def test_reference_model_has_scope_field(self):
        fields = list(ReferenceModel._meta.fields.keys())
        assert "_scope" in fields


class TestJavaEntityKinds:

    JAVA_ENT_KINDS_PATH = os.path.join(OUDB_PATH, "java_ent_kinds.txt")

    def test_java_ent_kinds_file_exists(self):
        assert os.path.exists(self.JAVA_ENT_KINDS_PATH)

    def test_java_ent_kinds_not_empty(self):
        with open(self.JAVA_ENT_KINDS_PATH, "r") as f:
            content = f.read()
        assert len(content.strip()) > 0

    def test_java_ent_kinds_contains_class(self):
        with open(self.JAVA_ENT_KINDS_PATH, "r") as f:
            content = f.read()
        assert "Class" in content

    def test_java_ent_kinds_contains_method(self):
        with open(self.JAVA_ENT_KINDS_PATH, "r") as f:
            content = f.read()
        assert "Method" in content

    def test_java_ent_kinds_contains_variable_or_field(self):
        with open(self.JAVA_ENT_KINDS_PATH, "r") as f:
            content = f.read()
        assert "Variable" in content or "Field" in content

    def test_java_ent_kinds_has_multiple_entries(self):
        with open(self.JAVA_ENT_KINDS_PATH, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert len(lines) >= 5

    def test_java_ent_kinds_no_duplicate_lines(self):
        with open(self.JAVA_ENT_KINDS_PATH, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert len(lines) == len(set(lines))


class TestJavaRefKinds:

    JAVA_REF_KINDS_PATH = os.path.join(OUDB_PATH, "java_ref_kinds.txt")

    def test_java_ref_kinds_file_exists(self):
        assert os.path.exists(self.JAVA_REF_KINDS_PATH)

    def test_java_ref_kinds_not_empty(self):
        with open(self.JAVA_REF_KINDS_PATH, "r") as f:
            content = f.read()
        assert len(content.strip()) > 0

    def test_java_ref_kinds_contains_call(self):
        with open(self.JAVA_REF_KINDS_PATH, "r") as f:
            content = f.read()
        assert "Call" in content or "call" in content

    def test_java_ref_kinds_contains_import(self):
        with open(self.JAVA_REF_KINDS_PATH, "r") as f:
            content = f.read()
        assert "Import" in content or "import" in content

    def test_java_ref_kinds_has_multiple_entries(self):
        with open(self.JAVA_REF_KINDS_PATH, "r") as f:
            lines = [l.strip() for l in f.readlines() if l.strip()]
        assert len(lines) >= 3


class TestAnalysisPasses:

    def test_analysis_passes_directory_exists(self):
        assert os.path.isdir(PASSES_PATH)

    def test_analysis_passes_has_python_files(self):
        py_files = [
            f for f in os.listdir(PASSES_PATH)
            if f.endswith(".py") and not f.startswith("__")
        ]
        assert len(py_files) >= 1

    def test_analysis_passes_has_init(self):
        init_path = os.path.join(PASSES_PATH, "__init__.py")
        assert os.path.exists(init_path)

    def test_multiple_analysis_passes_exist(self):
        py_files = [
            f for f in os.listdir(PASSES_PATH)
            if f.endswith(".py") and not f.startswith("__")
        ]
        assert len(py_files) >= 2

    def test_analysis_passes_path_is_string(self):
        assert isinstance(PASSES_PATH, str)
        assert len(PASSES_PATH) > 0
