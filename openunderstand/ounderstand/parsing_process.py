from openunderstand.ounderstand.project import Project
from openunderstand.ounderstand.listeners_and_parsers import ListenersAndParsers
import os
from openunderstand.utils.utilities import setup_config
from fnmatch import fnmatch


def get_files(dirName: str = ""):
    listOfFile = os.listdir(dirName)
    allFiles = list()
    for entry in listOfFile:
        # Create full path
        fullPath = os.path.join(dirName, entry)
        if os.path.isdir(fullPath):
            allFiles = allFiles + get_files(fullPath)
        # checks whether the fullPath content is a .java or not
        elif fnmatch(fullPath, "*.java"):
            allFiles.append(fullPath)
    return allFiles


def process_file(file_address):
    p = Project()
    lap = ListenersAndParsers()
    tree, parse_tree, file_ent = lap.parser(file_address=file_address, p=p)
    if tree is None and parse_tree is None and file_ent is None:
        return
    entity_generator = lap.entity_gen(file_address=file_address, parse_tree=parse_tree)
    listeners = [
        lap.type_listener,
        lap.define_listener,
        # After define_listener, not before it. `new` in a field initializer
        # has no enclosing method, so this pass's scope is the class -- and
        # running first, it created that scope itself with a Method kind. The
        # result was a second `org.json.JSONObject` in the method family which
        # then captured all 110 of the class's Define references, leaving the
        # real class entity with none.
        lap.create_listener,
        lap.use_variant_listener,
        lap.method_call_listener,
        lap.declare_listener,
        lap.override_listener,
        # callby_listener is gone: method_call_listener records the same
        # references from an enterMethodCall0 callback, which sees every call
        # site rather than only whole expression statements, and scopes each to
        # the method containing it. call_callby.py walked the tree itself from
        # enterClassDeclaration and passed the *class* context to findParents,
        # so every reference it produced was scoped to the package. Measured on
        # JSON: dropping it left the 394 correct Call references untouched and
        # removed 43 wrong ones and 15 placeholder entities, taking Call
        # precision from 48.9% to 51.7% and Call Nondynamic from 92.3% to 97.3%.
        lap.static_import_listener,
        lap.overrides_listener,
        lap.couple_listener,
        lap.useby_listener,
        lap.setby_listener,
        lap.setinitby_listener,
        lap.setbypartialby_listener,
        lap.dotref_listener,
        lap.throws_listener,
        lap.extend_coupled_listener,
        lap.variable_listener,
        lap.callbyNonDynamic_listener,
        lap.cast_by_listener,
        lap.contain_in_listener,
        lap.extend_implict_listener,
        lap.import_demand_listener,
        # import_listener, open_by_listener and use_module_listener are gone.
        # Understand reports no Java Import, Java Open or Java ModuleUse for
        # Java on either benchmark -- an import is not a reference it records,
        # and Open/ModuleUse belong to languages with modules. All three wrote
        # references scoped to a *file path* rather than an entity, so none
        # could ever match: 288 Open, 241 Import and 60 ModuleUse rows of pure
        # noise on TheAlgorithms, and 112 on JSON.
    ]
    for listener in listeners:
        listener(file_address=file_address, p=p, file_ent=file_ent, tree=tree)
    # Runs last, not first: add_modify_and_modifyby_reference() resolves the
    # modified variable by longname and drops the reference when it finds
    # nothing. Before define_listener/declare_listener have declared the
    # locals, that lookup misses and every += site is silently discarded.
    lap.modify_listener(
        entity_generator=entity_generator,
        parse_tree=parse_tree,
        file_address=file_address,
        p=p,
    )
