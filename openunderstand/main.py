from db.api import open as db_open, create_db
from db.fill import main


from antlr4 import *
from analysis_passes.Throws_ThrowsBy import Throws_TrowsBy
from analysis_passes.DotRef_DorRefBy import DotRef_DotRefBy
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaLexer import JavaLexer
from db.models import KindModel, EntityModel, ReferenceModel
from analysis_passes.class_properties import ClassPropertiesListener, InterfacePropertiesListener

import os
from fnmatch import fnmatch


class Project():
    tree = None

    def Parse(self, fileAddress):
        file_stream = FileStream(fileAddress)
        lexer = JavaLexer(file_stream)
        tokens = CommonTokenStream(lexer)
        parser = JavaParserLabeled(tokens)
        tree = parser.compilationUnit()
        self.tree = tree
        return tree

    def Walk(self, listener, tree):
        walker = ParseTreeWalker()
        walker.walk(listener=listener, t=tree)

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
        print("processing file:",file_ent)
        return file_ent

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

    def getPackageEntity(self, file_ent, name, longname):
        # package kind id: 72
        ent = EntityModel.get_or_create(_kind= 72, _name=name, _parent=file_ent,
                                        _longname=longname, _contents="")
        return ent[0]

    def getUnnamedPackageEntity(self, file_ent):
        # unnamed package kind id: 73
        ent = EntityModel.get_or_create(_kind= 73, _name="(Unnamed_Package)", _parent=file_ent,
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
                                            _parent= props["parent"] if props["parent"] is not None else file_ent,
                                            _contents=props["contents"])
        return ent[0]

    def getInterfaceEntity(self, interface_longname, file_address): # can't be of unknown kind!
        props = p.getInterfaceProperties(interface_longname, file_address)
        if not props:
            return None
        else:
            kind = self.findKindWithKeywords("Interface", props["modifiers"])
            ent = EntityModel.get_or_create(_kind=kind, _name=props["name"],
                                            _longname=props["longname"],
                                            _parent= props["parent"] if props["parent"] is not None else file_ent,
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
                if not leastspecific_kind_selected \
                        or len(leastspecific_kind_selected._name) > len(kind._name):
                    leastspecific_kind_selected = kind
        return leastspecific_kind_selected


    def checkModifiersInKind(self, modifiers, kind):
        for modifier in modifiers:
            if modifier.lower() not in kind._name.lower():
                return False
        return True

if __name__ == '__main__':
    p = Project()
    create_db("../benchmark2_database.db",
              project_dir="..\benchmark")
    main()
    db = db_open("../benchmark2_database.db")

    # path = "D:/Term 7/Compiler/Final proj/github/OpenUnderstand/benchmark"
    path = "D:\\Python\\Open_Undrestand\\compiler-project\\benchmark\\jvlt-1.3.2"
    # files = p.getListOfFiles(path)
    # ########## AGE KHASTID YEK FILE RO RUN KONID:
    files = ["D:\\Python\\Open_Undrestand\\compiler-project\\openunderstand\\test.java"]

    for file_address in files:
        try:
            file_ent = p.getFileEntity(file_address)
            tree = p.Parse(file_address)
        except Exception as e:
            # print("An Error occurred in file:" + file_address + "\n" + str(e) )
            continue
        try:
            # Throws
            listener = Throws_TrowsBy()
            listener.implement = []
            p.Walk(listener, tree)
            p.addThrows_TrowsByRefs(listener.implement, file_ent, file_address,236,237,True)
        except Exception as e:
            # print("An Error occurred for reference implement in file:" + file_address + "\n" + str(e))
            pass

        try:
            # dotref
            listener = DotRef_DotRefBy()
            listener.declare = []
            p.Walk(listener, tree)
            p.addThrows_TrowsByRefs(listener.implement, file_ent, file_address,198,199,False)
        except Exception as e:
            # print("An Error occurred for reference declare in file:" + file_address + "\n" + str(e))
            pass
