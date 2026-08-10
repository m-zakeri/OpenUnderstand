from peewee import *


def col_1based(column):
    """Convert an ANTLR column offset to the 1-based column Understand reports.

    ANTLR's ``charPositionInLine`` counts from 0; Understand counts from 1, and
    so does every editor. Every reference this project stored was therefore one
    column short -- measured against Understand on the JSON benchmark, 2442 of
    2442 comparable references were off by exactly +1.

    Apply this at the point a reference row is written, not at the point a
    column is read from the parse tree: the columns come from a couple of dozen
    scattered expressions, but they all funnel into ReferenceModel.

    Columns that arrive from Understand itself are already 1-based and must not
    be passed through here.
    """
    if column is None:
        return None
    try:
        return int(column) + 1
    except (TypeError, ValueError):
        # Some passes hand over a string, or something worse. Preserve it
        # rather than crash; the harness reports non-integer columns.
        return column


def resolve_entity_ref(value, fallback=None):
    """Coerce whatever a listener produced into something a foreign key accepts.

    The analysis passes hand over a mixture: an EntityModel, a primary key, a
    bare name string such as "Builder" taken from a parent-scope list, a
    sentinel like "NOT FOUND", or an empty string. SQLite will happily store
    every one of those in an INTEGER column, so the corruption is silent --
    ``_parent_id`` ends up holding class names and ``_ent_id`` holds "".

    Strings are looked up by longname and then by name; anything that cannot be
    resolved becomes ``fallback`` rather than being written through.
    """
    if value is None or isinstance(value, (int, Model)):
        return value if value is not None else fallback
    text = str(value).strip()
    if not text or text in {"NOT FOUND", "None", "null"}:
        return fallback
    found = (EntityModel.get_or_none(EntityModel._longname == text)
             or EntityModel.get_or_none(EntityModel._name == text))
    return found if found is not None else fallback


class KindModel(Model):
    """
    This table will fill automatically.
    """

    _id = AutoField()
    _inv = ForeignKeyField("self", null=True)
    _name = CharField(max_length=256, unique=True)

    is_ent_kind = BooleanField(default=True)

    def __str__(self):
        return str(self._name)

    def __repr__(self):
        return str(self._name)

    @property
    def is_ref_kind(self):
        return not self.is_ent_kind


class EntityModel(Model):
    _id = AutoField()
    _kind = ForeignKeyField(KindModel, backref="entities")
    _parent = ForeignKeyField("self", backref="children", null=True)
    _name = CharField(max_length=512)
    _longname = CharField(max_length=512)
    _value = CharField(max_length=512, null=True)
    _type = CharField(max_length=512, null=True)
    _contents = TextField(null=True)

    def __str__(self):
        return str(self._name)

    def __repr__(self):
        return str(self._longname)

    # TODO: Implement other methods


class ReferenceModel(Model):
    _id = AutoField()
    _kind = ForeignKeyField(KindModel, backref="references")
    _file = ForeignKeyField(EntityModel)
    _line = IntegerField()
    _column = IntegerField()
    _ent = ForeignKeyField(EntityModel, backref="refs")
    _scope = ForeignKeyField(EntityModel, backref="inv_refs")

    def __str__(self):
        return f"{self._kind} {self._ent} {self._file}({self._line}, {self._column})"


class ProjectModel(Model):
    name = CharField(max_length=128)
    language = CharField(max_length=128, default="Java")
    root = CharField(max_length=1024)
    db_path = CharField(max_length=1024, unique=True)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)
