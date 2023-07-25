from openunderstand.define_and_definein import *


def declare_class_variables():
    main()
    class_variables = {}
    for ent_model in EntityModel.select():
        if "Static" in ent_model._kind._name and "Variable" in ent_model._kind._name:
            exists = class_variables.get(ent_model._parent._longname, -1)
            if exists == -1:
                class_variables[ent_model._parent._longname] = 1
            else:
                class_variables[ent_model._parent._longname] += 1
    return class_variables


