#!/usr/bin/env python3
"""Build the speedy-antlr C++ accelerator for the Kotlin grammar.

Same recipe as ``../java8speedy/build.py`` (whose toolchain, C++ runtime and
compile step it reuses); only the grammar and the generated names differ.
The Kotlin grammar has no semantic predicates, so no Python-to-C++ rewrite.

    .venv/bin/python openunderstand/gen/kotlinspeedy/build.py

Output: ``sa_kotlin_cpp_parser<ext>`` next to this file, plus the Python-target
parser it was validated against in ``.build-cache/kotlin_py``. Entry rule:
``kotlinFile`` (``script`` for .kts).
"""

import importlib.util
import shutil
import sys
import sysconfig
from pathlib import Path

HERE = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location(
    "java_build", HERE.parent / "java8speedy" / "build.py"
)
jb = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(jb)

GRAMMARS = jb.REPO_ROOT / "grammars" / "kotlin"
MODULE = "sa_kotlin_cpp_parser"
SOURCES = [
    "KotlinLexer.cpp",
    "KotlinParser.cpp",
    "KotlinParserBaseVisitor.cpp",
    "KotlinParserVisitor.cpp",
    "sa_kotlin_translator.cpp",
    f"{MODULE}.cpp",
    "speedy_antlr.cpp",
]


def main() -> int:
    cache = jb.HERE / ".build-cache"  # share the jar and the built C++ runtime
    out_so = HERE / f"{MODULE}{sysconfig.get_config_var('EXT_SUFFIX') or '.so'}"
    work = HERE / ".build-work"
    shutil.rmtree(work, ignore_errors=True)
    cpp, py = work / "cpp", work / "py"
    cpp.mkdir(parents=True)
    py.mkdir()

    jar = jb.fetch(jb.ANTLR_JAR_URL, cache / f"antlr-{jb.ANTLR_VERSION}-complete.jar")
    inc, lib = jb.build_cpp_runtime(cache, 8)
    for lang, extra, out in (
        ("Cpp", ["-visitor", "-no-listener"], cpp),
        ("Python3", ["-no-visitor", "-no-listener"], py),
    ):
        for g in ("KotlinLexer.g4", "KotlinParser.g4"):
            shutil.copy(GRAMMARS / g, out)
        shutil.copy(GRAMMARS / "UnicodeClasses.g4", out)
        for g in ("KotlinLexer.g4", "KotlinParser.g4"):
            jb.run(
                ["java", "-jar", str(jar), f"-Dlanguage={lang}", *extra,
                 "-lib", str(out), "-o", str(out), g],
                cwd=out,
            )
    from speedy_antlr_tool import generate

    generate(py_parser_path=str(py / "KotlinParser.py"), cpp_output_dir=str(cpp))
    jb.CPP_SOURCES = SOURCES  # compile_extension reads this module global
    jb.compile_extension(cpp, inc, lib, out_so)
    print(f"built {out_so}")

    # validate: the C++ tree must equal the pure-Python tree on real files
    sys.path.insert(0, str(py))
    from antlr4 import CommonTokenStream, FileStream
    from KotlinLexer import KotlinLexer
    from KotlinParser import KotlinParser
    from speedy_antlr_tool.validate import validate_top_ctx

    spec = importlib.util.spec_from_file_location(MODULE, out_so)
    sa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sa)
    files = [Path(p) for p in sys.argv[1:]]
    for f in files:
        st = FileStream(str(f), encoding="utf8")
        want = KotlinParser(CommonTokenStream(KotlinLexer(st))).kotlinFile()
        got = sa.do_parse(KotlinParser, st, "kotlinFile", None)
        validate_top_ctx(want, got)
    print(f"validated {len(files)} file(s): C++ tree identical to Python tree")
    shutil.rmtree(work / "cpp", ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
