from antlr4 import *
from oudb.models import EntityModel
from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from oudb.api import open as db_open, create_db


class CyclomaticModifiedListener(JavaParserLabeledListener):
    def __init__(self):
        self.sum = 0

    @property
    def get_sum_cyclomatic_modified(self):
        return self.sum

    # if
    def enterStatement2(self, ctx: JavaParserLabeled.Statement2Context):
        self.sum += 1

    # for
    def enterStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        self.sum += 1

    # while
    def enterStatement4(self, ctx: JavaParserLabeled.Statement4Context):
        self.sum += 1

    # do-while
    def enterStatement5(self, ctx: JavaParserLabeled.Statement5Context):
        self.sum += 1

    # catch
    def enterStatement6(self, ctx: JavaParserLabeled.Statement6Context):
        self.sum += 1

    # switch
    def enterStatement8(self, ctx: JavaParserLabeled.Statement8Context):
        self.sum += 1

    # ?
    def enterExpression20(self, ctx: JavaParserLabeled.Expression20Context):
        self.sum += 1


if __name__ == "__main__":
    create_db("../../benchmark2_database.oudb", project_dir="..\..\benchmark")
    db = db_open("../../benchmark2_database.oudb")

    # enter file name here
    entity_longname = None

    files = {}
    if entity_longname is None:
        for ent in EntityModel.select().where(EntityModel._kind_id == 1):
            files[ent._contents] = 0
        listener = CyclomaticModifiedListener()
    else:
        # search in db
        entity = EntityModel.get_or_none(_longname=entity_longname)
        if entity is None:
            print("there is not such an entity")
        else:
            current = entity
            parent = EntityModel.get_or_none(_id=current._parent_id)
            while current._parent_id is not None and not (70 <= parent._kind._id <= 73):
                current = EntityModel.get_or_none(_id=current._parent_id)
                parent = EntityModel.get_or_none(_id=current._parent_id)
            files.append(current._contents)
            listener = CyclomaticModifiedListener()

    for file_content in files:
        file_stream = InputStream(file_content)
        lexer = JavaLexer(file_stream)
        tokens = CommonTokenStream(lexer)
        parser = JavaParserLabeled(tokens)
        parse_tree = parser.compilationUnit()

        walker = ParseTreeWalker()
        walker.walk(listener=listener, t=parse_tree)
    print(listener.get_sum_cyclomatic_modified)
