"""Parse Kotlin with the grammar in ``grammars/kotlin``.

The counterpart of ``antler_parser`` for Kotlin: the speedy-antlr C++
accelerator (``sa_kotlin_cpp_parser``, built by ``gen/kotlinspeedy/build.py`` or
by ``setup.py``) when the installed package has one, the pure-Python ANTLR
runtime when it does not. Both give the same tree, and the tree is built from
the listener-enabled ``gen.kotlin.KotlinParser`` either way, so a pass written
against it sees the same contexts from both engines.

This is parsing only. Nothing here extracts entities, references or metrics:
the analysis pipeline still reads ``.java`` files alone (see ``is_kotlin``).

Entry rules: ``kotlinFile`` for ``.kt``, ``script`` for ``.kts``. The accelerator
raises ``RuntimeError`` on input it cannot parse into the entry rule, where the
Python parser reports through the error listener; ``parse`` normalises that, so
``errors`` is the one place to look.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

from antlr4 import CommonTokenStream, FileStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from antlr4.tree.Tree import ParseTree

# Importing this patches ParserRuleContext.getText to memoise, for every parser.
from openunderstand.utils import antler_parser  # noqa: F401
from openunderstand.gen.kotlin.KotlinLexer import KotlinLexer
from openunderstand.gen.kotlin.KotlinParser import KotlinParser

logger = logging.getLogger(__name__)

try:
    from openunderstand.gen.kotlinspeedy import sa_kotlin_cpp_parser as _accelerator
except ImportError:  # not built -- expected, and fine
    _accelerator = None

SUFFIXES = (".kt", ".kts")
_warned = False


def is_kotlin(path: str) -> bool:
    return str(path).lower().endswith(SUFFIXES)


def entry_rule(path: str) -> str:
    return "script" if str(path).lower().endswith(".kts") else "kotlinFile"


def is_available() -> bool:
    """Whether the C++ accelerator is installed."""
    return _accelerator is not None


def unavailable_reason() -> str:
    if _accelerator is not None:
        return ""
    return (
        "Kotlin C++ accelerator not built; run "
        "`python openunderstand/gen/kotlinspeedy/build.py`"
    )


class _Collect(ErrorListener):
    def __init__(self):
        self.messages: list[str] = []

    def syntaxError(self, *args):
        # Python runtime: (recognizer, symbol, line, column, msg, exc).
        # Accelerator:    (stream, token, <three ints>, msg) -- take the token's position.
        if isinstance(args[-1], str):
            token, msg = args[1], args[-1]
            line, column = (token.line, token.column) if token is not None else args[2:4]
        else:
            line, column, msg = args[2], args[3], args[4]
        self.messages.append(f"{line}:{column} {msg}")


@dataclass
class Result:
    tree: ParseTree | None
    errors: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return self.tree is not None and not self.errors


def parse(
    stream: InputStream,
    entry_rule_name: str = "kotlinFile",
    prefer_cpp: bool = True,
) -> Result:
    """Parse a stream. Never raises on bad input: look at ``Result.errors``."""
    global _warned
    errors = _Collect()
    if prefer_cpp and _accelerator is not None:
        try:
            tree = _accelerator.do_parse(KotlinParser, stream, entry_rule_name, errors)
            return Result(tree, errors.messages)
        except RuntimeError as exc:  # the accelerator's way of saying "syntax error"
            return Result(None, errors.messages or [str(exc)])
    if prefer_cpp and not _warned:
        _warned = True
        logger.warning("%s; falling back to the Python parser", unavailable_reason())
    lexer = KotlinLexer(stream)
    lexer.removeErrorListeners()
    lexer.addErrorListener(errors)
    parser = KotlinParser(CommonTokenStream(lexer))
    parser.removeErrorListeners()
    parser.addErrorListener(errors)
    tree = getattr(parser, entry_rule_name)()
    return Result(tree, errors.messages)


def parse_text(text: str, script: bool = False, prefer_cpp: bool = True) -> Result:
    return parse(InputStream(text), "script" if script else "kotlinFile", prefer_cpp)


def parse_file(path: str, prefer_cpp: bool = True) -> Result:
    """Parse a ``.kt`` or ``.kts`` file, choosing the entry rule from the name."""
    return parse(
        FileStream(os.fspath(path), encoding="utf-8"), entry_rule(path), prefer_cpp
    )
