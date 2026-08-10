"""Build Understand's entity-kind names from a declaration and its modifiers.

Understand encodes everything it knows about a declaration into the kind name:
``Java Static Final Generic Method Public Member``. The token order is fixed
and differs per category -- a constructor is ``Java Method Constructor Member
Public``, with the visibility last, while a method is ``Java Static Method
Public Member``. Getting the order wrong produces a name that is not in the
seeded vocabulary, so the two are checked against each other here rather than
discovered at runtime.

``resolve()`` returns the first candidate that the database actually has, which
is what lets this degrade gracefully: an unusual modifier combination falls back
to a less specific name instead of raising, and finally to the category's
``Unknown`` kind, which ``EntityModel.get_or_create`` treats as a placeholder
and upgrades in place when a better-informed pass comes along.
"""

from openunderstand.oudb.models import KindModel

# Declaration categories the define pass distinguishes.
PACKAGE = "package"
CLASS = "class"
INTERFACE = "interface"
ANNOTATION = "annotation"
ENUM = "enum"
ENUM_CONSTANT = "enum_constant"
METHOD = "method"
CONSTRUCTOR = "constructor"
LAMBDA = "lambda"
FIELD = "field"
CONSTANT = "constant"
LOCAL = "local"
PARAMETER = "parameter"
CATCH_PARAMETER = "catch_parameter"
TYPE_PARAMETER = "type_parameter"

_VISIBILITY = ("public", "protected", "private")

# What to fall back to when no specific name matches. These carry an "Unknown"
# token, which models.is_placeholder_kind() recognises.
_UNKNOWN = {
    CLASS: "Java Unknown Class Type Member",
    INTERFACE: "Java Unknown Class Type Member",
    ANNOTATION: "Java Unknown Annotation Interface Type Member",
    ENUM: "Java Unknown Class Type Member",
    METHOD: "Java Unknown Method Member",
    CONSTRUCTOR: "Java Unknown Method Member",
    LAMBDA: "Java Unknown Method Member",
    FIELD: "Java Unknown Variable Member",
    CONSTANT: "Java Unknown Variable Member",
    LOCAL: "Java Unknown Variable Member",
    ENUM_CONSTANT: "Java Unknown Variable Member",
    PARAMETER: "Java Unknown Variable Member",
    CATCH_PARAMETER: "Java Unknown Variable Member",
    TYPE_PARAMETER: "Java Unknown Class Type Member",
    PACKAGE: "Java Unknown Package",
}


def _visibility(modifiers):
    for m in _VISIBILITY:
        if m in modifiers:
            return m.capitalize()
    return "Default"


def _prefix(modifiers, *, allow_static=True, allow_abstract=True):
    """The ``[Static] [Abstract|Final] [Generic]`` run shared by methods and types."""
    out = []
    if allow_static and "static" in modifiers:
        out.append("Static")
    if allow_abstract and "abstract" in modifiers:
        out.append("Abstract")
    elif "final" in modifiers:
        out.append("Final")
    if "generic" in modifiers:
        out.append("Generic")
    return out


def candidates(decl, modifiers=(), name=""):
    """Kind names for a declaration, most specific first."""
    mods = {str(m).lower() for m in modifiers}
    vis = _visibility(mods)
    out = []

    if decl == PACKAGE:
        return ["Java Package"]

    if decl == TYPE_PARAMETER:
        return ["Java GenericParameter Type"]

    if decl == CATCH_PARAMETER:
        return ["Java Catch Parameter"]

    if decl == PARAMETER:
        if "final" in mods:
            out.append("Java Final Parameter")
        out.append("Java Parameter")
        return out

    if decl == ENUM_CONSTANT:
        return ["Java Variable EnumConstant Public Member"]

    if decl == LAMBDA:
        return ["Java Method Lambda"]

    if decl == CONSTRUCTOR:
        # Note the token order: visibility comes last for constructors.
        return [f"Java Method Constructor Member {vis}"]

    if decl == LOCAL:
        if "final" in mods:
            out.append("Java Final Variable Local")
        out.append("Java Variable Local")
        return out

    if decl in (FIELD, CONSTANT):
        # An interface constant is implicitly public static final.
        if decl == CONSTANT:
            mods |= {"public", "static", "final"}
            vis = "Public"
        prefix = _prefix(mods, allow_abstract=False)
        out.append(" ".join(["Java", *prefix, "Variable", vis, "Member"]))
        if prefix:
            out.append(f"Java Variable {vis} Member")
        return out

    if decl == METHOD:
        prefix = _prefix(mods)
        if name == "main" and "static" in mods and "public" in mods:
            out.append("Java Static Method Public Main Member")
        out.append(" ".join(["Java", *prefix, "Method", vis, "Member"]))
        # Progressively drop the least load-bearing tokens.
        for drop in ("Generic", "Abstract", "Final", "Static"):
            if drop in prefix:
                prefix = [p for p in prefix if p != drop]
                out.append(" ".join(["Java", *prefix, "Method", vis, "Member"]))
        return out

    if decl in (CLASS, ENUM):
        prefix = _prefix(mods)
        body = "Enum Class Type" if decl == ENUM else "Class Type"
        out.append(" ".join(["Java", *prefix, body, vis, "Member"]))
        for drop in ("Generic", "Abstract", "Final", "Static"):
            if drop in prefix:
                prefix = [p for p in prefix if p != drop]
                out.append(" ".join(["Java", *prefix, body, vis, "Member"]))
        if decl == ENUM:
            out.append(f"Java Class Type {vis} Member")
        return out

    if decl in (INTERFACE, ANNOTATION):
        # Interfaces have no "Member" token and cannot be final or abstract.
        body = "Annotation Interface Type" if decl == ANNOTATION else "Interface Type"
        generic = "Generic " if "generic" in mods else ""
        if generic and decl == INTERFACE:
            out.append(f"Java Generic {body} {vis}")
        out.append(f"Java {body} {vis}")
        return out

    return []


def resolve(decl, modifiers=(), name=""):
    """Id of the best seeded kind for this declaration.

    Returns ``None`` only when the category is unknown to this module, which
    the caller should treat as "leave the kind alone".
    """
    for candidate in candidates(decl, modifiers, name):
        row = KindModel.get_or_none(KindModel._name == candidate)
        if row is not None:
            return row._id
    # Never return None: _kind is NOT NULL, and a single unmapped declaration
    # category would abort the whole file's define pass inside the listener's
    # try/except, silently costing every later declaration in that file.
    fallback = _UNKNOWN.get(decl, "Java Unknown Class Type Member")
    row = KindModel.get_or_none(KindModel._name == fallback)
    return row._id if row is not None else None