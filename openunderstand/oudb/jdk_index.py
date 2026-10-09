"""The JDK, as much of it as resolving external names needs.

Understand indexes the whole Java library. This project cannot, and for a long
time it compensated with five hand-written tables -- 208 entries spread over
symbol_table.py and models.py, each one added the day a benchmark tripped over
it: `java.lang` names, simple-name-to-package for wildcard imports, the type of
`System.out`, the members of the handful of interfaces a class might implement,
and which JDK classes are final. They were honest about being incomplete, and
every gap showed up as a wrong or missing reference: `new HashMap<>()` binding
to a project class, `String.length` reported as a virtual call, a class
implementing `Comparator` with no `Overrides` row.

`scripts/gen_jdk_index.py` generates the real thing from a JDK's own runtime
image -- 3,952 public java./javax. types with their modifiers, supertypes,
public fields, their methods' arities, and each method's return type where it
is a reference type. The result is committed as `jdk_index.txt.gz` (155 KB), so
neither a JDK nor an Understand licence is needed to use it.

Loaded once, on first access. The parse is a few milliseconds and this module
imports nothing outside the standard library, so it stays safe to reach from
anywhere -- including models.py, which sits below everything else.
"""

from __future__ import annotations

import gzip
import os
from functools import lru_cache

_PATH = os.path.join(os.path.dirname(__file__), "jdk_index.txt.gz")


@lru_cache(maxsize=1)
def _load() -> dict:
    types: dict[str, dict] = {}
    by_simple: dict[str, list[str]] = {}
    if not os.path.exists(_PATH):
        # An installed copy without the data file still works; every lookup
        # simply answers "unknown", which is the same answer the hand-written
        # tables gave for anything they did not list.
        return {"types": types, "by_simple": by_simple}
    with gzip.open(_PATH, "rt", encoding="utf8") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            parts = line.rstrip("\n").split("\t")
            # Five columns is the older format, which carries no member count
            # and no superclass; it still loads, answering 0 and "" for those.
            if len(parts) == 5:
                parts = parts + ["0", ""]
            if len(parts) != 7:
                continue
            longname, flags, supers, fields, methods, members, superclass = parts
            arities, returns, sealed = {}, {}, set()
            for item in methods.split(","):
                if item.startswith("!"):
                    # A name every overload of which is static or final.
                    sealed.add(item[1:])
                    continue
                if "/" not in item:
                    continue
                name, tail = item.split("/", 1)
                # `name/arity` or `name/arity>java.lang.Double` -- the return
                # type is present only where it is a reference type.
                arity, _, declared = tail.partition(">")
                arities[name] = int(arity)
                if declared:
                    returns[name] = declared
            types[longname] = {
                "final": "F" in flags,
                "interface": "I" in flags,
                "supers": supers.split(",") if supers else [],
                "fields": dict(
                    pair.split("=", 1) for pair in fields.split(",") if "=" in pair
                ),
                "methods": arities,
                "returns": returns,
                "sealed": sealed,
                # Declared members at this type -- constructors included, every
                # overload counted, at any visibility. This is what RFC sums
                # over the superclass chain: java.lang.Throwable is 27 and
                # org.json.JSONException's 53 is its own 3 plus 5, 5, 27, 13.
                "members": int(members or 0),
                # The superclass alone. Empty means java.lang.Object, which
                # javap never prints, or nothing at all for Object and for an
                # interface.
                "superclass": superclass,
            }
            if "N" not in flags:
                # A nested type is named through its outer type or an explicit
                # import, never by its bare simple name.
                by_simple.setdefault(longname.rsplit(".", 1)[-1], []).append(longname)
    return {"types": types, "by_simple": by_simple}


def resolve_simple(name: str, packages=()) -> str | None:
    """Long name for a JDK type's simple name, or None when it cannot be placed.

    A simple name is only accepted when it is unambiguous across the whole
    index, or when exactly one of the packages offered -- the file's wildcard
    imports -- declares it. 66 of the 3,957 names are ambiguous (`java.util.List`
    and `java.awt.List`), and guessing between them is what the packages are
    for.
    """
    candidates = _load()["by_simple"].get(name, ())
    if not candidates:
        return None
    if packages:
        offered = [c for c in candidates if c.rsplit(".", 1)[0] in packages]
        if len(offered) == 1:
            return offered[0]
        if offered:
            return None  # the imports do not settle it either
    return candidates[0] if len(candidates) == 1 else None


def package_of(name: str) -> str | None:
    """Package declaring a JDK simple name, when exactly one does."""
    longname = resolve_simple(name)
    return longname.rsplit(".", 1)[0] if longname else None


def is_final(longname: str) -> bool:
    """Whether a JDK type is declared final, so a call on it never dispatches."""
    entry = _load()["types"].get(longname)
    return bool(entry and entry["final"])


def cannot_dispatch(longname: str, member: str) -> bool:
    """Whether a call to a JDK method can never dispatch virtually: every
    overload of `member` declared at `longname` is static or final.

    Understand's split of Java Call from Java Call Nondynamic for a JDK
    callee: `List.of`, `Map.entry`, `BigDecimal.valueOf` are static and
    `Object.getClass`, `Enum.equals` final -- 151 of JSON's calls and 212 of
    jenetics', which a final *class* alone could not explain.
    """
    entry = _load()["types"].get(longname)
    return bool(entry and member in entry.get("sealed", ()))


def is_interface(longname: str) -> bool:
    """Whether a JDK type is an interface. False for anything not indexed."""
    return _load()["types"].get(longname, {}).get("interface", False)


def field_type(owner: str, field: str) -> str | None:
    """Declared type of a JDK type's public field -- `System.out` is a PrintStream."""
    entry = _load()["types"].get(owner)
    declared = entry["fields"].get(field) if entry else None
    # Primitive fields are indexed so a read can find the type declaring them
    # (`JSlider.HORIZONTAL` is SwingConstants'), but a primitive names no type
    # entity: answering `int` here put 162 couples to `int` on jhotdraw.
    return declared if declared and "." in declared else None


def members(longname: str) -> dict:
    """Member name -> parameter count, for an interface or java.lang.Object."""
    entry = _load()["types"].get(longname)
    return entry["methods"] if entry else {}


def declares(longname: str, member: str, arity: int) -> bool:
    """Whether a JDK type declares `member` taking `arity` parameters."""
    return members(longname).get(member) == arity


def supertypes(longname: str) -> list:
    """The types `longname` extends or implements directly. [] if not indexed."""
    entry = _load()["types"].get(longname)
    return entry["supers"] if entry else []


def declaring_type(longname: str, member: str, fields: bool = False) -> str | None:
    """The type in `longname`'s hierarchy that declares `member`.

    Understand attributes a call to the class that declares the method, not to
    the receiver's static type: `sb.append(x)` on a java.lang.StringBuilder is
    a call to java.lang.AbstractStringBuilder.append. That is the same rule
    symbol_table.declaring_type() applies inside the project, answered here
    from the generated hierarchy.

    Returns None when nothing in the chain declares it, so a caller keeps the
    static type rather than inventing one.
    """
    types = _load()["types"]
    seen, pending = set(), [longname]
    while pending:
        current = pending.pop(0)
        if current in seen:
            continue
        seen.add(current)
        entry = types.get(current)
        if entry is None:
            continue
        if member in entry["methods"] or (fields and member in entry["fields"]):
            return current
        pending.extend(entry["supers"])
    return None


def inherited_members(longname: str) -> int:
    """Declared members summed over `longname`'s superclass chain, Object last.

    Understand's CountDeclMethodAll is RFC: a type's own methods plus every
    member declared anywhere above it, constructors and private ones included.
    `org.json.junit.data.MyNumber` is its own 8 plus java.lang.Number's 7 plus
    java.lang.Object's 13, which is Understand's 28 exactly.

    Counts nothing for the type itself, and nothing for an interface, which
    inherits no implementation.
    """
    types = _load()["types"]
    entry = types.get(longname)
    if entry is None or entry["interface"]:
        return 0
    total, seen = 0, {longname}
    current = entry["superclass"] or (
        "java.lang.Object" if longname != "java.lang.Object" else ""
    )
    while current and current not in seen:
        seen.add(current)
        parent = types.get(current)
        if parent is None:
            break
        total += parent["members"]
        current = parent["superclass"] or (
            "java.lang.Object" if current != "java.lang.Object" else ""
        )
    return total


def member_count(longname: str) -> int:
    """Members declared at `longname` itself, or 0 when it is not indexed."""
    entry = _load()["types"].get(longname)
    return entry["members"] if entry else 0


def declares_on_object(member: str) -> bool:
    """Whether java.lang.Object declares `member`, which every type inherits.

    A last resort, never a step in a hierarchy walk: the generated `supers`
    column does not name Object (javap prints a superclass only when it is not
    Object), so answering it early stops a project type's walk before it
    reaches java.lang.Enum. `w.toString()` on a java.io.Writer is
    java.lang.Object.toString and `MyEnum.VAL1.equals(x)` is
    java.lang.Enum.equals, and only ordering tells the two apart.
    """
    return member in members("java.lang.Object")


def return_type(longname: str, member: str) -> str | None:
    """Reference type `longname.member(...)` evaluates to, searching supertypes.

    This is what lets a *chained* call resolve: `Double.valueOf(x).isNaN()`
    calls isNaN on whatever valueOf returns, and without it the receiver is
    unknown and the pass correctly emits nothing. 11 of the 13 `Java Call`
    rows missing from JSONArrayTest.opt were this shape.

    None for void, a primitive, an array or a type variable -- none of which
    can be a call receiver -- and for anything the index does not carry, so a
    caller keeps refusing rather than inventing a target.
    """
    types = _load()["types"]
    seen, pending = set(), [longname]
    while pending:
        current = pending.pop(0)
        if current in seen:
            continue
        seen.add(current)
        entry = types.get(current)
        if entry is None:
            continue
        if member in entry["returns"]:
            return entry["returns"][member]
        if member in entry["methods"]:
            return None  # declared here and returns nothing chainable
        pending.extend(entry["supers"])
    return None


def known(longname: str) -> bool:
    return longname in _load()["types"]


_SIGNATURES_PATH = os.path.join(os.path.dirname(__file__), "jdk_signatures.txt.gz")
_SIGNATURES = None


def _signatures() -> dict:
    """Long name -> (supertypes, {name: [erased parameter tuples]}), from the
    table scripts/gen_jdk_signatures.py writes. Empty when it is missing."""
    global _SIGNATURES
    if _SIGNATURES is None:
        table = {}
        if os.path.exists(_SIGNATURES_PATH):
            with gzip.open(_SIGNATURES_PATH, "rt", encoding="utf8") as handle:
                for line in handle:
                    parts = line.rstrip("\n").split("\t")
                    if len(parts) == 3:
                        parts.append("")
                    if len(parts) != 4:
                        continue
                    longname, supers, methods, type_params = parts
                    overloads, returns = {}, {}
                    for item in methods.split("|") if methods else ():
                        name, _, rest = item.partition("(")
                        params, _, returned = rest.partition(")")
                        overloads.setdefault(name, []).append(
                            tuple(params.split(";")) if params else ()
                        )
                        if returned.startswith(">?"):
                            returns.setdefault(name, returned[2:])
                    table[longname] = (
                        supers.split(",") if supers else [],
                        overloads,
                        type_params.split(",") if type_params else [],
                        returns,
                    )
        _SIGNATURES = table
    return _SIGNATURES


def signature_type(longname: str):
    """(supertypes, overloads) for a JDK type, org.w3c/org.xml included, or None."""
    found = _signatures().get(longname)
    return found[:2] if found else None


def returned_type_parameter(longname: str, member: str):
    """Index of the type parameter `longname.member()` returns, or None.

    `Queue<E>.peek()` is 0, `Map<K, V>.get()` is 1. Only for a method the
    type itself declares, so the index means the receiver's own arguments.
    """
    table = _signatures()
    found = table.get(longname)
    if not found:
        return None
    params = found[2]
    seen, pending = set(), [longname]
    while pending:
        current = pending.pop(0)
        if current in seen or current not in table:
            continue
        seen.add(current)
        supers, overloads, _, returns = table[current]
        if member in overloads:
            # Declared here. Its variable is named as *this* type names it;
            # the receiver's parameter of the same name is the one bound, the
            # way List<E> passes E on to Collection<E>. A renamed one refuses.
            returned = returns.get(member)
            return params.index(returned) if returned in params else None
        pending.extend(supers)
    return None

