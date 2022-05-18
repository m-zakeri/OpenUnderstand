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
from analysis_passes.define_definein import  DefineListener
from analysis_passes.modify_modifyby import ModifyListener
from analysis_passes.usemodule_usemoduleby_G11 import UseModuleUseModuleByListener
from analysis_passes.class_properties import ClassPropertiesListener, InterfacePropertiesListener
from analysis_passes.entity_manager_G11 import EntityGenerator, FileEntityManager, get_created_entity


from analysis_passes.type_typedby import TypedAndTypedByListener
from analysis_passes.use_useby import UseAndUseByListener
from analysis_passes.set_setby import SetAndSetByListener
from analysis_passes.setinit_setinitby import SetInitAndSetInitByListener



class Project():

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

    def getFileEntity(self, path):
        # kind id: 1
        path = path.replace("/", "\\")
        name = path.split("\\")[-1]
        file = open(path, mode='r')
        file_ent = EntityModel.get_or_create(_kind=1, _name=name, _longname=path, _contents=file.read())[0]
        file.close()
        print("processing file:", file_ent)
        return file_ent

    def addDeclareRefs(self, ref_dicts, file_ent):
        for ref_dict in ref_dicts:
            if ref_dict["scope"] is None:  # the scope is the file
                scope = file_ent
            else:  # a normal package
                scope = self.getPackageEntity(file_ent, ref_dict["scope"], ref_dict["scope_longname"])

            if ref_dict["ent"] is None:  # the ent package is unnamed
                ent = self.getUnnamedPackageEntity(file_ent)
            else:  # a normal package
                ent = self.getPackageEntity(file_ent, ref_dict["ent"], ref_dict["ent_longname"])

            # Declare: kind id 192
            declare_ref = ReferenceModel.get_or_create(_kind=192, _file=file_ent, _line=ref_dict["line"],
                                                       _column=ref_dict["col"], _ent=ent, _scope=scope)

            # Declarein: kind id 193
            declarein_ref = ReferenceModel.get_or_create(_kind=193, _file=file_ent, _line=ref_dict["line"],
                                                         _column=ref_dict["col"], _scope=ent, _ent=scope)


    def addTypeRefs(self, d_type, file_ent):
        for type_tuple in d_type['typedBy']:
            ent, h_c1 = EntityModel.get_or_create(_kind=224, _parent=None, _name=type_tuple[1],
                                                  _longname=type_tuple[6]+'.'+type_tuple[1], _value=None,
                                                  _type=None, _contents=stream)

            scope, h_c2 = EntityModel.get_or_create(_kind=225, _parent=None, _name=type_tuple[0],
                                                    _longname=type_tuple[6]+'.'+type_tuple[0], _value=None,
                                                    _type=None, _contents=stream)

            # 224		Java Typed
            typed_ref = ReferenceModel.get_or_create(_kind=224, _file=scope, _line=type_tuple[4],
                                                    _column=type_tuple[5],
                                                    _ent=ent, _scope=scope)
            # 225    	Java Typedby
            typedby_ref = ReferenceModel.get_or_create(_kind=225, _file=ent, _line=type_tuple[2],
                                                      _column=type_tuple[3],
                                                      _ent=scope, _scope=ent)

    def addSetInitRefs(self, d, file_ent):
        for type_tuple in d:
            par=EntityModel.get(_name=type_tuple[7])

            ent, h_c1 = EntityModel.get_or_create(_kind=220, _parent=par._id, _name=type_tuple[0],
                                                  _longname=type_tuple[1], _value=type_tuple[3],
                                                  _type=type_tuple[4], _contents=stream)

            scope, h_c2 = EntityModel.get_or_create(_kind=221, _parent=None, _name=type_tuple[7],
                                                    _longname=type_tuple[1], _value=None,
                                                    _type=None, _contents=stream)
            # 222: Java Set
            set_ref = ReferenceModel.get_or_create(_kind=220, _file=scope, _line=type_tuple[5],
                                                    _column=type_tuple[6],
                                                    _ent=ent, _scope=scope)
            # 223: Java Setby
            setby_ref = ReferenceModel.get_or_create(_kind=221, _file=ent, _line=type_tuple[5],
                                                      _column=type_tuple[6],
                                                      _ent=scope, _scope=ent)
            print("Set Init Added!")

    def addSetRefs(self, d, file_ent):

        for type_tuple in d:
            par = EntityModel.get(_name=type_tuple[7])
            ent, h_c1 = EntityModel.get_or_create(_kind=222, _parent=par._id, _name=type_tuple[0],
                                                  _longname=type_tuple[1], _value=type_tuple[3],
                                                  _type=None, _contents=stream)

            scope, h_c2 = EntityModel.get_or_create(_kind=223, _parent=None, _name=type_tuple[7],
                                                    _longname=type_tuple[1], _value=None,
                                                    _type=None, _contents=stream)
            # 222: Java Set
            set_ref = ReferenceModel.get_or_create(_kind=222, _file=scope, _line=type_tuple[4],
                                                    _column=type_tuple[5],
                                                    _ent=ent, _scope=scope)
            # 223: Java Setby
            setby_ref = ReferenceModel.get_or_create(_kind=223, _file=ent, _line=type_tuple[4],
                                                      _column=type_tuple[5],
                                                      _ent=scope, _scope=ent)
            print("Set Added!")


    def addUseRefs(self, d_use, file_ent):
        for use_tuple in d_use['useBy']:
            ent, h_c1 = EntityModel.get_or_create(_kind=226, _parent=None, _name=use_tuple[1],
                                                  _longname=use_tuple[6]+'.'+use_tuple[1], _value=None,
                                                  _type=None, _contents=stream)

            scope, h_c2 = EntityModel.get_or_create(_kind=227, _parent=None, _name=use_tuple[0],
                                                    _longname=use_tuple[6]+'.'+use_tuple[0], _value=None,
                                                    _type=None, _contents=stream)

            # 226		Java Use
            use_ref = ReferenceModel.get_or_create(_kind=226, _file=file_ent,
                                                _line=use_tuple[4], _column=use_tuple[5],
                                                _ent=ent, _scope=scope)
            # 227	 	Java Useby
            useby_ref = ReferenceModel.get_or_create(_kind=227, _file=file_ent,
                                                _line=use_tuple[2], _column=use_tuple[3],
                                                _ent=scope, _scope=ent)

    def addDefineRefs(self, ref_dicts, file_ent):
        for ref_dict in ref_dicts:
            if ref_dict["scope"] is None:  # the scope is the file
                scope = file_ent
            else:  # a normal package
                scope = self.getPackageEntity(file_ent, ref_dict["scope"], ref_dict["scope_longname"])

            ent = self.getPackageEntity(file_ent, ref_dict["ent"], ref_dict["ent_longname"])

            # Define: kind id 194
            define_ref = ReferenceModel.get_or_create(_kind=194, _file=file_ent, _line=ref_dict["line"],
                                                       _column=ref_dict["col"], _ent=ent, _scope=scope)

            # Definein: kind id 195
            definein_ref = ReferenceModel.get_or_create(_kind=195, _file=file_ent, _line=ref_dict["line"],
                                                         _column=ref_dict["col"], _scope=ent, _ent=scope)

    def addImplementOrImplementByRefs(self, ref_dicts, file_ent, file_address):
        pass
    
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
    create_db("../benchmark_database.oudb",
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
            
        try:
            # define
            listener = DefineListener()
            p.Walk(listener, tree)
            p.addDefineRefs(listener.defines, file_ent)
        except Exception as e:
            print("An Error occurred for reference contain in file:" + file_address + "\n" + str(e))

        try:
            listener = SetAndSetByListener(file_address)
            p.Walk(listener=listener, tree=tree)
            d = listener.setBy
            p.addSetRefs(d, file_ent)

        except Exception as e:
            print("An set Error occurred for reference contain in file:" + file_address + "\n" + str(e))

        try:
            listener = SetInitAndSetInitByListener(file_address)
            p.Walk(listener=listener, tree=tree)
            d = listener.set_init_by
            p.addSetInitRefs(d, file_ent)
        except Exception as e:
            print("An Error occurred for reference contain in file:" + file_address + "\n" + str(e))


    Project.add_create_and_createby_reference(create_createby_list)
    Project.add_modify_and_modifyby_reference(modify_modifyby_list)