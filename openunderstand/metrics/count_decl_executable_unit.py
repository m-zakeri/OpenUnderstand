from openunderstand.oudb.models import EntityModel, KindModel, ReferenceModel, kind_id


def reach_file(ent_model):
    """Longname of the file an entity is declared in, or None.

    _parent is a raw id here, not an entity, so the old loop dereferenced an
    int on its second iteration.
    """
    current = EntityModel.get_or_none(_id=getattr(ent_model, "_id", None))
    seen = set()
    while current is not None and current._id not in seen:
        if current._kind_id == kind_id("Java File"):
            return current._longname
        seen.add(current._id)
        current = EntityModel.get_or_none(_id=current._parent_id)
    return None


def declare_executable_unit(ent_model=None):
    kinds = KindModel.select().where(KindModel._name.contains("Method"))
    ents = EntityModel.select().where(EntityModel._kind.in_(kinds))
    file_name = reach_file(ent_model)
    if file_name is None:
        return 0
    return ents.select().where(EntityModel._name.contains(file_name)).count()
