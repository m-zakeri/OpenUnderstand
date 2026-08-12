from openunderstand.metrics import graph_metrics


def count_decl_method_private(ent_model=None):
    """Private methods a type declares.

    The previous implementation filtered on `EntityModel._parent._name`, which
    peewee cannot traverse without a join -- the expression compiled to a
    condition that matched nothing, so every class reported 0 where Understand
    reports 5 for JSONArray and 1 for CDL.

    Counted the same way as its public sibling: over the methods the entity
    Defines, by the visibility spelled out in the method's kind name.
    """
    if ent_model is None:
        return 0
    entity = graph_metrics._entity(ent_model)
    if entity is None:
        return 0
    return sum("private" in graph_metrics._visibility(method)
               for method in graph_metrics._declares(entity._id, "method"))
