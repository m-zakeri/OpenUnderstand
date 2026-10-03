"""`module-info.java` (Java 9): the module and its directives.

Read off Understand's database for a module-info declaring every directive.
Every reference is scoped to the module and sits at the first token of the
qualified name it is about:

    module com.ex.app {                       Java Module com.ex.app, Definein the file
        requires transitive java.logging;     Require -> java.logging (Unresolved Module)
        exports com.ex.api to java.base;      Export -> com.ex.api, Use -> java.base
        opens com.ex.app;                     Open -> com.ex.app
        uses com.ex.api.Service;              ModuleUse -> Service, DotRef -> com.ex.api
        provides com.ex.api.Service           Provide -> Service, DotRef -> com.ex.api
            with com.ex.app.Impl;             Use -> Impl, DotRef -> com.ex.app
    }

There is no forward Define from the file, only the Definein, as for a
package. The inverse of each relation is written by the writer and dropped
again for a target outside the project (an Unresolved Module, a JDK type).
"""

from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)

#: Filled in by the glue layer with the file entity's long name.
FILE = object()


class ModuleListener(JavaParserLabeledListener):
    def __init__(self):
        self.relations = []
        self.module = None

    def enterModuleDeclaration(self, ctx: JavaParserLabeled.ModuleDeclarationContext):
        name = ctx.qualifiedName()
        self.module = name.getText()
        self._add("Java Definein", FILE, name.start, inverse_only=True)

    def enterModuleDirective(self, ctx: JavaParserLabeled.ModuleDirectiveContext):
        if self.module is None:
            return
        keyword = ctx.IDENTIFIER(0).getText()
        names = ctx.qualifiedName()
        if keyword == "requires":
            self._add("Java Require", names[0].getText(), names[0].start,
                      ent_kind="Java Unresolved Module")
        elif keyword in ("exports", "opens"):
            kind = "Java Export" if keyword == "exports" else "Java Open"
            self._add(kind, names[0].getText(), names[0].start, ent_kind="Java Package")
            for target in names[1:]:  # `to m1, m2`
                self._add("Java Use", target.getText(), target.start,
                          ent_kind="Java Unresolved Module")
        elif keyword == "uses":
            self._type(names[0], "Java ModuleUse")
        elif keyword == "provides":
            self._type(names[0], "Java Provide")
            for implementation in names[1:]:  # `with a, b`
                self._type(implementation, "Java Use")

    def _type(self, name, kind):
        """A type named in full: the relation, and a DotRef to its package,
        both at the name's first token."""
        written = name.getText()
        self._add(kind, written, name.start)
        package = written.rpartition(".")[0]
        if package:
            self._add("Java DotRef", package, name.start, ent_kind="Java Package")

    def _add(self, kind, target, token, ent_kind=None, inverse_only=False):
        relation = {
            "kind": kind,
            "scope_longname": self.module,
            "scope_kind": "Java Module",
            "ent_longname": target,
            "name": self.module if target is FILE else target.rpartition(".")[2],
            "line": token.line,
            "col": token.column,
        }
        if ent_kind:
            relation["ent_kind"] = ent_kind
        if inverse_only:
            relation["inverse_only"] = True
        self.relations.append(relation)
