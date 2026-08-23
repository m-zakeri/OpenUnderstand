"""Java Importby / Java Importby Demand: what a file pulls in by static import.

    import static Sorts.SortUtils.less;   ->  Importby         scope=Sorts.SortUtils.less
    import static Sorts.SortUtils.*;      ->  Importby Demand  scope=Sorts.SortUtils

The reference is recorded against the *imported* thing, with the importing file
as the entity, positioned on the last identifier of the qualified name.

Only the inverse direction: Understand reports 10 Importby and 7 Importby
Demand on TheAlgorithms and no Java Import at all, so writing the forward half
too would add rows it never has.

A plain (non-static) import is not a reference Understand records for Java --
the pass that used to emit 241 of them scoped to a file path was removed.
"""

from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)


class StaticImportListener(JavaParserLabeledListener):
    def __init__(self, file_longname=""):
        self.file_longname = file_longname
        #: Positioned relations, written by Project.addTypeRelationRefs.
        self.relations = []

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        if ctx.STATIC() is None:
            return
        qualified = ctx.qualifiedName()
        if qualified is None:
            return
        identifiers = qualified.IDENTIFIER()
        if not identifiers:
            return
        on_demand = ctx.getText().rstrip(";").endswith(".*")
        token = identifiers[-1].symbol
        self.relations.append(
            {
                "kind": ("Java Importby Demand" if on_demand else "Java Importby"),
                "scope_longname": qualified.getText(),
                "ent_longname": self.file_longname,
                "name": identifiers[-1].getText(),
                "line": token.line,
                "col": token.column,
                "inverse_only": True,
            }
        )
