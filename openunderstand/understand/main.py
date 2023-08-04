"""This module is the main part for creating all entities and references in database. our task was the javaModify and
javaCreate and their reverse references. """
# import os
# from fnmatch import fnmatch
#
# from antlr4 import *
#
# from analysis_passes.variable_listener_g11 import VariableListener
# from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
# from gen.javaLabeled.JavaLexer import JavaLexer
#
# from oudb.models import KindModel, EntityModel, ReferenceModel
# from oudb.api import open as db_open, create_db
# from oudb.fill import fill
#
# from understand.override_overrideby__G12 import overridelistener
# from understand.couple_coupleby__G12 import CoupleAndCoupleBy
# from analysis_passes.couple_coupleby import CoupleAndCoupleBy
# from analysis_passes.create_createby_g11 import CreateAndCreateBy
# from analysis_passes.declare_declarein import DeclareAndDeclareinListener
# from analysis_passes.modify_modifyby import ModifyListener
# from analysis_passes.class_properties import (
#     ClassPropertiesListener,
#     InterfacePropertiesListener,
# )
# from analysis_passes.entity_manager_g11 import EntityGenerator, get_created_entity
# from analysis_passes.Throws_ThrowsBy import Throws_TrowsBy
# from analysis_passes.DotRef_DorRefBy import DotRef_DotRefBy
# from metrics.Lineofcode import LineOfCode, stringify
# from analysis_passes.g6_create_createby import CreateAndCreateByListener
# from analysis_passes.g6_declare_declarein import DeclareAndDeclareinListener
# from analysis_passes.g6_class_properties import ClassPropertiesListener
# from analysis_passes.define_definein import DefineListener
#
# from analysis_passes.callNonDynamic_callNonDynamicby import (
#     CallNonDynamicAndCallNonDynamicBy,
# )
# from analysis_passes.call_callby import CallAndCallBy
#
# from analysis_passes.variable_listener_g11 import VariableListener
#
# from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
# from gen.javaLabeled.JavaLexer import JavaLexer
#
# from oudb.models import KindModel, EntityModel, ReferenceModel
# from oudb.api import open as db_open, create_db
# from oudb.fill import fill
#
# # from openunderstand.analysis_passes.couple_coupleby import ImplementCoupleAndImplementByCoupleBy
# from analysis_passes.couple_coupleby import CoupleAndCoupleBy
# from analysis_passes.create_createby_g11 import CreateAndCreateBy
# from analysis_passes.declare_declarein import DeclareAndDeclareinListener
# from analysis_passes.define_definein import DefineListener
#
# from analysis_passes.modify_modifyby import ModifyListener
# from analysis_passes.usemodule_usemoduleby_g11 import UseModuleUseModuleByListener
# from analysis_passes.g6_class_properties import (
#     ClassPropertiesListener,
#     InterfacePropertiesListener,
# )
#
# from analysis_passes.entity_manager_g11 import (
#     EntityGenerator,
#     FileEntityManager,
#     get_created_entity,
# )
# from analysis_passes.type_typedby import TypedAndTypedByListener
# from analysis_passes.use_useby import UseAndUseByListener
# from analysis_passes.set_setby import SetAndSetByListener
# from analysis_passes.setinit_setinitby import SetInitAndSetInitByListener
# from understand.override_overrideby__G12 import overridelistener
# from understand.couple_coupleby__G12 import CoupleAndCoupleBy
# from analysis_passes.create_createby_g9 import CreateAndCreateBy
#
# # from analysis_passes.g6_declare_declarein import DeclareAndDeclareinListener
# from analysis_passes.declare_declarein import DeclareAndDeclareinListener
# from analysis_passes.g6_class_properties import (
#     ClassPropertiesListener,
#     InterfacePropertiesListener,
# )
#
#
# from metrics.AvgCyclomatic import CyclomaticListener
# from metrics.AvgCyclomaticStrict import CyclomaticStrictListener
# from metrics.AvgCyclomaticModified import CyclomaticModifiedListener
# from metrics.AvgEssential import EssentialListener
#
# # from analysis_passes.define_and_definin_g6 import DefineListener
# from utils.utilities import timer_decorator
from understand.project import Project
from understand.listeners_and_parsers import ListenersAndParsers


def runner(path_project: str = ""):

    p = Project()
    lap = ListenersAndParsers()
    files = p.getListOfFiles(path_project)
    for file_address in files:
        tree, parse_tree, file_ent = lap.parser(file_address=file_address, p=p)
        if tree is None and parse_tree is None and file_ent is None:
            continue

        entity_generator = lap.entity_gen(
            file_address=file_address, parse_tree=parse_tree
        )
        lap.create_listener(
            file_address=file_address, p=p, file_ent=file_ent, tree=tree
        )
        lap.define_listener(
            file_address=file_address, p=p, file_ent=file_ent, tree=tree
        )
        lap.declare_listener(
            file_address=file_address, p=p, file_ent=file_ent, tree=tree
        )
        lap.modify_listener(
            file_address=file_address,
            p=p,
            entity_generator=entity_generator,
            parse_tree=parse_tree,
        )
        lap.override_listener(
            file_address=file_address, p=p, file_ent=file_ent, tree=tree
        )
        lap.couple_listener(
            file_address=file_address, p=p, file_ent=file_ent, tree=tree
        )
        lap.throws_listener(
            file_address=file_address, p=p, file_ent=file_ent, tree=tree
        )
        lap.dotref_listener(
            file_address=file_address, p=p, file_ent=file_ent, tree=tree
        )
        lap.setby_listener(file_address=file_address, p=p, file_ent=file_ent, tree=tree)
        lap.useby_listener(file_address=file_address, p=p, file_ent=file_ent, tree=tree)
        lap.callby_listener(
            file_address=file_address, p=p, file_ent=file_ent, tree=tree
        )
