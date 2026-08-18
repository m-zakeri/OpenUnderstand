"""Resolved type of every expression in a file, computed once.

Five passes needed the same fact -- *what type is this expression* -- and each
derived it its own way. `method_calls.owner_longname`, `field_uses._owner` and
`declared_types.collect` were three separate answers to it, and the same defect
lived in two of them at once: a nested class's scope assigned on entry and
never restored, so `this.refTokens` in `JSONPointer.queryFrom` resolved to
`JSONPointer.Builder.refTokens`, a field of the inner class that happens to
share the name. `couple_coupleby` had a fourth answer that ended in an
unconditional `"java.lang." + name` and so reported `java.lang.Map`.

This is the one answer. It reads scopes off the parse tree by walking *up* from
the asking node, which is what Java scoping actually is -- no listener state to
forget to restore, so that whole class of bug cannot be written.

    binder = TypeBinder(tree, path)
    binder.type_of(expression_ctx)       # -> "java.util.ArrayList" | None
    binder.enclosing_type(any_ctx)       # -> "org.json.JSONArray" | None

None means *unknown*, and it is never a guess: a wrong type silently
misattributes every reference built on it, and writing a bare simple name is
what `merge_placeholder_entities()` folds into whichever project entity happens
to share it -- the failure that took `Java Call` precision to 19%.

What it does not do: generics (`List<String>.get` is an Object here), array
element types beyond stripping the brackets, and the flow-sensitive narrowing
of `instanceof`. Understand does not appear to need any of the three for the
references it records.
"""

from openunderstand.analysis_passes import class_properties

#: Contexts that open a scope holding declarations.
_SCOPE = ("MethodDeclaration", "ConstructorDeclaration",
          "GenericMethodDeclaration", "GenericConstructorDeclaration",
          "InterfaceMethodDeclaration", "LambdaExpression", "Block",
          "CatchClause", "Statement3", "Statement6", "Statement7")

#: Contexts that declare a type.
_TYPE_DECLARATION = ("ClassDeclaration", "InterfaceDeclaration",
                     "EnumDeclaration", "AnnotationTypeDeclaration")

#: A literal's type. A `null` literal has none, and the primitives cannot be
#: called on, so only the two that can be receivers are named.
_LITERAL_TYPES = {
    "Literal3Context": "java.lang.String",
    "Literal2Context": "java.lang.Character",
}


def _kids(ctx, prefix):
    return [c for c in (getattr(ctx, "children", None) or ())
            if type(c).__name__.startswith(prefix)]


def _common_prefix(a, b):
    """The dotted prefix two long names share, as a string."""
    left, right = a.split("."), b.split(".")
    shared = []
    for one, other in zip(left, right):
        if one != other:
            break
        shared.append(one)
    return ".".join(shared)


def _written_name(ctx):
    """The type a `typeType`/`classOrInterfaceType` node names, unadorned."""
    if ctx is None:
        return None
    text = ctx.getText().split("<")[0].split("[")[0]
    return text or None


class TypeBinder:
    """Types for one file's expressions. Build once per parsed file."""

    def __init__(self, tree, file_path=""):
        self.tree = tree
        self.file_path = file_path
        self.imports, self.wildcards = self._read_imports(tree)
        self._type_of = {}
        self._scope_names = {}
        self._fields = {}
        self._returns = {}
        self._enclosing = {}
        self._declared = None

    # ------------------------------------------------------------- imports

    @staticmethod
    def _read_imports(tree):
        imports, wildcards = {}, []
        stack = [tree]
        while stack:
            node = stack.pop()
            if type(node).__name__.startswith("ImportDeclaration"):
                qualified = node.qualifiedName()
                if qualified is None:
                    continue
                longname = qualified.getText()
                if node.getText().rstrip(";").endswith(".*"):
                    if node.STATIC() is None:
                        wildcards.append(longname)
                elif node.STATIC() is None:
                    imports[longname.split(".")[-1]] = longname
                continue
            stack.extend(c for c in (getattr(node, "children", None) or ())
                         if hasattr(c, "getRuleIndex"))
        return imports, wildcards

    def _resolve(self, written, scope_longname):
        """Long name for a type as written here, or None.

        This file's own declarations come first: a type declared in the same
        compilation unit is always in scope, and `resolve_type_name` can only
        see it once `symbol_table.build()` has run over the whole project --
        which is not true while a single file is being parsed, and not true at
        all in a test.
        """
        from openunderstand.ounderstand import symbol_table

        if not written:
            return None
        written = written.split("<")[0].split("[")[0]
        local = self._local_type(written, scope_longname)
        if local:
            return local
        return symbol_table.resolve_type_name(
            written, self.imports, self.wildcards, scope_longname or "")

    def _local_type(self, simple, scope_longname):
        """A type declared in this file, innermost enclosing scope first."""
        if not simple or "." in simple:
            return None
        candidates = [longname for longname in self._declared_types()
                      if longname.rsplit(".", 1)[-1] == simple]
        if not candidates:
            return None
        scope = scope_longname or ""
        # `Builder` inside JSONPointer means JSONPointer.Builder, not another
        # class of that name elsewhere in the file.
        return max(candidates,
                   key=lambda name: len(_common_prefix(name, scope)))

    # -------------------------------------------------------------- scopes

    def enclosing_type(self, ctx):
        """Long name of the type declaration `ctx` sits inside, or None."""
        key = id(ctx)
        if key in self._enclosing:
            return self._enclosing[key]
        node = ctx
        answer = None
        while node is not None:
            if type(node).__name__.startswith(_TYPE_DECLARATION):
                identifier = getattr(node, "IDENTIFIER", None)
                identifier = identifier() if callable(identifier) else None
                if identifier is not None and not isinstance(identifier, list):
                    parents = class_properties.ClassPropertiesListener.findParents(node)
                    answer = ".".join(parents + [identifier.getText()])
                break
            node = node.parentCtx
        self._enclosing[key] = answer
        return answer

    def _own_fields(self, type_ctx):
        """`{name: written type}` for a type's own fields, not a nested one's."""
        key = id(type_ctx)
        if key in self._fields:
            return self._fields[key]
        found = {}
        stack = [type_ctx]
        first = True
        while stack:
            node = stack.pop()
            name = type(node).__name__
            if not first and name.startswith(_TYPE_DECLARATION):
                continue                    # a nested type declares its own
            first = False
            if name.startswith("FieldDeclaration"):
                written = _written_name(node.typeType())
                declarators = node.variableDeclarators()
                for declarator in (declarators.variableDeclarator()
                                   if declarators is not None else []):
                    identifier = declarator.variableDeclaratorId()
                    if identifier is not None:
                        found[identifier.getText().split("[")[0]] = written
                continue
            if name.startswith(("MethodBody", "ConstructorBody")):
                continue                    # a body declares locals, not fields
            stack.extend(c for c in (getattr(node, "children", None) or ())
                         if hasattr(c, "getRuleIndex"))
        self._fields[key] = found
        return found

    def _declared_in(self, scope_ctx):
        """`{name: written type}` declared directly by one scope node."""
        from openunderstand.analysis_passes import declared_types

        key = id(scope_ctx)
        cached = self._scope_names
        if key in cached:
            return cached[key]
        found = declared_types.collect_own(scope_ctx)
        cached[key] = found
        return found

    def name_type(self, name, ctx):
        """Written type of a simple name visible at `ctx`, or None.

        Walks outwards: the block, then the method, then the enclosing types'
        own fields. That *is* Java's scoping rule, and it needs no listener to
        remember which class it is in.
        """
        node = ctx
        while node is not None:
            kind = type(node).__name__
            if kind.startswith(_SCOPE):
                declared = self._declared_in(node).get(name)
                if declared:
                    return declared
            elif kind.startswith(_TYPE_DECLARATION):
                declared = self._own_fields(node).get(name)
                if declared:
                    return declared
            node = node.parentCtx
        return None

    def _declared_types(self):
        """`{long name: declaration ctx}` for every type this file declares."""
        if self._declared is not None:
            return self._declared
        found = {}
        stack = [self.tree]
        while stack:
            node = stack.pop()
            if type(node).__name__.startswith(_TYPE_DECLARATION):
                identifier = getattr(node, "IDENTIFIER", None)
                identifier = identifier() if callable(identifier) else None
                if identifier is not None and not isinstance(identifier, list):
                    parents = class_properties.ClassPropertiesListener.findParents(node)
                    found[".".join(parents + [identifier.getText()])] = node
            stack.extend(c for c in (getattr(node, "children", None) or ())
                         if hasattr(c, "getRuleIndex"))
        self._declared = found
        return found

    def member_type(self, owner, member):
        """Type of `owner.member`, preferring this file's own declarations."""
        from openunderstand.oudb import jdk_index
        from openunderstand.ounderstand import symbol_table

        if not owner or not member:
            return None
        node = self._declared_types().get(owner)
        if node is not None:
            written = self._own_fields(node).get(member)
            if written:
                return self._resolve(written, owner)
        return (symbol_table.member_type(owner, member)
                or jdk_index.field_type(owner, member))

    def return_type(self, owner, member):
        """Type `owner.member(...)` evaluates to, preferring this file."""
        from openunderstand.oudb import jdk_index
        from openunderstand.ounderstand import symbol_table

        if not owner or not member:
            return None
        node = self._declared_types().get(owner)
        if node is not None:
            written = self._own_returns(node).get(member)
            if written:
                return self._resolve(written, owner)
        return (jdk_index.return_type(owner, member)
                or symbol_table.return_type(owner, member, owner))

    def _own_returns(self, type_ctx):
        """`{method name: written return type}` for a type's own methods.

        Overloads that disagree are dropped: a name with two return types
        cannot place a call, and guessing is what a wrong target costs.
        """
        key = id(type_ctx)
        if key in self._returns:
            return self._returns[key]
        found = {}
        stack, first = [type_ctx], True
        while stack:
            node = stack.pop()
            name = type(node).__name__
            if not first and name.startswith(_TYPE_DECLARATION):
                continue
            first = False
            if name.startswith(("MethodDeclaration", "InterfaceMethodDeclaration")):
                identifier = node.IDENTIFIER()
                declared = getattr(node, "typeTypeOrVoid", None)
                declared = declared() if callable(declared) else None
                written = _written_name(declared)
                if (identifier is not None and not isinstance(identifier, list)
                        and written and written != "void"):
                    member = identifier.getText()
                    found[member] = (written if found.get(member, written) == written
                                     else "")
            stack.extend(c for c in (getattr(node, "children", None) or ())
                         if hasattr(c, "getRuleIndex"))
        found = {k: v for k, v in found.items() if v}
        self._returns[key] = found
        return found

    def _superclass(self, longname):
        from openunderstand.ounderstand import symbol_table

        for written in symbol_table.INDEX.supertypes.get(longname, ()):
            resolved = self._resolve(written, longname)
            if resolved:
                return resolved
        return None

    # --------------------------------------------------------- expressions

    def type_of(self, ctx):
        """Long name of the type `ctx` evaluates to, or None when unknown."""
        if ctx is None:
            return None
        key = id(ctx)
        if key in self._type_of:
            return self._type_of[key]
        self._type_of[key] = None           # break cycles while computing
        answer = self._compute(ctx)
        self._type_of[key] = answer
        return answer

    def _compute(self, ctx):
        from openunderstand.oudb import jdk_index
        from openunderstand.ounderstand import symbol_table

        name = type(ctx).__name__
        scope = self.enclosing_type(ctx)

        if name in _LITERAL_TYPES:
            return _LITERAL_TYPES[name]
        if name.startswith("Literal"):
            return None                     # a number, a boolean, null
        if name == "Expression0Context":
            return self.type_of(ctx.primary())
        if name == "Primary0Context":       # ( expression )
            return self.type_of(ctx.expression())
        if name == "Primary1Context":       # this
            return scope
        if name == "Primary2Context":       # super
            return self._superclass(scope) if scope else None
        if name == "Primary3Context":       # a literal
            return self.type_of(ctx.literal())
        if name == "Primary5Context":       # X.class
            return "java.lang.Class"
        if name == "Primary4Context":       # a bare name
            identifier = ctx.IDENTIFIER().getText()
            written = self.name_type(identifier, ctx)
            if written:
                return self._resolve(written, scope)
            # Not a variable in scope, so the name is a type: `Math.abs(x)`.
            return self._resolve(identifier, scope)

        if name == "Expression5Context":    # ( T ) x
            return self._resolve(_written_name(ctx.typeType()), scope)
        if name == "Expression4Context":    # new T(...)
            return self._created(ctx, scope)
        if name == "Expression2Context":    # a[i] -- the element type
            inner = ctx.expression()
            return self.type_of(inner[0] if isinstance(inner, list) else inner)
        if name == "Expression3Context":    # f(...) with no receiver
            call = ctx.methodCall()
            member = self._call_name(call)
            if not member:
                return None
            owner = symbol_table.INDEX.declaring_type(scope, member) or scope
            return self.return_type(owner, member)
        if name == "Expression1Context":    # a.b, a.f(), a.this, a.new
            receiver = ctx.expression()
            if isinstance(receiver, list):
                receiver = receiver[0] if receiver else None
            owner = self.type_of(receiver)
            call = getattr(ctx, "methodCall", None)
            call = call() if callable(call) else None
            if call is not None:
                member = self._call_name(call)
                if not owner or not member:
                    return None
                return self.return_type(owner, member)
            identifier = ctx.IDENTIFIER()
            if identifier is not None and not isinstance(identifier, list):
                if not owner:
                    return None
                return self.member_type(owner, identifier.getText())
            return None

        if name in ("Expression6Context", "Expression7Context",
                    "Expression8Context", "Expression21Context"):
            inner = ctx.expression()
            return self.type_of(inner[0] if isinstance(inner, list) else inner)
        if name == "Expression20Context":   # a ? b : c
            branches = ctx.expression()
            for branch in (branches[1:] if isinstance(branches, list) else []):
                found = self.type_of(branch)
                if found:
                    return found
            return None
        # Arithmetic, comparison, instanceof, lambdas and method references
        # all yield something that cannot be a receiver here.
        return None

    @staticmethod
    def _call_name(call):
        identifier = getattr(call, "IDENTIFIER", None) if call is not None else None
        identifier = identifier() if callable(identifier) else None
        if identifier is None or isinstance(identifier, list):
            return None
        return identifier.getText()

    def _created(self, ctx, scope):
        creator = ctx.creator()
        if creator is None:
            return None
        created = getattr(creator, "createdName", None)
        created = created() if callable(created) else None
        identifiers = getattr(created, "IDENTIFIER", None) if created else None
        identifiers = identifiers() if callable(identifiers) else None
        if not identifiers:
            return None
        if isinstance(identifiers, list):
            written = ".".join(i.getText() for i in identifiers)
        else:
            written = identifiers.getText()
        return self._resolve(written.split(".")[-1] if "." not in written
                             else written, scope)


def demo():
    """Each expression shape, against the type it must resolve to."""
    from antlr4 import CommonTokenStream, InputStream

    from openunderstand.gen.javaLabeled.JavaLexer import JavaLexer
    from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled

    source = """
package org.json;

import java.util.ArrayList;

public class Outer {
    private final ArrayList<Object> items = new ArrayList<Object>();
    private String label;

    public Outer self() { return this; }

    public void shapes(Object value, int index) {
        this.items.size();
        this.label.trim();
        items.get(index);
        label.trim();
        ((Number) value).intValue();
        "".equals(label);
        new Outer().self().self();
        self().self();
        Outer.class.getName();
        value.getClass().getName();
        items.get(index).toString();
    }

    class Inner {
        private final String items = "";
        void peek() { this.items.trim(); }
    }
}
"""
    tree = JavaParserLabeled(
        CommonTokenStream(JavaLexer(InputStream(source)))).compilationUnit()
    binder = TypeBinder(tree, "Outer.java")

    # Collect every expression that is the receiver of a `.something`.
    found = {}
    stack = [tree]
    while stack:
        node = stack.pop()
        if type(node).__name__ == "Expression1Context":
            receiver = node.expression()
            if isinstance(receiver, list):
                receiver = receiver[0] if receiver else None
            if receiver is not None:
                # Keyed by the class too: `this.items` occurs in both Outer
                # and Inner and means a different field in each, which is the
                # whole point of the scope walk.
                key = (binder.enclosing_type(receiver), receiver.getText())
                found.setdefault(key, binder.type_of(receiver))
        stack.extend(c for c in (getattr(node, "children", None) or ())
                     if hasattr(c, "getRuleIndex"))

    OUTER, INNER = "org.json.Outer", "org.json.Outer.Inner"
    expected = {
        # The same text, a different field, because they are in different
        # classes. This is what the old listener-state passes got wrong.
        (OUTER, "this.items"): "java.util.ArrayList",
        (INNER, "this.items"): "java.lang.String",
        (OUTER, "this.label"): "java.lang.String",
        (OUTER, "items"): "java.util.ArrayList",
        (OUTER, "label"): "java.lang.String",
        (OUTER, "((Number)value)"): "java.lang.Number",
        (OUTER, '""'): "java.lang.String",
        (OUTER, "newOuter()"): "org.json.Outer",
        (OUTER, "newOuter().self()"): "org.json.Outer",
        (OUTER, "self()"): "org.json.Outer",
        (OUTER, "Outer.class"): "java.lang.Class",
        (OUTER, "value.getClass()"): "java.lang.Class",
        (OUTER, "this"): "org.json.Outer",
        (INNER, "this"): "org.json.Outer.Inner",
    }
    for text, want in expected.items():
        got = found.get(text, "MISSING")
        assert got == want, f"{text}: {got!r} != {want!r}"
    print(f"type_binding: {len(expected)} shapes ok")


if __name__ == "__main__":
    demo()
