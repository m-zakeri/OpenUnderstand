
__author__ = 'Parmida Majmasanaye , Zahra Momeninezhad , Bayan divaaniazar , Bavan Divaaniazar'
__version__ = '0.2.0'

from gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled


class DeclareAndDeclareinListener(JavaParserLabeledListener):

    # define an array for saving entity and reference information
    def __init__(self):
        self.declare_dicts = []

    # getter to return declaration array
    @property
    def get_declare_dicts(self):
        return self.declare_dicts

    # setter to append a data to declaration array
    def set_declare_dicts(self, data):
        self.declare_dicts.append(data)

    # override enterCompilationUnit function to check if a file declare any package or not
    def enterCompilationUnit(self, ctx: JavaParserLabeled.CompilationUnitContext):
        if not ctx.packageDeclaration():
            data = {"scope": None, "entity": None, "line": 1, "column": 0}  # unnamed package
            self.set_declare_dicts(data)

    # override enterPackageDeclaration function to set reference information
    def enterPackageDeclaration(self, ctx: JavaParserLabeled.PackageDeclarationContext):
        full_package_name_array = ctx.qualifiedName().IDENTIFIER()

        longname = ""
        for i in range(len(full_package_name_array)):
            entity_name = full_package_name_array[i].getText()
            entity_longname = longname + ("." if longname != "" else "") + entity_name
            [line, column] = str(ctx.start).split(",")[3].split(":")
            data = {
                "scope": full_package_name_array[i - 1].getText() if i != 0 else None, "entity": entity_name,
                "scope_longname": longname, "entity_longname": entity_longname,
                "line": line, "column": column.strip("]")
            }
            self.set_declare_dicts(data)
            longname = entity_longname

