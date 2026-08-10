from antlr4 import *
from openunderstand.metrics import context

from openunderstand.gen.javaLabeled.JavaLexer import JavaLexer
from openunderstand.oudb.models import kind_id, EntityModel
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


class CyclomaticStrictListener(JavaParserLabeledListener):
    def __init__(self):
        self.sum = 0

    @property
    def get_sum_cyclomatic_strict(self):
        return self.sum

    # if
    def enterStatement2(self, ctx: JavaParserLabeled.Statement2Context):
        self.sum += 1

    # while
    def enterStatement4(self, ctx: JavaParserLabeled.Statement4Context):
        self.sum += 1

    # for
    def enterStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        self.sum += 1

    # case
    def enterSwitchLabel(self, ctx: JavaParserLabeled.SwitchLabelContext):
        self.sum += 1

    # do-while
    def enterStatement5(self, ctx: JavaParserLabeled.Statement5Context):
        self.sum += 1

    # catch
    def enterStatement6(self, ctx: JavaParserLabeled.Statement6Context):
        self.sum += 1

    # and
    def enterExpression18(self, ctx: JavaParserLabeled.Expression18Context):
        self.sum += 1

    # or
    def enterExpression19(self, ctx: JavaParserLabeled.Expression19Context):
        self.sum += 1

    # ?
    def enterExpression20(self, ctx: JavaParserLabeled.Expression20Context):
        self.sum += 1



def _enclosing_file_contents(entity_longname):
    """Source of the file an entity lives in, as a one-item list.

    Walks up _parent to the File entity. The old walk compared
    `70 <= parent._kind._id <= 73` -- hard-coded package kind ids, which no
    longer mean that -- and dereferenced `parent` without checking it for
    None, so a top-level entity crashed the metric.
    """
    if entity_longname is None:
        return [
            e._contents
            for e in EntityModel.select().where(
                EntityModel._kind == kind_id("Java File")
            )
        ]
    entity = EntityModel.get_or_none(_longname=entity_longname)
    file_kind = kind_id("Java File")
    seen = set()
    while entity is not None and entity._id not in seen:
        if entity._kind_id == file_kind:
            return [entity._contents]
        seen.add(entity._id)
        entity = EntityModel.get_or_none(_id=entity._parent_id)
    return []


def get_sum_cyclomatic_strict(ent_model=None):

    # enter file name here
    entity_longname = ent_model.longname()

    listener = CyclomaticStrictListener()
    files = _enclosing_file_contents(entity_longname)

    for file_content in files:
        parse_tree = context.parse(file_content)

        walker = ParseTreeWalker()
        walker.walk(listener=listener, t=parse_tree)
    return listener.get_sum_cyclomatic_strict
