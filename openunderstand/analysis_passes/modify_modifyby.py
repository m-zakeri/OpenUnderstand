from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import (
    JavaParserLabeledListener,
)
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
        """Prefix `++i` / `--i`. The same alternative carries unary `-x` and
        `+x`, which modify nothing: 328 rows Understand does not have."""
        if ctx.prefix.text in ("++", "--"):
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
        kind = "Java Modify"
        if token is None or not token.text.isidentifier():
            # `arr[i] += 1` ends on `]`. Understand reports this against the
            # array itself, as a Java Modify Deref Partial positioned on the
            # array's own token -- the same shape as Set Deref Partial.
            token = target.start
            kind = "Java Modify Deref Partial"
            if token is None or not token.text.isidentifier():
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
        ent_longname = None
        if (
            kind == "Java Modify"
            and isinstance(target, JavaParserLabeled.Expression1Context)
            and target.IDENTIFIER() is not None
            and target.expression().getText() != "this"
        ):
            # `loc.x += 3` modifies java.awt.Point.x, the field of the
            # receiver's type; resolving the bare `x` in the method found any
            # local called x, or invented `show.x`. The receiver itself is a
            # Modify Deref Partial at its own token, as `a[i] += 1` is.
            ent_longname = _receiver_field(target, token.text)
            if ent_longname is None:
                return
            receiver = target.expression()
            if receiver.getText().isidentifier():
                self._append("Java Modify Deref Partial", receiver.start,
                             scope_longname, scope_longname,
                             _inherited_receiver(receiver, parents))
        self._append(kind, token, scope_longname, resolve_scope, ent_longname)

    def _append(self, kind, token, scope_longname, resolve_scope, ent_longname=None):
        self.modify.append(
            {
                "kind": kind,
                "file": self.entity_manager.file_ent,
                "line": token.line,
                "column": token.column,
                "name": token.text,
                "scope_longname": scope_longname,
                "resolve_scope": resolve_scope,
                "ent_longname": ent_longname,
            }
        )


def _inherited_receiver(receiver, parents):
    """Long name of a receiver that is a field some enclosing type inherits
    -- `fCurrentEntity` in XML11EntityScanner is XMLEntityScanner's -- or None
    for a local, a parameter or an own field, which the writer resolves by
    name. 126 of xerces' receivers resolved to nothing."""
    from openunderstand.analysis_passes.dotref_dotrefby import _binder
    from openunderstand.ounderstand import symbol_table

    name = receiver.getText()
    if _binder(receiver).name_type(name, receiver):
        return None
    for end in range(len(parents), 0, -1):
        owner = ".".join(parents[:end])
        if not symbol_table.is_project_type(owner):
            continue
        if symbol_table.INDEX.field_types.get((owner, name)):
            return None
        declarer = symbol_table.declaring_type_anywhere(owner, name, fields=True)
        if declarer and declarer != owner:
            return f"{declarer}.{name}"
    return None


def _receiver_field(target, name):
    """Long name of the field `recv.name` modifies, or None if the receiver's
    type is unknown -- a wrong target is worse than none."""
    from openunderstand.analysis_passes.dotref_dotrefby import _binder
    from openunderstand.ounderstand import symbol_table

    try:
        owner = _binder(target).type_of(target.expression())
    except Exception:
        owner = None
    if not owner or "." not in owner:
        return None
    declarer = symbol_table.declaring_type_anywhere(owner, name, fields=True)
    return f"{declarer or owner}.{name}"
