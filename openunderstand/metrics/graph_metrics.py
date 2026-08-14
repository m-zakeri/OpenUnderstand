"""Metrics answered from the reference graph instead of the source.

Understand's metrics split cleanly in two. One half asks about *structure* --
how many methods a class declares, who calls it, what it inherits -- and that
is exactly what the entity/reference tables already record. The other half asks
about *syntax* -- branches, statements, lines, nesting -- and genuinely needs
the parse tree.

The evidence for keeping them apart is in the comparison: on the calculator_app
fixture every metric already computed from the database agrees with Understand
100% of the time, while the ones that reparse source ranged from 11% to 79%.
Reparsing to answer a structural question means reimplementing, badly, an
analysis the passes already did.

Each function here takes an `Ent` and uses the same reference queries a user of
the API would write, so a bug in the reference data shows up here rather than
being papered over.
"""

from openunderstand.oudb.models import (EntityModel, KindModel, ReferenceModel,
                                        _kind_name, kind_family, kind_id)


def _refs(entity_id, kind_name):
    kind = KindModel.get_or_none(_name=kind_name)
    if kind is None:
        return []
    return list(ReferenceModel.select().where(
        (ReferenceModel._kind == kind._id) & (ReferenceModel._scope == entity_id)
    ))


def _targets(entity_id, kind_name, family=None):
    """Distinct entities on the far side of a reference kind."""
    out = {}
    for ref in _refs(entity_id, kind_name):
        target = EntityModel.get_or_none(_id=ref._ent_id)
        if target is None:
            continue
        if family and kind_family(target._kind_id) != family:
            continue
        out[target._id] = target
    return list(out.values())


def _entity(ent_model):
    return EntityModel.get_or_none(_id=getattr(ent_model, "_id", None))


def _declares(entity_id, family):
    return _targets(entity_id, "Java Define", family)


def _visibility(entity):
    return set((entity._kind._name if entity._kind else "").lower().split())


# ---------------------------------------------------------------- declarations

def count_decl_class(ent_model):
    """Classes declared in this entity.

    A package declares nothing -- a *file* defines a class and the package
    merely contains it -- so counting Java Define returned 0 for all 27
    packages on TheAlgorithms against Understand's 18 for Conversions alone.
    """
    entity = _entity(ent_model)
    if entity is None:
        return 0
    if "package" not in _visibility(entity):
        return len(_declares(entity._id, "type"))
    # A package's classes are the ones it *contains*. Preferring Define when it
    # happened to be non-empty answered 1 for DataStructures.Bags where Contain
    # gives Understand's 3: a file defines a class into the package, so Define
    # only ever sees the one file this entity was created from.
    # Contain reaches the package's top-level classes; a class nested inside
    # one of them is declared by *it*, and Understand counts those too --
    # DataStructures.Bags holds Bag and Bag.ListIterator, and stopping at the
    # top level reported 1 of 3.
    seen, pending = set(), _targets(entity._id, "Java Contain", "type")
    while pending:
        current = pending.pop()
        if current._id in seen:
            continue
        seen.add(current._id)
        pending += _declares(current._id, "type")
    return len(seen)


def count_decl_method(ent_model):
    """Methods declared locally, not counting inherited ones."""
    entity = _entity(ent_model)
    return 0 if entity is None else len(_declares(entity._id, "method"))


def count_decl_function(ent_model):
    return count_decl_method(ent_model)


def count_decl_method_public(ent_model):
    entity = _entity(ent_model)
    if entity is None:
        return 0
    return sum("public" in _visibility(m) for m in _declares(entity._id, "method"))


def count_decl_instance_method(ent_model):
    entity = _entity(ent_model)
    if entity is None:
        return 0
    return sum("static" not in _visibility(m)
               for m in _declares(entity._id, "method"))


def count_decl_instance_variable(ent_model, visibility=None):
    entity = _entity(ent_model)
    if entity is None:
        return 0
    total = 0
    for variable in _declares(entity._id, "variable"):
        tokens = _visibility(variable)
        if "static" in tokens or "local" in tokens or "parameter" in tokens:
            continue
        if visibility and visibility not in tokens:
            continue
        total += 1
    return total


# ------------------------------------------------------------------- coupling





def count_class_derived(ent_model):
    """Classes that extend this one directly."""
    entity = _entity(ent_model)
    if entity is None:
        return 0
    return len(_targets(entity._id, "Java Extendby Coupleby"))



def count_decl_file(ent_model):
    """Files this package is declared in -- Understand's "Number of files".

    Understand reports it for packages and nothing else, and it counts the
    files carrying a `package p;` of their own, not the files below `p` in the
    tree: `org.json` is 22 and its parent `org` is 0. That is exactly the
    package's own `Definein` refs, one per file, which reproduces all 95 of
    Understand's package values on the JSON benchmark.

    Looking for `Java Define` scoped to the package instead answered 0 for
    every package, because the define/definein pair a file's `package`
    statement writes puts the *file* on the ent side, not the package.
    """
    entity = _entity(ent_model)
    if entity is None or kind_family(entity._kind_id) != "package":
        return 0
    definein = KindModel.get_or_none(_name="Java Definein")
    if definein is None:
        return 0
    return len({
        ref._file_id
        for ref in ReferenceModel.select().where(
            (ReferenceModel._kind == definein._id)
            & (ReferenceModel._scope == entity._id)
        )
    })


def average_line_counts(ent_model) -> dict:
    """Understand's AvgCountLine family: mean lines per member.

    Understand names these AvgCountLine / AvgCountLineBlank / AvgCountLineCode
    / AvgCountLineComment. This project listed them as AvgLine, AvgLineBlank,
    AvgLineCode and AvgLineComment -- names Understand does not recognise, so a
    script written against Understand asked for AvgCountLine and got nothing
    back. Verified against Understand on `integral`: 9 / 0 / 8 / 1.
    """
    from openunderstand.metrics import context

    entity = _entity(ent_model)
    empty = {"total": 0, "blank": 0, "code": 0, "comment": 0}
    if entity is None:
        return empty

    members = _declares(entity._id, "method")
    if not members:
        return empty

    totals = dict(empty)
    for member in members:
        counts = context.line_counts(member._contents or "")
        for key in totals:
            totals[key] += counts[key]
    return {key: round(value / len(members)) for key, value in totals.items()}




# --------------------------------------------------- corrections from the manual
#
# metrics.pdf (Understand 7.0.1217) defines these precisely. Each function below
# quotes the sentence it implements, because several earlier versions here were
# fitted to sample values rather than written from the definition -- and were
# wrong in ways sampling could not reveal.

def count_class_base(ent_model):
    """"Number of immediate base classes. [aka IFANIN]"

    Immediate, not transitive: the previous version walked the whole ancestor
    chain. Every Java class has java.lang.Object as a base, so a class with no
    explicit `extends` still has one.
    """
    entity = _entity(ent_model)
    if entity is None:
        return 0
    direct = {t._id for t in _targets(entity._id, "Java Extend Couple")}
    direct |= {t._id for t in _targets(entity._id, "Java Implement Couple")}
    return len(direct) or 1


def count_class_coupled(ent_model, exclude_standard=False):
    """"Class A is coupled to class B if class A uses a type, data, or member
    from class B. Base classes and nested classes are not counted. Any number
    of couplings to a given class counts as 1."

    Base classes were being counted, which is what the manual explicitly
    excludes.

    `Java Couple` is the whole answer, and adding `Java Use` and `Java Typed`
    beside it was the error: reproducing this over Understand's own database,
    the Couple refs less bases and self match 105 of its 106 project classes,
    and the wider query matches 23. Understand has already decided what couples
    -- a coupling is what it writes a Couple ref for.
    """
    entity = _entity(ent_model)
    if entity is None:
        return 0
    bases = {t._id for t in _targets(entity._id, "Java Extend Couple")}
    bases |= {t._id for t in _targets(entity._id, "Java Implement Couple")}

    coupled = set()
    for target in _targets(entity._id, "Java Couple", "type"):
        if target._id == entity._id or target._id in bases:
            continue
        if exclude_standard and _is_standard(target):
            continue
        coupled.add(target._id)
    return len(coupled)


def _is_standard(entity):
    """A type from the standard library rather than this project."""
    longname = entity._longname or ""
    return longname.startswith(("java.", "javax.")) or "." not in longname


def count_decl_class_method(ent_model):
    """"Number of class methods." A class method is a static one."""
    entity = _entity(ent_model)
    if entity is None:
        return 0
    return sum("static" in _visibility(m) for m in _declares(entity._id, "method"))


def count_decl_class_variable(ent_model):
    """"Number of class variables. [aka NV]" -- static fields."""
    entity = _entity(ent_model)
    if entity is None:
        return 0
    return sum("static" in _visibility(v) and "local" not in _visibility(v)
               for v in _declares(entity._id, "variable"))


def count_semicolon(ent_model):
    """"Number of semicolons" -- in code, not in comments or string literals.

    Counting every `;` in the text also counted the ones inside strings and
    Javadoc, which is why this scored 75% instead of matching.
    """
    source = ent_model.contents() or ""
    total = 0
    i, n = 0, len(source)
    while i < n:
        c = source[i]
        if c == "/" and i + 1 < n and source[i + 1] == "/":
            i = source.find("\n", i)
            if i == -1:
                break
        elif c == "/" and i + 1 < n and source[i + 1] == "*":
            end = source.find("*/", i + 2)
            i = n if end == -1 else end + 2
        elif c in "\"'":
            quote, i = c, i + 1
            while i < n and source[i] != quote:
                i += 2 if source[i] == "\\" else 1
            i += 1
        else:
            total += c == ";"
            i += 1
    return total


def _fan_targets(entity_id, ref_kinds, owner_longname):
    """Distinct parameters, and variables declared outside the asking entity.

    Understand's fan metrics count "calling subprograms plus global variables
    read" -- and, as its own numbers show, the entity's parameters. On CDL:

        getValue(JSONTokener x)                In=2  = 1 caller  + 1 parameter
        rowToString(JSONArray ja)              In=3  = 2 callers + 1 parameter
        rowToJSONObject(JSONArray, JSONTokener) In=3 = 1 caller  + 2 parameters

    A method's *locals* are neither: counting them gave getValue an input of 8
    from its three locals and one parameter. Parameters and locals are both
    nested under the method's long name, so telling them apart needs the kind
    family -- and the long name is what separates a field from a local, since
    425 of the JSON benchmark's variable entities are `Java Unknown Variable
    Member` placeholders no pass ever upgraded, where kind says nothing.
    """
    prefix = (owner_longname or "") + "."
    out = set()
    for kind in ref_kinds:
        for target in _targets(entity_id, kind):
            if kind_family(target._kind_id) != "variable":
                continue
            # A parameter and a local are both the "variable" family -- Java
            # Parameter maps to it too -- so only the kind name tells them
            # apart, and only the long name tells a field from a local.
            if "Parameter" in (_kind_name(target._kind_id) or ""):
                out.add(target._id)
            elif not (owner_longname
                      and (target._longname or "").startswith(prefix)):
                out.add(target._id)
    return out


def count_output(ent_model):
    """"Functions calls + Parameters set/modify + Global Variables set/modify.
    A non-void return value adds one to the count." [aka FANOUT]

    The previous version counted calls only, and scored 2%.
    """
    entity = _entity(ent_model)
    if entity is None:
        return 0
    fan = {t._id for t in _targets(entity._id, "Java Call")}
    fan |= {t._id for t in _targets(entity._id, "Java Call Nondynamic")}
    fan.discard(entity._id)  # "Recursive function calls ... are not included"
    fan |= _fan_targets(entity._id, _kinds_like("Java Set", "Java Modify"),
                        entity._longname)
    declared = (entity._type or "").strip()
    if declared and declared != "void" and kind_family(entity._kind_id) == "method":
        fan.add(("return", entity._id))
    return len(fan)


def _kinds_like(*stems):
    """Every variant of a reference kind, because Understand's filter is a prefix.

    `ent.refs("Java Use")` in Understand also returns `Java Use Deref Partial`,
    `Java Use Return` and the rest; our kinds are stored under their full names
    and have to be enumerated. `Use Deref Partial` is the one that matters --
    `drop_shadowed_use_refs()` gives `x` in `x.next()` that kind and no plain
    `Use`, so asking only for `Java Use` missed most parameter reads.

    The trailing space keeps `Java Use` from dragging in `Java Useby`.
    """
    clause = None
    for stem in stems:
        match = (KindModel._name == stem) | (KindModel._name.startswith(stem + " "))
        clause = match if clause is None else (clause | match)
    return [k._name for k in KindModel.select().where(clause)]


def _use_kind_names():
    return _kinds_like("Java Use")


def count_input(ent_model):
    """"Functions calledby + Parameters read + Global Variables read." [aka FANIN]

    Understand's own wording: "Recursive function calls and local variables
    that are not class static variables are not included." Reproducing it over
    Understand's database -- distinct callers less the entity itself, plus the
    parameters and non-local variables it reads -- matches 20142 of its 20298
    method values on JSON (99.2%), which is what fixes this list of kinds.

    `Java DotRef` used to be counted here and is not a read; the `Java Use`
    variants were not, and are.
    """
    entity = _entity(ent_model)
    if entity is None:
        return 0
    fan = {t._id for t in _targets(entity._id, "Java Callby")}
    fan |= {t._id for t in _targets(entity._id, "Java Callby Nondynamic")}
    fan.discard(entity._id)  # a recursive call is not an input
    fan |= _fan_targets(entity._id, _use_kind_names(), entity._longname)
    return len(fan)


# ------------------------------------------------------------- container roll-up

#: Metrics a container aggregates rather than computing from its own text.
#: Verified against Understand on `com.calculator.app.method`: its CountLine 94,
#: CountLineCode 76, CountStmt 58 and SumCyclomatic 13 are exactly the sums over
#: the package's four files.
_NOT_AGGREGATED = {
    # A package's own definition answers this; summing it over the package's
    # files gives 0, because a file declares nothing -- the class is defined
    # in the package's scope, not the file's.
    "CountDeclClass",
    "CountDeclFile", "CountClassBase", "CountClassDerived",
    "CountClassCoupled", "CountClassCoupledModified", "MaxInheritanceTree",
    "PercentLackOfCohesion", "PercentLackOfCohesionModified",
    "RatioCommentToCode",
}


def container_members(ent_model):
    """Files a package spans, or None when the entity is not a container.

    Packages had no source of their own, so every metric that reads
    `contents()` returned 0 or 1 for them -- and packages are 6 of the 28
    entities the comparison covers, which is precisely the 79% ceiling that
    appeared on fifteen separate metrics.

    Files are deliberately *not* containers. A file has source of its own, so
    its line and statement metrics are right from text; rolling it up over its
    classes instead made a package's CountLine the sum over class bodies and
    dropped every file-level comment (org.json: 9015 -> 8451). Only a file's
    *declaration* counts need its types, and those are still wrong -- see the
    note below.

    ponytail: CountDecl* is unfixed at file and package level. `org.json`
    reports CountDeclMethod 0 where Understand says 330, because the rollup
    goes package -> file and a file counts no declarations of its own. Counting
    entities under the package directly gets CountDeclClass exactly right (26)
    but CountDeclMethod to 345 against 330, so the definition is not simply
    "entities nested under it" and needs measuring before it is implemented.
    """
    entity = _entity(ent_model)
    if entity is None or kind_family(entity._kind_id) != "package":
        return None
    contain = KindModel.get_or_none(_name="Java Contain")
    if contain is None:
        return []
    # The file each of the package's classes was found in. Read from Contain,
    # not Define: a package contains its classes and defines nothing, which is
    # how Understand records it and now how this project does. Verified against
    # Understand on com.calculator.app.method -- its CountLine 94,
    # CountLineCode 76, CountStmt 58 and SumCyclomatic 13 are exactly the sums
    # over the package's four files.
    file_ids = {
        ref._file_id
        for ref in ReferenceModel.select().where(
            (ReferenceModel._kind == contain._id)
            & (ReferenceModel._scope == entity._id)
        )
    }
    return [f for f in (EntityModel.get_or_none(_id=i) for i in file_ids) if f]


def container_methods(ent_model):
    """Every method nested anywhere inside a container.

    Avg* and Max* aggregate over these, not over files: the manual defines
    them "for all nested functions or methods", and Understand reports
    MaxCyclomatic 2 for a package whose file-level maximum is 6.
    """
    files = container_members(ent_model)
    if not files:
        return []
    define = KindModel.get_or_none(_name="Java Define")
    if define is None:
        return []
    file_ids = {f._id for f in files}
    methods = {}
    for ref in ReferenceModel.select().where(ReferenceModel._kind == define._id):
        if ref._file_id not in file_ids:
            continue
        target = EntityModel.get_or_none(_id=ref._ent_id)
        if target is not None and kind_family(target._kind_id) == "method":
            methods[target._id] = target
    return list(methods.values())


def aggregates_over_methods(name):
    return name.startswith(("Avg", "Max", "Min"))


def aggregate(name, values):
    """Combine member values the way Understand does for a container."""
    numbers = [v for v in values if isinstance(v, (int, float))]
    if not numbers:
        return 0
    if name.startswith("Max"):
        return max(numbers)
    if name.startswith("Avg"):
        return round(sum(numbers) / len(numbers))
    if name.startswith("Min"):
        return min(numbers)
    return sum(numbers)


def percent_lack_of_cohesion(ent_model, modified=False):
    """"Percentage of methods that do not use each instance variable." [LCOM]

    Computed from the reference graph rather than by reparsing. The listener
    this replaces collected a class's fields by walking
    getChild(0).getChild(1).getChild(0)... and its uses with its own
    primary4 handler; it found no uses at all on the JSON benchmark, so every
    class came out 100 -- total lack of cohesion -- against Understand's 76
    and 77. Use, Set and Modify references now name their variable exactly,
    which is the same question asked of data that has been checked.

    Understand reports whole percent, not a float.
    """
    entity = _entity(ent_model)
    if entity is None:
        return 0
    methods = _declares(entity._id, "method")
    # Cohesion is about *instance* state. A static utility class shares
    # nothing between its methods by construction, and Understand scores it 0
    # rather than a total lack of cohesion -- AnyBaseToAnyBase,
    # DecimalToHexaDecimal and RomanToInteger came out 67, 50 and 75.
    fields = [v for v in _declares(entity._id, "variable")
              if not {"local", "parameter", "static"} & _visibility(v)]
    if not methods or not fields:
        # Undefined for a class with no methods or no fields; Understand
        # reports 0 there, not total lack of cohesion.
        return 0

    reading = _kinds_like("Java Use", "Java Set", "Java Modify")
    field_ids = {f._id for f in fields}
    method_ids = {m._id for m in methods}
    users = {f._id: set() for f in fields}
    for method in methods:
        for kind in reading:
            for target in _targets(method._id, kind):
                if target._id in field_ids:
                    users[target._id].add(method._id)

    if modified:
        # "Does not penalize the use of accessor methods within a class to
        # set/read variables": a method that reaches a field only by calling
        # another method of the same class counts as using it, so the credit
        # propagates back along intra-class calls until it stops spreading.
        # Understand's own numbers need the full closure, not one hop --
        # JSONArray is 6, and direct use alone says 81. Measured against
        # Understand: 86% direct, 93% one hop, 99% at the fixed point.
        callers = {m._id: {c._id
                           for kind in ("Java Callby", "Java Callby Nondynamic")
                           for c in _targets(m._id, kind)} & method_ids
                   for m in methods}
        for field_id, reached in users.items():
            pending = list(reached)
            while pending:
                for caller in callers.get(pending.pop(), ()):
                    if caller not in reached:
                        reached.add(caller)
                        pending.append(caller)

    share = [len(users[f._id]) / len(methods) for f in fields]
    return round((1 - sum(share) / len(share)) * 100)
