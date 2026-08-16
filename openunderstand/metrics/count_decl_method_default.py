from openunderstand.metrics import graph_metrics


def count_decl_method_default(ent_model=None):
    """Default-visibility methods a type declares.

    Same fix as its protected sibling: `EntityModel._parent._name` is not a
    traversal peewee can compile without a join, so the filter landed on the
    method's own name instead of its parent's.
    """
    if ent_model is None:
        return 0
    entity = graph_metrics._entity(ent_model)
    if entity is None:
        return 0
    return sum("default" in graph_metrics._visibility(method)
               for method in graph_metrics._declares(entity._id, "method"))
