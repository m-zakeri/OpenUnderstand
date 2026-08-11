from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener


class MaxNesting(JavaParserLabeledListener):
    """Deepest nesting of control constructs, the way Understand counts it.

    Two rules this used to get wrong, both measured against Understand on the
    JSON benchmark:

      * `else if` is one construct, not two. The grammar nests the chain --
        `IF parExpression statement (ELSE statement)?` puts the `else if` in
        the ELSE slot of its predecessor -- so a three-branch chain looked
        three deep. org.json.XML came out 15 against Understand's 7.
      * `try` is a nesting level. JSONArray.getNumber is a try wrapping an if
        and Understand reports 2, where counting only if/for/while/do/switch
        gave 1.

    ponytail: `synchronized` (#statement9) is not counted, and that is a guess
    rather than a measurement -- the only three synchronized blocks in the JSON
    benchmark are inside overloaded methods, which the comparison excludes
    because Understand's dump strips parameter lists and collapses overloads
    onto one name. Check it against a fixture that uses synchronized in a
    uniquely-named method before trusting either answer.
    """

    def __init__(self):
        self.stack = []
        self.max_nesting = 0
        #: ids of the contexts a level was pushed for, so exit pops exactly
        #: those and an `else if` stays balanced.
        self._pushed = set()

    def push_to_stack(self, ctx=None):
        self._pushed.add(id(ctx))
        self.stack.append(0)
        if len(self.stack) > self.max_nesting:
            self.max_nesting = len(self.stack)

    def pop_from_stack(self, ctx=None):
        if id(ctx) in self._pushed:
            self._pushed.discard(id(ctx))
            self.stack.pop()

    @staticmethod
    def _is_else_if(ctx):
        """True when ctx is the `if` of an `else if`, i.e. an ELSE branch."""
        parent = ctx.parentCtx
        if type(parent).__name__ != "Statement2Context":
            return False
        children = parent.children or []
        # `IF parExpression statement ELSE statement` -- 5 children, and the
        # else branch is the last. `if` without `else` has 3.
        return len(children) == 5 and children[-1] is ctx

    # if statement
    def enterStatement2(self, ctx: JavaParserLabeled.Statement2Context):
        if not self._is_else_if(ctx):
            self.push_to_stack(ctx)

    # if statement
    def exitStatement2(self, ctx: JavaParserLabeled.Statement2Context):
        self.pop_from_stack(ctx)

    # while statement
    def enterStatement4(self, ctx: JavaParserLabeled.Statement4Context):
        self.push_to_stack(ctx)

    # while statement
    def exitStatement4(self, ctx: JavaParserLabeled.Statement4Context):
        self.pop_from_stack(ctx)

    # do while statement
    def enterStatement5(self, ctx: JavaParserLabeled.Statement5Context):
        self.push_to_stack(ctx)

    # do while statement
    def exitStatement5(self, ctx: JavaParserLabeled.Statement5Context):
        self.pop_from_stack(ctx)

    # for statement
    def enterStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        self.push_to_stack(ctx)

    # for statement
    def exitStatement3(self, ctx: JavaParserLabeled.Statement3Context):
        self.pop_from_stack(ctx)

    # switch case statement
    def enterStatement8(self, ctx: JavaParserLabeled.Statement8Context):
        self.push_to_stack(ctx)

    # switch case statement
    def exitStatement8(self, ctx: JavaParserLabeled.Statement8Context):
        self.pop_from_stack(ctx)

    # try / catch / finally
    def enterStatement6(self, ctx: JavaParserLabeled.Statement6Context):
        self.push_to_stack(ctx)

    def exitStatement6(self, ctx: JavaParserLabeled.Statement6Context):
        self.pop_from_stack(ctx)

    # try with resources
    def enterStatement7(self, ctx: JavaParserLabeled.Statement7Context):
        self.push_to_stack(ctx)

    def exitStatement7(self, ctx: JavaParserLabeled.Statement7Context):
        self.pop_from_stack(ctx)
