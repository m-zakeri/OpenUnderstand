from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.analysis_passes import class_properties


class ModifyListener(JavaParserLabeledListener):
    """Collect in-place modifications: `i++`, `++i`, `x += 1`.

    Understand puts the reference on the modified variable's own identifier and
    scopes it to the method containing it:

        JSONTokener.java:118:14  scope=org.json.JSONTokener.decrementIndexes
                                 ent=org.json.JSONTokener.index

    This pass used to take ctx.start, which is the *operator* for a prefix
    `++i` and the `this` keyword for `this.index--`, landing 2 and 5 columns
    short. It also built long names by gluing the package onto the identifier,
    so every `i` in the project was org.json.i.
    """

    COMPOUND_ASSIGNMENTS = frozenset(
        ["+=", "-=", "/=", "*=", "&=", "|=", "^=", "%=", ">>=", ">>>=", "<<="]
    )

    def __init__(self, entity_manager_object):
        self.entity_manager = entity_manager_object
        self.modify = []

    def enterExpression6(self, ctx: JavaParserLabeled.Expression6Context):
        """Postfix `i++` / `i--`."""
        self.record(ctx.expression())

    def enterExpression7(self, ctx: JavaParserLabeled.Expression7Context):
        """Prefix `++i` / `--i`."""
        self.record(ctx.expression())

    def enterExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        """`x += 1` and friends. Plain `x = 1` is a Java Set, not a Modify."""
        if ctx.children[1].getText() in self.COMPOUND_ASSIGNMENTS:
            self.record(ctx.expression()[0])

    def record(self, target):
        """Record one modification of `target`, an expression being written to.

        The position is the last token of the target: for `i` that is `i`, and
        for `this.index` it is `index` -- which is where Understand puts it in
        both cases. ctx.start would be `++` or `this`.
        """
        if target is None:
            return
        token = target.stop
        if token is None or not token.text.isidentifier():
            # `arr[i] += 1` ends on `]`. Understand reports the array element,
            # which this pass has no entity for.
            # ponytail: skipped rather than guessed; 0 such cases on JSON.
            return
        parents = class_properties.ClassPropertiesListener.findParents(target)
        if not parents:
            return
        scope_longname = ".".join(parents)
        # `this.index++` names a field of the enclosing class, never a local,
        # so resolution starts one scope out -- the same rule the set pass
        # needs for `this.refTokens = refTokens`.
        resolve_scope = (
            ".".join(parents[:-1])
            if target.getText().startswith("this.") and len(parents) > 1
            else scope_longname
        )
        self.modify.append(
            {
                "file": self.entity_manager.file_ent,
                "line": token.line,
                "column": token.column,
                "name": token.text,
                "scope_longname": scope_longname,
                "resolve_scope": resolve_scope,
            }
        )
