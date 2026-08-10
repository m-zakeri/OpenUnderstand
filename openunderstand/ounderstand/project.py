"""This module is the main part for creating all entities and references in database. our task was the javaModify and
javaCreate and their reverse references. """

import logging
import os
from fnmatch import fnmatch
from antlr4 import *
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaLexer import JavaLexer
from openunderstand.oudb.models import (KindModel, EntityModel, ReferenceModel,
                                        col_1based, resolve_entity_ref, kind_family)
from openunderstand.analysis_passes.modify_modifyby import ModifyListener
from openunderstand.analysis_passes.g6_class_properties import (
    ClassPropertiesListener,
    InterfacePropertiesListener,
)

from openunderstand.utils.utilities import ClassTypeData
from openunderstand.utils import antler_parser, utilities
from openunderstand.oudb.models import kind_id
from openunderstand.utils import kind_names

_ENGINE = None


def _use_cpp_engine():
    """Whether config.ini asked for the C++ parser, cached after the first read.

    Read once rather than per file: Project is constructed for every source
    file, and setup_config() re-parses config.ini on each call.

    Historically `engine_core` was written by the CLI but never read anywhere,
    so choosing "C++" did nothing. It now selects the accelerator -- and still
    falls back to the Python parser, with one warning, if it was never built.
    """
    global _ENGINE
    if _ENGINE is None:
        try:
            # Resolved through the module, not `from ... import`, so a caller
            # that swaps utilities.setup_config still wins regardless of import
            # order.
            requested = utilities.setup_config()["Config"]["engine_core"]
        except Exception:
            requested = "Python"
        # The CLI default is "Python", config.ini has said "Python3", and the
        # README says "C++ or Python". Accept anything that starts with a "c".
        _ENGINE = requested.strip().lower().startswith("c")
    return _ENGINE


class Project:
    def __init__(self):
        self.tree = None

    @staticmethod
    def listToString(s):
        """a method to find projects path dynamically"""
        str1 = ""
        for ele in s[0 : len(s) - 1]:
            str1 += ele + "\\"
        return str1

    def Parse(self, fileAddress):
        file_stream = FileStream(fileAddress, encoding="utf8")
        return_tree = antler_parser.parse(
            file_stream, "compilationUnit", prefer_cpp=_use_cpp_engine()
        )
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
            _kind=kind_id("Java File"), _name=name, _longname=path, _contents=file.read()
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
                _kind=kind_id("Java Declare"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _ent=ent,
                _scope=scope,
            )

            # Declarein: kind id 193
            declarein_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Declarein"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _scope=ent,
                _ent=scope,
            )

    def addTypeRefs(self, d_type, file_ent, stream: str = ""):
        for type_tuple in d_type["typedBy"]:
            ent, h_c1 = EntityModel.get_or_create(
                # was the reference kind Java Typed, written into an entity row; the referenced type
                _kind=kind_id("Java Unknown Class Type Member"),
                _parent=None,
                _name=type_tuple[1],
                _longname=type_tuple[6] + "." + type_tuple[1],
                _value=None,
                _type=None,
                _contents=stream,
            )

            scope, h_c2 = EntityModel.get_or_create(
                # was the reference kind Java Typedby, written into an entity row; the declared variable
                _kind=kind_id("Java Unknown Variable Member"),
                _parent=None,
                _name=type_tuple[0],
                _longname=type_tuple[6] + "." + type_tuple[0],
                _value=None,
                _type=None,
                _contents=stream,
            )

            # _file is the file the reference occurs in -- it used to be set to
            # the referenced entity, and the inverse to the declaration's own
            # position, so neither direction landed where Understand puts it.
            typed_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Typed"),
                _file=file_ent,
                _line=type_tuple[4],
                _column=col_1based(type_tuple[5]),
                _ent=ent,
                _scope=scope,
            )
            typedby_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Typedby"),
                _file=file_ent,
                _line=type_tuple[4],
                _column=col_1based(type_tuple[5]),
                _ent=scope,
                _scope=ent,
            )

    def addSetRefs(self, d, file_ent, stream: str = ""):

        for type_tuple in d:
            par = EntityModel.get(_name=type_tuple[7])
            ss = str(type_tuple[1]).rfind(".")
            ent, h_c1 = EntityModel.get_or_create(
                # was the reference kind Java Set, written into an entity row; the variable being set
                _kind=kind_id("Java Unknown Variable Member"),
                _parent=par._id,
                _name=type_tuple[0],
                _longname=type_tuple[1],
                _value=type_tuple[3],
                _type=type_tuple[9],
                _contents="",
            )

            scope, h_c2 = EntityModel.get_or_create(
                # was the reference kind Java Setby, written into an entity row; the setting scope
                _kind=kind_id("Java Unknown Method Member"),
                _parent=None,
                _name=type_tuple[10],  # PROBLEM
                _longname=str(type_tuple[1])[:ss],
                _value=None,
                _type=type_tuple[3],
                _contents=type_tuple[8],
            )
            # 222: Java Set
            set_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Set"),
                _file=file_ent,
                _line=type_tuple[4],
                _column=col_1based(type_tuple[5]),
                _ent=ent,
                _scope=scope,
            )
            # 223: Java Setby
            setby_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Setby"),
                _file=file_ent,
                _line=type_tuple[4],
                _column=col_1based(type_tuple[5]),
                _ent=scope,
                _scope=ent,
            )

    def addSetInitRefs(self, d, file_ent, stream: str = ""):
        for type_tuple in d:
            ss = str(type_tuple[1]).rfind(".")
            par = EntityModel.get(_name=type_tuple[7])
            ent, h_c1 = EntityModel.get_or_create(
                # was the reference kind Java Set Init, written into an entity row; the variable being init-set
                _kind=kind_id("Java Unknown Variable Member"),
                _parent=par._id,
                _name=type_tuple[0],
                _longname=type_tuple[1],
                _value=type_tuple[3],
                _type=type_tuple[8],
                _contents="",
            )

            scope, h_c2 = EntityModel.get_or_create(
                # was the reference kind Java Setby Init, written into an entity row; the setting scope
                _kind=kind_id("Java Unknown Method Member"),
                _parent=None,
                _name=type_tuple[10],  # PROBLEM
                _longname=str(type_tuple[1])[:ss],
                _value=None,
                _type=type_tuple[3],
                _contents=type_tuple[9],
            )
            # 222: Java SetInit
            set_init_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Set Init"),
                _file=file_ent,
                _line=type_tuple[5],
                _column=col_1based(type_tuple[6]),
                _ent=ent,
                _scope=scope,
            )
            # 223: Java SetInitby
            setby_init_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Setby Init"),
                _file=file_ent,
                _line=type_tuple[5],
                _column=col_1based(type_tuple[6]),
                _ent=scope,
                _scope=ent,
            )

    def addSetPartialRefs(self, d, file_ent, stream: str = ""):

        for type_tuple in d:
            ss = str(type_tuple[1]).rfind(".")
            par = EntityModel.get(_name=type_tuple[7])
            ent, h_c1 = EntityModel.get_or_create(
                # was the reference kind Java Set Partial, written into an entity row; the variable being partially set
                _kind=kind_id("Java Unknown Variable Member"),
                _parent=par._id,
                _name=type_tuple[0],
                _longname=type_tuple[1],
                _value=type_tuple[3],
                _type=type_tuple[8],
                _contents="",
            )

            scope, h_c2 = EntityModel.get_or_create(
                # was the reference kind Java Setby Partial, written into an entity row; the setting scope
                _kind=kind_id("Java Unknown Method Member"),
                _parent=None,
                _name=type_tuple[7],  # PROBLEM
                _longname=str(type_tuple[1])[:ss],
                _value=None,
                _type=type_tuple[3],
                _contents=type_tuple[9],
            )
            # 222: Java Set Partial
            set_partial_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Set Deref Partial"),
                _file=file_ent,
                _line=type_tuple[4],
                _column=col_1based(type_tuple[5]),
                _ent=ent,
                _scope=scope,
            )
            # 223: Java Setby Partial
            setby_partial_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Setby Deref Partial"),
                _file=file_ent,
                _line=type_tuple[4],
                _column=col_1based(type_tuple[5]),
                _ent=scope,
                _scope=ent,
            )

    def addUseRefs(self, d_use, file_ent, stream: str = ""):
        for use_tuple in d_use:
            ent, h_c1 = EntityModel.get_or_create(
                # was the reference kind Java Use, written into an entity row; the used entity
                _kind=kind_id("Java Unknown Variable Member"),
                _parent=None,
                _name=use_tuple[1],
                _longname=use_tuple[6] + "." + use_tuple[1],
                _value=None,
                _type=None,
                _contents=stream,
            )

            scope, h_c2 = EntityModel.get_or_create(
                # was the reference kind Java Useby, written into an entity row; the using scope
                _kind=kind_id("Java Unknown Method Member"),
                _parent=None,
                _name=use_tuple[0],
                _longname=use_tuple[6] + "." + use_tuple[0],
                _value=None,
                _type=None,
                _contents=stream,
            )

            use_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Use"),
                _file=file_ent,
                _line=use_tuple[4],
                _column=col_1based(use_tuple[5]),
                _ent=ent,
                _scope=scope,
            )
            # The inverse is the same reference read backwards, so it sits at
            # the same place in the same file. Pointing it at the declaration
            # instead made the two directions dedupe differently -- 903 Use
            # rows against 2771 Useby -- and put every inverse at a position
            # Understand never reports one at.
            useby_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Useby"),
                _file=file_ent,
                _line=use_tuple[4],
                _column=col_1based(use_tuple[5]),
                _ent=scope,
                _scope=ent,
            )

    def addDefineRefs(self, ref_dicts, file_ent):
        """Create every declared entity, with the kind Understand would give it.

        This is the pass that decides what most entities *are*. It used to route
        both sides of every Define reference through getPackageEntity(), which
        hard-codes Java Package -- so 964 of 2626 entities on the JSON benchmark
        claimed to be packages, including every parameter and local variable,
        while the parameter, constructor and annotation kinds had no rows at all.
        """
        for ref_dict in ref_dicts:
            if ref_dict["scope"] is None:  # a top-level declaration: scope is the file
                scope = file_ent
            else:
                scope = self.getScopeEntity(
                    file_ent, ref_dict["scope"], ref_dict["scope_longname"]
                )

            ent, _ = EntityModel.get_or_create(
                _kind=kind_names.resolve(
                    ref_dict.get("decl"),
                    ref_dict.get("modifiers") or (),
                    ref_dict["ent"],
                ),  # re-resolved below when an earlier pass already made the row
                # The enclosing scope, not the package: Understand's parent of a
                # method is its class, and of a local its method.
                _parent=scope,
                _name=ref_dict["ent"],
                _longname=ref_dict["ent_longname"],
                _value=None,
                _type=ref_dict["type"],
                _contents=ref_dict["contents"],
            )

            # The define pass is the only one that reads the declaration
            # itself -- its modifiers, its real source. Other passes run
            # before it and guess, and get_or_create keeps whichever row came
            # first, so `public class fibonacci extends basic_operation` was
            # left labelled Default by an earlier pass's guess. Declarations
            # are this pass's authority: it overwrites both.
            declared_kind = kind_names.resolve(
                ref_dict.get("decl"), ref_dict.get("modifiers") or (), ref_dict["ent"]
            )
            dirty = False
            if ref_dict["contents"] and ent._contents != ref_dict["contents"]:
                ent._contents = ref_dict["contents"]
                dirty = True
            if declared_kind is not None and ent._kind_id != declared_kind:
                ent._kind = declared_kind
                dirty = True
            if dirty:
                ent.save()

            define_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Define"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _ent=ent,
                _scope=scope,
            )

            # Definein: kind id 195
            definein_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Definein"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _scope=ent,
                _ent=scope,
            )

            # Understand marks the extent of every braced declaration with a
            # Begin at its first token and an End at its closing brace, both
            # referring to the entity itself.
            span = ref_dict.get("span")
            if span:
                for kind, (line, column) in zip(("Begin", "End"), span):
                    for name in (f"Java {kind}", f"Java {kind}by"):
                        ReferenceModel.get_or_create(
                            _kind=kind_id(name),
                            _file=file_ent,
                            _line=line,
                            _column=col_1based(column),
                            _ent=ent,
                            _scope=ent,
                        )

    def addMethodCallRefs(self, ref_dicts, file_ent):
        """Write Call/Callby for every call site, resolving what it can locally.

        A name that resolves to nothing here becomes an Unknown placeholder;
        merge_placeholder_entities() folds it into the real method once every
        file has been parsed, which is what makes cross-file calls resolve at
        all.
        """
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_none(
                EntityModel._longname == ref_dict["scope_longname"]
            )
            if scope is None:
                continue

            name = ref_dict["name"]
            ent = EntityModel.get_or_none(
                EntityModel._longname == f"{ref_dict['scope_longname']}.{name}"
            )
            if ent is None:
                ent, _ = EntityModel.get_or_create(
                    _kind=kind_id("Java Unknown Method Member"),
                    _name=name,
                    _parent=file_ent,
                    _longname=name,
                    _contents="",
                )
            if ent._id == scope._id:
                continue

            for kind, (a, b) in (("Java Call", (ent, scope)),
                                 ("Java Callby", (scope, ent))):
                ReferenceModel.get_or_create(
                    _kind=kind_id(kind),
                    _file=file_ent,
                    _line=ref_dict["line"],
                    _column=col_1based(ref_dict["col"]),
                    _ent=a,
                    _scope=b,
                )

    def addUseVariantRefs(self, ref_dicts, file_ent):
        """Write the qualified Use/Typed variants collected by use_variants.py.

        Each is resolved against the entity the define pass already created for
        the enclosing scope; a name that resolves to nothing becomes an Unknown
        placeholder, which merge_placeholder_entities() folds in afterwards.
        """
        for ref_dict in ref_dicts:
            scope_longname = ref_dict["scope_longname"]
            scope = EntityModel.get_or_none(EntityModel._longname == scope_longname)
            if scope is None:
                continue

            name = ref_dict["name"]
            ent = EntityModel.get_or_none(
                EntityModel._longname == f"{scope_longname}.{name}"
            ) or EntityModel.get_or_none(EntityModel._name == name)

            # A dereference is only "partial" when the receiver is a variable.
            # `JSONObject.NULL` reads the same way syntactically but names a
            # type, and Understand labels that differently -- without this the
            # pass emitted 1379 rows where Understand emits 788.
            if ref_dict["kind"] == "Java Use Deref Partial":
                if ent is None or kind_family(ent._kind_id) != "variable":
                    continue

            if ent is None:
                ent, _ = EntityModel.get_or_create(
                    _kind=kind_id("Java Unknown Class Type Member"),
                    _name=name,
                    _parent=file_ent,
                    _longname=name,
                    _contents="",
                )

            forward = ref_dict["kind"]
            inverse = KindModel.get_or_none(_name=forward)
            if inverse is None or inverse._inv_id is None:
                continue
            for kind, (a, b) in ((forward, (ent, scope)),
                                 (KindModel.get_by_id(inverse._inv_id)._name,
                                  (scope, ent))):
                ReferenceModel.get_or_create(
                    _kind=kind_id(kind),
                    _file=file_ent,
                    _line=ref_dict["line"],
                    _column=col_1based(ref_dict["col"]),
                    _ent=a,
                    _scope=b,
                )

    def addImplementOrImplementByRefs(self, ref_dicts, file_ent, file_address):
        pass

    def add_create_and_createby_reference(self, ref_dicts, file_address, file_ent):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(
                _kind=self.findKindWithKeywords(
                    ref_dict["scope_kind"], ref_dict["scope_modifiers"]
                ),
                _name=ref_dict["scope_name"],
                _parent=resolve_entity_ref(ref_dict["scope_parent"], file_ent),
                _longname=ref_dict["scope_longname"],
                _contents=ref_dict["scope_contents"],
            )[0]
            ent = self.getImplementEntity(
                ref_dict["type_ent_longname"], file_address, file_ent
            )
            implement_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Implement Couple"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _ent=ent,
                _scope=scope,
            )
            implementBy_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Implementby Coupleby"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _ent=scope,
                _scope=ent,
            )

    def add_references_extend_implicit_couple(
        self, importing_ent, imported_ent, cls_data
    ):
        ref, _ = ReferenceModel.get_or_create(
            _kind=KindModel.get_or_none(_name="Java Extend Couple Implicit")._id,
            _file_id=importing_ent._id,
            _line=cls_data.line,
            _column=col_1based(cls_data.column),
            _ent_id=imported_ent._id,
            _scope_id=importing_ent._id,
        )
        inverse_ref, _ = ReferenceModel.get_or_create(
            _kind=KindModel.get_or_none(_name="Java Extendby Coupleby Implicit")._id,
            _file_id=importing_ent._id,
            _line=cls_data.line,
            _column=col_1based(cls_data.column),
            _ent_id=importing_ent._id,
            _scope_id=imported_ent._id,
        )

    def addExtendCoupleOrExtendCoupleByRefs(self, ref_dicts, file_ent, file_address):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(
                _kind=self.findKindWithKeywords(
                    ref_dict["scope_kind"], ref_dict["scope_modifiers"]
                ),
                _name=ref_dict["scope_name"],
                _parent=resolve_entity_ref(ref_dict["scope_parent"], file_ent),
                _longname=ref_dict["scope_longname"],
                _contents=ref_dict["scope_contents"],
            )[0]
            ent = self.getImplementEntity(
                ref_dict["type_ent_longname"], file_address, file_ent
            )
            extend_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Extend Couple"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _ent=ent,
                _scope=scope,
            )
            extendBy_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Extendby Coupleby"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
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
                _parent=resolve_entity_ref(ref_dict["scope_parent"], file_ent),
                _longname=ref_dict["scope_longname"],
                _contents=ref_dict["scope_contents"],
            )[0]
            ent = self.getImplementEntity(
                ref_dict["type_ent_longname"], file_address, file_ent
            )
            call_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Call"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _ent=ent,
                _scope=scope,
            )
            callBy_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Callby"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _ent=scope,
                _scope=ent,
            )

    @staticmethod
    def add_modify_and_modifyby_reference(ref_dicts):
        for ref_dict in ref_dicts:
            longname = ref_dict["ent"]
            ent = ModifyListener.get_different_combinations(longname)
            scope = ref_dict["scope"]
            if ent is None:
                # This used to store the literal string "NOT FOUND" in _ent /
                # _scope, which SQLite accepts in an INTEGER column. A
                # reference whose endpoint cannot be resolved carries no
                # information, so drop it rather than write a corrupt row.
                continue
            _, _ = ReferenceModel.get_or_create(
                _kind=kind_id("Java Modify"),
                _file=ref_dict["file"],
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["column"]),
                _ent=ent,
                _scope=scope,
            )
            _, _ = ReferenceModel.get_or_create(
                _kind=kind_id("Java Modifyby"),
                _file=ref_dict["file"],
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["column"]),
                _ent=scope,
                _scope=ent,
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
                _parent=resolve_entity_ref(ref_dict["scope_parent"], file_ent),
                _longname=ref_dict["scope_longname"],
                _contents=ref_dict["scope_contents"],
            )[0]
            ent = self.getImplementEntity(
                ref_dict["type_ent_longname"], file_address, file_ent
            )
            call_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Call Nondynamic"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _ent=ent,
                _scope=scope,
            )
            callBy_ref = ReferenceModel.get_or_create(
                _kind=kind_id("Java Callby Nondynamic"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _ent=scope,
                _scope=ent,
            )

    def add_cast_by(self, ref_dicts_all, file_ent, file_address):
        for ref_dicts in ref_dicts_all:
            scope = EntityModel.get_or_create(
                _kind=self.findKindWithKeywords(
                    ref_dicts["p_kind"], ref_dicts["p_modifier"]
                ),
                _name=ref_dicts["p_name"],
                _parent=resolve_entity_ref(ref_dicts["p_parent"], file_ent),
                _longname=ref_dicts["p_longname"],
                _contents=ref_dicts["p_content"],
            )[0]
            ent = self.getImplementEntity(ref_dicts["longname"], file_address, file_ent)

            cast = ReferenceModel.get_or_create(
                _kind=kind_id("Java Use Cast"),
                _file=file_ent,
                _line=ref_dicts["line"],
                _column=col_1based(ref_dicts["col"]),
                _scope=scope,
                _ent=ent,
            )
            castby = ReferenceModel.get_or_create(
                _kind=kind_id("Java Useby Castby"),
                _file=file_ent,
                _line=ref_dicts["line"],
                _column=col_1based(ref_dicts["col"]),
                _scope=ent,
                _ent=scope,
            )

    def add_contain_in(self, ref_dicts, file_ent, file_address):
        for ref_dict in ref_dicts:
            scope = EntityModel.get_or_create(
                _kind=self.findKindWithKeywords(
                    ref_dict["kind"], ref_dict["modifiers"]
                ),
                _name=ref_dict["name"],
                _parent=resolve_entity_ref(ref_dict["parent"], file_ent),
                _longname=ref_dict["longname"],
                _contents=ref_dict["content"],
            )[0]
            ent = self.getImplementEntity(
                ref_dict["package_type"], file_address, file_ent
            )
            contain = ReferenceModel.get_or_create(
                _kind=kind_id("Java Contain"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _scope=ent,
                _ent=scope,
            )

            containin = ReferenceModel.get_or_create(
                _kind=kind_id("Java Containin"),
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _scope=scope,
                _ent=ent,
            )

    def get_parent(self, parent_file_path) -> EntityModel:
        return EntityModel.get_or_none(_longname=parent_file_path)

    def getNameEntity(self, prefixes) -> str:
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

        result_str = "Java{0}{1}{2} Class Type{3} Member".format(
            pattern_static, pattern_abstract, pattern_generic, pattern_visibility
        )
        return result_str

    def get_imported_entity(self, import_entity_listener):
        prefixes = ""
        kind = ""
        for branch in import_entity_listener.branches:
            if type(branch) == JavaParserLabeled.ClassDeclarationContext:
                kind = "Class"
                break
            elif type(branch) == JavaParserLabeled.InterfaceDeclarationContext:
                kind = "Interface"
                break
            elif type(branch) == JavaParserLabeled.EnumDeclarationContext:
                kind = "Enum Class"
                break
            prefixes += branch.getText() + " "
        return prefixes, import_entity_listener.body, kind

    def get_parent_import(self, parent_file_name, file):
        parent_entity, _ = EntityModel.get_or_create(
            _kind=kind_id("Java File"),
            _name=parent_file_name,
            _longname=file,
        )
        return parent_entity, file

    def get_kind_name(self, prefixes, kind):
        p_static = ""
        p_abstract = ""
        p_generic = ""
        p_type = "Type"
        p_visibility = "Default"
        p_member = "Member"

        if "static" in prefixes:
            p_static = "Static"

        if "generic" in prefixes:
            p_generic = "Generic"

        if "abstract" in prefixes:
            p_abstract = "Abstract"
        elif "final" in prefixes:
            p_abstract = "Final"

        if "private" in prefixes:
            p_visibility = "Private"
        elif "public" in prefixes:
            p_visibility = "Public"
        elif "protected" in prefixes:
            p_visibility = "Protected"

        if kind == "Interface":
            p_member = ""

        if kind == "Method":
            p_type = ""

        s = f"Java {p_static} {p_abstract} {p_generic} {kind} {p_type} {p_visibility} {p_member}"
        s = " ".join(s.split())
        return s

    def get_kind_name_opened(self, prefixes, kind):
        p_static = ""
        p_abstract = ""
        p_generic = ""
        p_type = "Type"
        p_visibility = "Default"
        p_member = "Member"

        if "static" in prefixes:
            p_static = "Static"

        if "generic" in prefixes:
            p_generic = "Generic"

        if "abstract" in prefixes:
            p_abstract = "Abstract"
        elif "final" in prefixes:
            p_abstract = "Final"

        if "private" in prefixes:
            p_visibility = "Private"
        elif "public" in prefixes:
            p_visibility = "Public"
        elif "protected" in prefixes:
            p_visibility = "Protected"

        if kind == "Interface":
            p_member = ""
            p_static = ""

        if kind == "Method":
            p_type = ""

        s = f"Java {p_static} {p_abstract} {p_generic} {kind} {p_type} {p_visibility} {p_member}"
        s = " ".join(s.split())
        return s

    def add_opened_entity(self, entity):
        entity_kind = self.get_kind_name_opened(entity["longname"], entity["kind"])
        imported_entity, _ = EntityModel.get_or_create(
            _kind=KindModel.get_or_none(_name=entity_kind).get_id(),
            # _parent=parent_entity.get_id(),
            _parent=None,
            _name=entity["name"],
            _longname=entity["longname"],
            _contents=entity["body"],
        )
        return imported_entity

    def add_references_opend(self, importing_ent, imported_ent, ref_dict):
        ref, _ = ReferenceModel.get_or_create(
            _kind=kind_id("Java Open"),
            _file=importing_ent.get_id(),
            _line=ref_dict["line"],
            _column=col_1based(ref_dict["column"]),
            _ent=imported_ent.get_id(),
            _scope=importing_ent.get_id(),
        )
        inverse_ref, _ = ReferenceModel.get_or_create(
            _kind=kind_id("Java Openby"),
            _file=importing_ent.get_id(),
            _line=ref_dict["line"],
            _column=col_1based(ref_dict["column"]),
            _ent=importing_ent.get_id(),
            _scope=imported_ent.get_id(),
        )

    def add_references_import(self, importing_ent, imported_ent, ref_dict):
        ref, _ = ReferenceModel.get_or_create(
            _kind=kind_id("Java Import"),
            _file=importing_ent.get_id(),
            _line=ref_dict["line"],
            _column=col_1based(ref_dict["column"]),
            _ent=imported_ent.get_id(),
            _scope=importing_ent.get_id(),
        )
        inverse_ref, _ = ReferenceModel.get_or_create(
            _kind=kind_id("Java Importby"),
            _file=importing_ent.get_id(),
            _line=ref_dict["line"],
            _column=col_1based(ref_dict["column"]),
            _ent=importing_ent.get_id(),
            _scope=imported_ent.get_id(),
        )

    def add_imported_entity(self, i, files, import_entity_listener):
        if i["is_built_in"]:
            imported_entity, _ = EntityModel.get_or_create(
                _kind=kind_id("Java Unknown Class Type Member"),
                _parent=None,
                _name=i["imported_class_name"],
                _longname=i["imported_class_longname"],
            )
        else:
            parent_entity, parent_file_path = self.get_parent_import(
                i["imported_class_file_name"], files
            )
            imported_entity, _ = EntityModel.get_or_create(
                # "Java Import" is a REFERENCE kind; it was being stored as this
                # entity's kind. The entity is a type pulled in from elsewhere,
                # so the unknown-class placeholder is the honest label -- and
                # it now upgrades itself if a pass later identifies the type.
                _kind=kind_id("Java Unknown Class Type Member"),
                _parent=parent_entity.get_id(),
                _name=i["imported_class_name"],
                _longname=i["imported_class_longname"],
                _contents="",
            )
        return imported_entity

    def add_import_demand(self, ents, file_path):
        for i in ents:
            ent, _ = EntityModel.get_or_create(
                _kind=kind_id("Java File"),
                _parent="None",
                _name=i["name"],
                _longname=i["longname"],
                _contents=FileStream(file_path, encoding="utf-8"),
            )

            ReferenceModel.get_or_create(
                _kind=kind_id("Java Import Demand"),
                _file=file_path,
                _line=i["line"],
                _column=col_1based(i["col"]),
                _ent=ent.get_id(),
                _scope=file_path,
            )

    def add_references(self, importing_ent, imported_ent, cls_data: ClassTypeData):
        ref, _ = ReferenceModel.get_or_create(
            _kind=KindModel.get_or_none(_name="Java Extend Couple Implicit")._id,
            _file_id=importing_ent._id,
            _line=cls_data.line,
            _column=col_1based(cls_data.column),
            _ent_id=imported_ent._id,
            _scope_id=importing_ent._id,
        )
        inverse_ref, _ = ReferenceModel.get_or_create(
            _kind=KindModel.get_or_none(_name="Java Extendby Coupleby Implicit")._id,
            _file_id=importing_ent._id,
            _line=cls_data.line,
            _column=col_1based(cls_data.column),
            _ent_id=importing_ent._id,
            _scope_id=imported_ent._id,
        )

    def add_imported_entity_factory(self, cls_data: ClassTypeData):
        parent_entity: EntityModel = self.get_parent(cls_data.file_path)
        kindModel = KindModel.get_or_none(
            _name=self.getNameEntity(cls_data.get_prefixes())
        )
        extend_implicit_entity = None
        if kindModel is not None:
            extend_implicit_entity, _ = EntityModel.get_or_create(
                _kind=kindModel._id,
                _parent=parent_entity._id,
                _name=cls_data.get_name(),
                _type=cls_data.get_type(),
                _longname=cls_data.get_long_name(),
                _contents=cls_data.get_contents(),
            )
        entity_kind_object = kind_id("Java Unknown Class Type Member")
        java_lang_entity, _ = EntityModel.get_or_create(
            _kind=entity_kind_object,
            _parent=None,
            _name="Object",
            _type=None,
            _longname=cls_data.parentClass,
            _contents="",
        )
        return extend_implicit_entity, java_lang_entity

    def addCreateRefs(self, ref_dicts, file_ent, file_address):

        for ref_dict in ref_dicts:
            try:
                scope = EntityModel.get_or_create(
                    _kind=self.findKindWithKeywords(
                        "Method", ref_dict["scopemodifiers"]
                    ),
                    _name=ref_dict["scopename"],
                    _type=ref_dict["scopereturntype"],
                    _parent=resolve_entity_ref(ref_dict["scope_parent"], file_ent),
                    _longname=ref_dict["scopelongname"],
                    # A missing subscript: this stored the literal list
                    # ["scopecontent"], so every entity this pass created first
                    # carried the string "['scopecontent']" as its source, and
                    # every metric that reparses contents returned 0.
                    _contents=ref_dict["scopecontent"],
                )[0]

                ent = self.getCreatedClassEntity(
                    ref_dict["refent"],
                    ref_dict["potential_refent"],
                    file_address,
                    file_ent,
                )

                Create = ReferenceModel.get_or_create(
                    _kind=kind_id("Java Create"),
                    _file=file_ent,
                    _line=ref_dict["line"],
                    _column=col_1based(ref_dict["col"]),
                    _scope=scope,
                    _ent=ent,
                )

                Createby = ReferenceModel.get_or_create(
                    _kind=kind_id("Java Createby"),
                    _file=file_ent,
                    _line=ref_dict["line"],
                    _column=col_1based(ref_dict["col"]),
                    _scope=ent,
                    _ent=scope,
                )
            except Exception as e:
                print("ERROR in project.py function addCreateRefs ")
                print("error message : ", e)

    def getPackageEntity(self, file_ent, name, longname):
        # A package is not declared *in* a file -- it spans every file that
        # names it, so parenting it to whichever file got there first made the
        # parent chain of every type in the package point at the wrong file.
        ent, _ = EntityModel.get_or_create(
            _kind=kind_id("Java Package"), _name=name, _parent=None,
            _longname=longname, _contents="",
        )
        return ent

    def getScopeEntity(self, file_ent, name, longname):
        """The enclosing entity of a declaration.

        Walk order is pre-order, so a class is defined before its methods and a
        method before its locals -- the scope almost always already exists with
        its real kind. When it does not, an Unknown kind is used, which
        EntityModel.get_or_create treats as a placeholder and upgrades in place.
        """
        existing = EntityModel.get_or_none(EntityModel._longname == longname)
        if existing is not None:
            return existing
        ent, _ = EntityModel.get_or_create(
            _kind=kind_id("Java Unknown Class Type Member"),
            _name=name,
            _parent=file_ent,
            _longname=longname,
            _contents="",
        )
        return ent

    def getUnnamedPackageEntity(self, file_ent):
        # unnamed package kind id: 73
        ent = EntityModel.get_or_create(
            _kind=kind_id("Java Package Unnamed"),
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
        self, class_longname, class_potential_longname, file_address, file_ent
    ):
        props = self.getClassProperties(class_potential_longname, file_address)
        if not props:
            return self.getClassEntity(class_longname, file_address, file_ent)
        else:
            return self.getClassEntity(class_potential_longname, file_address, file_ent)

    def getClassEntity(self, class_longname, file_address, file_ent):
        props = self.getClassProperties(class_longname, file_address)
        if not props:  # This class is unknown, unknown class id: 84
            ent = EntityModel.get_or_create(
                _kind=kind_id("Java Unknown Class Type Member"),
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
                _parent=resolve_entity_ref(props["parent"], file_ent),
                _contents=props["contents"],
            )
        return ent[0]

    def getInterfaceEntity(
        self, interface_longname, file_address, file_ent
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
                _parent=resolve_entity_ref(props["parent"], file_ent),
                _contents=props["contents"],
            )
        return ent[0]

    def getImplementEntity(self, longname, file_address, file_ent):
        ent = self.getInterfaceEntity(longname, file_address, file_ent)
        if not ent:
            ent = self.getClassEntity(longname, file_address, file_ent)
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
        try:
            for tuples in extendedfiles:
                try:
                    main = tuples[0]
                    fromx = tuples[1]
                    methodsmain = classes[main]
                except Exception as e:
                    print("ERROR 0 in addoverridereference : ", e)
                for x in methodsmain:
                    try:
                        file = x["File"]
                        kindx = self.findKindWithKeywords(
                            x["scope_kind"], x["scope_modifiers"]
                        )
                        if kindx is None:
                            kindx = x["modifiersx"]
                        scope = EntityModel.get_or_create(
                            _kind=kindx,
                            _name=x["scope_name"],
                            _parent=resolve_entity_ref(x["scope_parent"], file_ent),
                            _longname=x["scope_longname"],
                            _contents=x["scope_contents"],
                            _type=x["Methodkind"],
                        )
                        methodname1 = x["MethodIs"]
                    except Exception as e:
                        print("ERROR 1 in addoverridereference : ", e)
                    if fromx in classes:
                        try:
                            mathodsfrom = classes[fromx]
                        except Exception as e:
                            print("ERROR 2 in addoverridereference : ", e)
                        for y in mathodsfrom:
                            try:
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
                                        _parent=resolve_entity_ref(y["scope_parent"], fe),
                                        _longname=y["scope_longname"],
                                        _contents=y["scope_contents"],
                                        _type=y["Methodkind"],
                                    )

                                    override_ref = ReferenceModel.get_or_create(
                                        _kind=kind_id("Java Overrides"),
                                        _file=file_ent,
                                        _line=x["line"],
                                        _column=col_1based(x["col"]),
                                        _ent=ent[0],
                                        _scope=scope[0],
                                    )
                                    overrideBy_ref = ReferenceModel.get_or_create(
                                        _kind=kind_id("Java Overriddenby"),
                                        _file=fe,
                                        _line=y["line"],
                                        _column=col_1based(y["col"]),
                                        _ent=scope[0],
                                        _scope=ent[0],
                                    )
                            except Exception as e:
                                print("ERROR 3 in addoverridereference : ", e)
                    elif x["is_overrided"]:
                        overrideword = list(x.values())
                        classes = [
                            list(i[0].values())[0]
                            for i in [item for item in list(classes.values())]
                        ]
                        if overrideword[0] not in classes:

                            ent = EntityModel.get_or_create(
                                _kind=kind_id("Java Unknown Method Member"),
                                _name=overrideword[1],
                                _parent=file_ent,
                                _longname=overrideword,
                                _contents="",
                            )
                            override_ref = ReferenceModel.get_or_create(
                                _kind=kind_id("Java Overrides"),
                                _file=file_ent,
                                _line=x["line"],
                                _column=col_1based(x["col"]),
                                _ent=ent[0],
                                _scope=scope[0],
                            )
        except Exception as e:
            print("ERROR 6 in addoverridereference : ", e)

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
            _column=col_1based(package_name["column"]),
            _ent_id=file_entity._id,
            _scope_id=created_entity._id,
        )
        ReferenceModel.get_or_create(
            _kind_id=KindModel.get_or_none(_name="Java Definein")._id,
            _file_id=file_entity._id,
            _line=package_name["line"],
            _column=col_1based(package_name["column"]),
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

    def add_use_module_reference(
        self,
        use_module: list = None,
        unknown_module: list = None,
        unresolved_module: list = None,
        file_address: str = "",
    ) -> None:
        file_entity = self.get_parent_entity(file_address)
        use_kind = KindModel.get_or_none(_name="Java ModuleUse")._id
        useby_kind = KindModel.get_or_none(_name="Java ModuleUseby")._id

        # "Java Unknown Module" and "Java Unresolved Module" are ENTITY kinds.
        # They used to be written into ReferenceModel._kind, labelling the
        # reference with an entity kind. The resolution state describes the
        # module, so it belongs on the entity; the reference is a module use
        # either way.
        for items, entity_kind_name in (
            (unknown_module or [], "Java Unknown Module"),
            (unresolved_module or [], "Java Unresolved Module"),
            (use_module or [], "Java Module"),
        ):
            entity_kind = KindModel.get_or_none(_name=entity_kind_name)
            if entity_kind is None:
                continue
            for item in items:
                created_entity, _ = EntityModel.get_or_create(
                    _kind_id=entity_kind._id,
                    _parent_id=file_entity._id,
                    _name=item["name"].split(".")[-1],
                    _longname=item["package"],
                    _contents="",
                )
                # item["ent"] / item["scope"] arrive as name strings; writing
                # them straight into the integer foreign keys stored text in
                # _ent_id and _scope_id. The referenced module is the entity we
                # just created, and the using scope defaults to the file.
                scope_entity = resolve_entity_ref(item.get("scope"), file_entity)
                ReferenceModel.get_or_create(
                    _kind_id=use_kind,
                    _file_id=file_entity._id,
                    _line=item["line"],
                    _column=col_1based(item["col"]),
                    _ent_id=created_entity._id,
                    _scope_id=scope_entity._id,
                )
                ReferenceModel.get_or_create(
                    _kind_id=useby_kind,
                    _file_id=file_entity._id,
                    _line=item["line"],
                    _column=col_1based(item["col"]),
                    _ent_id=scope_entity._id,
                    _scope_id=created_entity._id,
                )

    def check_and_create_record(self, name, kind):
        existing_record = EntityModel.select().where(EntityModel._name == name).first()
        return not (existing_record and existing_record._kind == kind)

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
            # Not `kind_id` -- that name is the module-level lookup helper.
            resolved_kind = kind_name._id if kind_name else kind_id("Java File")

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
            model_parent = self.define_parent(
                entity_type, entity_values, file_path, package_name
            )

            created_entity, _ = EntityModel.get_or_create(
                _kind_id=resolved_kind,
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
                _column=col_1based(reference_column),
                _ent_id=model_parent._id,
                _scope_id=created_entity._id,
            )
            ReferenceModel.get_or_create(
                _kind_id=KindModel.get_or_none(_name="Java Definein")._id,
                _file_id=reference_file._id,
                _line=reference_line,
                _column=col_1based(reference_column),
                _ent_id=created_entity._id,
                _scope_id=model_parent._id,
            )

    def getThrowEntity(self, longname, file_address, file_ent):
        ent = self.getInterfaceEntity(longname, file_address, file_ent)
        if not ent:
            ent = self.getClassEntity(longname, file_address, file_ent)
        return ent

    def addThrows_TrowsByRefs(self, ref_dicts, file_ent, file_address, id1, id2, Throw):
        for ref_dict in ref_dicts:

            # Prefer the entity the define pass already declared. Guessing a
            # Method kind here created a second row for names that are really
            # classes -- an `org.json.CDL` in the method family alongside the
            # real one in the type family, which do not merge by design.
            scope = EntityModel.get_or_none(
                EntityModel._longname == ref_dict["scopelongname"]
            )
            if scope is None:
                scope = EntityModel.get_or_create(
                    _kind=self.findKindWithKeywords(
                        "Method", ref_dict["scopemodifiers"]
                    ),
                    _name=ref_dict["scopename"],
                    _parent=resolve_entity_ref(ref_dict["scope_parent"], file_ent),
                    _longname=ref_dict["scopelongname"],
                    _contents=ref_dict["scopecontent"],
                )[0]

            if not Throw:
                if ref_dict["refent"] is None:
                    ent = self.getUnnamedPackageEntity(file_ent)
                else:
                    ent = self.getScopeEntity(
                        file_ent, ref_dict["refent"], ref_dict["refent"]
                    )
            else:
                ent = self.getThrowEntity(ref_dict["refent"], file_address, file_ent)

            implement_ref = ReferenceModel.get_or_create(
                _kind=id1,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _ent=ent,
                _scope=scope,
            )
            implementBy_ref = ReferenceModel.get_or_create(
                _kind=id2,
                _file=file_ent,
                _line=ref_dict["line"],
                _column=col_1based(ref_dict["col"]),
                _ent=scope,
                _scope=ent,
            )

    def add_couple_and_couple_by_refs(self, classes, couples):
        keykind = ''
        for c in couples:
            file_ent = self.getFileEntity(c['File'])
            scope = EntityModel.get_or_create(_kind=self.findKindWithKeywords(c["scope_kind"], c["scope_modifiers"]),
                                              _name=c["scope_name"],
                                              _parent=resolve_entity_ref(c["scope_parent"], file_ent),
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
                                _parent=resolve_entity_ref(c1["scope_parent"], file_ent2),
                                _longname=c1["scope_longname"],
                                _contents=c1["scope_contents"])
                            CoupleBy_ref = ReferenceModel.get_or_create(_kind=kind_id("Java Coupleby"), _file=file_ent2, _line=c["line"],
                                                                        _column=col_1based(c["col"]), _ent=scope[0], _scope=ent[0])

                        else:
                            kw = key.split('.')
                            # 84 = Java Unknown Class Type Member. This was the
                            # string "Unknown Class", written into an integer
                            # foreign-key column.
                            keykind = kind_id("Java Unknown Class Type Member")
                            ent = EntityModel.get_or_create(_kind=keykind, _name=kw[-1],
                                                            _parent=file_ent,
                                                            _longname=key,
                                                            )
                        Couple_ref = ReferenceModel.get_or_create(_kind=kind_id("Java Couple"), _file=file_ent, _line=c["line"],
                                                                  _column=col_1based(c["col"]), _ent=ent[0], _scope=scope[0])

    # for c in couples:
        #     ent = self.getImplementEntity(
        #         c["type_ent_longname"], file_address, file_ent
        #     )
        #     scope = EntityModel.get_or_create(
        #         _kind=self.findKindWithKeywords(c["scope_kind"], c["scope_modifiers"]),
        #         _name=c["scope_name"],
        #         _parent=(
        #             c["scope_parent"] if c["scope_parent"] is not None else file_ent
        #         ),
        #         _longname=c["scope_longname"],
        #         _contents=c["scope_contents"],
        #     )[0]
        #     Couple_ref = ReferenceModel.get_or_create(
        #         _kind=kind_id("Java Couple"),
        #         _file=file_ent,
        #         _line=c["line"],
        #         _column=col_1based(c["col"]),
        #         _ent=ent,
        #         _scope=scope,
        #     )
        #     CoupleBy_ref = ReferenceModel.get_or_create(
        #         _kind=kind_id("Java Coupleby"),
        #         _file=file_ent,
        #         _line=c["line"],
        #         _column=col_1based(c["col"]),
        #         _ent=scope,
        #         _scope=ent,
        #     )

    def addcouplereference(self, classes, couples, file_ent):
        keykind = ""
        for c in couples:
            try:
                scope = EntityModel.get_or_create(
                    _kind=self.findKindWithKeywords(
                        c["scope_kind"], c["scope_modifiers"]
                    ),
                    _name=c["scope_name"],
                    _parent=resolve_entity_ref(c["scope_parent"], file_ent),
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
                                    _parent=resolve_entity_ref(c1["scope_parent"], file_ent2),
                                    _longname=c1["scope_longname"],
                                    _contents=c1["scope_contents"],
                                )
                            else:
                                kw = key.split(".")
                                ent = EntityModel.get_or_create(
                                    _kind=kind_id("Java Unknown Class Type Member"),
                                    _name=kw[-1],
                                    _parent=file_ent,
                                    _longname=key,
                                )
                            Couple_ref = ReferenceModel.get_or_create(
                                _kind=kind_id("Java Couple"),
                                _file=file_ent,
                                _line=c["line"],
                                _column=col_1based(c["col"]),
                                _ent=ent[0],
                                _scope=scope[0],
                            )
                            # The inverse used to live inside the `key in
                            # classes` branch, so a couple to a class this file
                            # had not catalogued produced a forward reference
                            # with no inverse: 364 Couple rows against 3.
                            CoupleBy_ref = ReferenceModel.get_or_create(
                                _kind=kind_id("Java Coupleby"),
                                _file=file_ent,
                                _line=c["line"],
                                _column=col_1based(c["col"]),
                                _ent=scope[0],
                                _scope=ent[0],
                            )

            except Exception as e:
                print(e)

