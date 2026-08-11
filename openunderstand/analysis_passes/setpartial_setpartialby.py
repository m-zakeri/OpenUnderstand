from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
from openunderstand.analysis_passes import class_properties
from os.path import basename


class SetPartialAndSetByPartialListener(JavaParserLabeledListener):
    """Collect assignments made *through* a dereference: `Java Set Deref Partial`.

    `a[i] = x` and `obj.field = x` set only part of what `a` / `obj` refer to,
    so Understand reports the reference against the dereferenced variable, at
    that variable's own identifier:

        AES.java:321:7  scope=ciphers.AES.keyExpansion
                        ent=ciphers.AES.keyExpansion.roundKeys   // roundKeys[i] = ...
        Bag.java:41:5   scope=DataStructures.Bags.Bag.add
                        ent=DataStructures.Bags.Bag.firstElement // firstElement.content = ...

    Note the entity is the thing being dereferenced (`firstElement`), not the
    member being written (`content`).

    `this.field = x` is NOT one of these -- it sets the field outright and is a
    plain Java Set, emitted by set_setby.

    The previous implementation raised on every input: `self.stream` was read in
    add_set_by_entry but never initialised, and a trailing unconditional call
    used locals that only one branch defined. A bare `except: x = 0` hid both,
    leaving 24 references where Understand reports 468.
    """

    #: Target shapes that constitute a dereference. expression2 is `a[i]`,
    #: expression1 is `obj.field`.
    DEREFERENCING_TARGETS = ("Expression1Context", "Expression2Context")

    def __init__(self, file_name):
        self.file_name = basename(file_name)
        self.set_by_partial = []

    def exitExpression21(self, ctx: JavaParserLabeled.Expression21Context):
        if ctx.children[1].getText() != "=":
            # `a[i] += 1` is a Java Modify Deref Partial, a kind this project
            # does not produce yet.
            return
        target = ctx.expression()[0]
        if type(target).__name__ not in self.DEREFERENCING_TARGETS:
            return
        # The dereferenced variable is the leftmost token of the target, for
        # `a[i][j]` as much as for `obj.f.g`.
        token = target.start
        if token.text == "this" or not token.text.isidentifier():
            return
        parents = class_properties.ClassPropertiesListener.findParents(ctx)
        if not parents:
            return
        self.set_by_partial.append(
            {
                "name": token.text,
                "scope_longname": ".".join(parents),
                "line": token.line,
                "column": token.column,
            }
        )
