"""CyclomaticStrict -- Cyclomatic, counting each `&&` and `||` as a decision.

Understand's own numbers say the two differ by exactly that and nothing else.
On a hand-written fixture of 31 methods, `ifAnd` is Cyclomatic 2 / Strict 3 and
`ifAndOr` is 2 / 4, and a `&&` in a plain declaration -- `boolean b = x > 0 &&
x < 5;` -- lifts 1 to 2 with no statement involved. On JSON's three worst
disagreements the sum lands exactly: JSONTokener.nextSimpleValue is 12 + 9 = 21,
CDL.getValue 10 + 4 = 14, JSONArray.isSimilar 10 + 2 = 12.

This replaces a listener that counted the operators only inside a
`blockStatement`, and only while a flag set by `enterClassDeclaration` matching
a class name it was never given happened to be true.
"""

from openunderstand.metrics import context
from openunderstand.metrics.cyclomatic import cyclomatic, get_method_ctx

#: `expression bop='&&' expression` and its `||` twin.
_SHORT_CIRCUIT = ("Expression18Context", "Expression19Context")


def _short_circuits(ent_model):
    """`&&` and `||` in the entity's own body, not in one nested inside it.

    A lambda or an anonymous class declared in a method is an entity in its own
    right and carries its own complexity, which is the same rule
    `cyclomatic()` applies to the decision points.
    """
    tree = context.parse_entity(ent_model.contents() or "")
    outermost = _outermost_declaration(tree)
    total = 0
    stack = [tree]
    while stack:
        node = stack.pop()
        if type(node).__name__ in _SHORT_CIRCUIT:
            if get_method_ctx(node) in (outermost, None):
                total += 1
        stack.extend(c for c in (getattr(node, "children", None) or ())
                     if hasattr(c, "getRuleIndex"))
    return total


def _outermost_declaration(tree):
    """The method or constructor declaration the parsed source is, or None."""
    stack, found = [tree], None
    while stack:
        node = stack.pop()
        if type(node).__name__ in (
                "MethodDeclarationContext", "ConstructorDeclarationContext",
                "GenericMethodDeclarationContext",
                "GenericConstructorDeclarationContext"):
            if found is None or node.start.start < found.start.start:
                found = node
        stack.extend(c for c in (getattr(node, "children", None) or ())
                     if hasattr(c, "getRuleIndex"))
    return found


def cyclomatic_strict(ent_model):
    if ent_model is None:
        return 0
    if context.declares_without_body(ent_model):
        return 0
    return cyclomatic(ent_model) + _short_circuits(ent_model)
