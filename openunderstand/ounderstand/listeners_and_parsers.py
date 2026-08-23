from openunderstand.analysis_passes.throws_throwsby import Throws_TrowsBy
from openunderstand.analysis_passes.dotref_dotrefby import DotRef_DotRefBy
from openunderstand.analysis_passes.callnondynamic_callnondynamicby import (
    CallNonDynamicAndCallNonDynamicBy,
)

from openunderstand.analysis_passes.cast_castby import CastAndCastBy
from openunderstand.analysis_passes.contain_containby import ContainAndContainBy
from openunderstand.analysis_passes.extends_implicit_couple_coupleby import (
    PackageImportListener,
    DSCmetric,
)
from openunderstand.analysis_passes.import_importby import (
    ImportListener,
    ImportedEntityListener,
)
from openunderstand.analysis_passes.import_demand import ImportListenerDemand

from openunderstand.analysis_passes.define_definein import DefineListener
from openunderstand.analysis_passes.use_variants import UseVariantListener
from openunderstand.analysis_passes.method_calls import MethodCallListener
from openunderstand.analysis_passes.overrides import OverridesListener
from openunderstand.analysis_passes.static_imports import StaticImportListener
from openunderstand.analysis_passes.lambdas import LambdaListener
from openunderstand.analysis_passes.field_uses import FieldUseListener

from openunderstand.analysis_passes.modify_modifyby import ModifyListener
from openunderstand.analysis_passes.entity_manager import (
    EntityGenerator,
    FileEntityManager,
    get_created_entity,
)

from openunderstand.analysis_passes.use_useby import UseAndUseByListener
from openunderstand.analysis_passes.type_typedby import TypedAndTypedByListener
from openunderstand.analysis_passes.set_setby import SetAndSetByListener
from openunderstand.analysis_passes.setinit_setinitby import SetInitAndSetByInitListener
from openunderstand.analysis_passes.setpartial_setpartialby import (
    SetPartialAndSetByPartialListener,
)
from openunderstand.ounderstand.override_overrideby import overridelistener
from openunderstand.analysis_passes.couple_coupleby import CoupleAndCoupleBy
from openunderstand.analysis_passes.create_createby import CreateAndCreateBy
from openunderstand.analysis_passes.declare_declarein import DeclareAndDeclareinListener
from openunderstand.analysis_passes.extend_listener import ExtendListener
from openunderstand.analysis_passes.extendcouple_extendcoupleby import (
    ExtendCoupleAndExtendCoupleBy,
)
from openunderstand.analysis_passes.variable_listener import VariableListener
from openunderstand.analysis_passes.open_openby import OpenListener
from openunderstand.analysis_passes.usemodule_usemoduleby import (
    UseModuleUseModuleByListener,
)
from openunderstand.utils.utilities import setup_logger, timer_decorator
import os
from pathlib import Path
import traceback

from openunderstand.oudb.models import kind_id


class ListenersAndParsers:
    """The glue between a pass's listener and the write layer.

    Each pass used to build a listener, walk the tree with it and write its
    result in one breath. That is why the tree is walked 33 times per file and
    why collection cannot move to a worker process: build and write are welded
    together. `_stage()` separates them without changing anything by default.
    """

    #: None runs build and write in one breath, exactly as before the split.
    #: "build" constructs and walks, storing the listener; "write" replays it.
    BOTH, BUILD, WRITE = None, "build", "write"

    def __init__(self, phase=None):
        self.logger = setup_logger()
        self.phase = phase
        #: Pass name -> the listener built for the file being processed.
        self._built = {}
        #: Listeners built in this phase that have not been walked yet.
        self._pending_walk = []
        #: What a worker read off the tree so a writer does not need one.
        self.tree_facts = {}

    #: Attributes a listener keeps only while walking. They hold parse-tree
    #: nodes, which cannot cross a process boundary, and no write reads them:
    #: contain_in writes `contain`, setby writes `setBy`, and `_binder` is a
    #: resolved-type cache.
    _SCRATCH = ("_binder", "ent_value", "packageInfo")

    def transfer_state(self):
        """What a worker sends back: each listener's class and its result.

        Pickle reconstructs the real class, so a write reading a property --
        `listener.get_type`, `listener.get_couples` -- still works.
        """
        payload = {}
        for name, listener in self._built.items():
            state = {k: v for k, v in vars(listener).items() if k not in self._SCRATCH}
            handler = state.get("dbHandler")
            if handler is not None:
                # The one result that holds parse-tree contexts.
                for item in getattr(handler, "classTypes", ()):
                    item.freeze()
            payload[name] = (type(listener), state)
        return payload

    def restore(self, payload, tree_facts=None):
        """Rebuild what a worker collected, without running any __init__."""
        self._built = {}
        for name, (cls, state) in payload.items():
            listener = cls.__new__(cls)
            listener.__dict__.update(state)
            self._built[name] = listener
        self.tree_facts = tree_facts or {}

    def walk_built(self, tree, p):
        """Walk the tree once for every listener built in this phase."""
        pending, self._pending_walk = self._pending_walk, []
        if not pending:
            return
        names = {id(listener): name for name, listener in self._built.items()}

        def on_error(listener, error):
            self.logger.error(
                "An Error occurred during the shared walk in %s:\n%s",
                names.get(id(listener), type(listener).__name__),
                error,
            )

        p.WalkAll(pending, tree, on_error)

    def _stage(self, name, build, tree, p, walk=True):
        """The listener whose result this pass should write, or None.

        None means "not in this phase": in BUILD the listener is constructed
        and walked and the write is skipped, and the caller returns early.

        `walk=False` is for a pass that walks more than once and has to do it
        itself -- extend_implict reads a package name with one listener before
        it can construct the second.
        """
        if self.phase == self.WRITE:
            return self._built.get(name)
        listener = build()
        if self.phase is self.BOTH:
            if walk:
                p.Walk(listener, tree)
            return listener
        self._built[name] = listener
        if walk:
            # Not walked here: every pass in this phase shares one walk, which
            # `walk_built()` performs once they are all built.
            self._pending_walk.append(listener)
        return None

    @timer_decorator()
    def parser(self, file_address, p):
        try:
            parse_tree = p.Parse(file_address)
            file_ent = p.getFileEntity(
                path=file_address, name=os.path.basename(file_address)
            )
            tree = parse_tree
            self.logger.info("file parse success")
            return tree, parse_tree, file_ent
        except Exception as e:
            self.logger.error(
                "An Error occurred in file file parse:" + file_address + "\n" + str(e)
            )
            return None, None, None

    @timer_decorator()
    def entity_gen(self, file_address, parse_tree):
        return EntityGenerator(
            file_address,
            parse_tree,
            declared_types=self.tree_facts.get("declared_types"),
            package_data=self.tree_facts.get("package_data"),
        )

    @timer_decorator()
    def variable_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = VariableListener()
                return listener

            listener = self._stage("variable_listener", _build, tree, p)
            if listener is None:
                return
            generator = self.entity_gen(file_address=file_address, parse_tree=tree)
            for item in listener.var:
                generator.get_or_create_variable_entity(res_dict=item)
            for item in listener.var_const:
                generator.get_or_create_variable_entity(res_dict=item)
            self.logger.info("variable refs success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in file variable refs :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def extend_coupled_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = ExtendCoupleAndExtendCoupleBy()
                return listener

            listener = self._stage("extend_coupled_listener", _build, tree, p)
            if listener is None:
                return
            p.addTypeRelationRefs(listener.relations, file_ent)
            self.logger.info("extends coupled refs success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in file extends coupled refs :"
                + file_address
                + "\n"
                + str(e)
            )

    @timer_decorator()
    def extend_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = ExtendListener()
                return listener

            listener = self._stage("extend_listener", _build, tree, p)
            if listener is None:
                return
            p.addTypeRefs(listener.get_refers, file_ent)
            self.logger.info("extends refs success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in file extends refs :"
                + file_address
                + "\n"
                + str(e)
            )

    @timer_decorator()
    def type_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = TypedAndTypedByListener()
                return listener

            listener = self._stage("type_listener", _build, tree, p)
            if listener is None:
                return
            p.addTypeRefs(listener.get_type, file_ent)
            self.logger.info("type refs success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in file type refs :" + file_address + "\n" + str(e)
            )

    @timer_decorator()
    def create_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = CreateAndCreateBy()
                listener.file_address = file_address
                return listener

            listener = self._stage("create_listener", _build, tree, p)
            if listener is None:
                return
            p.addCreateRefs(listener.create, file_ent, file_address)
            self.logger.info("create refs success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in file create refs :" + file_address + "\n" + str(e)
            )

    @timer_decorator()
    def field_use_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = FieldUseListener(file_address)
                return listener

            listener = self._stage("field_use_listener", _build, tree, p)
            if listener is None:
                return
            p.addTypeRelationRefs(listener.relations, file_ent)
            self.logger.info("field uses success")
        except Exception as e:
            self.logger.error(
                "An Error occurred in field uses in file :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def lambda_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = LambdaListener(file_address)
                return listener

            listener = self._stage("lambda_listener", _build, tree, p)
            if listener is None:
                return
            p.addTypeRelationRefs(listener.relations, file_ent)
            self.logger.info("lambdas success")
        except Exception as e:
            self.logger.error(
                "An Error occurred in lambdas in file :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def static_import_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = StaticImportListener(file_address)
                return listener

            listener = self._stage("static_import_listener", _build, tree, p)
            if listener is None:
                return
            p.addTypeRelationRefs(listener.relations, file_ent)
            self.logger.info("static imports success")
        except Exception as e:
            self.logger.error(
                "An Error occurred in static imports in file :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def overrides_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = OverridesListener()
                return listener

            listener = self._stage("overrides_listener", _build, tree, p)
            if listener is None:
                return
            p.addTypeRelationRefs(listener.relations, file_ent)
            self.logger.info("overrides success")
        except Exception as e:
            self.logger.error(
                "An Error occurred in overrides in file :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def method_call_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = MethodCallListener(file_address)
                return listener

            listener = self._stage("method_call_listener", _build, tree, p)
            if listener is None:
                return
            p.addMethodCallRefs(listener.calls, file_ent)
            self.logger.info("method calls success")
        except Exception as e:
            self.logger.error(
                "An Error occurred in method calls in file :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def use_variant_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = UseVariantListener(file_address)
                return listener

            listener = self._stage("use_variant_listener", _build, tree, p)
            if listener is None:
                return
            p.addUseVariantRefs(listener.uses, file_ent)
            self.logger.info("use variants success")
        except Exception as e:
            self.logger.error(
                "An Error occurred in use variants in file :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def define_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = DefineListener(file_address)
                return listener

            listener = self._stage("define_listener", _build, tree, p)
            if listener is None:
                return
            p.addDefineRefs(listener.defines, file_ent)
            self.logger.info("define success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred for reference implement in file define:"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def declare_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                # declare
                listener = DeclareAndDeclareinListener()
                return listener

            listener = self._stage("declare_listener", _build, tree, p)
            if listener is None:
                return
            p.addDeclareRefs(listener.declare, file_ent)
            self.logger.info("declare success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred for reference declare in file:"
                + file_address
                + "\n"
                + str(e)
            )

    @timer_decorator()
    def modify_listener(self, parse_tree, entity_generator, file_address, p):
        try:

            def _build():
                listener = ModifyListener(entity_generator)
                return listener

            listener = self._stage("modify_listener", _build, parse_tree, p)
            if listener is None:
                return
            p.add_modify_and_modifyby_reference(listener.modify)
            self.logger.info("modify success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred for reference modify in file:"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def override_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = overridelistener()
                return listener

            listener = self._stage("override_listener", _build, tree, p)
            if listener is None:
                return
            classesx = listener.get_classes
            extendedlist = listener.get_extendeds
            p.addoverridereference(classesx, extendedlist, file_ent)
            self.logger.info("overrides success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in override reference in file :"
                + file_address
                + "\n"
                + str(e)
            )

    @timer_decorator()
    def couple_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                couple = []
                classescoupleby = {}
                listener = CoupleAndCoupleBy()
                listener.set_file(filex=file_address)
                listener.set_classesx(classesx=classescoupleby)
                listener.set_couples(couples=couple)
                return listener

            listener = self._stage("couple_listener", _build, tree, p)
            if listener is None:
                return
            classescoupleby = listener.get_classes
            couple = listener.get_couples
            p.addcouplereference(classescoupleby, couple, file_ent)
            p.addTypeRelationRefs(listener.relations, file_ent)
            self.logger.info("couple success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in couple reference in file :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def throws_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                # Throws
                listener = Throws_TrowsBy()
                return listener

            listener = self._stage("throws_listener", _build, tree, p)
            if listener is None:
                return
            p.addTypeRelationRefs(listener.relations, file_ent)
            self.logger.info("Throws success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in throws in file :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def dotref_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = DotRef_DotRefBy()
                return listener

            listener = self._stage("dotref_listener", _build, tree, p)
            if listener is None:
                return
            p.addDotRefRefs(listener.implement, file_ent)
            self.logger.info("DotRef success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in dotref in file :" + file_address + "\n" + str(e)
            )

    @timer_decorator()
    def setby_listener(self, tree, file_ent, file_address, p, stream: str = ""):
        try:

            def _build():
                # set ref
                listener = SetAndSetByListener(file_address)
                return listener

            listener = self._stage("setby_listener", _build, tree, p)
            if listener is None:
                return
            p.addSetRefs(listener.setBy, file_ent, stream)
            self.logger.info("set Ref success")
        except Exception as e:
            self.logger.error(
                "An Error occurred in set ref in file :" + file_address + "\n" + str(e)
            )

    def setinitby_listener(self, tree, file_ent, file_address, p, stream: str = ""):
        try:

            def _build():
                # setinit ref
                listener = SetInitAndSetByInitListener(file_address)
                return listener

            listener = self._stage("setinitby_listener", _build, tree, p)
            if listener is None:
                return
            p.addSetInitRefs(listener.set_init_by, file_ent, stream)
            self.logger.info("setInit Ref success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in setInit ref in file :"
                + file_address
                + "\n"
                + str(e)
            )

    def setbypartialby_listener(
        self, tree, file_ent, file_address, p, stream: str = ""
    ):
        try:

            def _build():
                listener = SetPartialAndSetByPartialListener(file_address)
                return listener

            listener = self._stage("setbypartialby_listener", _build, tree, p)
            if listener is None:
                return
            p.addSetPartialRefs(listener.set_by_partial, file_ent, stream)
            self.logger.info("set Partial Ref success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in setInit ref in file :"
                + file_address
                + "\n"
                + str(e)
            )

    @timer_decorator()
    def useby_listener(self, tree, file_ent, file_address, p, stream: str = ""):
        try:

            def _build():
                # use ref
                listener = UseAndUseByListener()
                return listener

            listener = self._stage("useby_listener", _build, tree, p)
            if listener is None:
                return
            p.addUseRefs(listener.useBy, file_ent, stream)
            self.logger.info("use ref success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in use ref in file :" + file_address + "\n" + str(e)
            )

    @timer_decorator()
    def callbyNonDynamic_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = CallNonDynamicAndCallNonDynamicBy()
                return listener

            listener = self._stage("callbyNonDynamic_listener", _build, tree, p)
            if listener is None:
                return
            p.addCallNonDynamicOrCallNonDynamicByRefs(
                listener.implement, file_ent, file_address
            )
            self.logger.info("call non dynamic ref success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in call non dynamic ref in file :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def cast_by_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = CastAndCastBy(file_address)
                return listener

            listener = self._stage("cast_by_listener", _build, tree, p)
            if listener is None:
                return
            p.addTypeRelationRefs(listener.relations, file_ent)
            self.logger.info("cast success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in cast in file :"
                + file_address
                + "\n"
                + str(e)
                + traceback.format_exc()
            )

    @timer_decorator()
    def contain_in_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = ContainAndContainBy()
                return listener

            listener = self._stage("contain_in_listener", _build, tree, p)
            if listener is None:
                return
            p.add_contain_in(listener.contain, file_ent, file_address)
            self.logger.info("contain success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in contain in file :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def extend_implict_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                # Two walks, and the second listener needs the first's answer,
                # so this pass does its own walking.
                package_import_listener = PackageImportListener()
                p.Walk(package_import_listener, tree)
                my_listener = DSCmetric(package_import_listener.package_name)
                p.Walk(my_listener, tree)
                return my_listener

            my_listener = self._stage(
                "extend_implict_listener", _build, tree, p, walk=False
            )
            if my_listener is None:
                return
            for item in my_listener.dbHandler.classTypes:
                imported_entity, importing_entity = p.add_imported_entity_factory(item)
                p.add_references(imported_entity, importing_entity, item)
            self.logger.info("extend implict success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in extend implict in file :"
                + file_address
                + "\n"
                + str(e)
            )

    @timer_decorator()
    def import_demand_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = ImportListenerDemand(file_address)
                return listener

            listener = self._stage("import_demand_listener", _build, tree, p)
            if listener is None:
                return
            p.add_import_demand(listener.repository, file_address)
            self.logger.info("import demand success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in import demand in file :"
                + file_address
                + "\n"
                + str(e)
            )

    @timer_decorator()
    def import_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = ImportListener(file_address)
                return listener

            listener = self._stage("import_listener", _build, tree, p)
            if listener is None:
                return
            listener_import = ImportedEntityListener(name=Path(file_address).stem)
            for i in listener.repository:
                imported_entity = p.add_imported_entity(
                    i, file_address, listener_import
                )
                p.add_references_import(file_ent, imported_entity, i)
            self.logger.info("import success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in import in file :" + file_address + "\n" + str(e)
            )

    @timer_decorator()
    def use_module_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = UseModuleUseModuleByListener()
                return listener

            listener = self._stage("use_module_listener", _build, tree, p)
            if listener is None:
                return
            p.add_use_module_reference(
                use_module=listener.useModules,
                unknown_module=listener.useUnknownModules,
                unresolved_module=listener.useUnresolvedModules,
                file_address=file_address,
            )
            self.logger.info("use module by success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in use module by in file :"
                + file_address
                + "\n"
                + str(e)
                + "\n"
                + traceback.format_exc()
            )

    @timer_decorator()
    def open_by_listener(self, tree, file_ent, file_address, p):
        try:

            def _build():
                listener = OpenListener(file_address)
                return listener

            listener = self._stage("open_by_listener", _build, tree, p)
            if listener is None:
                return
            for i in listener.repository:
                imported_entity = p.add_opened_entity(i)
                p.add_references_opend(file_ent, imported_entity, i)
            self.logger.info("open by success ")
        except Exception as e:
            self.logger.error(
                "An Error occurred in open by in file :" + file_address + "\n" + str(e)
            )
