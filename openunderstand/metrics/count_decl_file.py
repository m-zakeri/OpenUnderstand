from define_and_definein import *


def declare_file():
    main()
    packages = {}
    for ent_model in EntityModel.select():
        if "Java Package" in ent_model._kind._name:
            exists = packages.get(ent_model._longname, -1)
            if exists == -1:
                packages[ent_model._longname] = 1
            else:
                packages[ent_model._longname] += 1
    return packages


