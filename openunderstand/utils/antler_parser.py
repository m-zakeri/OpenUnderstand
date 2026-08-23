"""Optional C++ parse accelerator.

Wraps the ``sa_javalabeled_cpp_parser`` extension built by
``openunderstand/gen/java8speedy/build.py``. The extension is not in version
control and may not be present; every entry point here degrades to the
pure-Python ANTLR parser instead of failing.

The accelerator is ~8x faster and produces a structurally identical parse tree,
so the analysis listeners walk it unchanged. That works because the generated
C++ translator resolves each parse-tree context class by name off the
``parser_cls`` argument at runtime -- and we hand it the real, listener-enabled
``gen.javaLabeled.JavaParserLabeled``. Passing the accelerator's own internal
parser class instead would build a tree whose contexts have no enterRule/
exitRule, and every listener would silently see nothing.
"""

from __future__ import annotations

import logging

from antlr4 import CommonTokenStream, InputStream
from antlr4.tree.Tree import ParseTree

from openunderstand.gen.javaLabeled.JavaLexer import JavaLexer
from openunderstand.gen.javaLabeled.JavaParserLabeled import JavaParserLabeled

logger = logging.getLogger(__name__)

try:
    from openunderstand.gen.java8speedy import sa_javalabeled_cpp_parser as _accelerator
except ImportError:  # not built -- expected, and fine
    _accelerator = None

_warned = False


def _memoise_get_text():
    """Make `ctx.getText()` remember its answer, once, for every parse tree.

    `getText()` concatenates every token beneath a node, so asking a class body
    for its text walks the class. The passes ask constantly -- an entity's
    `_contents` is the text of its declaration, and receiver resolution reads
    expression text -- and a build of the JSON benchmark makes **4.1 million**
    calls, re-deriving the same strings over and over. Caching them is 3.5s of
    a 14.9s per-file loop.

    Sound because a parse tree is immutable here: no pass rewrites a node, and
    the tree is rebuilt for each file, so the cache dies with it. Patched on
    `ParserRuleContext` rather than on each pass because every pass asks, and
    the C++ accelerator builds the same generated context classes.
    """
    from antlr4 import ParserRuleContext

    original = ParserRuleContext.getText
    if getattr(original, "_ou_memoised", False):
        return

    def get_text(self):
        try:
            return self._ou_text
        except AttributeError:
            text = original(self)
            self._ou_text = text
            return text

    get_text._ou_memoised = True
    ParserRuleContext.getText = get_text


_memoise_get_text()


def is_available() -> bool:
    return _accelerator is not None


def unavailable_reason() -> str:
    if _accelerator is not None:
        return ""
    return (
        "C++ accelerator not built; run "
        "`python openunderstand/gen/java8speedy/build.py`"
    )


def _py_parse(
    stream: InputStream, entry_rule_name: str = "compilationUnit"
) -> ParseTree:
    parser = JavaParserLabeled(CommonTokenStream(JavaLexer(stream)))
    return getattr(parser, entry_rule_name)()


def _cpp_parse(
    stream: InputStream,
    entry_rule_name: str = "compilationUnit",
    sa_err_listener=None,
    java_parser_labeld=JavaParserLabeled,
) -> ParseTree:
    """Parse with the C++ accelerator. Raises RuntimeError if it is missing.

    ``java_parser_labeld`` keeps its original (misspelled) name because
    project.py already calls it by keyword.
    """
    if _accelerator is None:
        raise RuntimeError(unavailable_reason())
    return _accelerator.do_parse(
        java_parser_labeld, stream, entry_rule_name, sa_err_listener
    )


def parse(
    stream: InputStream,
    entry_rule_name: str = "compilationUnit",
    prefer_cpp: bool = True,
    err_listener=None,
) -> ParseTree:
    """Parse, using the accelerator when it is available and wanted.

    Falls back to pure Python if the extension is missing, warning once so the
    fallback is visible in the log without flooding it -- this runs once per
    file per listener pass.
    """
    global _warned
    if prefer_cpp and _accelerator is not None:
        return _cpp_parse(stream, entry_rule_name, sa_err_listener=err_listener)
    if prefer_cpp and not _warned:
        _warned = True
        logger.warning("%s; falling back to the Python parser", unavailable_reason())
    parser = JavaParserLabeled(CommonTokenStream(JavaLexer(stream)))
    if err_listener is not None:
        parser.removeErrorListeners()
        parser.addErrorListener(err_listener)
    return getattr(parser, entry_rule_name)()
