"""This module is the main part for creating all entities and references in database. our task was the javaModify and
javaCreate and their reverse references. """
import os
from fnmatch import fnmatch

from antlr4 import *

from analysis_passes.variable_listener_g11 import VariableListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaLexer import JavaLexer

from oudb.models import KindModel, EntityModel, ReferenceModel
from oudb.api import open as db_open, create_db
from oudb.fill import fill

from understand.override_overrideby__G12 import overridelistener
from understand.couple_coupleby__G12 import CoupleAndCoupleBy
from analysis_passes.couple_coupleby import CoupleAndCoupleBy
from analysis_passes.create_createby_g11 import CreateAndCreateBy
from analysis_passes.declare_declarein import DeclareAndDeclareinListener
from analysis_passes.modify_modifyby import ModifyListener
from analysis_passes.class_properties import ClassPropertiesListener, InterfacePropertiesListener
from analysis_passes.entity_manager_g11 import EntityGenerator, get_created_entity
from analysis_passes.Throws_ThrowsBy import Throws_TrowsBy
from analysis_passes.DotRef_DorRefBy import DotRef_DotRefBy
from metrics.Lineofcode import LineOfCode , stringify
from analysis_passes.g6_create_createby import CreateAndCreateByListener
from analysis_passes.g6_declare_declarein import DeclareAndDeclareinListener
from analysis_passes.g6_class_properties import ClassPropertiesListener
from analysis_passes.define_definein import  DefineListener

from analysis_passes.callNonDynamic_callNonDynamicby import CallNonDynamicAndCallNonDynamicBy
from analysis_passes.call_callby import CallAndCallBy

from analysis_passes.variable_listener_g11 import VariableListener

from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaLexer import JavaLexer

from oudb.models import KindModel, EntityModel, ReferenceModel
from oudb.api import open as db_open, create_db
from oudb.fill import fill

# from openunderstand.analysis_passes.couple_coupleby import ImplementCoupleAndImplementByCoupleBy
from analysis_passes.couple_coupleby import CoupleAndCoupleBy
from analysis_passes.create_createby_g11 import CreateAndCreateBy
from analysis_passes.declare_declarein import DeclareAndDeclareinListener
from analysis_passes.define_definein import  DefineListener
from analysis_passes.modify_modifyby import ModifyListener
from analysis_passes.usemodule_usemoduleby_g11 import UseModuleUseModuleByListener
from analysis_passes.g6_class_properties import ClassPropertiesListener, InterfacePropertiesListener

from analysis_passes.entity_manager_g11 import EntityGenerator, FileEntityManager, get_created_entity
from analysis_passes.type_typedby import TypedAndTypedByListener
from analysis_passes.use_useby import UseAndUseByListener
from analysis_passes.set_setby import SetAndSetByListener
from analysis_passes.setinit_setinitby import SetInitAndSetInitByListener
from understand.override_overrideby__G12 import overridelistener
from understand.couple_coupleby__G12 import CoupleAndCoupleBy
from analysis_passes.g6_create_createby import CreateAndCreateByListener
from analysis_passes.g6_declare_declarein import DeclareAndDeclareinListener
from analysis_passes.g6_class_properties import ClassPropertiesListener, InterfacePropertiesListener
from metrics.AvgCyclomatic import CyclomaticListener
from metrics.AvgCyclomaticStrict import CyclomaticStrictListener
from metrics.AvgCyclomaticModified import CyclomaticModifiedListener
from metrics.AvgEssential import EssentialListener



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

    def getFileEntity(self, mpath:str = "", name: str =""):
        # kind id: 1
        file = open(mpath, mode='r')
        file_ent = EntityModel.get_or_create(_kind=1, _name=name, _longname=mpath, _contents=file.read())[0]
        file.close()
        print("processing file:", file_ent)
        return file_ent

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
                                                         
    def addThrows_TrowsByRefs(self, ref_dicts, file_ent, file_address,id1,id2,Throw):
        for ref_dict in ref_dicts:

            scope = EntityModel.get_or_create(_kind=self.findKindWithKeywords("Method", ref_dict["scopemodifiers"]),
                                              _name=ref_dict["scopename"],
                                              _parent= ref_dict["scope_parent"] if ref_dict["scope_parent"] is not None else file_ent,
                                              _longname=ref_dict["scopelongname"],
                                              _contents=ref_dict["scopecontent"])[0]

            if not Throw:
                if ref_dict["refent"] is None:
                    ent = self.getUnnamedPackageEntity(file_ent)
                else:
                    ent = self.getPackageEntity(file_ent, ref_dict["refent"], ref_dict["refent"])
            else:
                ent = self.getThrowEntity(ref_dict["refent"], file_address)

            implement_ref = ReferenceModel.get_or_create(_kind=id1, _file=file_ent, _line=ref_dict["line"],
                                                         _column=ref_dict["col"], _ent=ent, _scope=scope)
            implementBy_ref = ReferenceModel.get_or_create(_kind=id2, _file=file_ent, _line=ref_dict["line"],
                                                           _column=ref_dict["col"], _ent=scope, _scope=ent)


    def addDeclareRefs(self, ref_dicts, file_ent):
        for ref_dict in ref_dicts:

            if ref_dict["scope"] is None:  # the scope is the file
                scope = file_ent
            else:  # a normal package
                scope = self.getPackageEntity(file_ent, ref_dict["scope"], ref_dict["scope_longname"])

            if ref_dict["entity"] is None:  # the entity package is unnamed
                ent = self.getUnnamedPackageEntity(file_ent)
            else:  # a normal package
                ent = self.getPackageEntity(file_ent, ref_dict["entity"], ref_dict["entity_longname"])

            # Declare reference - kind id = 192
            ReferenceModel.get_or_create(_kind=192, _file=file_ent, _line=ref_dict["line"],
                                         _column=ref_dict["column"], _ent=ent, _scope=scope)

            # Declare in reference - kind id = 193
            ReferenceModel.get_or_create(_kind=193, _file=file_ent, _line=ref_dict["line"],
                                         _column=ref_dict["column"], _scope=ent, _ent=scope)

    def addImplementOrImplementByRefs(self, ref_dicts, file_ent, file_address):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(_kind=self.findKindWithKeywords(ref_dict["scope_kind"],
                                                                              ref_dict["scope_modifiers"]),
                                              _name=ref_dict["scope_name"],
                                              _parent=ref_dict["scope_parent"] if ref_dict[
                                                                                      "scope_parent"] is not None else file_ent,
                                              _longname=ref_dict["scope_longname"],
                                              _contents=ref_dict["scope_contents"])[0]
            ent = self.getImplementEntity(ref_dict["type_ent_longname"], file_address)
            implement_ref = ReferenceModel.get_or_create(_kind=188, _file=file_ent, _line=ref_dict["line"],
                                                         _column=ref_dict["col"], _ent=ent, _scope=scope)
            implementBy_ref = ReferenceModel.get_or_create(_kind=189, _file=file_ent, _line=ref_dict["line"],
                                                           _column=ref_dict["col"], _ent=scope, _scope=ent)

    def addCreateRefs(self, ref_dicts, file_ent, file_address):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(_kind=self.findKindWithKeywords("Method", ref_dict["scope_modifiers"]),
                                              _name=ref_dict["scope_name"],
                                              _type=ref_dict["scope_return_type"]
                                              , _parent=ref_dict["scope_parent"] if ref_dict[
                                                                                        "scope_parent"] is not None else file_ent
                                              , _longname=ref_dict["package_name"] + "." + ref_dict["scope_longname"]
                                              , _contents=ref_dict["scope_content"])[0]
            new_file_address = file_address.split('\com')[0] + "\\" + ref_dict["new_class_path"]
            ent = self.getCreatedClassEntity(ref_dict["new_class_name"], new_file_address)
            Create = ReferenceModel.get_or_create(_kind=190, _file=file_ent, _line=ref_dict["line"],
                                                  _column=ref_dict["col"], _scope=scope, _ent=ent)
            Createby = ReferenceModel.get_or_create(_kind=191, _file=file_ent, _line=ref_dict["line"],
                                                    _column=ref_dict["col"], _scope=ent, _ent=scope)
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

    def getPackageEntity(self, file_ent, name, longname):
        # package kind id: 72
        ent = EntityModel.get_or_create(_kind=72, _name=name, _parent=file_ent,
                                        _longname=longname, _contents="")
        return ent[0]

    def getUnnamedPackageEntity(self, file_ent):
        # unnamed package kind id: 73
        ent = EntityModel.get_or_create(_kind=73, _name="(Unnamed_Package)", _parent=file_ent,
                                        _longname="(Unnamed_Package)", _contents="")
        return ent[0]

    def getClassProperties(self, class_longname, file_address2):

        listener = ClassPropertiesListener()
        listener.class_longname = class_longname.split(".")
        listener.class_properties = None
        tree2 = self.Parse(file_address2)
        try:
            tree2 = self.Parse(file_address2)
        except Exception as e:
            print("An Error occurred in file 1 :" + file_address2 + "\n" + str(e))
        self.Walk(listener, tree2)
        return listener.class_properties

    def getInterfaceProperties(self, interface_longname, file_address):
        listener = InterfacePropertiesListener()
        listener.interface_longname = interface_longname.split(".")
        listener.interface_properties = None
        self.Walk(listener, self.tree)
        return listener.interface_properties

    def getCreatedClassEntity(self, class_name, file_address2):
        return self.getClassEntity(class_name, file_address2)

    def getClassEntity(self, class_longname, file_address2):
        props = p.getClassProperties(class_longname, file_address2)
        if not props:  # This class is unknown, unknown class id: 84
            ent = EntityModel.get_or_create(_kind=84, _name=class_longname.split(".")[-1],
                                            _longname=class_longname, _contents="")
        else:
            if len(props["modifiers"]) == 0:
                props["modifiers"].append("default")
            kind = self.findKindWithKeywords("Class", props["modifiers"])
            ent = EntityModel.get_or_create(_kind=kind, _name=props["name"],
                                            _longname=props["package_name"] + "." + props["longname"],
                                            _parent=props["parent"] if props["parent"] is not None else file_ent,
                                            _contents=props["contents"])
        return ent[0]

    def getInterfaceEntity(self, interface_longname, file_address):  # can't be of unknown kind!
        props = p.getInterfaceProperties(interface_longname, file_address)
        if not props:
            return None
        else:
            kind = self.findKindWithKeywords("Interface", props["modifiers"])
            ent = EntityModel.get_or_create(_kind=kind, _name=props["name"],
                                            _longname=props["longname"],
                                            _parent=props["parent"] if props["parent"] is not None else file_ent,
                                            _contents=props["contents"])
        return ent[0]

    def getThrowEntity(self, longname, file_address):
        ent = self.getInterfaceEntity(longname, file_address)
        if not ent:
            ent = self.getClassEntity(longname, file_address)
        return ent


    def findKindWithKeywords(self, type, modifiers):
        if len(modifiers) == 0:
            modifiers.append("default")
        leastspecific_kind_selected = None
        for kind in KindModel.select().where(KindModel._name.contains(type)):
            if self.checkModifiersInKind(modifiers, kind):
                if not leastspecific_kind_selected or len(leastspecific_kind_selected._name)  and len(kind._name):
                    leastspecific_kind_selected = kind
        return leastspecific_kind_selected

    def checkModifiersInKind(self, modifiers, kind):
        for modifier in modifiers:
            if modifier.lower() not in kind._name.lower():
                return False
        return True


# if __name__ == '__main__':
#     p = Project()
#     create_db("../benchmark2_database.oudb",
#               project_dir="..\benchmark")
#     main()
#     db = db_open("../benchmark2_database.oudb")
#     # get file name
#     rawPath = str(os.path.dirname(__file__).replace("\\", "/"))
#     pathArray = rawPath.split('/')
#     path = Project.listToString(pathArray) + "benchmark"
#     files = p.getListOfFiles(path)
#
#
#     for file_address in files:
#         try:
#             file_ent = p.getFileEntity(file_address)
#             tree = p.Parse(file_address)
#         except Exception as e:
#             print("An Error occurred in file:" + file_address + "\n" + str(e))
#             continue
#         try:
#             listener = CreateAndCreateByListener()
#             p.Walk(listener, tree)
#             listener.get_refers()
#             p.addCreateRefs(listener.get_create(), file_ent, file_address)
#         except Exception as e:
#             print("An Error occurred for reference implement in file:" + file_address + "\n" + str(e))
#
#
#         try:
#             # implement
#             listener = CallAndCallBy()
#             listener.implement = []
#             p.Walk(listener, tree)
#             p.addImplementOrImplementByRefs(listener.implement, file_ent, file_address)
#         except Exception as e:
#             print("An Error occurred for reference implement in file:" + file_address + "\n" + str(e))
#
#         try:
#             # import
#             listener = ImportListener()
#             p.Walk(listener, tree)
#         except Exception as e:
#             print("An Error occurred for reference import in file:" + file_address + "\n" + str(e))
#
#         try:
#             # declare
#             listener = DeclareAndDeclareinListener()
#             p.Walk(listener, tree)
#             p.addDeclareRefs(listener.get_declare_dicts, file_ent)
#         except Exception as e:
#             print("An Error occurred for reference declare in file:" + file_address + "\n" + str(e))

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

    def getFileEntity(self, path:str= "", name:str = ""):
        # kind id: 1
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
            scope = EntityModel.get_or_create(_kind=self.findKindWithKeywords(ref_dict["scope_kind"],
                                                                              ref_dict["scope_modifiers"]),
                                              _name=ref_dict["scope_name"],
                                              _parent=ref_dict["scope_parent"] if ref_dict[
                                                                                      "scope_parent"] is not None else file_ent,
                                              _longname=ref_dict["scope_longname"],
                                              _contents=ref_dict["scope_contents"])[0]
            ent = self.getImplementEntity(ref_dict["type_ent_longname"], file_address)
            implement_ref = ReferenceModel.get_or_create(_kind=188, _file=file_ent, _line=ref_dict["line"],
                                                         _column=ref_dict["col"], _ent=ent, _scope=scope)
            implementBy_ref = ReferenceModel.get_or_create(_kind=189, _file=file_ent, _line=ref_dict["line"],
                                                           _column=ref_dict["col"], _ent=scope, _scope=ent)

    def addExtendCoupleOrExtendCoupleByRefs(self, ref_dicts, file_ent, file_address):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(_kind=self.findKindWithKeywords(ref_dict["scope_kind"],
                                                                              ref_dict["scope_modifiers"]),
                                              _name=ref_dict["scope_name"],
                                              _parent=ref_dict["scope_parent"] if ref_dict[
                                                                                      "scope_parent"] is not None else file_ent,
                                              _longname=ref_dict["scope_longname"],
                                              _contents=ref_dict["scope_contents"])[0]
            ent = self.getImplementEntity(ref_dict["type_ent_longname"], file_address)
            extend_ref = ReferenceModel.get_or_create(_kind=178, _file=file_ent, _line=ref_dict["line"],
                                                         _column=ref_dict["col"], _ent=ent, _scope=scope)
            extendBy_ref = ReferenceModel.get_or_create(_kind=179, _file=file_ent, _line=ref_dict["line"],
                                                           _column=ref_dict["col"], _ent=scope, _scope=ent)

    def addCallOrCallByRefs(self, ref_dicts, file_ent, file_address):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(_kind=self.findKindWithKeywords(ref_dict["scope_kind"],
                                                                              ref_dict["scope_modifiers"]),
                                              _name=ref_dict["scope_name"],
                                              _parent=ref_dict["scope_parent"] if ref_dict[
                                                                                      "scope_parent"] is not None else file_ent,
                                              _longname=ref_dict["scope_longname"],
                                              _contents=ref_dict["scope_contents"])[0]
            ent = self.getImplementEntity(ref_dict["type_ent_longname"], file_address)
            call_ref = ReferenceModel.get_or_create(_kind=172, _file=file_ent, _line=ref_dict["line"],
                                                         _column=ref_dict["col"], _ent=ent, _scope=scope)
            callBy_ref = ReferenceModel.get_or_create(_kind=173, _file=file_ent, _line=ref_dict["line"],
                                                           _column=ref_dict["col"], _ent=scope, _scope=ent)

    def addCallNonDynamicOrCallNonDynamicByRefs(self, ref_dicts, file_ent, file_address):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(_kind=self.findKindWithKeywords(ref_dict["scope_kind"],
                                                                              ref_dict["scope_modifiers"]),
                                              _name=ref_dict["scope_name"],
                                              _parent=ref_dict["scope_parent"] if ref_dict[
                                                                                      "scope_parent"] is not None else file_ent,
                                              _longname=ref_dict["scope_longname"],
                                              _contents=ref_dict["scope_contents"])[0]
            ent = self.getImplementEntity(ref_dict["type_ent_longname"], file_address)
            call_ref = ReferenceModel.get_or_create(_kind=170, _file=file_ent, _line=ref_dict["line"],
                                                         _column=ref_dict["col"], _ent=ent, _scope=scope)
            callBy_ref = ReferenceModel.get_or_create(_kind=171, _file=file_ent, _line=ref_dict["line"],
                                                           _column=ref_dict["col"], _ent=scope, _scope=ent)


    def addCreateRefs(self, ref_dicts, file_ent, file_address):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(_kind=self.findKindWithKeywords("Method", ref_dict["scopemodifiers"]),
                                              _name=ref_dict["scopename"],
                                              _type=ref_dict["scopereturntype"]
                                              , _parent=ref_dict["scope_parent"] if ref_dict[
                                                                                        "scope_parent"] is not None else file_ent
                                              , _longname=ref_dict["scopelongname"]
                                              , _contents=["scopecontent"])[0]
            ent = self.getCreatedClassEntity(ref_dict["refent"], ref_dict["potential_refent"], file_address)
            Create = ReferenceModel.get_or_create(_kind=190, _file=file_ent, _line=ref_dict["line"],
                                                  _column=ref_dict["col"], _scope=scope, _ent=ent)
            Createby = ReferenceModel.get_or_create(_kind=191, _file=file_ent, _line=ref_dict["line"],
                                                    _column=ref_dict["col"], _scope=ent, _ent=scope)

    def getPackageEntity(self, file_ent, name, longname):
        # package kind id: 72
        ent = EntityModel.get_or_create(_kind=72, _name=name, _parent=file_ent,
                                        _longname=longname, _contents="")
        return ent[0]

    def getUnnamedPackageEntity(self, file_ent):
        # unnamed package kind id: 73
        ent = EntityModel.get_or_create(_kind=73, _name="(Unnamed_Package)", _parent=file_ent,
                                        _longname="(Unnamed_Package)", _contents="")
        return ent[0]

    def getClassProperties(self, class_longname, file_address):
        listener = ClassPropertiesListener()
        listener.class_longname = class_longname.split(".")
        listener.class_properties = None
        self.Walk(listener, self.tree)
        return listener.class_properties

    def getInterfaceProperties(self, interface_longname, file_address):
        listener = InterfacePropertiesListener()
        listener.interface_longname = interface_longname.split(".")
        listener.interface_properties = None
        self.Walk(listener, self.tree)
        return listener.interface_properties

    def getCreatedClassEntity(self, class_longname, class_potential_longname, file_address):
        props = p.getClassProperties(class_potential_longname, file_address)
        if not props:
            return self.getClassEntity(class_longname, file_address)
        else:
            return self.getClassEntity(class_potential_longname, file_address)

    def getClassEntity(self, class_longname, file_address):
        props = p.getClassProperties(class_longname, file_address)
        if not props:  # This class is unknown, unknown class id: 84
            ent = EntityModel.get_or_create(_kind=84, _name=class_longname.split(".")[-1],
                                            _longname=class_longname, _contents="")
        else:
            if len(props["modifiers"]) == 0:
                props["modifiers"].append("default")
            kind = self.findKindWithKeywords("Class", props["modifiers"])
            ent = EntityModel.get_or_create(_kind=kind, _name=props["name"],
                                            _longname=props["longname"],
                                            _parent=props["parent"] if props["parent"] is not None else file_ent,
                                            _contents=props["contents"])
        return ent[0]

    def getInterfaceEntity(self, interface_longname, file_address):  # can't be of unknown kind!
        props = p.getInterfaceProperties(interface_longname, file_address)
        if not props:
            return None
        else:
            kind = self.findKindWithKeywords("Interface", props["modifiers"])
            ent = EntityModel.get_or_create(_kind=kind, _name=props["name"],
                                            _longname=props["longname"],
                                            _parent=props["parent"] if props["parent"] is not None else file_ent,
                                            _contents=props["contents"])
        return ent[0]


    def getImplementEntity(self, longname, file_address):
        ent = self.getInterfaceEntity(longname, file_address)
        if not ent:
            ent = self.getClassEntity(longname, file_address)
        return ent

    def findKindWithKeywords(self, type, modifiers):
        if len(modifiers) == 0:
            modifiers.append("default")
        leastspecific_kind_selected = None
        for kind in KindModel.select().where(KindModel._name.contains(type)):
            if self.checkModifiersInKind(modifiers, kind):
                if not leastspecific_kind_selected \
                        or len(leastspecific_kind_selected._name) > len(kind._name):
                    leastspecific_kind_selected = kind
        return leastspecific_kind_selected

    def checkModifiersInKind(self, modifiers, kind):
        for modifier in modifiers:
            if modifier.lower() not in kind._name.lower():
                return False
        return True

    def addoverridereference(self, classes, extendedfiles):
        for tuples in extendedfiles:
            main = tuples[0]
            fromx = tuples[1]
            methodsmain = classes[main]
            for x in methodsmain:
                file = x['File']
                file_ent = self.getFileEntity(file)
                kindx = self.findKindWithKeywords(x["scope_kind"], x["scope_modifiers"])
                if kindx is None:
                    kindx = x['modifiersx']
                scope = EntityModel.get_or_create(_kind=kindx, _name=x["scope_name"],
                                                  _parent=x["scope_parent"] if x[
                                                                                   "scope_parent"] is not None else file_ent,
                                                  _longname=x["scope_longname"],
                                                  _contents=x["scope_contents"], _type=x['Methodkind'])
                methodname1 = x['MethodIs']

                if (fromx in classes):
                    mathodsfrom = classes[fromx]
                    for y in mathodsfrom:

                        if y['MethodIs'] == methodname1:
                            fe = self.getFileEntity(y['File'])
                            kind = self.findKindWithKeywords(y["scope_kind"], y["scope_modifiers"])
                            if kind is None:
                                kind = y['modifiersx']
                            ent = EntityModel.get_or_create(_kind=kind, _name=y["scope_name"],
                                                            _parent=y["scope_parent"] if y[
                                                                                             "scope_parent"] is not None else fe,
                                                            _longname=y["scope_longname"],
                                                            _contents=y["scope_contents"], _type=y['Methodkind'])

                            override_ref = ReferenceModel.get_or_create(_kind=211, _file=file_ent, _line=x["line"],
                                                                        _column=x["col"], _ent=ent[0], _scope=scope[0])
                            overrideBy_ref = ReferenceModel.get_or_create(_kind=212, _file=fe, _line=y["line"],
                                                                          _column=y["col"], _ent=scope[0],
                                                                          _scope=ent[0])
                elif (x['is_overrided']):
                    overrideword = x[0]
                    if (overrideword not in classes):
                        ent = EntityModel.get_or_create(
                            _kind='Unknown Method',
                            _name=overrideword[1],
                            _parent=file_ent,
                            _longname=overrideword,
                            _contents='', )
                        override_ref = ReferenceModel.get_or_create(_kind=211, _file=file_ent, _line=x["line"],
                                                                    _column=x["col"], _ent=ent[0], _scope=scope[0])

    def addcouplereference(self, classes, couples):
        keykind = ''
        for c in couples:
            file_ent = self.getFileEntity(c['File'])
            scope = EntityModel.get_or_create(_kind=self.findKindWithKeywords(c["scope_kind"], c["scope_modifiers"]),
                                              _name=c["scope_name"],
                                              _parent=c["scope_parent"] if c["scope_parent"] is not None else file_ent,
                                              _longname=c["scope_longname"],
                                              _contents=c["scope_contents"])
            if 'type_ent_longname' in c:
                keylist = c['type_ent_longname']
                if (len(keylist) != 0):
                    for key in keylist:
                        if key in classes:
                            c1 = classes[key]
                            file_ent2 = self.getFileEntity(c1['File'])
                            keykind = self.findKindWithKeywords(c1["scope_kind"], c1["scope_modifiers"])
                            ent = EntityModel.get_or_create(
                                _kind=self.findKindWithKeywords(c1["scope_kind"], c1["scope_modifiers"]),
                                _name=c1["scope_name"],
                                _parent=c1["scope_parent"] if c1["scope_parent"] is not None else file_ent2,
                                _longname=c1["scope_longname"],
                                _contents=c1["scope_contents"])
                            CoupleBy_ref = ReferenceModel.get_or_create(_kind=180, _file=file_ent2, _line=c["line"],
                                                                        _column=c["col"], _ent=scope[0], _scope=ent[0])

                        else:
                            kw = key.split('.')
                            keykind = "Unknown Class"
                            ent = EntityModel.get_or_create(_kind="Unknown Class", _name=kw[-1],
                                                            _parent=file_ent,
                                                            _longname=key,
                                                            )
                        Couple_ref = ReferenceModel.get_or_create(_kind=179, _file=file_ent, _line=c["line"],
                                                                  _column=c["col"], _ent=ent[0], _scope=scope[0])

def runner(path_project:str = ""):
    p = Project()
    files = p.getListOfFiles(path_project)
    modify_modifyby_list = []
    classesx= {}
    extendedlist= []
    classescoupleby = {}
    couple = []
    open('AvgCyclomatic', 'w').close()
    open('AvgCyclomaticStrict', 'w').close()
    open('AvgCyclomaticModified', 'w').close()
    open('AvgEssential', 'w').close()
    a = b = c = d = 0
    for file_address in files:
        try:
            print(" fileaddress : ", file_address)
            parse_tree = p.Parse(file_address)
            print(os.path.basename(file_address))
            file_ent = p.getFileEntity(path=file_address, name=os.path.basename(file_address))
            tree = p.Parse(file_address)
        except Exception as e:
            print("An Error occurred in file:" + file_address + "\n" + str(e))
            continue

        entity_generator = EntityGenerator(file_address, parse_tree)

        try:
            listener = CreateAndCreateByListener()
            p.Walk(listener, tree)
            listener.get_refers()
            p.addCreateRefs(listener.get_create(), file_ent, file_address)
        except Exception as e:
            print("An Error occurred for reference implement in file:" + file_address + "\n" + str(e))

        try:
            # define
            listener = DefineListener()
            p.Walk(listener, tree)
            p.addDefineRefs(listener.defines, file_ent)
        except Exception as e:
            print("An Error occurred for reference define in file:" +file_address + "\n" + str(e))

        try:
            # declare
            listener = DeclareAndDeclareinListener()
            p.Walk(listener, tree)
            p.addDeclareRefs(listener.get_declare_dicts, file_ent)
            print('declaration dictionary : \n')
            print(listener.get_declare_dicts)
        except Exception as e:
            print("An Error occurred for reference declare in file:" + file_address + "\n" + str(e))

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
            listener = overridelistener()
            listener.extendedtoentity = {}
            listener.set_dictionary(classesx)
            listener.set_file(file_address)
            listener.set_list(extendedlist)
            p.Walk(listener, tree)
            classesx = listener.get_classes
            extendedlist = listener.get_extendeds
        except Exception as e:
            print("An Error occurred in override reference in file :" + file_address + "\n" + str(e))
            continue

        try:
            listener = CoupleAndCoupleBy()
            listener.set_file(filex=file_address)
            listener.set_classesx(classesx=classescoupleby)
            listener.set_couples(couples=couple)
            p.Walk(listener, tree)
            classescoupleby = listener.get_classes
            couple = listener.get_couples
        except Exception as e:
            print("An Error occurred in couple reference in file :" + file_address + "\n" + str(e))
            continue
        try:
            # Throws
            listener = Throws_TrowsBy()
            listener.implement = []
            p.Walk(listener, tree)
            p.addThrows_TrowsByRefs(listener.implement, file_ent, file_address, 236, 237, True)
        except Exception as e:
            print("An Error occurred in couple reference in file :" + file_address + "\n" + str(e))
            pass

        try:
            # dotref
            listener = DotRef_DotRefBy()
            listener.declare = []
            p.Walk(listener, tree)
            p.addThrows_TrowsByRefs(listener.implement, file_ent, file_address, 198, 199, False)
        except Exception as e:
            print("An Error occurred in couple reference in file :" + file_address + "\n" + str(e))
            pass

    #     try:
    #
    #         listener = CyclomaticListener()
    #         p.Walk(listener, tree)
    #         with open('AvgCyclomatic.txt', 'a') as f:
    #             f.write(f"AvgCyclomatic:{listener.get_dict}")
    #             f.write('\n')
    #     except Exception as e:
    #         print("An Error occurred for AvgCyclomatic implement in file:" + file_address + "\n" + str(e))
    #
    #     try:
    #
    #         listener = CyclomaticStrictListener()
    #         p.Walk(listener, tree)
    #         with open('AvgCyclomaticStrict.txt', 'a') as f:
    #             f.write(f"AvgCyclomaticStrict:{listener.get_dict}")
    #             f.write('\n')
    #     except Exception as e:
    #         print("An Error occurred for AvgCyclomaticStrict implement in file:" + file_address + "\n" + str(e))
    #
    #     try:
    #
    #         listener = CyclomaticModifiedListener()
    #         p.Walk(listener, tree)
    #         with open('AvgCyclomaticModified.txt', 'a') as f:
    #             f.write(f"AvgCyclomaticModified:{listener.get_dict}")
    #             f.write('\n')
    #     except Exception as e:
    #         print("An Error occurred for AvgCyclomaticModified implement in file:" + file_address + "\n" + str(e))
    #
    #     try:
    #
    #         listener = EssentialListener()
    #         p.Walk(listener, tree)
    #         with open('AvgEssential.txt', 'a') as f:
    #             f.write(f"AvgEssential:{listener.get_dict}")
    #             f.write('\n')
    #     except Exception as e:
    #         print("An Error occurred for AvgEssential implement in file:" + file_address + "\n" + str(e))
    #
    #
    # try:
    #     p.addoverridereference(classesx, extendedlist)
    # except Exception as e:
    #     print("An Error occurred in couple reference " + str(e))
    #
    # try:
    #     p.addcouplereference(classescoupleby , couple)
    #
    # except Exception as e:
    #     print("An Error occurred in override reference " + str(e))
    #
    #
    # # Project.add_create_and_createby_reference(create_createby_list)
    # # Project.add_modify_and_modifyby_reference(modify_modifyby_list)
    # try:
    #     # metrics lot
    #     listener = LineOfCode(file_address=file_address)
    #     p.Walk(listener, tree)
    #     CountLineCode = listener.get_countLineCode
    #     CountLineComment = listener.get_countLineComment
    #     ContLineDecl = listener.get_countLineDecl
    #     CountLineExe = listener.get_countLineExec
    #     a += CountLineCode['file']
    #     b += CountLineComment['file']
    #     c += CountLineExe['file']
    #     d += ContLineDecl['file']
    #     print(f'CuntLineCode={CountLineCode}')
    #     print(f'CuntLineComment={CountLineComment}')
    #     print(f'CuntLineExe={CountLineExe}')
    #     print(f'CuntLineDecl={ContLineDecl}')
    #     # print(
    #     #     f'CountLIneCode: {CountLineCode["file"]} , CountLIneComment: {CountLineComment["file"]} , CountLINeExec: {CountLineExe["file"]} , CountLINeDecl: {ContLineDecl["file"]} ')
    #     # print("''''''''''''''''''''''''''''''''''''''''''''''''''''''''''\n")
    #     # df_clc = pd.DataFrame(data=stringify(listener.get_countLineCode), index=[1])
    #     # df_clcomment = pd.DataFrame(data=stringify(listener.get_countLineComment), index=[1])
    #     # df_cld = pd.DataFrame(data=stringify(listener.get_countLineDecl), index=[1])
    #     # df_cle = pd.DataFrame(data=stringify(listener.get_countLineExec), index=[1])
    #     # writer = pd.ExcelWriter(
    #     #     r'C:\Users\Lenovo\Desktop\compiler\compiler-project-dev\openunderstand\countlinecode.xlsx')
    #     # df_clc.to_excel(writer, 'countLineCode', index=False)
    #     # df_clcomment.to_excel(writer, 'countLineComnnet', index=False)
    #     # df_cld.to_excel(writer, 'countLineDecl', index=False)
    #     # df_cle.to_excel(writer, 'countLineExe', index=False)
    #     # writer.save()
    # except Exception as e:
    #     print("An Error occurred in couple reference in file :" + file_address + "\n" + str(e))
    #     pass
    # try:
    #     p.addoverridereference(classesx, extendedlist)
    # except Exception as e:
    #     print("An Error occurred in couple reference " + str(e))
    #
    # try:
    #     p.addcouplereference(classescoupleby, couple)
    #
    # except Exception as e:
    #     print("An Error occurred in override reference " + str(e))
    # try:
    #     print(f'TotalCountLIneCode: {a} , TotalCountLineComment:{b} , TotalCountLineExe:{c} , TotalCOuntLIneDecl:{d} ')
    # except Exception as e:
    #     print("An Error occurred in override reference " + str(e))
