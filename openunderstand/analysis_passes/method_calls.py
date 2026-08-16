"""Record every method-call site, resolved or not.

The existing call pass resolves a call against the classes it can see in the
one file being parsed, so on the JSON benchmark it found 172 of the 1722 calls
Understand reports. Most calls in a project cross files, and `process_file`
never sees more than one.

Rather than build a project-wide symbol table up front, this pass records the
call site unconditionally and lets the write layer create a placeholder entity
for a name it cannot resolve locally. `merge_placeholder_entities()` already
runs after every file has been parsed and folds a placeholder into the real
entity when exactly one project-wide match exists -- which is the symbol table,
arrived at from the other direction.
"""

from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
from openunderstand.gen.javaLabeled.JavaParserLabeledListener import JavaParserLabeledListener
import re

import openunderstand.analysis_passes.class_properties as class_properties
from openunderstand.analysis_passes import declared_types


#: `((Number)object)` and `(Number)object` -- a parenthesised cast, whose
#: type is what a call on it lands on.
_CAST = re.compile(r"^\(?\(([A-Z][\w.$]*)\)[^)]*\)?$")


class MethodCallListener(JavaParserLabeledListener):
    def __init__(self, file_address=""):
        self.file_address = file_address
        self.calls = []
        #: Declared types in scope. A class's fields are collected when the
        #: class opens and a method's parameters and locals when it opens, both
        #: of which precede any call inside them.
        self.field_types = {}
        self.local_types = {}
        #: Explicitly imported types, by simple name, and the `x.y.*` packages.
        self.imports = {}
        self.wildcards = []
        #: Statically imported member -> the type declaring it. A call with no
        #: receiver may be one of these: TheAlgorithms statically imports
        #: Sorts.SortUtils.less and calls `less(a, b)` bare, 32 times.
        self.static_imports = {}
        #: The file's expression -> type table, built on first use. It answers
        #: every receiver shape from the parse tree; the ladder below is kept
        #: for the ones it declines, and answers nothing the binder does not.
        self._binder = None
        #: Long name of the class currently open, for a `this` receiver.
        self.enclosing_type = ""
        #: Saved (enclosing_type, field_types) per open class declaration.
        self._scopes = []

    def enterClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        # A stack, because a nested class ends and the outer one resumes.
        # Assigned and never restored, the last nested class a file declared
        # owned every field name after it.
        self._scopes.append((self.enclosing_type, self.field_types))
        body = ctx.classBody()
        # collect_own: a class body contains its nested classes, and the
        # plain walk folded their fields in with its own -- `this.items`
        # resolved to whichever `items` was declared last in the file.
        self.field_types = (declared_types.collect_own(body) if body is not None
                            else {})
        self.enclosing_type = ".".join(
            class_properties.ClassPropertiesListener.findParents(ctx)
            + [ctx.IDENTIFIER().getText()])

    def exitClassDeclaration(self, ctx: JavaParserLabeled.ClassDeclarationContext):
        if self._scopes:
            self.enclosing_type, self.field_types = self._scopes.pop()

    def enterMethodDeclaration(self, ctx: JavaParserLabeled.MethodDeclarationContext):
        self.local_types = declared_types.collect(ctx)

    def enterConstructorDeclaration(self, ctx: JavaParserLabeled.ConstructorDeclarationContext):
        self.local_types = declared_types.collect(ctx)

    def enterImportDeclaration(self, ctx: JavaParserLabeled.ImportDeclarationContext):
        longname = ctx.qualifiedName().getText()
        on_demand = ctx.getText().rstrip(";").endswith(".*")
        if ctx.STATIC() is not None:
            if not on_demand:
                owner, _, member = longname.rpartition(".")
                if owner:
                    self.static_imports[member] = owner
            return
        if on_demand:
            self.wildcards.append(longname)
            return          # a package, not a type
        self.imports[longname.split(".")[-1]] = longname

    def declared_type(self, name):
        """Simple name of `name`'s declared type: a local first, then a field."""
        if not name:
            return None
        return self.local_types.get(name) or self.field_types.get(name)

    def chained_owner(self, ctx, scope_longname):
        """Type a receiver that is *itself a call* evaluates to, or None.

        `Double.valueOf(x).isNaN()` calls isNaN on whatever valueOf returns,
        and the JDK index records return types for exactly this. Understand
        reports 13 calls in JSONArrayTest.opt that this pass had nowhere to
        put, 11 of them this shape.

        A chain through a *project* method stays unresolved: the index covers
        java./javax. only, and inventing a target is the failure that took
        `Java Call` precision to 19%.
        """
        from openunderstand.oudb import jdk_index
        from openunderstand.ounderstand import symbol_table

        if ctx is None:
            return None
        created = self._created_type(ctx, scope_longname)
        if created:
            return created
        call = getattr(ctx, "methodCall", None)
        call = call() if callable(call) else None
        identifier = getattr(call, "IDENTIFIER", None) if call is not None else None
        identifier = identifier() if callable(identifier) else None
        if identifier is None:
            return None
        if type(ctx).__name__ != "Expression1Context":
            # `unescape(x.nextTo(';')).trim()` -- the inner call has no
            # receiver, so it is a method of the enclosing class. 595 of
            # JSON's calls chain off one of these.
            return (symbol_table.return_type(self.enclosing_type,
                                             identifier.getText(),
                                             scope_longname)
                    if self.enclosing_type else None)
        inner = ctx.expression()
        if inner is None or isinstance(inner, list):
            return None
        owner = self.owner_longname(inner.getText(), scope_longname, inner)
        if not owner:
            return None
        member = identifier.getText()
        # The JDK index covers java./javax. only; the symbol table answers for
        # the project's own methods, which is 1,598 of JSON's calls.
        return (jdk_index.return_type(owner, member)
                or symbol_table.return_type(owner, member, scope_longname))

    def binder(self, ctx):
        """The type table for this file, built from the tree `ctx` sits in."""
        if self._binder is None:
            from openunderstand.ounderstand.type_binding import TypeBinder

            root = ctx
            while root.parentCtx is not None:
                root = root.parentCtx
            self._binder = TypeBinder(root, self.file_address)
        return self._binder

    def _created_type(self, ctx, scope_longname):
        """Type of a `new X()` receiver -- `new JSONArray().put(x)`.

        Read off the tree, not the text: `getText()` gives `newJSONArray()`,
        which is indistinguishable from a call to a factory method actually
        named `newJSONArray`.
        """
        from openunderstand.ounderstand import symbol_table

        for child in (getattr(ctx, "children", None) or ()):
            if type(child).__name__.startswith("Creator"):
                name = getattr(child, "createdName", None)
                name = name() if callable(name) else None
                identifiers = name.IDENTIFIER() if name is not None else None
                if identifiers:
                    return symbol_table.resolve_type_name(
                        identifiers[-1].getText(), self.imports,
                        self.wildcards, scope_longname)
        return None

    def owner_longname(self, receiver, scope_longname, ctx=None):
        """Long name of the type a call on `receiver` lands on, or None.

        Four shapes, and only the first was handled before -- which is why
        1,197 of TheAlgorithms' 1,416 missing calls were to the JDK:

          sb.append(x)         a variable, so the call lands on its type
          Arrays.sort(a)       a *type*: a static call lands on the type itself
          System.out.println() a field, so the call lands on the field's type
          f(x).g()             a chain, so the call lands on f's return type

        A JDK type is as valid a target as a project one -- Understand reports
        `sb.append(...)` as java.lang.StringBuilder.append -- and a fully
        qualified JDK long name is safe to write, unlike a bare simple name
        that merge_placeholder_entities() would fold into any project match.
        """
        from openunderstand.ounderstand import symbol_table

        if not receiver:
            return None
        cast = _CAST.match(receiver)
        if cast:
            # `((Number)object).doubleValue()` -- the call lands on the type
            # the cast names, whatever the expression under it was. 584 of
            # JSON's calls, and every one had an unparseable receiver head.
            return symbol_table.resolve_type_name(
                cast.group(1).split(".")[-1], self.imports, self.wildcards,
                scope_longname)
        if receiver.endswith(".class"):
            return "java.lang.Class"
        if receiver.startswith('"') and receiver.endswith('"'):
            # `"".equals(x)` -- a literal receiver, and its type is not in
            # doubt. 263 calls on JSON, every one of them on a String.
            return "java.lang.String"
        head, _, field = receiver.partition(".")
        if not head.isidentifier():
            # `roundKeys[i - 1].remainder(...)` calls a method of the array's
            # *element*; the head is still a name this pass can resolve.
            indexed = head.split("[")[0]
            if "[" not in head or not indexed.isidentifier():
                # `unescape(x.nextTo(';')).trim()` -- the receiver is a call,
                # and the head is the front of its argument list rather than a
                # name. Returning here skipped the chain handler entirely.
                return self.chained_owner(ctx, scope_longname)
            head = indexed
        if field and not field.isidentifier():
            # A chained call is answerable when the JDK says what the inner
            # call returns. Anything else is still a guess and is refused.
            return self.chained_owner(ctx, scope_longname)

        if head == "this":
            # `this.myArrayList.size()` calls a method of the *field's* type,
            # and `this.parse()` one of the enclosing class. Neither resolved:
            # `this` is not a variable in scope, so this fell through to
            # reading it as a type name and gave up. JSONArray.length is
            # Understand's CountOutput 2 -- one call and a non-void return --
            # and was 1 for want of exactly this.
            if not self.enclosing_type:
                return None
            if not field:
                return self.enclosing_type
            declared = self.field_types.get(field)
            if declared:
                return symbol_table.resolve_type_name(
                    declared.split("[")[0], self.imports, self.wildcards,
                    scope_longname)
            # Not declared in this class: an inherited field, which only the
            # project-wide index can place.
            return symbol_table.member_type(self.enclosing_type, field)

        type_name = self.declared_type(head)
        if type_name:
            type_name = type_name.split("[")[0]
        owner = symbol_table.resolve_type_name(
            # No declared type means the receiver is not a variable in scope,
            # so read it as the type itself: `Math.abs(x)`, `Arrays.sort(a)`.
            type_name or head, self.imports, self.wildcards, scope_longname)
        if owner is None or not field:
            return owner
        # `System.out.println()` lands on the declared type of the *field*,
        # java.io.PrintStream, not on java.lang.System. member_type() answers
        # for a project field too, which a pass reading one file cannot.
        return symbol_table.member_type(owner, field)

    def _owner(self, receiver, scope_longname, receiver_ctx):
        """Type a call on this receiver lands on: the table, then the ladder."""
        if receiver_ctx is not None:
            try:
                resolved = self.binder(receiver_ctx).type_of(receiver_ctx)
            except Exception:
                resolved = None
            if resolved:
                return resolved
        return self.owner_longname(receiver, scope_longname, receiver_ctx)

    def enterMethodCall0(self, ctx: JavaParserLabeled.MethodCall0Context):
        identifier = ctx.IDENTIFIER()
        if identifier is None:
            return
        parent = ctx.parentCtx
        receiver = receiver_ctx = None
        # `a.b()` parses as expression1 with the call as its right-hand side;
        # a bare `b()` has no receiver and is therefore a call on `this`.
        if type(parent).__name__ == "Expression1Context":
            expression = parent.expression()
            if expression is not None and not isinstance(expression, list):
                receiver = expression.getText()
                # The context too: a chained receiver has to be walked, and
                # getText() has already thrown the structure away.
                receiver_ctx = expression
        scope_longname = ".".join(
            class_properties.ClassPropertiesListener.findParents(ctx))
        self.calls.append({
            "name": identifier.getText(),
            "receiver": receiver,
            # Declared type of the receiver, when the source states one. The
            # write layer needs it to place the call: without it a name is
            # resolved project-wide and `entry.getValue()` on a Map.Entry
            # became a call to org.json.CDL.getValue, the only getValue the
            # project declares.
            # A bare call may be a statically imported member rather than one
            # of the enclosing class's own.
            "owner_longname": (self._owner(receiver, scope_longname, receiver_ctx)
                               if receiver
                               else self.static_imports.get(identifier.getText())),
            "scope_longname": scope_longname,
            "line": identifier.symbol.line,
            "col": identifier.symbol.column,
        })
