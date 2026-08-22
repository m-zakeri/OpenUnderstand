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
    exact = [(row, words) for row, words in candidates
             if family in words and wanted <= words]
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
    loose = [(row, words) for row, words in candidates
             if family in (row._name or "").lower()
             and all(m in (row._name or "").lower() for m in wanted)]
    return _least_specific(loose) if loose else None


def _least_specific(candidates):
    """Fewest words, then the shortest name, then alphabetical.

    The shortest *name* has to stay in the ordering: `Java Enum Class Type
    Public Member` and `Java Abstract Enum Type Public Member` both carry six
    words and both satisfy ("Enum", ["public"]), and an enum is not abstract.
    Sorting on word count alone left the winner to whatever order the rows came
    back in.
    """
    row, _ = min(candidates,
                 key=lambda pair: (len(pair[1]), len(pair[0]._name or ""),
                                   pair[0]._name or ""))
    return row


@lru_cache(maxsize=8)
def _entity_kind_words(_database):
    return [(row, frozenset(w.lower() for w in (row._name or "").split()))
            for row in KindModel.select().where(KindModel.is_ent_kind == True)]  # noqa: E712


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
    # Where the declaration is. Understand separates overloads by declaration
    # site, not by name -- its long names carry no parameter list either, so
    # `println.print` names two entities there. Without a position this table
    # cannot express that, and every overload collapsed into one row.
    _line = IntegerField(null=True)
    _column = IntegerField(null=True)

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
        for row in cls.select().where(cls._longname == longname):
            row_placeholder = is_placeholder_kind(row._kind_id)
            if not (incoming_placeholder or row_placeholder
                    or kind_family(row._kind_id) == incoming_family):
                continue
            row_site = (row._line, row._column)
            if (all(incoming_site) and all(row_site) and incoming_site != row_site
                    and incoming_family == "method"):
                # Only methods overload. Two locals sharing a long name are the
                # same declaration seen twice -- `main.name` declared in two
                # blocks -- and splitting them by position produced 155 of the
                # duplicate rows the comparison reports.
                continue
            match = row
            if not row_placeholder:
                break  # prefer a row that already has a real kind
        if match is not None:
            dirty = False
            if is_placeholder_kind(match._kind_id) and not incoming_placeholder \
                    and incoming is not None:
                match._kind = incoming
                dirty = True
            if all(incoming_site) and not all((match._line, match._column)):
                match._line, match._column = incoming_site
                dirty = True
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
                    dirty = True
            if dirty:
                match.save()
            return match, False

        return super().create(**fields), True

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
                tuple(row) for row in cls.select(
                    cls._kind, cls._file, cls._line, cls._column, cls._ent, cls._scope
                ).tuples()
            }
            _REFERENCE_KEYS_DB = database
        if key in _REFERENCE_KEYS:
            return super().get_or_create(defaults=defaults, **kwargs)
        _REFERENCE_KEYS.add(key)
        return super().create(**fields), True

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
    define = KindModel.get_or_none(_name="Java Define")
    if define is None:
        return set(file_entity_ids)

    closure = set(file_entity_ids)
    pending = list(file_entity_ids)
    while pending:
        current = pending.pop()
        declared = []
        for ref in ReferenceModel.select().where(
            (ReferenceModel._kind == define._id)
            & (ReferenceModel._file == current)
        ):
            target = EntityModel.get_or_none(_id=ref._ent_id)
            if target is not None and kind_family(target._kind_id) == "type":
                declared.append(target._id)
        if not declared:
            continue
        for ref in ReferenceModel.select().where(
            (ReferenceModel._ent.in_(declared))
            | (ReferenceModel._scope.in_(declared))
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

    refs_removed = ReferenceModel.delete().where(
        ReferenceModel._file == file_entity_id
    ).execute()

    entities_removed = 0
    for entity_id in declared:
        entity = EntityModel.get_or_none(_id=entity_id)
        if entity is None or entity._id == file_entity_id:
            continue
        still_used = ReferenceModel.select().where(
            (ReferenceModel._ent == entity_id) | (ReferenceModel._scope == entity_id)
        ).exists()
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
                entity._line = entity._column = None
                entity._contents = ""
                entity.save()
            continue
        EntityModel.update({EntityModel._parent: None}).where(
            EntityModel._parent == entity_id
        ).execute()
        entity.delete_instance()
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
    database = database or ReferenceModel._meta.database
    for name, column in _REFERENCE_INDEXES.items():
        database.execute_sql(
            f'CREATE INDEX IF NOT EXISTS "{name}" ON "referencemodel" ("{column}")'
        )


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
    ensure_reference_indexes()
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
        if "external" in _kind_name(ghost._kind_id).lower().split():
            # `Java Unresolved External Method ...` means "outside the analysed
            # source", which is a decision, not a failure to qualify a name.
            # These carry a bare simple name on purpose -- it is what
            # Understand calls them -- and folding one would put every
            # `parse(...)` from com.jayway.jsonpath onto org.json.XML.parse.
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
    doomed = [
        e._id for e in EntityModel.select()
        if is_placeholder_kind(e._kind_id)
        and not ReferenceModel.select().where(
            (ReferenceModel._ent == e._id)
            | (ReferenceModel._scope == e._id)
            | (ReferenceModel._file == e._id)
        ).exists()
    ]
    if not doomed:
        return 0
    # Nothing may point at them as a parent either, or the delete leaves a
    # dangling foreign key behind.
    EntityModel.update({EntityModel._parent: None}).where(
        EntityModel._parent << doomed).execute()
    EntityModel.delete().where(EntityModel._id << doomed).execute()
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
    # The target is _ent on the forward reference and _scope on its inverse.
    doomed = set()
    for name, side in (("Java Use Deref Partial", "_ent_id"),
                       ("Java Useby Deref Partial", "_scope_id"),
                       ("Java Set Deref Partial", "_ent_id"),
                       ("Java Setby Deref Partial", "_scope_id"),
                       ("Java Modify Deref Partial", "_ent_id"),
                       ("Java Modifyby Deref Partial", "_scope_id")):
        kind = KindModel.get_or_none(KindModel._name == name)
        if kind is None:
            continue
        for ref in ReferenceModel.select().where(ReferenceModel._kind == kind._id):
            target = EntityModel.get_or_none(_id=getattr(ref, side))
            if target is None or is_placeholder_kind(target._kind_id) \
                    or kind_family(target._kind_id) != "variable":
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

    Runs after merge_placeholder_entities(), which upgrades every placeholder
    it can resolve -- deciding before the merge would delete inverses for
    entities that are about to become real.

    Returns the number of references deleted.
    """
    # Which half of a pair is the inverse comes from the seed file, whose lines
    # are `forward | inverse`. It cannot come from KindModel._inv: that is set
    # on *both* halves and they point at each other, so a `_inv_id IS NULL`
    # test selects entity kinds and quietly deletes nothing.
    seed = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "java_ref_kinds.txt")
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
    return cursor.rowcount


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
    cursor = ReferenceModel._meta.database.execute_sql(
        """
        DELETE FROM referencemodel
         WHERE _kind_id IN (SELECT _id FROM kindmodel
                             WHERE _name IN ('Java Use', 'Java Useby'))
           AND EXISTS (SELECT 1 FROM referencemodel other
                        WHERE other._file_id  = referencemodel._file_id
                          AND other._line     = referencemodel._line
                          AND other._column   = referencemodel._column
                          AND other._kind_id NOT IN
                              (SELECT _id FROM kindmodel
                                WHERE _name IN ('Java Use', 'Java Useby')))
        """
    )
    return cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0


def relabel_nondynamic_calls():
    """Split Java Call into Call/Call Nondynamic once targets are known.

    Whether a call is virtual depends on the callee's modifiers, which the call
    site cannot see -- especially across files. Deciding it here, after
    merge_placeholder_entities() has resolved the targets, is what makes it
    answerable at all.

    Returns the number of references relabelled.
    """
    pairs = [("Java Call", "Java Callby"),
             ("Java Call Nondynamic", "Java Callby Nondynamic")]
    ids = {}
    for forward, inverse in pairs:
        for name in (forward, inverse):
            row = KindModel.get_or_none(KindModel._name == name)
            if row is None:
                return 0
            ids[name] = row._id

    def is_nondynamic(entity_id):
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
        if set(_kind_name(entity._kind_id).lower().split()) & _NONDYNAMIC_TOKENS:
            return True
        # A JDK callee carries no modifiers here -- it is a placeholder named
        # from the receiver's type, never a declaration this project parsed.
        # Its class being final is what settles it: nothing can override
        # java.lang.String.length, so the call cannot dispatch virtually.
        # These are 303 of TheAlgorithms' missing Call Nondynamic rows for
        # String alone, and 180 of JSON's.
        return jdk_index.is_final(owner)

    relabelled = 0
    # The callee is _ent on a Call and _scope on its inverse.
    for kind_name, target, callee in (
        ("Java Call", "Java Call Nondynamic", "_ent_id"),
        ("Java Callby", "Java Callby Nondynamic", "_scope_id"),
    ):
        for ref in ReferenceModel.select().where(
            ReferenceModel._kind == ids[kind_name]
        ):
            if is_nondynamic(getattr(ref, callee)):
                ref._kind = ids[target]
                ref.save()
                relabelled += 1
    return relabelled


class ProjectModel(Model):
    name = CharField(max_length=128)
    language = CharField(max_length=128, default="Java")
    root = CharField(max_length=1024)
    db_path = CharField(max_length=1024, unique=True)

    def __str__(self):
        return str(self.name)

    def __repr__(self):
        return str(self.name)
