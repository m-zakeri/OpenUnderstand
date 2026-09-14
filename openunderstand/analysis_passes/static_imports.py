"""Java Importby / Java Importby Demand: what a file pulls in by import.

    import org.json.CDL;                  ->  Importby         scope=org.json.CDL
    import org.json.*;                    ->  Importby Demand  scope=org.json
    import static Sorts.SortUtils.less;   ->  Importby         scope=Sorts.SortUtils.less
    import static Sorts.SortUtils.*;      ->  Importby Demand  scope=Sorts.SortUtils

Whether the import is static changes nothing about the endpoints: the reference
is recorded against the *imported* thing, with the importing file as the entity,
positioned on the last identifier of the qualified name. This pass used to
return early on anything without `static`, so every plain import went
unrecorded -- Understand emits 91 `Java Importby` on JSON and this project
emitted none.

Only the inverse direction: Understand reports no `Java Import` at all, so
writing the forward half too would add rows it never has. And it records an
inverse only for a target it declares -- `import java.util.Map;` and
`import static org.junit.Assert.*;` get none -- which `drop_external_inverse_refs()`
settles after every file has run, keyed on the target's kind.
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
