"""This module is for managing project files and walking on parse tree"""

__author__ = "Navid Mousavizadeh, Amir Mohammad Sohrabi, Sara Younesi, Deniz Ahmadi"
__copyright__ = "Copyright 2022, The OpenUnderstand Project, Iran University of Science and technology"
__credits__ = ["Dr.Parsa", "Dr.Zakeri", "Mehdi Razavi", "Navid Mousavizadeh", "Amir Mohammad Sohrabi", "Sara Younesi",
               "Deniz Ahmadi"]
__license__ = "GPL"
__version__ = "1.0.0"

from antlr4 import *

from gen.javaLabeled.JavaLexer import JavaLexer
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from analysis_passes.entity_manager_G11 import get_created_entity_longname, get_all_files, get_created_entity_id
from oudb.api import open as db_open, create_db


class AntlrHandler:
    @staticmethod
    def Parse(entity_content):
        file_stream = InputStream(entity_content)
        lexer = JavaLexer(file_stream)
        tokens = CommonTokenStream(lexer)
        parser = JavaParserLabeled(tokens)
        return_tree = parser.compilationUnit()
        return return_tree

    @staticmethod
    def Walk(reference_listener, parse_tree):
        walker = ParseTreeWalker()
        walker.walk(listener=reference_listener, t=parse_tree)


class EssentialMetric:
    def __init__(self, entity_longname='Project'):
        """get project or method entity and will calculate Cyclomatic Modified Metric of it."""
        self.files = []
        self.method = None
        if entity_longname != 'Project':
            entity = get_created_entity_longname(entity_longname)
            if entity is None:
                raise Exception("Couldn't find entity.")
            if not 3 <= int(entity._kind._id) <= 66:
                raise Exception("Entity is not a method.")
            current = entity
            parent = get_created_entity_id(current._parent_id)
            while current._parent_id is not None and not (70 <= parent._kind._id <= 73):
                current = get_created_entity_id(current._parent_id)
                parent = get_created_entity_id(current._parent_id)
            self.files.append(current._contents)
            self.method = entity
            listener = EssentialMetricListener(method_entity=self.method)
        else:
            self.files = get_all_files()
            listener = EssentialMetricListener()
        for file_content in self.files:
            parse_tree = AntlrHandler.Parse(file_content)
            AntlrHandler.Walk(listener, parse_tree)
        print(listener.essential_metric)


class EssentialMetricListener(JavaParserLabeledListener):
    def __init__(self, method_entity=None):
        self.method = method_entity
        self.method_entered = False
        self.index = 0
        self.layers = []
        self.counts = []
        self.count_essential_metric = 1
        self.entered_switch = False

    @property
    def essential_metric(self):
        return self.count_essential_metric

    # enter if clause
    def enterStatement2(self, ctx: JavaParserLabeled.Statement2Context):
        if self.method is not None:
            if self.method_entered:
                self.index += 1
                if ctx.ELSE() is not None:
                    self.layers.append(1)
                else:
                    self.layers.append(0)
                self.counts.append(0)
        else:
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
                    self.count_essential_metric += self.counts.pop(0) + last
                else:
                    break
            self.layers = []
            self.counts = []

    # enter while loop
    def enterStatement4(self, ctx: JavaParserLabeled.Statement4Context):
        if self.method is not None:
            if self.method_entered:
                if len(self.layers) == 0:
                    self.count_essential_metric += 1
                else:
                    self.counts[-1] += 1
        else:
            if len(self.layers) == 0:
                self.count_essential_metric += 1
            else:
                self.counts[-1] += 1

    # enter for loop
    def enterStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        if self.method is not None:
            if self.method_entered:
                if len(self.layers) == 0:
                    self.count_essential_metric += 1
                else:
                    self.counts[-1] += 1
        else:
            if len(self.layers) == 0:
                self.count_essential_metric += 1
            else:
                self.counts[-1] += 1

    # enter do-while class
    def enterStatement5(self, ctx: JavaParserLabeled.Statement5Context):
        if self.method is not None:
            if self.method_entered:
                if len(self.layers) == 0:
                    self.count_essential_metric += 1
                else:
                    self.counts[-1] += 1
        else:
            if len(self.layers) == 0:
                self.count_essential_metric += 1
            else:
                self.counts[-1] += 1

    # enter switch clause
    def enterStatement8(self, ctx: JavaParserLabeled.Statement8Context):
        self.entered_switch = True

    def exitStatement8(self, ctx: JavaParserLabeled.Statement8Context):
        self.entered_switch = False

    def enterStatement12(self, ctx: JavaParserLabeled.Statement12Context):
        if not self.entered_switch:
            if self.layers[-1] < 2:
                self.layers[-1] += 1

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        if self.method is not None:
            if ctx.IDENTIFIER().getText() == self.method._name:
                self.method_entered = True

    def exitMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        if self.method is not None:
            if ctx.IDENTIFIER().getText() == self.method._name:
                self.method_entered = False


if __name__ == '__main__':
    create_db("../../benchmark2_database.oudb", project_dir="..\..\benchmark")
    db = db_open("../../benchmark2_database.oudb")
    # try:
    essential_manager = EssentialMetric('com.calculator.app.display.print_success.main')
    # except Exception as e:
    # print("Error:", e)
