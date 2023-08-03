import os
from oudb.api import open
from oudb.models import EntityModel, KindModel
import os


def count_decl_method_private(db_path):
    open(db_path)
    class_methods = {}

    for ent_model in EntityModel.select():
        if "Class" in ent_model._kind._name:
            class_methods[ent_model._name] = 0

    for ent_model in EntityModel.select():
        if "Private" in ent_model._kind._name and "Method" in ent_model._kind._name:
            exists = class_methods.get(ent_model._parent._name, -1)
            if exists == -1:
                class_methods[ent_model._parent._name] = 1
            else:
                class_methods[ent_model._parent._name] += 1
    return class_methods


if __name__ == "__main__":
    print(count_decl_method_private("../../benchmark2_database.oudb"))
