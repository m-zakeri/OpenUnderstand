from openunderstand.oudb.models import (EntityModel, KindModel, ReferenceModel,
                                        kind_family, kind_id)


def _defined_methods(entity_id):
    """Ids of the methods an entity declares, via its Define references."""
    define = kind_id("Java Define")
    out = set()
    for ref in ReferenceModel.select().where(
        (ReferenceModel._kind == define) & (ReferenceModel._scope == entity_id)
    ):
        target = EntityModel.get_or_none(_id=ref._ent_id)
        if target is not None and kind_family(target._kind_id) == "method":
            out.add(target._id)
    return out


def _superclasses(entity_id):
    """Ids of the types this one extends, as far as the project can see."""
    extend_kinds = [
        k._id for k in KindModel.select().where(
            (KindModel.is_ent_kind == False) & (KindModel._name.contains("Extend"))  # noqa: E712
        )
    ]
    if not extend_kinds:
        return set()
    return {
        ref._ent_id
        for ref in ReferenceModel.select().where(
            ReferenceModel._kind.in_(extend_kinds)
            & (ReferenceModel._scope == entity_id)
        )
    }


def count_decl_method_all(ent_model=None) -> int:
    """Methods declared by a type, including inherited ones.

    The previous implementation reassigned its own `ent_model` parameter inside
    a loop over every entity in the database, then looked the answer up in a
    map keyed by simple class name -- so it returned a project-wide number, or
    0, regardless of which entity was asked about.

    Inheritance is only followed as far as the project's own types: no JDK is
    analysed, so methods inherited from java.lang.Object are not counted and
    this will read lower than Understand's by that amount.
    """
    if ent_model is None:
        return 0
    entity = EntityModel.get_or_none(_id=getattr(ent_model, "_id", None))
    if entity is None or kind_family(entity._kind_id) != "type":
        return 0

    methods = set()
    pending, seen = [entity._id], set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        methods |= _defined_methods(current)
        pending.extend(_superclasses(current))
    return len(methods)
