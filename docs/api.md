# API reference

The API mirrors SciTools Understand's Python API. Where a method is
implemented, it takes the same arguments and returns the same shape. Where it
is not, it raises `NotImplementedError` rather than returning something
plausible and wrong.

```python
import openunderstand.ounderstand as und
db = und.open("myproject.udb")
```

## Filter strings

Several methods take a *kindstring* — the same filter grammar Understand uses.

| Syntax | Meaning |
| --- | --- |
| `"Class"` | kind name contains the word `Class` |
| `"Static Method"` | contains both words |
| `"Method ~Static"` | contains `Method`, does not contain `Static` |
| `"Class,Interface"` | either alternative |

Words match whole tokens of the kind name, so `"Call"` selects `Java Call` and
`Java Call Nondynamic` alike. Matching is case-insensitive; entity names are
not, because Java is not.

---

## Module functions

### `open(dbname)` → `Db`

Open a database. Raises `UnderstandError` if the file does not exist or holds
no project.

### `version()` → `str`

Build number of this module.

---

## `Db`

### `ents([kindstring])` → `list[Ent]`

Every entity, or those whose kind matches the filter.

```python
db.ents("Class")                 # all classes
db.ents("Method ~Static")        # instance methods only
```

### `ent_from_id(id)` → `Ent`

The entity with this database id.

### `lookup(name [, kindstring])` → `list[Ent]`

Entities whose name or long name matches the regular expression `name`. Pass a
compiled pattern for case-insensitive search:

```python
db.lookup(re.compile("json", re.I), "Class")
```

### `name()` → `str`

The project name.

### `language()` → `str`

`"Java"`.

### `relative_file_name(ent)` → `str`

A file entity's path relative to the project root.

### `close()`

Release the database.

*Not implemented:* `lookup_uniquename`, `metric`, `metrics`, `root_archs`.

---

## `Ent`

An entity: a file, class, method, variable, parameter, package.

### Identity

| Method | Returns |
| --- | --- |
| `name()` | `getValue` |
| `longname()` | `org.json.CDL.getValue` |
| `simplename()` | name without any qualification |
| `id()` | database id |
| `kind()` | the entity's `Kind` |
| `kindname()` | `Java Method Private Member` |
| `language()` | `"Java"` |
| `parent()` | enclosing entity, or `None` |
| `type()` | declared type, for variables and methods |
| `value()` | initialiser text, for variables |
| `contents()` | source text of the declaration |

### `refs([refkindstring [, entkindstring [, unique]]])` → `list[Ref]`

References whose scope is this entity.

```python
cls.refs()                          # everything
cls.refs("Define")                  # what it defines
cls.refs("Define", "Method")        # the methods it defines
cls.refs("Call", "", True)          # one reference per called entity
```

`unique` keeps the first reference to each distinct entity.

### `ref(...)` → `Ref | None`

The first result of `refs(...)`, or `None`.

### `ents(refkindstring [, entkindstring])` → `list[Ent]`

The entities on the far side of matching references — `refs()` with the
references thrown away.

### `filerefs([refkindstring [, entkindstring [, unique]]])` → `list[Ref]`

References in this file entity.

### `metric(names)` → `dict`

Metric values. An unrecognised name maps to `None`; a recognised but
unimplemented one raises `NotImplementedError`.

```python
cls.metric(["CountDeclMethodAll", "Cyclomatic"])
# {'CountDeclMethodAll': 12, 'Cyclomatic': 34}
```

### `metrics()` → `list[str]`

Names accepted by `metric()`. 63 names; 39 return values, 24 raise
`NotImplementedError`. The list is deduplicated and ordered.

*Not implemented:* `comments`, `depends`, `dependsby`, `draw`, `freetext`,
`ib`, `lexer`, `parameters`, `parsetime`, `uniquename`.

---

## `Ref`

One place an entity appears.

| Method | Returns |
| --- | --- |
| `kind()` | the reference's `Kind` |
| `kindname()` | `Java Call` |
| `ent()` | the entity referred to |
| `scope()` | the entity referring |
| `file()` | the file entity it occurs in |
| `line()` | 1-based line |
| `column()` | 1-based column |
| `isforward()` | whether this is the forward direction |

Every reference is stored twice, once in each direction, at the same file,
line and column. `Java Call` and `Java Callby` are the same fact read from
opposite ends.

---

## `Kind`

| Method | Returns |
| --- | --- |
| `name()` / `longname()` | `Java Call` |
| `check(kindstring)` | whether this kind matches a filter |
| `inv()` | the inverse reference kind; raises for an entity kind |
| `Kind.list_entity([filter])` | all entity kinds (static) |
| `Kind.list_reference([filter])` | all reference kinds (static) |

See [Kinds](kinds.md) for the full vocabulary.

---

## Differences from Understand

These are deliberate and measured, not accidental:

- **Long names carry no parameter list.** `org.json.JSONObject.put` names every
  overload of `put`, where Understand distinguishes them. Overloads therefore
  merge into one entity.
- **External types are not resolved.** No JDK or third-party jars are analysed,
  so `java.lang.String` exists as an unresolved entity with no members.
- **Java 8 only.** The grammar predates records, sealed types, `var`, text
  blocks and `yield`. Files using them fail to parse and contribute nothing.
- **Coverage is partial.** [Parity](parity.md) reports exactly how partial,
  per kind, against the real tool.
