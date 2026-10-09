"""Java Importby / Java Importby Demand: what a file pulls in by import.

    import org.json.CDL;                  ->  Importby         scope=org.json.CDL
    import org.json.*;                    ->  Importby Demand  scope=org.json
    import static Sorts.SortUtils.less;   ->  Importby         scope=Sorts.SortUtils.less
    import static Sorts.SortUtils.*;      ->  Importby Demand  scope=Sorts.SortUtils

The reference is recorded against the *imported* thing, with the importing file
as the entity, positioned on the last identifier of the qualified name --
column 17 for `import org.json.CDL;`, column 12 for `import org.json.*;`, both
confirmed against the dump.

Only the inverse direction: Understand reports 10 Importby and 7 Importby
Demand on TheAlgorithms and no Java Import at all, so writing the forward half
too would add rows it never has.

**Plain imports count.** This pass returned early on anything without `static`,
and said in this docstring that Understand does not record them. It records 91
`Java Importby` on JSON alone, every one of them a plain `import org.json.X;`.
Whether the import is static changes nothing here: the imported name is the
scope either way.

Nothing is emitted for a target outside the analysed source. Understand hangs
an inverse only on an entity the project declares, so `import static
org.junit.Assert.*;` gets no row -- it has 12 Importby Demand on JSON, all
`org.json`, and none for org.junit. That filtering is left to
`drop_external_inverse_refs()`, which is where every other inverse kind is
filtered and which keys on the referenced entity's kind.

**An import is also a `Java DotRefby` on everything enclosing the imported
type**, inverse-only and at the *first* identifier: `import org.json.CDL;` is
DotRefby scope=org.json at column 8, and `import static p.Outer.Inner.X;` adds
one for p.Outer too. Intermediate packages get nothing, a plain `import p.*;`
gets nothing, and neither does a type outside the project. Read off 26,821 of
26,959 import lines over eight fixtures; it was 12,976 missing rows.
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
        # `import static Sorts.SortUtils.print;` imports every overload of
        # print, and Understand writes one Importby per overload -- two rows
        # at the same token, each on its own entity.
        from openunderstand.ounderstand import symbol_table

        sites = [None]
        if ctx.STATIC() is not None and not on_demand:
            overloads = symbol_table.INDEX.overloads.get(qualified.getText()) or ()
            sites = [(entry[1], entry[2]) for entry in overloads] or [None]
        for site in sites:
            self.relations.append(
                {
                    "kind": ("Java Importby Demand" if on_demand else "Java Importby"),
                    "scope_longname": qualified.getText(),
                    "ent_longname": self.file_longname,
                    "name": identifiers[-1].getText(),
                    "line": token.line,
                    "col": token.column,
                    "inverse_only": True,
                    **({"scope_site": site} if site else {}),
                }
            )
        if on_demand and ctx.STATIC() is None:
            return
        names = [i.getText() for i in identifiers]
        head = identifiers[0].symbol
        for qualifier, kind in _enclosing(names):
            self.relations.append(
                {
                    "kind": "Java DotRefby",
                    "scope_longname": qualifier,
                    **({"scope_kind": kind} if kind else {}),
                    "ent_longname": self.file_longname,
                    "name": names[0],
                    "line": head.line,
                    "col": head.column,
                    "inverse_only": True,
                }
            )


def _enclosing(names):
    """(long name, kind) of each package or outer type enclosing the innermost
    project type the import names; nothing when no prefix is a project type."""
    # Deferred: ounderstand's package import reaches the module importing this.
    from openunderstand.ounderstand import symbol_table

    prefixes = [".".join(names[: i + 1]) for i in range(len(names))]
    types = [p for p in prefixes if symbol_table.is_project_type(p)]
    if not types:
        return []
    first = prefixes.index(types[0])
    out = [(prefixes[first - 1], "Java Package")] if first else []
    return out + [(t, None) for t in types[:-1]]
