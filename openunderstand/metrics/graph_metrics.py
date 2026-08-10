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
                                        kind_family, kind_id)


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
    """Classes declared in this entity."""
    entity = _entity(ent_model)
    return 0 if entity is None else len(_declares(entity._id, "type"))


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

def count_input(ent_model):
    """Distinct entities that call this one."""
    entity = _entity(ent_model)
    if entity is None:
        return 0
    callers = {t._id for t in _targets(entity._id, "Java Callby")}
    callers |= {t._id for t in _targets(entity._id, "Java Callby Nondynamic")}
    return len(callers)


def count_output(ent_model):
    """Distinct entities this one calls."""
    entity = _entity(ent_model)
    if entity is None:
        return 0
    callees = {t._id for t in _targets(entity._id, "Java Call")}
    callees |= {t._id for t in _targets(entity._id, "Java Call Nondynamic")}
    return len(callees)


def count_class_base(ent_model):
    """Ancestor classes, following Extend as far as the project can see."""
    entity = _entity(ent_model)
    if entity is None:
        return 0
    seen, pending = set(), [entity._id]
    while pending:
        current = pending.pop()
        for parent in _targets(current, "Java Extend Couple"):
            if parent._id not in seen:
                seen.add(parent._id)
                pending.append(parent._id)
    # +1 for java.lang.Object, which Understand counts even though no JDK is
    # analysed here -- the same adjustment MaxInheritanceTree needs.
    return len(seen) + 1


def count_class_derived(ent_model):
    """Classes that extend this one directly."""
    entity = _entity(ent_model)
    if entity is None:
        return 0
    return len(_targets(entity._id, "Java Extendby Coupleby"))


def count_class_coupled(ent_model):
    """Distinct other classes this one is coupled to."""
    entity = _entity(ent_model)
    if entity is None:
        return 0
    coupled = set()
    for kind in ("Java Couple", "Java Extend Couple", "Java Use", "Java Typed"):
        for target in _targets(entity._id, kind, "type"):
            if target._id != entity._id:
                coupled.add(target._id)
    return len(coupled)


def count_decl_file(ent_model):
    """Files that contribute declarations to this entity.

    For a package that is the number of source files declaring into it, which
    is what Understand reports; the previous implementation counted the
    entity's own file and so answered 1 for every package.
    """
    entity = _entity(ent_model)
    if entity is None:
        return 0
    define = KindModel.get_or_none(_name="Java Define")
    if define is None:
        return 0
    return len({
        ref._file_id
        for ref in ReferenceModel.select().where(
            (ReferenceModel._kind == define._id)
            & (ReferenceModel._scope == entity._id)
        )
    })


def count_semicolon(ent_model):
    """Statements terminated by a semicolon.

    Counted from source rather than references -- punctuation is syntax -- but
    it needs no parse, only the entity's text.
    """
    source = ent_model.contents() or ""
    return source.count(";")
