"""This module is the main part for creating all entities and references in database. our task was the javaModify and
javaCreate and their reverse references. """

__author__ = "Navid Mousavizadeh, Amir Mohammad Sohrabi, Sara Younesi, Deniz Ahmadi"
__copyright__ = "Copyright 2022, The OpenUnderstand Project, Iran University of Science and technology"
__credits__ = ["Dr.Parsa", "Dr.Zakeri", "Mehdi Razavi", "Navid Mousavizadeh", "Amir Mohammad Sohrabi", "Sara Younesi",
               "Deniz Ahmadi"]
__license__ = "GPL"
__version__ = "1.0.0"

import os
from fnmatch import fnmatch

from antlr4 import *

from analysis_passes.variable_listener_G11 import VariableListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaLexer import JavaLexer

from oudb.models import KindModel, EntityModel, ReferenceModel
from oudb.api import open as db_open, create_db
from oudb.fill import main

from analysis_passes.couple_coupleby import ImplementCoupleAndImplementByCoupleBy
from analysis_passes.create_createby_G11 import CreateAndCreateBy
from analysis_passes.declare_declarein import DeclareAndDeclareinListener
from analysis_passes.modify_modifyby import ModifyListener
from analysis_passes.usemodule_usemoduleby_G11 import UseModuleUseModuleByListener
from analysis_passes.class_properties import ClassPropertiesListener, InterfacePropertiesListener
from analysis_passes.entity_manager_G11 import EntityGenerator, FileEntityManager, get_created_entity


class Project:
    tree = None

    @staticmethod
    def listToString(s):
        """a method to find projects path dynamically"""
        str1 = ""
        for ele in s[0:len(s) - 1]:
            str1 += (ele + "\\")
        return str1

    def Parse(self, fileAddress):
        file_stream = FileStream(fileAddress, encoding='utf8')
        lexer = JavaLexer(file_stream)
        tokens = CommonTokenStream(lexer)
        parser = JavaParserLabeled(tokens)
        return_tree = parser.compilationUnit()
        self.tree = return_tree
        return return_tree

    @staticmethod
    def Walk(reference_listener, parse_tree):
        walker = ParseTreeWalker()
        walker.walk(listener=reference_listener, t=parse_tree)

    def getListOfFiles(self, dirName):
        listOfFile = os.listdir(dirName)
        allFiles = list()
        for entry in listOfFile:
            # Create full path
            fullPath = os.path.join(dirName, entry)
            if os.path.isdir(fullPath):
                allFiles = allFiles + self.getListOfFiles(fullPath)
            elif fnmatch(fullPath, "*.java"):
                allFiles.append(fullPath)

        return allFiles

    @staticmethod
    def add_create_and_createby_reference(ref_dicts):
        for ref_dict in ref_dicts:
            ent = get_created_entity(ref_dict['ent_name'])
            if ent is None:
                ent, _ = EntityModel.get_or_create(
                    _kind=84,
                    _name=ref_dict['ent_name'],
                    _longname=ref_dict['ent_name']
                )
            scope = ref_dict['scope']
            # print(ref_dict)
            _, _ = ReferenceModel.get_or_create(
                _kind=190,
                _file=ref_dict['file'],
                _line=ref_dict['line'],
                _column=ref_dict['column'],
                _ent=ent,
                _scope=scope,
            )
            _, _ = ReferenceModel.get_or_create(
                _kind=191,
                _file=ref_dict['file'],
                _line=ref_dict['line'],
                _column=ref_dict['column'],
                _ent=scope,
                _scope=ent,
            )

    @staticmethod
    def add_modify_and_modifyby_reference(ref_dicts):
        for ref_dict in ref_dicts:
            longname = ref_dict['ent']
            ent = ModifyListener.get_different_combinations(longname)
            scope = ref_dict['scope']
            # print(ref_dict)
            _, _ = ReferenceModel.get_or_create(
                _kind=208,
                _file=ref_dict['file'],
                _line=ref_dict['line'],
                _column=ref_dict['column'],
                _ent=ent if ent is not None else "NOT FOUND",
                _scope=scope,
            )
            _, _ = ReferenceModel.get_or_create(
                _kind=209,
                _file=ref_dict['file'],
                _line=ref_dict['line'],
                _column=ref_dict['column'],
                _ent=scope,
                _scope=ent if ent is not None else "NOT FOUND",
            )


if __name__ == '__main__':
    p = Project()
    create_db("../benchmark2_database.oudb",
              project_dir="..\benchmark")
    main()
    db = db_open("../benchmark2_database.oudb")
    # get file name
    rawPath = str(os.path.dirname(__file__).replace("\\", "/"))
    pathArray = rawPath.split('/')
    path = Project.listToString(pathArray) + "benchmark"
    files = p.getListOfFiles(path)
    # Lists
    create_createby_list = []
    modify_modifyby_list = []

    for file_address in files:
        try:
            parse_tree = p.Parse(file_address)
        except Exception as e:
            print("An Error occurred in file:" + file_address + "\n" + str(e))
            continue

        entity_generator = EntityGenerator(file_address, parse_tree)

        try:
            # create
            listener = CreateAndCreateBy(entity_generator)
            listener.create = []
            Project.Walk(listener, parse_tree)
            create_createby_list = create_createby_list + listener.create
        except Exception as e:
            print("An Error occurred for reference create/createBy in file:" + file_address + "\n" + str(e))

        try:
            listener = VariableListener(entity_generator)
            Project.Walk(listener, parse_tree)
        except Exception as e:
            print("An Error occurred for reference variable in file:" + file_address + "\n" + str(e))

        try:
            # modify
            listener = ModifyListener(entity_generator)
            listener.modify = []
            Project.Walk(listener, parse_tree)
            modify_modifyby_list = modify_modifyby_list + listener.modify
        except Exception as e:
            print("An Error occurred for reference create/createBy in file:" + file_address + "\n" + str(e))

    Project.add_create_and_createby_reference(create_createby_list)
    Project.add_modify_and_modifyby_reference(modify_modifyby_list)
