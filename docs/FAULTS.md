# Fault Reports (Part 6)

Faults discovered while building the isolated unit-test suite for
`openunderstand/oudb/api.py`. Each entry below is written as a ready-to-file
GitHub issue: copy it into a new issue at
<https://github.com/m-zakeri/OpenUnderstand/issues>.

The two confirmed, test-backed faults (#1 and #2) are reproduced by `xfail`
tests already in the suite, so they are documented without breaking the CI
"all tests passing" gate.

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
`tests/test_kind.py::test_inv_on_reference_kind_returns_forward_kind`
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
`tests/test_entity_and_db.py::test_lookup_without_kind_filter_should_find_entities`
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
