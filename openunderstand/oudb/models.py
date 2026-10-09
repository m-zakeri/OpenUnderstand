import os
from functools import lru_cache

from peewee import *

from openunderstand.oudb import jdk_index


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
    found = EntityModel.get_or_none(
        EntityModel._longname == text
    ) or EntityModel.get_or_none(EntityModel._name == text)
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
    ("typevariable", "type"),
    ("annotation", "type"),
    ("interface", "type"),
    # Understand's own irregular spelling, `Java SealedInterface Type Public`:
    # without it a sealed interface fell into "other" and every pass that
    # named it as an interface created a second row.
    ("sealedinterface", "type"),
    ("constructor", "method"),
    ("parameter", "variable"),
    ("namespace", "package"),
    ("package", "package"),
    ("variable", "variable"),
    ("property", "variable"),
    ("method", "method"),
    ("module", "module"),
    ("record", "type"),
    ("class", "type"),
    ("field", "variable"),
    ("enum", "type"),
    ("file", "file"),
    ("function", "method"),
    ("label", "label"),
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


def find_kind(family: str, modifiers=()) -> "KindModel | None":
    """The entity kind named by a family word plus these modifier words.

    Matching used to be `KindModel._name.contains(family)` and a substring test
    per modifier, which is not a match on *words*: `find_kind("Parameter",
    ["generic"])` selected `Java GenericParameter Type`, because both strings
    occur inside the single word `GenericParameter`. That kind is a type
    parameter and has nothing to do with a generic method's argument. Nothing
    reaches that combination today -- `Java GenericParameter Type` is assigned
    by name through `kind_id` -- but the mechanism was one modifier away from
    naming the wrong kind for every entity built through it.

    Words, then, and the *fewest* extra of them, which is the "least specific"
    rule the substring version was reaching for with `len(name)`. An annotation
    is not a modifier: `@SuppressWarnings("boxing") public class XML` arrived
    with the annotation in the list, no kind name contains it, every candidate
    was rejected and this returned None -- which failed the NOT NULL constraint
    and, through a caller's bare `except`, dropped org.json.XML entirely.

    Cached per process and per database. This is called once per entity
    created, and it used to issue a `SELECT ... LIKE` every time.
    """
    wanted = frozenset(
        w.lower() for w in modifiers if w and not w.startswith("@")
    ) or frozenset({"default"})
    return _find_kind(_database_name(), (family or "").lower(), wanted)


def _database_name():
    database = KindModel._meta.database
    return getattr(database, "database", None)


@lru_cache(maxsize=4096)
def _find_kind(_database, family, wanted):
    candidates = _entity_kind_words(_database)
    exact = [
        (row, words) for row, words in candidates if family in words and wanted <= words
    ]
    if exact:
        return _least_specific(exact)
    # Nothing carries every modifier. The family alone still beats None, which
    # is what the NOT NULL constraint turns into a dropped entity -- and it is
    # the only answer for `Java Parameter`, `Java Package` and `Java File`,
    # which carry no visibility word for the implicit "default" to match.
    family_only = [(row, words) for row, words in candidates if family in words]
    if family_only:
        return _least_specific(family_only)
    # Last: the substring behaviour this replaced, so that no caller can lose
    # an answer it used to get. `Constant` only ever matched inside the single
    # word `EnumConstant`, which is the shape this function exists to stop
    # trusting -- but a None here is a NOT NULL failure and a dropped entity,
    # and that is the worse outcome.
    loose = [
        (row, words)
        for row, words in candidates
        if family in (row._name or "").lower()
        and all(m in (row._name or "").lower() for m in wanted)
    ]
    return _least_specific(loose) if loose else None


def _least_specific(candidates):
    """Fewest words, then the shortest name, then alphabetical.

    The shortest *name* has to stay in the ordering: `Java Enum Class Type
    Public Member` and `Java Abstract Enum Type Public Member` both carry six
    words and both satisfy ("Enum", ["public"]), and an enum is not abstract.
    Sorting on word count alone left the winner to whatever order the rows came
    back in.
    """
    row, _ = min(
        candidates,
        key=lambda pair: (len(pair[1]), len(pair[0]._name or ""), pair[0]._name or ""),
    )
    return row


@lru_cache(maxsize=8)
def _entity_kind_words(_database):
    return [
        (row, frozenset(w.lower() for w in (row._name or "").split()))
        for row in KindModel.select().where(KindModel.is_ent_kind == True)
    ]  # noqa: E712


def _parameter_vs_member(a, b) -> bool:
    """True when one kind is a parameter and the other a member field."""
    ta = set(_kind_name(a).lower().split())
    tb = set(_kind_name(b).lower().split())
    return ("parameter" in ta and "member" in tb) or ("parameter" in tb and "member" in ta)


def kind_family(kind) -> str:
    tokens = set(_kind_name(kind).lower().split())
    for token, family in _FAMILY_TOKENS:
        if token in tokens:
            return family
    return "other"


def _declared_per_site(kind):
    """A parameter, catch parameter or type parameter is one entity per
    declaration even when overloads give two of them one long name:
    `CDL.toJSONArray.string` is four rows in Understand, one per overload,
    and was one here -- 4,674 parameters over eight fixtures. Locals too: one
    per declaration, even within one method."""
    name = _kind_name(kind)
    return "Parameter" in name or "Local" in name


def is_placeholder_kind(kind) -> bool:
    """A kind meaning "something is here but I could not identify it".

    Several passes create these when they encounter a name they cannot
    resolve. A placeholder must never win over, or compete with, a row that
    already carries a real kind.
    """
    tokens = set(_kind_name(kind).lower().split())
    return bool(tokens & {"unknown", "unresolved"})


#: long name -> the rows carrying it, for the process that is writing.
#: `EntityModel.get_or_create` resolves identity by long name and used to ask
#: the database every time: 11,153 SELECTs and 21% of a build of the JSON
#: benchmark. One process writes a database, so it can answer itself. This is
#: the same trade `ReferenceModel.get_or_create` already makes.
_ENTITY_ROWS = None
_ENTITY_ROWS_DB = None


def forget_entity_rows():
    """Drop the long-name index. Anything that deletes a row must call this."""
    global _ENTITY_ROWS, _ENTITY_ROWS_DB
    _ENTITY_ROWS = None
    _ENTITY_ROWS_DB = None


def _entity_rows(cls, longname):
    """Every row carrying `longname`, from the index, seeding it if needed.

    Seeded from the database on first use, which costs one query and keeps a
    run over an *existing* database correct.
    """
    global _ENTITY_ROWS, _ENTITY_ROWS_DB
    database = cls._meta.database
    if _ENTITY_ROWS is None or _ENTITY_ROWS_DB is not database:
        index = {}
        for row in cls.select():
            index.setdefault(row._longname, []).append(row)
        _ENTITY_ROWS, _ENTITY_ROWS_DB = index, database
    return _ENTITY_ROWS.get(longname, ())


#: Model field name -> column name, for the columns `get_or_create` completes
#: in place. Read from the model rather than written out, so a renamed field
#: cannot silently stop being updated.
_ENTITY_COLUMNS = {
    "_kind": "_kind_id",
    "_parent": "_parent_id",
    "_line": "_line",
    "_column": "_column",
    "_type": "_type",
    "_value": "_value",
    "_contents": "_contents",
}


def _update_entity_columns(row, fields):
    """UPDATE only `fields`, without going through peewee's `save()`.

    A build of JSON completes 11,604 entity rows in place -- a row is created
    by whichever pass reaches the name first and filled in by the two or three
    that follow -- and `save()` was 1.29s of a 19s per-file loop. Naming only
    the dirty columns took that to 1.06s, which is the tell: the cost is
    peewee's query construction per call, not the width of the row. The
    statement here is built from a fixed dict and executed on the cursor.

    Deliberately not deferred the way reference inserts are. Passes still run
    `EntityModel.select()` during the file loop -- 34,009 times on JSON -- and
    a buffered update would leave those reading a stale column.
    """
    meta = row._meta
    columns, values = [], []
    for name in fields:
        columns.append(_ENTITY_COLUMNS[name])
        raw = getattr(
            row, _ENTITY_COLUMNS[name] if name in ("_kind", "_parent") else name
        )
        # Through the field's own converter, not straight to the cursor. A
        # CharField coerces with str(), and `_contents` is handed a FileStream
        # by one pass -- binding that raw fails, which is how the shortcut was
        # caught: 14 references and one logged failure, on a build whose
        # fingerprint must not move at all.
        values.append(meta.fields[name].db_value(raw) if raw is not None else None)
    assignments = ", ".join(f'"{column}" = ?' for column in columns)
    meta.database.execute_sql(
        f'UPDATE "entitymodel" SET {assignments} WHERE "_id" = ?', values + [row._id]
    )


def entity_rows(longname):
    """Every entity row carrying `longname`, in `_id` order.

    The public read of the same index `EntityModel.get_or_create` and
    `get_or_none` resolve identity through, for the callers that need *all*
    the rows rather than the first: `project.scope_of` picks the enclosing
    overload by declaration line, and `project.callee_of` scans for a
    declaration position. Both ran `EntityModel.select()` per reference --
    34,009 times on a build of JSON.

    Returns the cached list itself. Callers must not mutate it.
    """
    return _entity_rows(EntityModel, longname)


def _remember_entity(cls, row):
    if _ENTITY_ROWS is not None and _ENTITY_ROWS_DB is cls._meta.database:
        _ENTITY_ROWS.setdefault(row._longname, []).append(row)


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
    # Where the declaration is. Understand separates overloads by declaration
    # site, not by name -- its long names carry no parameter list either, so
    # `println.print` names two entities there. Without a position this table
    # cannot express that, and every overload collapsed into one row.
    _line = IntegerField(null=True)
    _column = IntegerField(null=True)

    @classmethod
    def get_or_none(cls, *args, **kwargs):
        """Answer a plain long-name lookup from the index, not from SQL.

        20,063 of the 23,194 `get_or_none` calls a build of the JSON benchmark
        makes are exactly `_longname == x`, and they cost 3.35s of a 23s
        per-file loop -- 17% of it, spent asking the database a question this
        process can already answer. `get_or_create` has read `_ENTITY_ROWS` for
        the same question since it was the same 21%; this is the other half of
        that fix, and the two now agree by construction rather than by luck.

        Only the single-term long-name shapes are intercepted, in both the
        expression and the keyword spelling. Anything compound, or keyed on
        another field, falls through to peewee untouched.

        The index preserves insertion order and is seeded in `_id` order, so
        the row returned for a duplicated long name -- overloads, which are
        deliberately separate rows -- is the one SQL would have returned.
        """
        longname = None
        if not args and set(kwargs) == {"_longname"}:
            longname = kwargs["_longname"]
        elif len(args) == 1 and not kwargs:
            expression = args[0]
            if (
                getattr(getattr(expression, "lhs", None), "name", None) == "_longname"
                and getattr(expression, "op", None) == OP.EQ
                and isinstance(getattr(expression, "rhs", None), str)
            ):
                longname = expression.rhs
        if longname is None:
            return super().get_or_none(*args, **kwargs)
        rows = _entity_rows(cls, longname)
        return rows[0] if rows else None

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

        Overloads are the other exception. Two rows with the same long name
        declared at different positions are different declarations -- that is
        how Understand tells `println.print(String)` from
        `println.print(String, String)`. Only a caller that knows it is looking
        at a declaration supplies a position; every other pass omits it and
        keeps resolving by name.
        """
        defaults = dict(kwargs.pop("defaults", None) or {})
        fields = {**defaults, **kwargs}
        longname = fields.get("_longname")

        if longname is None or not isinstance(longname, str):
            return super().get_or_create(defaults=defaults, **kwargs)

        incoming = fields.get("_kind", fields.get("_kind_id"))
        incoming_placeholder = is_placeholder_kind(incoming)
        incoming_family = kind_family(incoming)
        incoming_site = (fields.get("_line"), fields.get("_column"))

        match = None
        for row in _entity_rows(cls, longname):
            row_placeholder = is_placeholder_kind(row._kind_id)
            if not (
                incoming_placeholder
                or row_placeholder
                or kind_family(row._kind_id) == incoming_family
            ):
                continue
            if (
                not incoming_placeholder
                and not row_placeholder
                and _parameter_vs_member(row._kind_id, incoming)
            ):
                # A record component `R(T c)` is both the field R.c and the
                # implicit constructor's parameter R.c -- Understand's long
                # names for the two are identical. Nowhere else can a
                # parameter and a member share a long name (C.m.x, C.x).
                continue
            row_site = (row._line, row._column)
            if (
                all(incoming_site)
                and all(row_site)
                and incoming_site != row_site
                and (
                    incoming_family == "method"
                    or _declared_per_site(incoming)
                    or _declared_per_site(row._kind_id)
                )
            ):
                # A method overload, or a parameter, local or type parameter
                # declared at another site: Understand keeps one entity per
                # declaration. That includes a local -- two `for (int i ...)`
                # loops in one method are two `m.i` in its database, 3,153 such
                # over thirteen fixtures against none here. This used to say
                # splitting locals "produced 155 duplicate rows"; those were
                # duplicates by the harness's count, never measured against
                # Understand.
                continue
            incoming_parent = fields.get("_parent")
            incoming_parent_id = getattr(incoming_parent, "_id", incoming_parent)
            if (
                all(incoming_site)
                and incoming_site == row_site
                and not incoming_placeholder
                and not row_placeholder
                and incoming_family != "package"  # every file declares it
                and isinstance(incoming_parent_id, int)
                and row._parent_id is not None
                and incoming_parent_id != row._parent_id
            ):
                # The same declaration at the same position under another
                # parent is a copy in another file: testing_legacy_code holds
                # each EvoSuite class three times under one long name, and
                # Understand keeps three entities, one per file.
                continue
            match = row
            if not row_placeholder:
                break  # prefer a row that already has a real kind
        if match is not None:
            # The columns that actually changed, so the UPDATE names those and
            # not all ten. A build of JSON saves 11,604 times against 5,260
            # entities -- a row is completed by two or three passes on average
            # -- and rewriting every column each time was 1.29s of a 19s loop.
            dirty = []
            if (
                is_placeholder_kind(match._kind_id)
                and not incoming_placeholder
                and incoming is not None
            ):
                match._kind = incoming
                dirty.append("_kind")
            if all(incoming_site) and not all((match._line, match._column)):
                match._line, match._column = incoming_site
                dirty += ["_line", "_column"]
            # Fill in facts the row is missing rather than discarding them.
            # A pass that meets a method before define_listener declares it
            # creates the row with no type, and the declared return type was
            # then thrown away for 271 of JSON's 440 methods -- CountOutput
            # adds one for a non-void return, so each of those was short by
            # exactly one.
            for field in ("_type", "_value", "_contents"):
                incoming_value = fields.get(field)
                if incoming_value and not getattr(match, field, None):
                    setattr(match, field, incoming_value)
                    dirty.append(field)
            incoming_parent = fields.get("_parent")
            if incoming_parent is not None and match._parent_id is None:
                match._parent = incoming_parent
                dirty.append("_parent")
            if dirty:
                _update_entity_columns(match, dirty)
            return match, False

        created = super().create(**fields)
        _remember_entity(cls, created)
        return created, True

    def __str__(self):
        return str(self._name)

    def __repr__(self):
        return str(self._longname)

    # TODO: Implement other methods


#: Reference rows already written, as (kind, file, line, column, ent, scope),
#: and the database they were read from. Seeded on first use so an incremental
#: run over a populated database still sees what is already there, and rebuilt
#: when a different database is bound -- `create_db` and `open` each construct
#: a new SqliteDatabase, and reusing one database's keys against another would
#: silently drop every reference they happen to share.
_REFERENCE_KEYS = None
_REFERENCE_KEYS_DB = None

#: The fields a reference is identified by, in key order.
_REFERENCE_FIELDS = ("_kind", "_file", "_line", "_column", "_ent", "_scope")


#: Reference rows written but not yet inserted. Flushed per file, and by
#: every project-wide pass before it reads.
_PENDING_REFERENCES = []
#: The same rows by identity key, so a repeat within one file resolves to the
#: buffered row instead of asking a database that cannot see it yet.
_PENDING_BY_KEY = {}


def flush_reference_writes():
    """Insert the buffered reference rows. Returns how many were written."""
    global _PENDING_REFERENCES
    if not _PENDING_REFERENCES:
        return 0
    rows, _PENDING_REFERENCES = _PENDING_REFERENCES, []
    _PENDING_BY_KEY.clear()
    database = ReferenceModel._meta.database
    with database.atomic():
        # SQLite caps the variables in one statement; 400 rows of six columns
        # stays well inside it on every build of Python it ships with.
        for start in range(0, len(rows), 400):
            ReferenceModel.insert_many(rows[start : start + 400]).execute()
    return len(rows)


def _row_id(value):
    """A field value as it is stored: a foreign key's id, or the value itself."""
    if isinstance(value, Model):
        return value._id
    return value


class ReferenceModel(Model):
    _id = AutoField()
    _kind = ForeignKeyField(KindModel, backref="references")
    _file = ForeignKeyField(EntityModel)
    _line = IntegerField()
    _column = IntegerField()
    _ent = ForeignKeyField(EntityModel, backref="refs")
    _scope = ForeignKeyField(EntityModel, backref="inv_refs")

    @classmethod
    def get_or_create(cls, **kwargs):
        """Create the row without asking the database whether it exists.

        peewee's default issues a SELECT keyed on every field and then an
        INSERT. That SELECT was 50% of `process_file` on JSONObject.java --
        4.4s of 8.8s across 8624 calls -- and it answers a question this
        process can answer itself: one process writes the database, so a set of
        the keys it has already written is authoritative.

        A key that has been seen falls through to the original path, so a
        genuine duplicate still resolves to the existing row rather than a
        second one. The set is seeded from the database on first use, which
        costs one query and keeps an incremental run over an existing database
        correct.
        """
        global _REFERENCE_KEYS, _REFERENCE_KEYS_DB
        defaults = dict(kwargs.pop("defaults", None) or {})
        fields = {**defaults, **kwargs}
        try:
            key = tuple(_row_id(fields[name]) for name in _REFERENCE_FIELDS)
        except KeyError:
            # A caller identifying a reference some other way; let peewee decide.
            return super().get_or_create(defaults=defaults, **kwargs)

        database = cls._meta.database
        if _REFERENCE_KEYS is None or _REFERENCE_KEYS_DB is not database:
            _REFERENCE_KEYS = {
                tuple(row)
                for row in cls.select(
                    cls._kind, cls._file, cls._line, cls._column, cls._ent, cls._scope
                ).tuples()
            }
            _REFERENCE_KEYS_DB = database
        if key in _REFERENCE_KEYS:
            # A key written earlier in this file is still in the buffer, so the
            # database cannot see it: falling through to peewee would SELECT,
            # miss, and INSERT a second copy that the flush then duplicates.
            buffered = _PENDING_BY_KEY.get(key)
            if buffered is not None:
                return buffered, False
            return super().get_or_create(defaults=defaults, **kwargs)
        _REFERENCE_KEYS.add(key)
        # Buffered, not inserted. peewee's per-row INSERT was the rest of the
        # write layer once the SELECT above was gone -- 18,932 statements for
        # one build of the JSON benchmark. Nothing reads a reference during
        # analysis: every reader is in the query layer or in a project-wide
        # pass, and both flush first.
        row = cls(**fields)
        pending = dict(row.__data__)
        pending.pop("_id", None)
        _PENDING_REFERENCES.append(pending)
        _PENDING_BY_KEY[key] = row
        return row, True

    def __str__(self):
        return f"{self._kind} {self._ent} {self._file}({self._line}, {self._column})"


#: What a declaration demotes to when its file no longer declares it.
_PLACEHOLDER_FOR = {
    "method": "Java Unknown Method Member",
    "type": "Java Unknown Class Type Member",
    "variable": "Java Unknown Variable Member",
    "package": "Java Unknown Package",
}


def dependent_files(file_entity_ids):
    """Files that must be re-analysed when these change, transitively.

    Understand's incremental analysis re-analyses "all files that have been
    changed and all files that depend on those changed". Editing a base class
    changes what its subclasses inherit, so analysing only the edited file
    leaves their members and couplings stale.

    A file depends on another when it references a *type* declared there.
    Only types: a package entity is "declared" by every file in the package,
    so following those made every file depend on every other -- editing a leaf
    class pulled in the whole project.
    Both halves of that are already stored -- Define references say where an
    entity is declared, and every reference records the file it occurs in --
    so the graph is a query, not a new table.

    Transitive, because inheritance chains: editing C must reach B extends C
    and A extends B. Returns the closure *including* the starting files.
    """
    flush_reference_writes()
    define = KindModel.get_or_none(_name="Java Define")
    if define is None:
        return set(file_entity_ids)

    closure = set(file_entity_ids)
    pending = list(file_entity_ids)
    while pending:
        current = pending.pop()
        declared = []
        for ref in ReferenceModel.select().where(
            (ReferenceModel._kind == define._id) & (ReferenceModel._file == current)
        ):
            target = EntityModel.get_or_none(_id=ref._ent_id)
            if target is not None and kind_family(target._kind_id) == "type":
                declared.append(target._id)
        if not declared:
            continue
        for ref in ReferenceModel.select().where(
            (ReferenceModel._ent.in_(declared)) | (ReferenceModel._scope.in_(declared))
        ):
            if ref._file_id is not None and ref._file_id not in closure:
                closure.add(ref._file_id)
                pending.append(ref._file_id)
    return closure


def purge_file(file_entity_id):
    """Remove everything a file contributed, so it can be re-analysed.

    Re-running an analysis pass over a changed file only ever *adds* rows --
    `get_or_create` dedupes what is still there and knows nothing about what
    has gone. Rename a method and the database ends up holding both names.
    An incremental update therefore has to delete the file's contribution
    first.

    An entity declared in this file is deleted only if nothing else still
    refers to it: a class named from another file must survive as the
    placeholder it will become again.

    Returns (entities_removed, references_removed).
    """
    flush_reference_writes()
    define = KindModel.get_or_none(_name="Java Define")
    declared = set()
    if define is not None:
        declared = {
            ref._ent_id
            for ref in ReferenceModel.select().where(
                (ReferenceModel._kind == define._id)
                & (ReferenceModel._file == file_entity_id)
            )
        }

    refs_removed = (
        ReferenceModel.delete().where(ReferenceModel._file == file_entity_id).execute()
    )
    # The metric store is derived from the reference graph, and re-analysing one
    # file can change any entity's value -- a caller's CountInput moves when its
    # callee's file is rewritten. Dropping the lot is the only answer that is
    # right without tracking dependencies, and it costs a recompute rather than
    # a wrong number.
    try:
        MetricModel.delete().execute()
    except Exception:
        pass

    entities_removed = 0
    for entity_id in declared:
        entity = EntityModel.get_or_none(_id=entity_id)
        if entity is None or entity._id == file_entity_id:
            continue
        still_used = (
            ReferenceModel.select()
            .where(
                (ReferenceModel._ent == entity_id)
                | (ReferenceModel._scope == entity_id)
            )
            .exists()
        )
        if still_used:
            # Named from another file, so the row has to stay -- but its
            # declaration is gone, so it is no longer a known method or class.
            # Demoting it to a placeholder says exactly that, and lets
            # merge_placeholder_entities() re-resolve it if the declaration
            # reappears elsewhere. Leaving the old kind would claim a
            # declaration that no longer exists.
            unknown = _PLACEHOLDER_FOR.get(kind_family(entity._kind_id))
            if unknown:
                entity._kind = kind_id(unknown)
                entity._contents = ""
                # The declaration position stays. It is not a fact about the
                # old source, it is this row's *identity*: overloads share a
                # long name and are separate rows only because their positions
                # differ. Clearing it left `org.json.CDL.toJSONArray`'s eight
                # rows indistinguishable, so re-analysis matched declarations
                # to whichever placeholder came first and the eight positions
                # came back shuffled -- which then moved every call that
                # resolves to one of them. If the declaration really has gone,
                # a stale position is what makes the next one at a *different*
                # position correctly create its own row rather than claim this.
                entity.save()
            continue
        EntityModel.update({EntityModel._parent: None}).where(
            EntityModel._parent == entity_id
        ).execute()
        entity.delete_instance()
        forget_entity_rows()
        entities_removed += 1
    return entities_removed, refs_removed


#: Long-name roots that belong to the JDK rather than to the project. An
#: entity under one of these is external and already fully qualified, however
#: unresolved its kind looks.
EXTERNAL_ROOTS = ("java.", "javax.")


#: Reference-table foreign-key indexes, dropped for the per-file loop and
#: rebuilt once before anything reads references. Building an index over a
#: finished table sorts once; maintaining it per row re-balances a growing tree
#: on every insert.
_REFERENCE_INDEXES = {
    "referencemodel__kind_id": "_kind_id",
    "referencemodel__file_id": "_file_id",
    "referencemodel__ent_id": "_ent_id",
    "referencemodel__scope_id": "_scope_id",
}


def drop_reference_indexes(database=None):
    """Drop the reference indexes so the build does not maintain them."""
    database = database or ReferenceModel._meta.database
    for name in _REFERENCE_INDEXES:
        database.execute_sql(f'DROP INDEX IF EXISTS "{name}"')


def ensure_reference_indexes(database=None):
    """Rebuild them. Idempotent, so an already-indexed database is untouched."""
    flush_reference_writes()
    database = database or ReferenceModel._meta.database
    for name, column in _REFERENCE_INDEXES.items():
        database.execute_sql(
            f'CREATE INDEX IF NOT EXISTS "{name}" ON "referencemodel" ("{column}")'
        )


def _deliberate_unknown_kinds():
    """Kinds a bare-named or package placeholder is written with on purpose."""
    return {
        kind_id(name)
        for name in ("Java Unknown Variable Member", "Java Unknown Package")
    }


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
    flush_reference_writes()
    ensure_reference_indexes()
    placeholders = [e for e in EntityModel.select() if is_placeholder_kind(e._kind_id)]
    if not placeholders:
        return 0

    by_simple = {}
    file_kind = kind_id("Java File")
    for e in EntityModel.select():
        if is_placeholder_kind(e._kind_id):
            continue
        if e._kind_id == file_kind:
            # A file's long name is a path, and every one of them ends in
            # `.java` -- so the simple name this derives for it is `java`, and
            # a project with exactly one file made that the single candidate
            # for the unresolved `java` heading `java.lang.System.setProperty`.
            # Four references in the hand-written fixture pointed at the file
            # itself. A file is never what a name in source resolves to.
            continue
        by_simple.setdefault((e._longname or "").rsplit(".", 1)[-1], []).append(e)

    merged = 0
    for ghost in placeholders:
        if "external" in _kind_name(ghost._kind_id).lower().split():
            # `Java Unresolved External Method ...` means "outside the analysed
            # source", which is a decision, not a failure to qualify a name.
            # These carry a bare simple name on purpose -- it is what
            # Understand calls them -- and folding one would put every
            # `parse(...)` from com.jayway.jsonpath onto org.json.XML.parse.
            continue
        if ghost._kind_id in _deliberate_unknown_kinds() and (
            ghost._kind_id == kind_id("Java Unknown Package") or "." not in (ghost._longname or "")
        ):
            # A segment of a qualified name into a library outside the
            # analysed source -- `RuntimeSettings` in
            # `org.evosuite.runtime.RuntimeSettings.x` -- or the package it was
            # reached through. Understand names them exactly this way; folding
            # `runtime` into a project entity of that name is the
            # bare-simple-name failure, so they are left as written.
            continue
        if (ghost._longname or "").startswith(EXTERNAL_ROOTS):
            # A JDK long name is fully qualified by construction -- it is not a
            # local name a pass failed to qualify, so there is nothing here to
            # resolve. Folding it on the simple name turned
            # java.lang.Object.equals into org.json.JSONObject.Null.equals,
            # the only `equals` the project declares, and the reference then
            # pointed at itself from both ends.
            continue
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
        forget_entity_rows()
        merged += 1
    return merged


#: A call to one of these cannot be dispatched virtually, so Understand labels
#: it Nondynamic rather than Call.
_NONDYNAMIC_TOKENS = {"static", "private", "final", "constructor"}


def drop_orphan_placeholders():
    """Delete placeholder entities that no reference points at.

    A placeholder means "something is here but I could not identify it". With
    no reference at either end, nothing is here: the row is a name a pass
    speculated about and then never used. Most are created by the use pass for
    a name it cannot place -- `Character` in `Character.isDigit(c)` is a type,
    not a variable of the enclosing method, so it became
    `org.json.Cookie.escape.Character` -- and are orphaned when
    drop_shadowed_use_refs() removes the reference that named them.

    Only placeholder kinds. 126 entities on org.json have no reference at all
    and 4 of them are real declarations Understand also reports, mis-kinded
    rather than imaginary; those carry a real kind and are left alone.

    Runs after drop_shadowed_use_refs(), which is what orphans them.

    Returns the number of rows deleted.
    """
    flush_reference_writes()
    doomed = [
        e._id
        for e in EntityModel.select()
        if is_placeholder_kind(e._kind_id)
        and not ReferenceModel.select()
        .where(
            (ReferenceModel._ent == e._id)
            | (ReferenceModel._scope == e._id)
            | (ReferenceModel._file == e._id)
        )
        .exists()
    ]
    if not doomed:
        return 0
    # Nothing may point at them as a parent either, or the delete leaves a
    # dangling foreign key behind.
    EntityModel.update({EntityModel._parent: None}).where(
        EntityModel._parent << doomed
    ).execute()
    EntityModel.delete().where(EntityModel._id << doomed).execute()
    forget_entity_rows()
    return len(doomed)


def drop_nonvariable_deref_refs():
    """Delete Deref Partial references whose target is not a variable.

    `a.b` is a partial dereference only when `a` is a variable. In
    `org.evosuite.runtime.sandbox.Sandbox.goingToExecuteSUT()` the `org` is a
    *package* qualifier and Understand reports no dereference on it at all.

    The use pass already refuses a target it can see is not a variable, but it
    runs fourth and the entity is still an unresolved placeholder at that
    point -- the package pass upgrades the kind afterwards, and the row it
    guarded against is written anyway. Deciding it here, once every pass has
    run and the kinds are final, is the same reason relabel_nondynamic_calls()
    and drop_shadowed_use_refs() live here.

    The same holds for the Set and Modify variants: `a.b = v` sets a field of
    `a`, and `org.foo.BAR = v` does not. All 80 of testing_legacy_code's Set
    Deref Partial rows target a package or a placeholder, against 0 of JSON's
    8, 0 of TheAlgorithms' 467 and 0 of ganttproject's 161.

    Measured on Use Deref Partial: this removes 380 of testing_legacy_code's
    538 rows, which is where its 53% precision came from, and 0 of JSON's 781,
    0 of calculator_app's, 6 of TheAlgorithms' 2402 and 0 of jfreechart's
    30063 -- every one of those targets a real declared variable or parameter.

    Returns the number of references deleted.
    """
    flush_reference_writes()
    # One lookup per distinct target, not one per reference. The question is
    # about the target's kind and thousands of dereferences share a few hundred
    # targets: this was 1.15s of a 2.19s incremental update, and it is the same
    # N+1 `relabel_nondynamic_calls` had.
    verdicts = {}

    def is_doomed(entity_id):
        try:
            return verdicts[entity_id]
        except KeyError:
            target = EntityModel.get_or_none(_id=entity_id)
            answer = (
                target is None
                or is_placeholder_kind(target._kind_id)
                or kind_family(target._kind_id) != "variable"
            )
            verdicts[entity_id] = answer
            return answer

    # The target is _ent on the forward reference and _scope on its inverse.
    doomed = set()
    for name, side in (
        ("Java Use Deref Partial", "_ent_id"),
        ("Java Useby Deref Partial", "_scope_id"),
        ("Java Set Deref Partial", "_ent_id"),
        ("Java Setby Deref Partial", "_scope_id"),
        ("Java Modify Deref Partial", "_ent_id"),
        ("Java Modifyby Deref Partial", "_scope_id"),
    ):
        kind = KindModel.get_or_none(KindModel._name == name)
        if kind is None:
            continue
        for ref in ReferenceModel.select().where(ReferenceModel._kind == kind._id):
            if is_doomed(getattr(ref, side)):
                doomed.add(ref._id)
    if not doomed:
        return 0
    ReferenceModel.delete().where(ReferenceModel._id << list(doomed)).execute()
    return len(doomed)


def drop_external_inverse_refs():
    """Delete inverse references whose referenced entity is a placeholder.

    Understand writes an inverse only when the referenced entity is one the
    project declares. A call to `java.lang.String.trim` gets a `Java Call` and
    no `Java Callby`, because there is no analysed entity to hang the inverse
    on; a call to a project method gets both. Measured on JSON, the split is
    exact across every asymmetric kind -- of 8,251 `Java Call` rows Understand
    emits, the 4,651 carrying an inverse target a project entity and the other
    3,600 target none, with no exception either way. The same 100/0 split holds
    for Typed (1,380 of 3,357), Create (1,087 of 1,467), DotRef, Overrides,
    Use Cast, Use Annotation (11 of 798) and Typed GenericArgument (26 of 378).

    Writing both halves unconditionally is therefore wrong on 18 reference
    kinds at once, and every surplus row is unmatchable by construction. On
    JSON it costs roughly 9,000 rows: `Java Callby` alone stood at 7,633
    against Understand's 4,651.

    The test is the entity's kind. Placeholders -- the kinds carrying `Unknown`
    or `Unresolved` -- are exactly the entities this project never saw
    declared, which is the same population Understand declines to hang an
    inverse on. Verified against its output: of our `Java Callby` rows whose
    callee is a real kind, Understand keeps 3,370 of 3,375; of those whose
    callee is `Java Unknown Method Member` or `Java Unknown Class Type Member`,
    it keeps 0 of 3,129.

    A `Java Useby` on a package holding no type is the second population; see
    the comment on the second statement below.

    Runs after merge_placeholder_entities(), which upgrades every placeholder
    it can resolve -- deciding before the merge would delete inverses for
    entities that are about to become real.

    Returns the number of references deleted.
    """
    flush_reference_writes()
    # Which half of a pair is the inverse comes from the seed file, whose lines
    # are `forward | inverse`. It cannot come from KindModel._inv: that is set
    # on *both* halves and they point at each other, so a `_inv_id IS NULL`
    # test selects entity kinds and quietly deletes nothing.
    seed = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "java_ref_kinds.txt"
    )
    inverse_names = []
    with open(seed, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line and not line.startswith("#") and "|" in line:
                inverse_names.append(line.split("|", 1)[1].strip())
    if not inverse_names:
        return 0

    placeholders = ",".join("?" * len(inverse_names))
    cursor = ReferenceModel._meta.database.execute_sql(
        f"""
        DELETE FROM referencemodel
         WHERE _kind_id IN (SELECT _id FROM kindmodel WHERE _name IN ({placeholders}))
           AND _scope_id IN (SELECT e._id FROM entitymodel e
                              JOIN kindmodel k ON k._id = e._kind_id
                             WHERE k._name LIKE '%Unknown%'
                                OR k._name LIKE '%Unresolved%')
        """,
        inverse_names,
    )
    dropped = cursor.rowcount

    # The implicit array `length` is one global entity Understand reads with a
    # Use, and like a JDK member it has no inverse: every `Useby`/`Useby
    # Return` hung on it was ours alone. Its kind is concrete -- that is what
    # keeps the merge from folding the bare name -- so the test above, which
    # keys on placeholder kinds, never saw it.
    cursor = ReferenceModel._meta.database.execute_sql(
        f"""
        DELETE FROM referencemodel
         WHERE _kind_id IN (SELECT _id FROM kindmodel WHERE _name IN ({placeholders}))
           AND _scope_id IN (SELECT e._id FROM entitymodel e
                              JOIN kindmodel k ON k._id = e._kind_id
                             WHERE e._longname = 'length'
                               AND k._name LIKE '%Implicit%')
        """,
        inverse_names,
    )
    dropped += cursor.rowcount

    # A package that declares no type is the second population, and it is not
    # a placeholder: `org` is a real `Java Package` because
    # `org.craftedsw.harddependencies` is, but nothing declares `package org;`
    # and no type sits directly in it. Understand writes a `Java Use` at every
    # such package -- 304 of them on testing_legacy_code, one per qualified
    # name starting `org.` -- and hangs no `Java Useby` on any. On freemind's
    # `freemind.modes`, a package full of classes, all 238 inverses are there.
    #
    # Restricted to Useby, and measured before it was: the rule stated over
    # every inverse kind also deletes `Java Declarein`, which Understand does
    # hang on an empty package. `package com.calculator.app;` declares `com`
    # and `com.calculator` as well, and calculator_app lost 16 matched rows to
    # that before the kind was pinned down.
    cursor = ReferenceModel._meta.database.execute_sql(
        """
        DELETE FROM referencemodel
         WHERE _kind_id = (SELECT _id FROM kindmodel WHERE _name = 'Java Useby')
           AND _scope_id IN (
                 SELECT e._id FROM entitymodel e
                   JOIN kindmodel k ON k._id = e._kind_id
                  WHERE k._name = 'Java Package'
                    AND NOT EXISTS (SELECT 1 FROM entitymodel c
                                      JOIN kindmodel ck ON ck._id = c._kind_id
                                     WHERE ck._name <> 'Java Package'
                                       AND c._longname = e._longname || '.' || c._name))
        """
    )
    return dropped + cursor.rowcount


def drop_unresolved_scoped_use_refs():
    """Delete a Use whose target is a placeholder invented inside the reader.

    `use_useby` records every bare identifier it walks past, and the write
    layer gives an unresolvable one the only long name it can invent: the
    reading scope plus the identifier. For a real local that is exactly right
    -- `org.json.CDL.getValue.c` is where `c` lives. For the head of a
    qualified name it is a fiction. `java.lang.System.setProperty(...)` made
    `...setSystemProperties.java`, a `Java Unknown Variable Member` no
    declaration pass ever created, and 192 rows of testing_legacy_code pointed
    at six of them.

    Understand puts an *unresolved* entity there instead, named by the bare
    segment, and this project refuses bare simple names as targets because
    `merge_placeholder_entities()` would fold them into whichever project
    entity happens to share the name. Emitting nothing is the consistent
    choice, and it is the same rule the call pass already follows: ask the
    symbol table, and when it refuses, write no row.

    The test is that the target is a placeholder *and* its long name sits
    inside the reading scope's -- a placeholder the reader itself invented.
    A placeholder that resolves elsewhere, `java.lang.Class` or an unresolved
    field of another type, is a genuine reference to something outside the
    project and is kept. Measured: 192 rows on testing_legacy_code, 87 on
    JSON, 17 on TheAlgorithms, and not one of them a reference Understand
    reports, so no matched row is lost on any of the three.

    Runs after merge_placeholder_entities(), which upgrades every placeholder
    it can resolve.

    Returns the number of references deleted.
    """
    flush_reference_writes()
    # A `Java Use` names its target in _ent and the reader in _scope; the
    # inverse swaps them. substr() rather than LIKE: `_` is a single-character
    # wildcard in LIKE and Java identifiers are full of them, so
    # `TripService_Original` would match names it is not a prefix of.
    cursor = ReferenceModel._meta.database.execute_sql(
        """
        DELETE FROM referencemodel WHERE _id IN (
            SELECT r._id FROM referencemodel r
              JOIN kindmodel k ON k._id = r._kind_id
              JOIN entitymodel t ON t._id = CASE WHEN k._name = 'Java Use'
                                                 THEN r._ent_id ELSE r._scope_id END
              JOIN entitymodel s ON s._id = CASE WHEN k._name = 'Java Use'
                                                 THEN r._scope_id ELSE r._ent_id END
              JOIN kindmodel tk ON tk._id = t._kind_id
             WHERE k._name IN ('Java Use', 'Java Useby')
               AND (tk._name LIKE '%Unknown%' OR tk._name LIKE '%Unresolved%')
               AND substr(t._longname, 1, length(s._longname) + 1)
                   = s._longname || '.'
        )
        """
    )
    return cursor.rowcount


def relabel_return_uses():
    """Turn a plain Use into a Use Return where the use pass marked a returned
    value, keeping the plain row's entity.

    `use_variants` knows *that* `this.f` in `return this.f;` is returned but
    resolves `f` by name; the field pass resolves it against the receiver's
    type. So where both wrote a row at one token, the plain row is relabelled
    and the marker removed, with each inverse following its forward row. A
    marker with no plain row beside it stays, unless it names a placeholder.
    Returns the number of plain rows relabelled.
    """
    flush_reference_writes()
    database = ReferenceModel._meta.database
    database.execute_sql(
        'CREATE INDEX IF NOT EXISTS "referencemodel__position" '
        'ON "referencemodel" ("_file_id", "_line", "_column")'
    )
    ids = {
        name: kind_id(name)
        for name in ("Java Use", "Java Useby", "Java Use Return", "Java Useby Return")
    }
    same_position = """
        other._file_id = r._file_id AND other._line = r._line
        AND other._column = r._column"""
    plain = database.execute_sql(f"""
        SELECT r._id, r._kind_id FROM referencemodel r
         WHERE r._kind_id IN (?, ?)
           AND EXISTS (SELECT 1 FROM referencemodel other
                        WHERE {same_position} AND other._kind_id = ?)""",
        (ids["Java Use"], ids["Java Useby"], ids["Java Use Return"]),
    ).fetchall()
    if plain:
        # The markers first, while they are still the only Return rows there.
        database.execute_sql(f"""
            DELETE FROM referencemodel
             WHERE _kind_id IN (?, ?)
               AND EXISTS (SELECT 1 FROM referencemodel other
                            WHERE other._file_id = referencemodel._file_id
                              AND other._line = referencemodel._line
                              AND other._column = referencemodel._column
                              AND other._kind_id = ?)""",
            (ids["Java Use Return"], ids["Java Useby Return"], ids["Java Use"]),
        )
        relabel = {ids["Java Use"]: ids["Java Use Return"],
                   ids["Java Useby"]: ids["Java Useby Return"]}
        for row_id, kind in plain:
            database.execute_sql(
                "UPDATE referencemodel SET _kind_id = ? WHERE _id = ?",
                (relabel[kind], row_id),
            )
    database.execute_sql("""
        DELETE FROM referencemodel
         WHERE _kind_id IN (?, ?)
           AND (CASE WHEN _kind_id = ? THEN _ent_id ELSE _scope_id END) IN
               (SELECT e._id FROM entitymodel e JOIN kindmodel k ON k._id = e._kind_id
                 WHERE k._name LIKE '%Unknown%' OR k._name LIKE '%Unresolved%')""",
        (ids["Java Use Return"], ids["Java Useby Return"], ids["Java Use Return"]),
    )
    return len(plain)


def drop_shadowed_use_refs():
    """Delete plain Java Use/Useby where a more specific kind sits on it.

    Understand reports exactly one reference kind per (entity, scope,
    position): `x` in `x.next()` is a Use Deref Partial, an assignment target
    is a Set, `i++` is a Modify -- and in none of those cases does it also
    report a plain Use. Measured on the JSON benchmark: 0 of 1810 Use
    references share a position with a variant.

    The Use pass cannot make this call itself. It walks one file and runs
    before set/dotref/modify have written anything, so the more specific fact
    does not exist yet. Deciding it here, after every pass over every file, is
    what makes it answerable -- the same reason relabel_nondynamic_calls()
    lives here.

    Returns the number of references deleted.
    """
    flush_reference_writes()
    database = ReferenceModel._meta.database
    # The EXISTS below is correlated on (file, line, column), and without an
    # index on those three SQLite rescans the whole reference table for every
    # candidate row: 8.39s of a 23.8s build of JSON, the single largest step in
    # it and larger than the entire per-file loop's write layer. Built here
    # rather than kept in `_REFERENCE_INDEXES` because it earns its keep only
    # for this statement, and the build deliberately does not maintain
    # reference indexes while it is inserting.
    database.execute_sql(
        'CREATE INDEX IF NOT EXISTS "referencemodel__position" '
        'ON "referencemodel" ("_file_id", "_line", "_column")'
    )
    # Any other kind at the identical position wins, whatever its endpoints.
    # Matching endpoints too was stricter than Understand: a DotRef resolves
    # its receiver to java.lang.Character where the use pass leaves an
    # unresolved placeholder, so the two rows describe the same fact under
    # different names and the plain Use survived. Position is the rule --
    # Understand emits no plain Use at a position carrying a variant, 0 of 1810
    # on JSON. Enumerating the variants instead would silently stop shadowing
    # the day a new one is added. Measured: this drops 110 rows on JSON and 895
    # on TheAlgorithms, and not one of them is a reference Understand reports
    # as a plain Use.
    #
    # Typed is the exception. `x instanceof Character v` is a Use of Character
    # *and* v Typed Character, at the same token, and Understand keeps both --
    # 74 positions on jenetics, none on JSON or TheAlgorithms, which have no
    # patterns. They are two facts about two entities, not one fact twice.
    #
    # A module's Use is kept too: `provides p.S with p.Impl` is a Use of
    # p.Impl and a DotRef of p at the same token, and Understand keeps both.
    # Exempting DotRef everywhere instead added 2,382 false Uses on JSON,
    # which this project writes beside a DotRef where Understand does not.
    cursor = database.execute_sql("""
        DELETE FROM referencemodel
         WHERE _kind_id IN (SELECT _id FROM kindmodel
                             WHERE _name IN ('Java Use', 'Java Useby'))
           AND EXISTS (SELECT 1 FROM referencemodel other
                        WHERE other._file_id  = referencemodel._file_id
                          AND other._line     = referencemodel._line
                          AND other._column   = referencemodel._column
                          AND other._kind_id NOT IN
                              (SELECT _id FROM kindmodel
                                WHERE _name IN ('Java Use', 'Java Useby',
                                                'Java Typed', 'Java Typedby')))
           AND NOT EXISTS (SELECT 1 FROM entitymodel m
                            WHERE m._id IN (referencemodel._scope_id,
                                            referencemodel._ent_id)
                              AND m._kind_id = (SELECT _id FROM kindmodel
                                                 WHERE _name = 'Java Module'))
        """)
    return cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0


def drop_duplicate_bare_call_refs():
    """Delete a bare-name callee when a resolved one sits at the same position.

    `super.withKeepStrings(v)` produces two Call rows at the identical
    (file, line, column): the call pass resolves it to
    `org.json.ParserConfiguration.withKeepStrings`, and a second pass leaves a
    bare `withKeepStrings` placeholder that never merged (three classes override
    it, so `merge_placeholder_entities()` has more than one candidate and folds
    nothing). Understand records only the resolved call, so the bare row is a
    pure duplicate -- it inflates CountOutput, which counts distinct callees,
    and it is a bare simple name the codebase otherwise refuses to store.

    Position is the rule, as in `drop_shadowed_use_refs`: a call site belongs to
    one scope, so a resolved Call-family row at the same (file, line, column) is
    the same call. Only 4 rows on JSON, all `super.method()`.

    Returns the number of references deleted.
    """
    flush_reference_writes()
    database = ReferenceModel._meta.database
    database.execute_sql(
        'CREATE INDEX IF NOT EXISTS "referencemodel__position" '
        'ON "referencemodel" ("_file_id", "_line", "_column")'
    )
    cursor = database.execute_sql("""
        DELETE FROM referencemodel
         WHERE _kind_id IN (SELECT _id FROM kindmodel
                             WHERE _name IN ('Java Call', 'Java Call Nondynamic'))
           AND _ent_id IN (SELECT _id FROM entitymodel WHERE instr(_longname, '.') = 0)
           AND EXISTS (SELECT 1 FROM referencemodel other
                        JOIN entitymodel oe ON oe._id = other._ent_id
                        WHERE other._file_id = referencemodel._file_id
                          AND other._line    = referencemodel._line
                          AND other._column  = referencemodel._column
                          AND other._kind_id IN
                              (SELECT _id FROM kindmodel
                                WHERE _name IN ('Java Call', 'Java Call Nondynamic'))
                          AND instr(oe._longname, '.') > 0)
        """)
    return cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0


def _declared_in_final_class(entity):
    """Whether a project method's declaring class is declared `final`."""
    if entity._parent_id is None or kind_family(entity._kind_id) != "method":
        return False
    owner = EntityModel.get_or_none(_id=entity._parent_id)
    if owner is None:
        return False
    tokens = set(_kind_name(owner._kind_id).lower().split())
    return "final" in tokens and "class" in tokens and not {"record", "enum"} & tokens


def invocation_is_nondynamic(constructor):
    """Whether `this(...)`/`super(...)` naming `constructor` is Call Nondynamic.

    Understand labels such a call Nondynamic when the target is private or its
    class is final (not a record or an enum) -- the rule for methods. Read off
    jenetics: 5 of 5 such calls, and none of the 33 others. `new X(...)` is a
    plain Call whatever X is, which is why relabel_nondynamic_calls() leaves
    constructors alone and the call writer applies this instead.
    """
    if "private" in _kind_name(constructor._kind_id).lower().split():
        return True
    return _declared_in_final_class(constructor)


def relabel_nondynamic_calls(file_ids=None):
    """Split Java Call into Call/Call Nondynamic once targets are known.

    Whether a call is virtual depends on the callee's modifiers, which the call
    site cannot see -- especially across files. Deciding it here, after
    merge_placeholder_entities() has resolved the targets, is what makes it
    answerable at all.

    `file_ids` restricts the scan to calls occurring in those files, which is
    what an incremental update wants: it re-analyses a file and every file
    depending on it, and a call anywhere else cannot have changed. Scanning the
    whole project after each edit was half of `update_files`' runtime. The
    dependency closure is what makes the restriction safe -- finality is a
    property of the *callee*, so making a method final has to reach its
    callers, and `dependent_files()` already pulls in every file referencing a
    type the edited file declares.

    Returns the number of references relabelled.
    """
    flush_reference_writes()
    pairs = [
        ("Java Call", "Java Callby"),
        ("Java Call Nondynamic", "Java Callby Nondynamic"),
    ]
    ids = {}
    for forward, inverse in pairs:
        for name in (forward, inverse):
            row = KindModel.get_or_none(KindModel._name == name)
            if row is None:
                return 0
            ids[name] = row._id

    # One lookup per distinct callee, not one per call. A project-wide scan
    # asks about 12,902 references on JSON and gets 3,015 distinct answers.
    verdicts = {}

    def is_nondynamic(entity_id):
        if entity_id in verdicts:
            return verdicts[entity_id]
        verdicts[entity_id] = answer = _is_nondynamic(entity_id)
        return answer

    def _is_nondynamic(entity_id):
        entity = EntityModel.get_or_none(_id=entity_id)
        if entity is None:
            return False
        longname = entity._longname or ""
        owner, _, simple = longname.rpartition(".")
        # Checked before anything else. A constructor is never virtual and
        # `constructor` is in _NONDYNAMIC_TOKENS, yet Understand reports every
        # `new X(...)` as a plain Java Call -- 219 on JSON, 433 on
        # TheAlgorithms, not one of them Nondynamic. Testing the kind first
        # relabelled all of them and cost 17 points of Call Nondynamic
        # precision.
        if owner and owner.rsplit(".", 1)[-1] == simple:
            return False
        # So is a record's implicit canonical constructor, which carries the
        # record's own long name rather than R.R.
        if "constructor" in _kind_name(entity._kind_id).lower().split():
            return False
        # A call to a record accessor targets the component's *field*, which
        # is private -- and Understand still reports it as a plain Call.
        if kind_family(entity._kind_id) == "variable":
            return False
        if set(_kind_name(entity._kind_id).lower().split()) & _NONDYNAMIC_TOKENS:
            return True
        # A method of a *final class* cannot be overridden either: Understand
        # labels 142 of 142 such calls on jenetics Nondynamic. Not a record or
        # an enum, though both are implicitly final -- 24 of 26 record calls
        # there are a plain Call.
        if _declared_in_final_class(entity):
            return True
        # A JDK callee carries no modifiers here -- it is a placeholder named
        # from the receiver's type, never a declaration this project parsed.
        # Its class being final is what settles it: nothing can override
        # java.lang.String.length, so the call cannot dispatch virtually.
        # These are 303 of TheAlgorithms' missing Call Nondynamic rows for
        # String alone, and 180 of JSON's.
        #
        # A static or final *method* on a class that is neither settles the
        # rest: java.util.Collections is not final and
        # `Collections.emptyList()` is still Nondynamic. The index records
        # which names those are, per type.
        return jdk_index.is_final(owner) or jdk_index.cannot_dispatch(owner, simple)

    relabelled = 0
    # The callee is _ent on a Call and _scope on its inverse.
    for kind_name, target, callee in (
        ("Java Call", "Java Call Nondynamic", "_ent_id"),
        ("Java Callby", "Java Callby Nondynamic", "_scope_id"),
    ):
        query = ReferenceModel.select().where(ReferenceModel._kind == ids[kind_name])
        if file_ids is not None:
            query = query.where(ReferenceModel._file.in_(list(file_ids)))
        hits = [ref._id for ref in query if is_nondynamic(getattr(ref, callee))]
        if hits:
            # One UPDATE rather than a save() per row: the whole point of
            # scoping this pass is that it stops costing an edit anything.
            ReferenceModel.update(_kind=ids[target]).where(
                ReferenceModel._id.in_(hits)
            ).execute()
            relabelled += len(hits)
    return relabelled


def retarget_compact_constructor_reads():
    """Inside a record's compact constructor a component's name is the
    *parameter*, not the field.

    `record Accuracy(double relative, ...) { public Accuracy { if
    (Double.isNaN(relative)) ... } }` reads the parameter Accuracy.relative --
    and the field is also Accuracy.relative, so every pass resolving the name
    by long name landed on whichever row came first, the field. Understand
    gives Accuracy a PercentLackOfCohesion of 100 (no method touches a field);
    with the reads on the field it was 0.

    The constructor that `Define Implicit`s a parameter is the canonical one;
    its references to the field of that name are moved to the parameter, both
    halves. Returns the number of rows moved.
    """
    flush_reference_writes()
    database = ReferenceModel._meta.database
    define_implicit = kind_id("Java Define Implicit")
    pairs = database.execute_sql(
        """
        SELECT r._scope_id, p._id, f._id
          FROM referencemodel r
          JOIN entitymodel p ON p._id = r._ent_id
          JOIN entitymodel f ON f._longname = p._longname AND f._id != p._id
         WHERE r._kind_id = ?
        """,
        (define_implicit,),
    ).fetchall()
    moved = 0
    for constructor, parameter, field in pairs:
        if kind_family(EntityModel.get_by_id(constructor)._kind_id) != "method":
            continue
        if not _parameter_vs_member(
            EntityModel.get_by_id(parameter)._kind_id,
            EntityModel.get_by_id(field)._kind_id,
        ):
            continue
        moved += database.execute_sql(
            "UPDATE referencemodel SET _ent_id = ? WHERE _scope_id = ? AND _ent_id = ?",
            (parameter, constructor, field),
        ).rowcount
        moved += database.execute_sql(
            "UPDATE referencemodel SET _scope_id = ? WHERE _ent_id = ? AND _scope_id = ?"
            " AND _kind_id != ?",
            (parameter, constructor, field, define_implicit),
        ).rowcount
    return moved


def finalise_analysis(file_ids=None):
    """The project-wide passes that must run after every file has been written.

    Seven passes in a fixed order, and the order is load-bearing: the merge runs
    first so that an entity about to become real is not read as external, and
    the inverse and shadow drops run after it for the same reason. The bare-call
    drop runs after `relabel_nondynamic_calls` so both Call kinds are settled.

    One function because there were three copies of this list -- in
    `start_parsing()`, in `mcp_server.analyze()` and in
    `scripts/compare/02_build_ou.py` -- kept in step by a comment saying
    "all six, in this order, exactly as the others run them". A fourth caller,
    `api.update_files()`, ran two of the six, so an updated database carried
    114 rows a rebuilt one does not: plain `Java Use` shadowed by a variant,
    and inverses hung on `java.lang.StringBuilder` and friends that Understand
    never writes.

    `file_ids` is passed through to `relabel_nondynamic_calls`, the only one of
    the six an incremental update can scope. Returns the counts, keyed by pass.
    """
    return {
        "merged_placeholders": merge_placeholder_entities(),
        "relabelled_calls": relabel_nondynamic_calls(file_ids=file_ids),
        "duplicate_bare_calls_dropped": drop_duplicate_bare_call_refs(),
        "nonvariable_deref_dropped": drop_nonvariable_deref_refs(),
        "return_uses_relabelled": relabel_return_uses(),
        "shadowed_use_dropped": drop_shadowed_use_refs(),
        "external_inverses_dropped": drop_external_inverse_refs(),
        "unresolved_use_dropped": drop_unresolved_scoped_use_refs(),
        "orphan_placeholders_dropped": drop_orphan_placeholders(),
        "compact_constructor_reads": retarget_compact_constructor_reads(),
    }


class MetricModel(Model):
    """One computed metric value, so a second query does not recompute it.

    Understand computes metrics during analysis and stores them, which is most
    of why its `ent.metric()` costs microseconds where this project's costs
    milliseconds. Computing the whole set at analysis time here would add ~99s
    to a 58s build of the JSON benchmark, because the computation is Python
    over SQL rather than C++ over an in-memory graph -- so it is filled on
    demand instead: the first caller pays, every later one reads, including in
    another process.

    Written best-effort. A database opened read-only still answers, just
    without remembering.
    """

    _id = AutoField()
    #: A plain integer, not a foreign key: this table is a cache, and the
    #: constraint would cost an index maintenance per insert for nothing.
    _ent_id = IntegerField(index=True)
    _name = CharField(max_length=64)
    #: Stored as text because a metric value is an int, a float or a string
    #: (`RatioCommentToCode` is "0.53"), and the caller knows which.
    _value = CharField(max_length=64, null=True)

    class Meta:
        indexes = ((("_ent_id", "_name"), True),)


class ProjectModel(Model):
    name = CharField(max_length=128)
    language = CharField(max_length=128, default="Java")
    root = CharField(max_length=1024)
    db_path = CharField(max_length=1024, unique=True)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)
