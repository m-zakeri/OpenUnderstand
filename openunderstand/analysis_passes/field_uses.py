"""Java Use / Java Useby on the member of a field access.

    System.out.println(x)      Use on java.lang.System.out
    currentElement.content     Use on DataStructures.Bags.Bag.Node.content
    this.cursor                Use on ...DynamicArrayIterator.cursor

`a.b` records two separate facts and only one of them was produced here: the
receiver is a `Use Deref Partial`, and the *member* is a plain `Java Use` on
the field it names. Missing the second is 1,513 of TheAlgorithms' 1,565
absent `Java Use` references -- 490 of them `System.out` alone.

The receiver is resolved the same three ways a call receiver is, because it is
the same question:

    sb.length         a variable, so the field belongs to its declared type
    Integer.MAX_VALUE a *type*, so the field belongs to the type itself
    System.out        a field, whose own type comes from JDK_FIELD_TYPES

A member that is called rather than read is not a use -- `println` in
`System.out.println(x)` is a `Java Call`, and the grammar separates them:
`methodCall` is a different alternative of expression1 from `IDENTIFIER`.

Every row this pass gets wrong sits at a position Understand does report --
700 of them as `Use Deref Partial`, where `a.b.c` dereferences b rather than
reading it. Relabelling those by whether the member is itself dereferenced was
tried and measured worse: they did not match Understand's Deref Partial rows
either, because its entity at that position is not the field this pass
resolves. Recall fell 93.5% to 84.6% for 0.2 points of precision, so the plain
`Java Use` stands until what Understand names there is established.
"""

from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
import openunderstand.analysis_passes.class_properties as class_properties
from openunderstand.analysis_passes import declared_types


class FieldUseListener(JavaParserLabeledListener):
    def __init__(self, file_address=""):
        self.file_address = file_address
        #: Positioned relations, written by Project.addTypeRelationRefs.
        self.relations = []
        self.field_types = {}
        self.local_types = {}
        self.imports = {}
        self.wildcards = []
        #: Long name of the class currently open, for `this.x`.
        self.enclosing_type = ""

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        longname = ctx.qualifiedName().getText()
        if ctx.getText().rstrip(";").endswith(".*"):
            self.wildcards.append(longname)
            return
        self.imports[longname.split(".")[-1]] = longname

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        body = ctx.classBody()
        if body is not None:
            self.field_types = declared_types.collect(body)
        self.enclosing_type = ".".join(
            class_properties.ClassPropertiesListener.findParents(ctx)
            + [ctx.IDENTIFIER().getText()])

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.local_types = declared_types.collect(ctx)

    def enterConstructorDeclaration(
        self, ctx: JavaParserLabeled.ConstructorDeclarationContext
    ):
        self.local_types = declared_types.collect(ctx)

    def _owner(self, receiver, scope_longname):
        """Long name of the type whose member `receiver.x` names, or None."""
        from openunderstand.ounderstand import symbol_table

        if not receiver:
            return None
        if receiver == "this":
            return self.enclosing_type or None
        head, _, field = receiver.partition(".")
        if not head.isidentifier() or (field and not field.isidentifier()):
            return None
        if head == "this":
            # `this.a.b` -- the field `a` of the enclosing type.
            return None
        declared = self.local_types.get(head) or self.field_types.get(head)
        owner = symbol_table.resolve_type_name(
            declared or head, self.imports, self.wildcards, scope_longname)
        if owner is None or not field:
            return owner
        return symbol_table.member_type(owner, field)

    def enterExpression1(self, ctx: JavaParserLabeled.Expression1Context):
        identifier = ctx.IDENTIFIER()
        if identifier is None or isinstance(identifier, list):
            return          # a methodCall, `this`, `new`, `super`: not a read
        receiver = ctx.expression()
        if receiver is None:
            return
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        scope = ".".join(parents)
        owner = self._owner(receiver.getText(), scope)
        if not owner or "." not in owner:
            # Never a bare simple name: merge_placeholder_entities() would fold
            # it into whichever project entity happens to share it.
            return
        name = identifier.getText()
        token = identifier.symbol
        self.relations.append({
            "kind": "Java Use",
            "scope_longname": scope,
            "ent_longname": f"{owner}.{name}",
            "name": name,
            "line": token.line,
            "col": token.column,
        })
