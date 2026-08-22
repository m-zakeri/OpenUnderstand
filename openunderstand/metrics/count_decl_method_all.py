from openunderstand.oudb.models import (EntityModel, KindModel, ReferenceModel,
                                        _kind_name, kind_family, kind_id)


#: java.lang.Object's declared methods, plus Object().
_OBJECT_METHODS = 13


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
    # Forward Extend kinds only. Matching every name containing "Extend" also
    # matched the inverses -- `Java Extendby Coupleby Implicit External` is
    # scoped to java.lang.Object and points at *every* class in the project, so
    # the walk went class -> Object -> all 26 classes and summed their methods.
    # CountDeclMethodAll returned the same 193 for every type on JSON.
    extend_kinds = [
        k._id for k in KindModel.select().where(
            (KindModel.is_ent_kind == False)  # noqa: E712
            & (KindModel._name.contains("Extend"))
            & ~(KindModel._name.contains("Extendby"))
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

    from openunderstand.oudb import jdk_index

    methods = set()
    inherited = 0
    pending, seen = [entity._id], set()
    while pending:
        current = pending.pop()
        if current in seen:
            continue
        seen.add(current)
        row = EntityModel.get_or_none(_id=current)
        longname = (row._longname or "") if row is not None else ""
        if jdk_index.known(longname):
            # The chain leaves the project. Understand keeps counting: every
            # member declared above, constructors and private ones included,
            # all the way to java.lang.Object. org.json.JSONException is its
            # own 3 plus 5, 5, 27 and 13 -- Understand's 53, where stopping at
            # the boundary and adding a flat 13 for Object gave 16.
            inherited += (jdk_index.member_count(longname)
                          + jdk_index.inherited_members(longname))
            continue
        methods |= _defined_methods(current)
        pending.extend(_superclasses(current))
    # Every *class* inherits java.lang.Object: 12 methods plus its
    # constructor. Understand counts them; no JDK is analysed here, so they
    # are added as a constant. Verified against Understand on the four
    # calculator_app classes that extend nothing -- local + 13 matches exactly.
    #
    # An interface inherits nothing. Understand reports 1 for JSONString --
    # its own single method -- where adding Object's 13 gave 14, and JSON has
    # seven interfaces and annotations that were all wrong by exactly that.
    if {"interface", "annotation"} & set(
            (_kind_name(entity._kind_id) or "").lower().split()):
        return len(methods)
    if inherited:
        # java.lang.Object is the end of that chain, so it is already counted.
        return len(methods) + inherited
    return len(methods) + _OBJECT_METHODS
