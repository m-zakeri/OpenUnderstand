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
from analysis_passes.class_properties import (
    ClassPropertiesListener,
    InterfacePropertiesListener,
)
from analysis_passes.entity_manager_g11 import EntityGenerator, get_created_entity
from analysis_passes.Throws_ThrowsBy import Throws_TrowsBy
from analysis_passes.DotRef_DorRefBy import DotRef_DotRefBy
from metrics.Lineofcode import LineOfCode, stringify
from analysis_passes.g6_create_createby import CreateAndCreateByListener
from analysis_passes.g6_declare_declarein import DeclareAndDeclareinListener
from analysis_passes.g6_class_properties import ClassPropertiesListener
from analysis_passes.define_definein import DefineListener

from analysis_passes.callNonDynamic_callNonDynamicby import (
    CallNonDynamicAndCallNonDynamicBy,
)
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
from analysis_passes.define_definein import DefineListener

from analysis_passes.modify_modifyby import ModifyListener
from analysis_passes.usemodule_usemoduleby_g11 import UseModuleUseModuleByListener
from analysis_passes.g6_class_properties import (
    ClassPropertiesListener,
    InterfacePropertiesListener,
)

from analysis_passes.entity_manager_g11 import (
    EntityGenerator,
    FileEntityManager,
    get_created_entity,
)
from analysis_passes.type_typedby import TypedAndTypedByListener
from analysis_passes.use_useby import UseAndUseByListener
from analysis_passes.set_setby import SetAndSetByListener
from analysis_passes.setinit_setinitby import SetInitAndSetInitByListener
from understand.override_overrideby__G12 import overridelistener
from understand.couple_coupleby__G12 import CoupleAndCoupleBy
from analysis_passes.create_createby_g9 import CreateAndCreateBy
# from analysis_passes.g6_declare_declarein import DeclareAndDeclareinListener
from analysis_passes.declare_declarein import DeclareAndDeclareinListener
from analysis_passes.g6_class_properties import (
    ClassPropertiesListener,
    InterfacePropertiesListener,
)


from metrics.AvgCyclomatic import CyclomaticListener
from metrics.AvgCyclomaticStrict import CyclomaticStrictListener
from metrics.AvgCyclomaticModified import CyclomaticModifiedListener
from metrics.AvgEssential import EssentialListener

# from analysis_passes.define_and_definin_g6 import DefineListener


class Project:
    def __init__(self):
        pass

    tree = None

    @staticmethod
    def listToString(s):
        """a method to find projects path dynamically"""
        str1 = ""
        for ele in s[0 : len(s) - 1]:
            str1 += ele + "\\"
        return str1

    def Parse(self, fileAddress):
        file_stream = FileStream(fileAddress, encoding="utf8")
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

    def getFileEntity(self, path: str = "", name: str = ""):
        # kind id: 1
        file = open(path, mode="r")
        file_ent = EntityModel.get_or_create(
            _kind=1, _name=name, _longname=path, _contents=file.read()
        )[0]
        file.close()
        print("processing file:", file_ent)
        return file_ent

    def addDeclareRefs(self, ref_dicts, file_ent):
        for ref_dict in ref_dicts:
            if ref_dict["scope"] is None:  # the scope is the file
                scope = file_ent
            else:  # a normal package
                scope = self.getPackageEntity(
                    file_ent, ref_dict["scope"], ref_dict["scope_longname"]
                )

            if ref_dict["ent"] is None:  # the ent package is unnamed
                ent = self.getUnnamedPackageEntity(file_ent)
            else:  # a normal package
                ent = self.getPackageEntity(
                    file_ent, ref_dict["ent"], ref_dict["ent_longname"]
                )

            # Declare: kind id 192
            declare_ref = ReferenceModel.get_or_create(
                _kind=192,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _ent=ent,
                _scope=scope,
            )

            # Declarein: kind id 193
            declarein_ref = ReferenceModel.get_or_create(
                _kind=193,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _scope=ent,
                _ent=scope,
            )

    def addTypeRefs(self, d_type, file_ent):
        for type_tuple in d_type["typedBy"]:
            ent, h_c1 = EntityModel.get_or_create(
                _kind=224,
                _parent=None,
                _name=type_tuple[1],
                _longname=type_tuple[6] + "." + type_tuple[1],
                _value=None,
                _type=None,
                _contents=stream,
            )

            scope, h_c2 = EntityModel.get_or_create(
                _kind=225,
                _parent=None,
                _name=type_tuple[0],
                _longname=type_tuple[6] + "." + type_tuple[0],
                _value=None,
                _type=None,
                _contents=stream,
            )

            # 224		Java Typed
            typed_ref = ReferenceModel.get_or_create(
                _kind=224,
                _file=scope,
                _line=type_tuple[4],
                _column=type_tuple[5],
                _ent=ent,
                _scope=scope,
            )
            # 225    	Java Typedby
            typedby_ref = ReferenceModel.get_or_create(
                _kind=225,
                _file=ent,
                _line=type_tuple[2],
                _column=type_tuple[3],
                _ent=scope,
                _scope=ent,
            )

    def addSetInitRefs(self, d, file_ent):
        for type_tuple in d:
            par = EntityModel.get(_name=type_tuple[7])

            ent, h_c1 = EntityModel.get_or_create(
                _kind=220,
                _parent=par._id,
                _name=type_tuple[0],
                _longname=type_tuple[1],
                _value=type_tuple[3],
                _type=type_tuple[4],
                _contents=stream,
            )

            scope, h_c2 = EntityModel.get_or_create(
                _kind=221,
                _parent=None,
                _name=type_tuple[7],
                _longname=type_tuple[1],
                _value=None,
                _type=None,
                _contents=stream,
            )
            # 222: Java Set
            set_ref = ReferenceModel.get_or_create(
                _kind=220,
                _file=scope,
                _line=type_tuple[5],
                _column=type_tuple[6],
                _ent=ent,
                _scope=scope,
            )
            # 223: Java Setby
            setby_ref = ReferenceModel.get_or_create(
                _kind=221,
                _file=ent,
                _line=type_tuple[5],
                _column=type_tuple[6],
                _ent=scope,
                _scope=ent,
            )
            print("Set Init Added!")

    def addSetRefs(self, d, file_ent, stream):

        for type_tuple in d:
            par = EntityModel.get(_name=type_tuple[7])
            ent, h_c1 = EntityModel.get_or_create(
                _kind=222,
                _parent=par._id,
                _name=type_tuple[0],
                _longname=type_tuple[1],
                _value=type_tuple[3],
                _type=None,
                _contents=stream,
            )

            scope, h_c2 = EntityModel.get_or_create(
                _kind=223,
                _parent=None,
                _name=type_tuple[7],
                _longname=type_tuple[1],
                _value=None,
                _type=None,
                _contents=stream,
            )
            # 222: Java Set
            set_ref = ReferenceModel.get_or_create(
                _kind=222,
                _file=scope,
                _line=type_tuple[4],
                _column=type_tuple[5],
                _ent=ent,
                _scope=scope,
            )
            # 223: Java Setby
            setby_ref = ReferenceModel.get_or_create(
                _kind=223,
                _file=ent,
                _line=type_tuple[4],
                _column=type_tuple[5],
                _ent=scope,
                _scope=ent,
            )


    def addUseRefs(self, d_use, file_ent, stream):
        for use_tuple in d_use:
            ent, h_c1 = EntityModel.get_or_create(
                _kind=226,
                _parent=None,
                _name=use_tuple[1],
                _longname=use_tuple[6] + "." + use_tuple[1],
                _value=None,
                _type=None,
                _contents=stream,
            )

            scope, h_c2 = EntityModel.get_or_create(
                _kind=227,
                _parent=None,
                _name=use_tuple[0],
                _longname=use_tuple[6] + "." + use_tuple[0],
                _value=None,
                _type=None,
                _contents=stream,
            )

            # 226		Java Use
            use_ref = ReferenceModel.get_or_create(
                _kind=226,
                _file=file_ent,
                _line=use_tuple[4],
                _column=use_tuple[5],
                _ent=ent,
                _scope=scope,
            )
            # 227	 	Java Useby
            useby_ref = ReferenceModel.get_or_create(
                _kind=227,
                _file=file_ent,
                _line=use_tuple[2],
                _column=use_tuple[3],
                _ent=scope,
                _scope=ent,
            )

    def addDefineRefs(self, ref_dicts, file_ent):
        for ref_dict in ref_dicts:
            if ref_dict["scope"] is None:  # the scope is the file
                scope = file_ent
            else:  # a normal package
                scope = self.getPackageEntity(
                    file_ent, ref_dict["scope"], ref_dict["scope_longname"]
                )

            ent = self.getPackageEntity(
                file_ent, ref_dict["ent"], ref_dict["ent_longname"]
            )

            # Define: kind id 194
            define_ref = ReferenceModel.get_or_create(
                _kind=194,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _ent=ent,
                _scope=scope,
            )

            # Definein: kind id 195
            definein_ref = ReferenceModel.get_or_create(
                _kind=195,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _scope=ent,
                _ent=scope,
            )

    def addImplementOrImplementByRefs(self, ref_dicts, file_ent, file_address):
        pass

    @staticmethod
    def add_create_and_createby_reference(ref_dicts):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(
                _kind=self.findKindWithKeywords(
                    ref_dict["scope_kind"], ref_dict["scope_modifiers"]
                ),
                _name=ref_dict["scope_name"],
                _parent=ref_dict["scope_parent"]
                if ref_dict["scope_parent"] is not None
                else file_ent,
                _longname=ref_dict["scope_longname"],
                _contents=ref_dict["scope_contents"],
            )[0]
            ent = self.getImplementEntity(ref_dict["type_ent_longname"], file_address)
            implement_ref = ReferenceModel.get_or_create(
                _kind=188,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _ent=ent,
                _scope=scope,
            )
            implementBy_ref = ReferenceModel.get_or_create(
                _kind=189,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _ent=scope,
                _scope=ent,
            )

    def addExtendCoupleOrExtendCoupleByRefs(self, ref_dicts, file_ent, file_address):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(
                _kind=self.findKindWithKeywords(
                    ref_dict["scope_kind"], ref_dict["scope_modifiers"]
                ),
                _name=ref_dict["scope_name"],
                _parent=ref_dict["scope_parent"]
                if ref_dict["scope_parent"] is not None
                else file_ent,
                _longname=ref_dict["scope_longname"],
                _contents=ref_dict["scope_contents"],
            )[0]
            ent = self.getImplementEntity(ref_dict["type_ent_longname"], file_address)
            extend_ref = ReferenceModel.get_or_create(
                _kind=178,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _ent=ent,
                _scope=scope,
            )
            extendBy_ref = ReferenceModel.get_or_create(
                _kind=179,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _ent=scope,
                _scope=ent,
            )

    def addCallOrCallByRefs(self, ref_dicts, file_ent, file_address):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(
                _kind=self.findKindWithKeywords(
                    ref_dict["scope_kind"], ref_dict["scope_modifiers"]
                ),
                _name=ref_dict["scope_name"],
                _parent=ref_dict["scope_parent"]
                if ref_dict["scope_parent"] is not None
                else file_ent,
                _longname=ref_dict["scope_longname"],
                _contents=ref_dict["scope_contents"],
            )[0]
            ent = self.getImplementEntity(ref_dict["type_ent_longname"], file_address)
            call_ref = ReferenceModel.get_or_create(
                _kind=172,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _ent=ent,
                _scope=scope,
            )
            callBy_ref = ReferenceModel.get_or_create(
                _kind=173,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
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

    def addCallNonDynamicOrCallNonDynamicByRefs(
        self, ref_dicts, file_ent, file_address
    ):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(
                _kind=self.findKindWithKeywords(
                    ref_dict["scope_kind"], ref_dict["scope_modifiers"]
                ),
                _name=ref_dict["scope_name"],
                _parent=ref_dict["scope_parent"]
                if ref_dict["scope_parent"] is not None
                else file_ent,
                _longname=ref_dict["scope_longname"],
                _contents=ref_dict["scope_contents"],
            )[0]
            ent = self.getImplementEntity(ref_dict["type_ent_longname"], file_address)
            call_ref = ReferenceModel.get_or_create(
                _kind=170,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _ent=ent,
                _scope=scope,
            )
            callBy_ref = ReferenceModel.get_or_create(
                _kind=171,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _ent=scope,
                _scope=ent,
            )

    def addCreateRefs(self, ref_dicts, file_ent, file_address):

        for ref_dict in ref_dicts:

            scope = EntityModel.get_or_create(
                _kind=self.findKindWithKeywords("Method", ref_dict["scopemodifiers"]),
                _name=ref_dict["scopename"],
                _type=ref_dict["scopereturntype"],
                _parent=ref_dict["scope_parent"]
                if ref_dict["scope_parent"] is not None
                else file_ent,
                _longname=ref_dict["scopelongname"],
                _contents=["scopecontent"],
            )[0]

            ent = self.getCreatedClassEntity(
                ref_dict["refent"], ref_dict["potential_refent"], file_address
            )

            Create = ReferenceModel.get_or_create(
                _kind=190,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _scope=scope,
                _ent=ent,
            )

            Createby = ReferenceModel.get_or_create(
                _kind=191,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=ref_dict["col"],
                _scope=ent,
                _ent=scope,
            )


    def getPackageEntity(self, file_ent, name, longname):
        # package kind id: 72
        ent = EntityModel.get_or_create(
            _kind=72, _name=name, _parent=file_ent, _longname=longname, _contents=""
        )
        return ent[0]

    def getUnnamedPackageEntity(self, file_ent):
        # unnamed package kind id: 73
        ent = EntityModel.get_or_create(
            _kind=73,
            _name="(Unnamed_Package)",
            _parent=file_ent,
            _longname="(Unnamed_Package)",
            _contents="",
        )
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

    def getCreatedClassEntity(
        self, class_longname, class_potential_longname, file_address
    ):
        props = self.getClassProperties(class_potential_longname, file_address)
        if not props:
            return self.getClassEntity(class_longname, file_address)
        else:
            return self.getClassEntity(class_potential_longname, file_address)

    def getClassEntity(self, class_longname, file_address):
        props = self.getClassProperties(class_longname, file_address)
        if not props:  # This class is unknown, unknown class id: 84
            ent = EntityModel.get_or_create(
                _kind=84,
                _name=class_longname.split(".")[-1],
                _longname=class_longname,
                _contents="",
            )
        else:
            if len(props["modifiers"]) == 0:
                props["modifiers"].append("default")
            kind = self.findKindWithKeywords("Class", props["modifiers"])
            ent = EntityModel.get_or_create(
                _kind=kind,
                _name=props["name"],
                _longname=props["longname"],
                _parent=props["parent"] if props["parent"] is not None else file_ent,
                _contents=props["contents"],
            )
        return ent[0]

    def getInterfaceEntity(
        self, interface_longname, file_address
    ):  # can't be of unknown kind!
        props = self.getInterfaceProperties(interface_longname, file_address)
        if not props:
            return None
        else:
            kind = self.findKindWithKeywords("Interface", props["modifiers"])
            ent = EntityModel.get_or_create(
                _kind=kind,
                _name=props["name"],
                _longname=props["longname"],
                _parent=props["parent"] if props["parent"] is not None else file_ent,
                _contents=props["contents"],
            )
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
                if not leastspecific_kind_selected or len(
                    leastspecific_kind_selected._name
                ) > len(kind._name):
                    leastspecific_kind_selected = kind
        return leastspecific_kind_selected

    def checkModifiersInKind(self, modifiers, kind):
        for modifier in modifiers:
            if modifier.lower() not in kind._name.lower():
                return False
        return True

    def addoverridereference(self, classes, extendedfiles, file_ent):
        for tuples in extendedfiles:
            main = tuples[0]
            fromx = tuples[1]
            methodsmain = classes[main]
            for x in methodsmain:
                file = x["File"]
                kindx = self.findKindWithKeywords(x["scope_kind"], x["scope_modifiers"])
                if kindx is None:
                    kindx = x["modifiersx"]
                scope = EntityModel.get_or_create(
                    _kind=kindx,
                    _name=x["scope_name"],
                    _parent=x["scope_parent"]
                    if x["scope_parent"] is not None
                    else file_ent,
                    _longname=x["scope_longname"],
                    _contents=x["scope_contents"],
                    _type=x["Methodkind"],
                )
                methodname1 = x["MethodIs"]

                if fromx in classes:
                    mathodsfrom = classes[fromx]
                    for y in mathodsfrom:

                        if y["MethodIs"] == methodname1:
                            fe = file_ent
                            kind = self.findKindWithKeywords(
                                y["scope_kind"], y["scope_modifiers"]
                            )
                            if kind is None:
                                kind = y["modifiersx"]
                            ent = EntityModel.get_or_create(
                                _kind=kind,
                                _name=y["scope_name"],
                                _parent=y["scope_parent"]
                                if y["scope_parent"] is not None
                                else fe,
                                _longname=y["scope_longname"],
                                _contents=y["scope_contents"],
                                _type=y["Methodkind"],
                            )

                            override_ref = ReferenceModel.get_or_create(
                                _kind=211,
                                _file=file_ent,
                                _line=x["line"],
                                _column=x["col"],
                                _ent=ent[0],
                                _scope=scope[0],
                            )
                            overrideBy_ref = ReferenceModel.get_or_create(
                                _kind=212,
                                _file=fe,
                                _line=y["line"],
                                _column=y["col"],
                                _ent=scope[0],
                                _scope=ent[0],
                            )
                elif x["is_overrided"]:
                    overrideword = x[0]
                    if overrideword not in classes:
                        ent = EntityModel.get_or_create(
                            _kind="Unknown Method",
                            _name=overrideword[1],
                            _parent=file_ent,
                            _longname=overrideword,
                            _contents="",
                        )
                        override_ref = ReferenceModel.get_or_create(
                            _kind=211,
                            _file=file_ent,
                            _line=x["line"],
                            _column=x["col"],
                            _ent=ent[0],
                            _scope=scope[0],
                        )

    def get_parent_entity(self, file_path):
        return EntityModel.get_or_none(_longname=file_path)

    def add_entity_package(self, package_name, file_path):
        file_entity = self.get_parent_entity(file_path)
        created_entity, _ = EntityModel.get_or_create(
            _kind_id=KindModel.get_or_none(_name="Java Package")._id,
            _parent_id=file_entity._id,
            _name=package_name["package_name"].split(".")[-1],
            _longname=package_name["package_name"],
            _contents="",
        )
        ReferenceModel.get_or_create(
            _kind_id=KindModel.get_or_none(_name="Java Define")._id,
            _file_id=file_entity._id,
            _line=package_name["line"],
            _column=package_name["column"],
            _ent_id=file_entity._id,
            _scope_id=created_entity._id,
        )
        ReferenceModel.get_or_create(
            _kind_id=KindModel.get_or_none(_name="Java Definein")._id,
            _file_id=file_entity._id,
            _line=package_name["line"],
            _column=package_name["column"],
            _ent_id=created_entity._id,
            _scope_id=file_entity._id,
        )

    def define_parent(self, entity_type, entity_values, file_path, package_name):
        if entity_type == "class" or entity_type == "interface":
            return EntityModel.get_or_none(_longname=file_path)
        else:
            return EntityModel.get_or_none(
                _longname=f"{package_name}.{entity_values['parent_name']}"
            )

    def extract_is_constructor(self, prefixes):
        pattern_visibility = " Default"
        if "private" in prefixes:
            pattern_visibility = " Private"
        elif "public" in prefixes:
            pattern_visibility = " Public"
        elif "protected" in prefixes:
            pattern_visibility = " Protected"
        return f"Java Method Constructor Member{pattern_visibility}"

    def config_entity_type(self, type_entity):
        if type_entity == "class":
            return "Class Type"
        if type_entity == "interface":
            return "Interface Type"
        if type_entity == "variable":
            return "Variable"
        if type_entity == "method":
            return "Method"

    def extract_all_kind(self, prefixes, type_entity, is_constructor) -> str:
        if is_constructor:
            return self.extract_is_constructor(prefixes)

        pattern_static = ""
        pattern_generic = ""
        pattern_abstract = ""
        pattern_visibility = " Default"
        if "static" in prefixes:
            pattern_static = " Static"
        if "generic" in prefixes:
            pattern_generic = " Generic"
        if "abstract" in prefixes:
            pattern_abstract = " Abstract"
        elif "final" in prefixes:
            pattern_abstract = " Final"
        if "private" in prefixes:
            pattern_visibility = " Private"
        elif "public" in prefixes:
            pattern_visibility = " Public"
        elif "protected" in prefixes:
            pattern_visibility = " Protected"

        result_str = "Java{0}{1}{2} {3}{4} Member".format(
            pattern_static,
            pattern_abstract,
            pattern_generic,
            self.config_entity_type(type_entity),
            pattern_visibility,
        )
        if type_entity == "interface":
            result_str = result_str.replace("Member", "").strip()
        return result_str

    def add_defined_entities(self, entities, entity_type, package_name, file_path):
        for entity_key, entity_values in entities.items():
            is_constructor = False
            if entity_type == "method" and entity_values["type"] == "":
                is_constructor = True
            kind_str = (
                entity_values["kind_name"]
                if entity_type == "local variable" or entity_type == "parameter"
                else self.extract_all_kind(
                    entity_values["prefixes"], entity_type, is_constructor
                )
            )

            kind_name = KindModel.get_or_none(_name=kind_str)
            kind_id = kind_name._id if kind_name else 1

            model_name = entity_values["name"]
            model_type = entity_values["type"]
            model_value = entity_values["value"]
            index_equal = model_value.find("=")
            if index_equal != -1:
                model_value = model_value[index_equal + 1 :]
            else:
                model_value = ""
            model_longname = (
                f"{package_name}.{entity_values['parent_name']}.{model_name}"
                if entity_values["parent_name"] != ""
                else f"{package_name}.{model_name}"
            )
            model_contents = entity_values["contents"]
            model_parent = define_parent(
                entity_type, entity_values, file_path, package_name
            )

            created_entity, _ = EntityModel.get_or_create(
                _kind_id=kind_id,
                _name=model_name,
                _type=model_type,
                _value=model_value,
                _longname=model_longname,
                _parent_id=model_parent._id,
                _contents=model_contents,
            )

            reference_line = entity_values["line"]
            reference_column = entity_values["column"]
            reference_file = EntityModel.get_or_none(_longname=file_path)

            ReferenceModel.get_or_create(
                _kind_id=KindModel.get_or_none(_name="Java Define")._id,
                _file_id=reference_file._id,
                _line=reference_line,
                _column=reference_column,
                _ent_id=model_parent._id,
                _scope_id=created_entity._id,
            )

            ReferenceModel.get_or_create(
                _kind_id=KindModel.get_or_none(_name="Java Definein")._id,
                _file_id=reference_file._id,
                _line=reference_line,
                _column=reference_column,
                _ent_id=created_entity._id,
                _scope_id=model_parent._id,
            )

    def getThrowEntity(self, longname, file_address):
        ent = self.getInterfaceEntity(longname, file_address)
        if not ent:
            ent = self.getClassEntity(longname, file_address)
        return ent

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

    def addcouplereference(self, classes, couples, file_ent):
        keykind = ""
        for c in couples:

            scope = EntityModel.get_or_create(
                _kind=self.findKindWithKeywords(c["scope_kind"], c["scope_modifiers"]),
                _name=c["scope_name"],
                _parent=c["scope_parent"]
                if c["scope_parent"] is not None
                else file_ent,
                _longname=c["scope_longname"],
                _contents=c["scope_contents"],
            )
            if "type_ent_longname" in c:
                keylist = c["type_ent_longname"]
                if len(keylist) != 0:
                    for key in keylist:
                        if key in classes:
                            c1 = classes[key]
                            file_ent2 = file_ent
                            keykind = self.findKindWithKeywords(
                                c1["scope_kind"], c1["scope_modifiers"]
                            )
                            ent = EntityModel.get_or_create(
                                _kind=self.findKindWithKeywords(
                                    c1["scope_kind"], c1["scope_modifiers"]
                                ),
                                _name=c1["scope_name"],
                                _parent=c1["scope_parent"]
                                if c1["scope_parent"] is not None
                                else file_ent2,
                                _longname=c1["scope_longname"],
                                _contents=c1["scope_contents"],
                            )
                            CoupleBy_ref = ReferenceModel.get_or_create(
                                _kind=180,
                                _file=file_ent2,
                                _line=c["line"],
                                _column=c["col"],
                                _ent=scope[0],
                                _scope=ent[0],
                            )

                        else:
                            kw = key.split(".")
                            keykind = "Unknown Class"
                            ent = EntityModel.get_or_create(
                                _kind="Unknown Class",
                                _name=kw[-1],
                                _parent=file_ent,
                                _longname=key,
                            )
                        Couple_ref = ReferenceModel.get_or_create(
                            _kind=179,
                            _file=file_ent,
                            _line=c["line"],
                            _column=c["col"],
                            _ent=ent[0],
                            _scope=scope[0],
                        )


import logging
import configparser


def setup_logger():
    # Read configurations from config.ini file
    config = configparser.ConfigParser()
    config.read("config.ini")

    # Create logger object
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    # Create file handler and set the log level based on the configuration
    file_handler = logging.FileHandler(config["Logging"]["filename"])
    file_handler.setLevel(getattr(logging, config["Logging"]["level"].upper()))

    # Create log formatter
    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    file_handler.setFormatter(formatter)

    # Add file handler to the logger
    logger.addHandler(file_handler)

    return logger

def addDefineEntity(p,define_listener, logger, ent, package_name, file_address):
    try:
        # define
        p.add_defined_entities(
            define_listener, ent, package_name, file_address
        )
    except Exception as e:
        logger.error("define fail ")
        logger.error(
            "An Error occurred for reference define in file:"
            + file_address
            + "\n"
            + str(e)
        )


def runner(path_project: str = ""):
    logger = setup_logger()
    p = Project()
    files = p.getListOfFiles(path_project)
    classesx = {}
    extendedlist = []
    classescoupleby = {}
    couple = []
    a = b = c = d = 0
    for file_address in files:
        try:
            parse_tree = p.Parse(file_address)
            file_ent = p.getFileEntity(
                path=file_address, name=os.path.basename(file_address)
            )
            tree = p.Parse(file_address)
            logger.info("file parse success")
        except Exception as e:
            logger.error("An Error occurred in file file parse:" + file_address + "\n" + str(e))
            continue

        entity_generator = EntityGenerator(file_address, parse_tree)

        try:
            #  create refs TODO: fix NOT NULL constraint failed: entitymodel._kind_id
            listener = CreateAndCreateBy()
            p.Walk(listener, tree)
            p.addCreateRefs(listener.create, file_ent, file_address)
            logger.info("create refs success ")
        except Exception as e:
            logger.error(
                "An Error occurred in file create refs :" + file_address + "\n" + str(e))
        try:
            listener = DefineListener()
            p.Walk(listener, tree)
            p.addDefineRefs(listener.defines, file_ent)
            logger.info("define success ")
        except Exception as e:
            logger.error(
                "An Error occurred for reference implement in file define:"
                + file_address
                + "\n"
                + str(e)
            )

        try:
            # declare
            listener = DeclareAndDeclareinListener()
            p.Walk(listener, tree)
            p.addDeclareRefs(listener.declare, file_ent)
            logger.info("declare success ")
        except Exception as e:
            logger.error(
                "An Error occurred for reference declare in file:"
                + file_address
                + "\n"
                + str(e)
            )


        try:
            # modify TODO : FIX modify error not found
            listener = ModifyListener(entity_generator, logger)
            p.Walk(listener, parse_tree)
            p.add_modify_and_modifyby_reference(listener.modify)
            logger.info("modify success ")
        except Exception as e:
            logger.error(
                "An Error occurred for reference modify in file:"
                + file_address
                + "\n"
                + str(e)
            )

        try:
            listener = overridelistener()
            listener.extendedtoentity = {}
            listener.set_dictionary(classesx)
            listener.set_file(file_address)
            listener.set_list(extendedlist)
            p.Walk(listener, tree)
            classesx = listener.get_classes
            extendedlist = listener.get_extendeds
            p.addoverridereference(classesx, extendedlist, file_ent)
            logger.info("overrides success ")
        except Exception as e:
            logger.error(
                "An Error occurred in override reference in file :"
                + file_address
                + "\n"
                + str(e)
            )
            continue

        try:
            listener = CoupleAndCoupleBy()
            listener.set_file(filex=file_address)
            listener.set_classesx(classesx=classescoupleby)
            listener.set_couples(couples=couple)
            p.Walk(listener, tree)
            classescoupleby = listener.get_classes
            couple = listener.get_couples
            p.addcouplereference(classescoupleby, couple, file_ent)
            logger.info("couple success ")
        except Exception as e:
            logger.error(
                "An Error occurred in couple reference in file :"
                + file_address
                + "\n"
                + str(e)
            )
            continue
        try:
            # Throws
            listener = Throws_TrowsBy()
            listener.implement = []
            p.Walk(listener, tree)
            p.addThrows_TrowsByRefs(
                listener.implement, file_ent, file_address, 236, 237, True
            )
            logger.info("Throws success ")
        except Exception as e:
            logger.error(
                "An Error occurred in throws in file :"
                + file_address
                + "\n"
                + str(e)
            )
            pass

        try:
            # dot ref TODO:  'ClassBodyDeclaration1Context' object has no attribute 'modifier'
            listener = DotRef_DotRefBy()
            p.Walk(listener, tree)
            p.addThrows_TrowsByRefs(
                listener.implement, file_ent, file_address, 198, 199, False
            )
            logger.info("DotRef success ")
        except Exception as e:
            logger.error(
                "An Error occurred in dotref in file :"
                + file_address
                + "\n"
                + str(e)
            )
            pass

        try:
            # set ref
            listener = SetAndSetByListener(file_address)
            p.Walk(listener, tree)
            p.addSetRefs(
                listener.setBy, file_ent, ""
            )
            logger.info("set Ref success ")
        except Exception as e:
            logger.error(
                "An Error occurred in set ref in file :"
                + file_address
                + "\n"
                + str(e)
            )
            pass

        try:
            # use ref
            listener = UseAndUseByListener()
            p.Walk(listener, tree)
            p.addUseRefs(
                listener.useBy, file_ent, ""
            )
            logger.info("use ref success ")
        except Exception as e:
            logger.error(
                "An Error occurred in use ref in file :"
                + file_address
                + "\n"
                + str(e)
            )
            pass

        try:
            # call ref
            listener = CallNonDynamicAndCallNonDynamicBy()
            p.Walk(listener, tree)
            p.addCallOrCallByRefs(
                listener.implement, file_ent, file_address
            )
            logger.info("call ref success ")
        except Exception as e:
            logger.error(
                "An Error occurred in call ref in file :"
                + file_address
                + "\n"
                + str(e)
            )
            pass

