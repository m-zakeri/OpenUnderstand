from openunderstand.metrics import graph_metrics


def count_decl_method_protected(ent_model=None):
    """Protected methods a type declares.

    The previous implementation filtered on `EntityModel._parent._name`, which
    peewee cannot traverse without a join: the expression compiled to
    `entitymodel._name ILIKE '%<class>%'`, matching the *method's own* name.
    `Manager` then reported 0 for its two `protected static` methods, while
    `employee` reported 5 only because its methods are named `getEmployeeId`,
    `setEmployeeName` and so on -- and SQLite's LIKE is case-insensitive.

    Counted the same way as its public sibling: over the methods the entity
    Defines, by the visibility spelled out in the method's kind name.
    """
    if ent_model is None:
        return 0
    entity = graph_metrics._entity(ent_model)
    if entity is None:
        return 0
    return sum(
        "protected" in graph_metrics._visibility(method)
        for method in graph_metrics._declares(entity._id, "method")
    )
