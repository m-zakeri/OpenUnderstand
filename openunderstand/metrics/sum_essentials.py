from antlr4 import *
from openunderstand.oudb.models import kind_id, EntityModel
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


class EssentialListener(JavaParserLabeledListener):
    def __init__(self):
        self.index = 0
        self.layers = []
        self.counts = []
        self.sum = 0
        self.entered_switch = False

    @property
    def get_sum_essential(self):
        return self.sum

    # if
    def enterStatement2(self, ctx: JavaParserLabeled.Statement2Context):
        self.index += 1
        if ctx.ELSE() is not None:
            self.layers.append(1)
        else:
            self.layers.append(0)
        self.counts.append(0)

    def exitStatement2(self, ctx: JavaParserLabeled.Statement2Context):
        self.index -= 1
        if self.index == 0:
            while len(self.layers) != 0:
                last = self.layers.pop(0)
                if last > 0:
                    self.sum += self.counts.pop(0) + last
                else:
                    break
            self.layers = []
            self.counts = []

    # while
    def enterStatement4(self, ctx: JavaParserLabeled.Statement4Context):
        if len(self.layers) == 0:
            self.sum += 1
        else:
            self.counts[-1] += 1

    # for
    def enterStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        if len(self.layers) == 0:
            self.sum += 1
        else:
            self.counts[-1] += 1

    # do-while
    def enterStatement5(self, ctx: JavaParserLabeled.Statement5Context):
        if len(self.layers) == 0:
            self.sum += 1
        else:
            self.counts[-1] += 1

    # switch
    def enterStatement8(self, ctx: JavaParserLabeled.Statement8Context):
        self.entered_switch = True

    def exitStatement8(self, ctx: JavaParserLabeled.Statement8Context):
        self.entered_switch = False

    def enterStatement12(self, ctx: JavaParserLabeled.Statement12Context):
        if not self.entered_switch:
            if self.layers[-1] < 2:
                self.layers[-1] += 1



def _enclosing_file_contents(entity_longname):
    """Source of the file an entity lives in, as a one-item list.

    The old walk compared `70 <= parent._kind._id <= 73` -- hard-coded package
    kind ids, which no longer mean that -- and dereferenced `parent` without
    checking it for None, so a top-level entity crashed the metric.
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


def get_sum_essentials(ent_model=None):
    # enter file name here
    entity_longname = ent_model.longname()

    listener = EssentialListener()
    files = _enclosing_file_contents(entity_longname)

    for file_content in files:
        file_stream = InputStream(file_content)
        lexer = JavaLexer(file_stream)
        tokens = CommonTokenStream(lexer)
        parser = JavaParserLabeled(tokens)
        parse_tree = parser.compilationUnit()

        walker = ParseTreeWalker()
        walker.walk(listener=listener, t=parse_tree)
    return listener.get_sum_essential
