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


_KIND_NAMES: dict = {}
_KIND_IDS: dict = {}


class UnknownKind(KeyError):
    """Raised when code asks for a kind name the seed files never defined."""


def kind_id(name: str) -> int:
    """Primary key of a kind, by name.

    Kind ids are assigned by ``AutoField`` in the order ``fill.py`` reads the
    two seed files, so hard-coding them -- as this project did at 89 sites --
    means editing, reordering or inserting a single line in either ``.txt``
    silently repoints every one of them at a different kind. Resolving by name
    makes the seed files editable, which is what allows the vocabulary to track
    Understand's.

    Cached per process: the seeded rows never change during a run.
    """
    if name not in _KIND_IDS:
        row = KindModel.get_or_none(KindModel._name == name)
        if row is None:
            raise UnknownKind(f"no seeded kind named {name!r}")
        _KIND_IDS[name] = row._id
        _KIND_NAMES[row._id] = name
    return _KIND_IDS[name]

# Coarse groupings of entity kinds. Two rows with the same longname in the same
# family are the same thing; two in different families are a genuine kind
# disagreement and are left alone so the harness can still report them.
# Longest-matching token wins, so "typevariable" does not read as "variable".
_FAMILY_TOKENS = (
    ("typevariable", "type"), ("annotation", "type"), ("interface", "type"),
    ("constructor", "method"), ("parameter", "variable"), ("namespace", "package"),
    ("package", "package"), ("variable", "variable"), ("property", "variable"),
    ("method", "method"), ("module", "module"), ("record", "type"),
    ("class", "type"), ("field", "variable"), ("enum", "type"), ("file", "file"),
    ("function", "method"), ("label", "label"),
)


def _kind_name(kind) -> str:
    """Name of a kind given an id, a KindModel, or None. Cached per process."""
    if kind is None:
        return ""
    kind_id = kind._id if isinstance(kind, Model) else kind
    if not isinstance(kind_id, int):
        return ""
    if kind_id not in _KIND_NAMES:
        row = KindModel.get_or_none(KindModel._id == kind_id)
        _KIND_NAMES[kind_id] = row._name if row is not None else ""
    return _KIND_NAMES[kind_id]


def kind_family(kind) -> str:
    tokens = set(_kind_name(kind).lower().split())
    for token, family in _FAMILY_TOKENS:
        if token in tokens:
            return family
    return "other"


def is_placeholder_kind(kind) -> bool:
    """A kind meaning "something is here but I could not identify it".

    Several passes create these when they encounter a name they cannot
    resolve. A placeholder must never win over, or compete with, a row that
    already carries a real kind.
    """
    tokens = set(_kind_name(kind).lower().split())
    return bool(tokens & {"unknown", "unresolved"})


class EntityModel(Model):
    _id = AutoField()
    _kind = ForeignKeyField(KindModel, backref="entities")
    _parent = ForeignKeyField("self", backref="children", null=True)
    _name = CharField(max_length=512)
    # Indexed: entity identity is resolved by longname on every create, and
    # the comparison harness groups by it too.
    _longname = CharField(max_length=512, index=True)
    _value = CharField(max_length=512, null=True)
    _type = CharField(max_length=512, null=True)
    _contents = TextField(null=True)

    @classmethod
    def get_or_create(cls, **kwargs):
        """Resolve an entity by longname before creating a new row.

        peewee's default keys on *every* field passed in, so two passes
        describing the same class with different `_contents` or `_parent` each
        get their own row. On the JSON benchmark that produced ~190 rows for
        `org.json` alone and 1707 duplicate rows overall.

        Identity here is (longname, kind family). Rows in different families
        are left separate: a method longname carrying a Package kind is a
        wrong-kind bug, and merging it would hide the defect rather than fix
        it.

        Placeholder kinds (Unknown/Unresolved) are the exception -- they mean
        "unidentified", so they match a row in any family and never displace a
        real kind. When a real kind arrives for a row currently holding a
        placeholder, the row is upgraded in place. That is what makes the
        result independent of the order the passes run in.
        """
        defaults = dict(kwargs.pop("defaults", None) or {})
        fields = {**defaults, **kwargs}
        longname = fields.get("_longname")

        if longname is None or not isinstance(longname, str):
            return super().get_or_create(defaults=defaults, **kwargs)

        incoming = fields.get("_kind", fields.get("_kind_id"))
        incoming_placeholder = is_placeholder_kind(incoming)
        incoming_family = kind_family(incoming)

        match = None
        for row in cls.select().where(cls._longname == longname):
            row_placeholder = is_placeholder_kind(row._kind_id)
            if incoming_placeholder or row_placeholder or \
                    kind_family(row._kind_id) == incoming_family:
                match = row
                if not row_placeholder:
                    break  # prefer a row that already has a real kind
        if match is not None:
            if is_placeholder_kind(match._kind_id) and not incoming_placeholder \
                    and incoming is not None:
                match._kind = incoming
                match.save()
            return match, False

        return super().create(**fields), True

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


def merge_placeholder_entities():
    """Fold Unknown/Unresolved entities into the real entity they describe.

    Only the define pass builds a full scope chain. The others qualify a name
    with just the package -- ``com.app.display.print_fail_message`` for a
    method that really lives at ``com.app.display.print_fail
    .print_fail_message`` -- so their rows never join to the declared entity,
    and every reference built on them misses.

    This runs after every pass rather than inside get_or_create because the
    passes run in a fixed order and several placeholder-creating ones (type,
    create) run *before* define: at creation time the real entity does not
    exist yet, so there is nothing to match against.

    A placeholder is folded only when exactly one non-placeholder entity ends
    with the same simple name. More than one means guessing, and a wrong merge
    is worse than a duplicate.

    Returns the number of rows merged.
    """
    placeholders = [
        e for e in EntityModel.select() if is_placeholder_kind(e._kind_id)
    ]
    if not placeholders:
        return 0

    by_simple = {}
    for e in EntityModel.select():
        if is_placeholder_kind(e._kind_id):
            continue
        by_simple.setdefault((e._longname or "").rsplit(".", 1)[-1], []).append(e)

    merged = 0
    for ghost in placeholders:
        candidates = by_simple.get((ghost._longname or "").rsplit(".", 1)[-1], [])
        if len(candidates) != 1:
            continue
        real = candidates[0]
        if real._id == ghost._id:
            continue
        for field in (ReferenceModel._ent, ReferenceModel._scope, ReferenceModel._file):
            ReferenceModel.update({field: real._id}).where(field == ghost._id).execute()
        EntityModel.update({EntityModel._parent: real._id}).where(
            EntityModel._parent == ghost._id
        ).execute()
        ghost.delete_instance()
        merged += 1
    return merged


class ProjectModel(Model):
    name = CharField(max_length=128)
    language = CharField(max_length=128, default="Java")
    root = CharField(max_length=1024)
    db_path = CharField(max_length=1024, unique=True)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)
