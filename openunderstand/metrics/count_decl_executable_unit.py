from openunderstand.define_and_definein import *


def reach_file(ent_model):
    tmp = ent_model
    while "Java File" not in tmp._kind._name:
        tmp = tmp._parent
    return tmp._longname


def declare_executable_unit():
    main()
    executable_unit = {}
    for ent_model in EntityModel.select():
        if "Method" in ent_model._kind._name:
            file_name = reach_file(ent_model)
            exists = executable_unit.get(file_name, -1)
            if exists == -1:
                executable_unit[file_name] = 1
            else:
                executable_unit[file_name] += 1
    return executable_unit



