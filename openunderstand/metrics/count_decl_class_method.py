from openunderstand.define_and_definein import *


def declare_method_count():
    main()
    class_methods = {}
    for ent_model in EntityModel.select():
        if "Static" in ent_model._kind._name and "Method" in ent_model._kind._name:
            exists = class_methods.get(ent_model._parent._longname, -1)
            if exists == -1:
                class_methods[ent_model._parent._longname] = 1
            else:
                class_methods[ent_model._parent._longname] += 1
    return class_methods


