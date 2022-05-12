from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


class SetInitAndSetInitByListener(JavaParserLabeledListener):
    def __init__(self, file_name):
        self.ex_name=""
        self.in_expreession_21=False
        self.has_primary_3 = False
        self.in_variable_initializer = False
        self.initializer_identifier_number = 0
        self.number_of_primary_4 = 0
        self.file_name = file_name
        self.package_name = ""
        self.set_init_by = []


    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        name_of_file = self.file_name.split('\\')[self.file_name.split('\\').count(0) - 1]
        self.ex_name = ctx.children[1].getText()
        long_name = name_of_file.replace(".java", "") + '.' + self.ex_name
        line = ctx.children[0].symbol.line
        col = ctx.children[0].symbol.column


    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):

        name_of_file = self.file_name.split('\\')[self.file_name.split('\\').count(0) - 1]
        self.ex_name = ctx.children[1].getText()




    def enterVariableInitializer1(self, ctx: JavaParserLabeled.VariableInitializer1Context):
        try:
            name_of_file = self.file_name.split('\\')[self.file_name.split('\\').count(0) - 1]
            set_init_long_name = name_of_file.replace(".java", "") + '.' + self.ex_name + '.' + ctx.parentCtx.children[
                0].getText()
            set_init_short_name = ctx.parentCtx.children[0].getText()
            set_init_value = ctx.getText()
            set_init_type = ctx.parentCtx.parentCtx.parentCtx.children[0].getText()
            line = ctx.parentCtx.parentCtx.parentCtx.children[0].children[0].children[0].symbol.line
            column = ctx.parentCtx.parentCtx.parentCtx.children[0].children[0].children[0].symbol.column


            self.set_init_by.append((set_init_short_name,set_init_long_name,name_of_file,set_init_value,set_init_type,line,column,self.ex_name))


        except:
            x = 0

