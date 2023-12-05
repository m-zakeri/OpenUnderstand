from oudb.models import EntityModel, KindModel, ReferenceModel

def declare_class_variables(ent_model=None) -> object:
    class_variables = {}
    kinds = KindModel.select().where(
        KindModel._name.contains("Variable")
    )
    for e in EntityModel.select().where(EntityModel._kind_id.in_(kinds)):
        print("ent_model.kind() : ", ent_model.kind())
        print("ent_model.name() : ", ent_model.name())
        print("e._longname ", e._longname)
        print("e._name ", e._name)
        exists = class_variables.get(e._parent._longname, -1)
        if exists == -1:
            class_variables[e._parent._longname] = 1
        else:
            class_variables[e._parent._longname] += 1
    return class_variables
