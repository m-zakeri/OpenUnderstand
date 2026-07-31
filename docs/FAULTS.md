# Fault Reports (Part 6)

Faults discovered while building the isolated unit-test suite for
`openunderstand/oudb/api.py`. Each entry below is written as a ready-to-file
GitHub issue: copy it into a new issue at
<https://github.com/m-zakeri/OpenUnderstand/issues>.

The three confirmed, test-backed faults (#1, #2 and #5) are reproduced by
`xfail` tests already in the suite, so they are documented without breaking the
CI "all tests passing" gate.

## Filed issue links

| Fault | Failing test | Issue URL |
|---|---|---|
| #1 `Kind.inv()` raises `TypeError` | `tests/unit/test_kind.py::test_inv_on_reference_kind_returns_forward_kind` | _to be filled in after filing_ |
| #2 `Db.lookup(name)` returns `[]` | `tests/unit/test_entity_and_db.py::test_lookup_without_kind_filter_should_find_entities` | _to be filled in after filing_ |
| #5 `Db.relative_file_name()` escapes the project root | `tests/property/test_api_properties.py::test_relative_file_name_preserves_the_basename` | _to be filled in after filing_ |

---

## Issue #1 — `Kind.inv()` raises `TypeError` for every reference kind

**Labels:** bug, api

### Summary
`openunderstand.oudb.api.Kind.inv()` always raises `TypeError` when called on a
valid reference kind. The inverse of a reference kind (e.g. `Java Callby` →
`Java Call`) can therefore never be retrieved through the public API.

### Environment
- OpenUnderstand @ `master`
- Python 3.12 (also reproduces on 3.10/3.11)
- peewee 3.14.4
- OS: Windows 11 / Ubuntu 22.04

### Root cause
`api.py`, in `Kind.inv()`:

```python
inverse = KindModel.get_by_id(pk=self._inv)
return Kind(**inverse.__data__.get("__data__"))   # <-- bug
```

`inverse.__data__` is already peewee's field-data dict. Calling
`.get("__data__")` on it returns `None`, so the call becomes `Kind(**None)`,
which raises `TypeError`. Every other site in `api.py` correctly uses
`inverse.__dict__.get("__data__")` (e.g. lines 428, 445, 499, 755, 1130, 1386).

### Steps to reproduce
```python
from openunderstand.oudb import api
from openunderstand.oudb.models import KindModel
# given a reference kind "Java Callby" whose _inv points at "Java Call"
callby = KindModel.get(_name="Java Callby")
api.Kind(**callby.__dict__["__data__"]).inv()
```

### Expected behaviour
Returns a `Kind` whose `name()` is `"Java Call"`.

### Observed behaviour
```
TypeError: api.Kind() argument after ** must be a mapping, not NoneType
```

### Failing test
`tests/unit/test_kind.py::test_inv_on_reference_kind_returns_forward_kind`
(currently marked `xfail(raises=TypeError)`).

### Suggested fix (optional PR)
```diff
-        return Kind(**inverse.__data__.get("__data__"))
+        return Kind(**inverse.__dict__.get("__data__"))
```
After the fix, remove the `xfail` marker from the test above.

---

## Issue #2 — `Db.lookup(name)` without a kind filter always returns `[]`

**Labels:** bug, api

### Summary
`Db.lookup(name)` returns an empty list when called without the optional
`kindstring` argument, even when entities clearly match `name`. The optional
argument is documented as optional, so this is a contract violation.

### Root cause
`api.py`, in `Db.lookup()`, the final filtering loop runs unconditionally:

```python
for ent in query:
    if re.search(f'Java\\s+{kindstring}'.lower(), str(ent._kind._name).lower()):
        ents.append(...)
```

When `kindstring is None`, the pattern becomes the literal string
`"java\\s+none"`, which matches no real kind name, so every candidate is
filtered out and the method returns `[]`.

### Steps to reproduce
```python
db.lookup("Main")          # entities named "Main" exist -> returns []
db.lookup("Main", "Class") # works, returns the class entity
```

### Expected behaviour
With no `kindstring`, return all entities whose name/longname matches `name`,
regardless of kind.

### Observed behaviour
Always returns `[]`.

### Failing test
`tests/unit/test_entity_and_db.py::test_lookup_without_kind_filter_should_find_entities`
(currently marked `xfail`).

### Suggested fix (optional PR)
Only apply the kind regex when `kindstring` is provided:
```diff
-    for ent in query:
-        if re.search(f'Java\\s+{kindstring}'.lower(), str(ent._kind._name).lower()):
-            ents.append(Ent(**ent.__dict__.get("__data__")))
+    for ent in query:
+        if kindstring and not re.search(
+            rf'java\s+{kindstring}'.lower(), str(ent._kind._name).lower()
+        ):
+            continue
+        ents.append(Ent(**ent.__dict__.get("__data__")))
```

---

## Issue #5 — `Db.relative_file_name()` can escape the project root

**Labels:** bug, api

### Summary
`Db.relative_file_name(path)` uses `os.path.commonprefix`, which compares paths
**character by character** rather than by path component. When a file name and
the project root merely share a few leading characters, the method relativises
against a directory that does not exist, and returns a path that walks *out* of
the project with `..` — or collapses the file name entirely.

> Discovered by the Hypothesis property-based suite, not by hand: the property
> "relativising a path must never change its basename" was falsified within a
> few dozen generated examples.

### Environment
- OpenUnderstand @ `master`
- Python 3.12 (also reproduces on 3.10/3.11)
- OS: Windows 11 / Ubuntu 22.04

### Root cause
`api.py`, in `Db.relative_file_name()`:

```python
list_of_paths = [self._root, absolute_path]
common_prefix = os.path.commonprefix(list_of_paths)   # <-- character-wise
return os.path.relpath(absolute_path, common_prefix)
```

`os.path.commonprefix` is documented as operating on strings, **not** paths; the
standard library provides `os.path.commonpath` for the path-aware version.

### Steps to reproduce
```python
# project root = "com/example"
db.relative_file_name("common/Other.java")
# commonprefix(["com/example", "common/Other.java"]) == "com"
# -> relpath("common/Other.java", "com") == "../common/Other.java"

db.relative_file_name("c")
# commonprefix(["com/example", "c"]) == "c"
# -> relpath("c", "c") == "."          # the file name is lost entirely
```

### Expected behaviour
A path inside the project root is returned relative to it; a path outside the
root is either returned unchanged or rejected. The basename is never altered.

### Observed behaviour
`"../common/Other.java"` — a path that escapes the project root — and `"."` for
the second case, which loses the file name completely. Any reported source
location built on this is wrong.

### Failing tests
- `tests/property/test_api_properties.py::test_relative_file_name_preserves_the_basename`
  (property, marked `xfail`)
- `tests/property/test_api_properties.py::test_relative_file_name_can_escape_the_project_root`
  (deterministic reproduction, passes by asserting the buggy behaviour)

### Suggested fix (optional PR)
```diff
-        list_of_paths = [self._root, absolute_path]
-        common_prefix = os.path.commonprefix(list_of_paths)
-        return os.path.relpath(absolute_path, common_prefix)
+        try:
+            common = os.path.commonpath([self._root, absolute_path])
+        except ValueError:
+            # different drives / mix of absolute and relative -> not relativisable
+            return absolute_path
+        return os.path.relpath(absolute_path, common)
```

---

## Additional findings (lower priority)

These are noted for completeness; they are not gating the suite.

### Finding #3 — `Ent.refs()` crashes when called with no arguments
`refs(self, refkindstring=None, ...)` immediately does
`refkindstring.split(",")`, raising `AttributeError: 'NoneType' object has no
attribute 'split'` despite the docstring stating the argument is optional. The
method also contains leftover `print(...)` debug statements that pollute stdout.

**Suggested fix:** guard for `None`/empty and remove debug prints.

### Finding #4 — `Db.ents()` multi-token filter logic is contradictory
For a multi-token filter such as `"Class Public"`, `Db.ents()` builds one
condition per token and then applies both their **OR** and their **AND**:
```python
query.where(reduce(operator.or_, conditions)).where(reduce(operator.and_, conditions))
```
The `AND` requires a single entity's kind to satisfy every token's separate
`_kind IN (...)` subquery at once, which is generally impossible, so multi-token
filters silently return nothing. (A `# TODO: Complete this later` already marks
this code.)

**Suggested fix:** intersect the per-token kind sets first, or apply a single
`AND` over per-token `_name.contains(token)` conditions on `KindModel`.

### Finding #6 — `Db.ents()` returns a `set`, but its docstring promises a list
The docstring reads `oudb.ents([kindstring]) -> list of Ent`, and the commercial
Understand API returns a list. The implementation builds and returns a `set`, so
callers cannot index or slice the result, and iteration order is unspecified.
`Ent.ents()` has the mirror-image problem: it builds a `set` and then wraps it in
`list(...)`, so it *is* a list but its **order is non-deterministic**.

This is why the CI pipeline pins `PYTHONHASHSEED=0` — without it, set iteration
order varies per process and any test asserting on a multi-element result would
be flaky.

**Suggested fix:** return a list built in a deterministic order (e.g. sorted by
entity id), and de-duplicate explicitly rather than relying on `set`.

### Finding #7 — `Db.lookup()` interpolates user input into a regular expression
`Db.lookup()` builds its filter with an f-string:

```python
re.search(f'Java\\s+{kindstring}'.lower(), str(ent._kind._name).lower())
```

`kindstring` reaches `re.search` unescaped, so a caller passing regex
metacharacters changes the match semantics, and a pathological pattern such as
`"(a+)+$"` causes catastrophic backtracking (a ReDoS) on every candidate entity.
The same applies to `name`, which is passed to peewee's `contains()`.

**Suggested fix:** `re.escape(kindstring)`, or drop the regex entirely — the
surrounding SQL query already performs the kind filtering.

### Finding #8 — `fill.py` never persists the forward kind's inverse
In `openunderstand/oudb/fill.py::append_java_ref_kind`:

```python
inv_kind, _ = KindModel.get_or_create(_name=inv, is_ent_kind=False, _inv=ref_kind)
ref_kind.inverse = inv_kind      # <-- `inverse` is not a model field
return ref_kind.save()
```

`KindModel` declares `_inv`, not `inverse`, so this assignment sets an ordinary
Python attribute that `save()` never writes to the database. Only the *inverse*
kind gets its `_inv` populated; the forward kind's stays `NULL`.

Consequence: even after Fault #1 is fixed, `Kind("Java Call").inv()` still cannot
return `Java Callby` — the link only exists in one direction. The test fixtures
in `tests/conftest.py` reproduce this asymmetry deliberately, which is why the
inverse-reference test runs in the `Callby → Call` direction.

**Suggested fix:** `ref_kind._inv = inv_kind` before `save()`.
