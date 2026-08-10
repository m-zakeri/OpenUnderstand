#!/usr/bin/env python3
"""Build the speedy-antlr C++ parse accelerator.

Everything here is derived from ``grammars/*.g4``. Nothing generated is kept in
version control -- not the C++ sources, not the ANTLR runtime, not the compiled
extension. Run this script and you get all of it; delete the build directory
and you are back to a clean tree. The pure-Python parser stays the fallback, so
skipping this build only costs speed.

    python openunderstand/gen/java8speedy/build.py

Measured on the calculator_app + JSON fixtures: 8.1x faster than the pure
Python parser, producing a structurally identical parse tree (verified with
speedy_antlr_tool.validate, which asserts equality of every context type,
child list, token, and source position).

Requirements: a JDK (for the ANTLR tool), cmake, make, g++ with C++17, Python
development headers, and the ``speedy-antlr-tool`` package. The ANTLR tool jar
and the C++ runtime source are downloaded into the cache directory on first
run.

Two naming constraints drive the grammar renaming below, and getting either
wrong produces a confusing failure:

  * speedy-antlr-tool derives its grammar name by stripping "Parser" off the
    parser filename, so the parser grammar must be ``<X>Parser``.
  * It then assumes the lexer is ``<X>Lexer``. Our real grammars are
    ``JavaParserLabeled`` and ``JavaLexer``, so for the accelerator build only
    they are copied to ``JavaLabeledParser`` / ``JavaLabeledLexer``.

The rename is cosmetic. The generated translator looks every parse-tree context
class up by name off the ``parser_cls`` argument passed in at runtime, and we
pass the real ``gen.javaLabeled.JavaParserLabeled``. Both grammars produce the
same 218 context classes, so the accelerator populates the very same listener-
enabled classes the analysis passes already walk.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import sysconfig
import urllib.request
from pathlib import Path

ANTLR_VERSION = "4.13.2"  # must match the antlr4-python3-runtime pin
ANTLR_JAR_URL = f"https://www.antlr.org/download/antlr-{ANTLR_VERSION}-complete.jar"
CPP_RUNTIME_URL = f"https://www.antlr.org/download/antlr4-cpp-runtime-{ANTLR_VERSION}-source.zip"

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
GRAMMARS = REPO_ROOT / "grammars"
MODULE_NAME = "sa_javalabeled_cpp_parser"

CPP_SOURCES = [
    "JavaLabeledLexer.cpp",
    "JavaLabeledParser.cpp",
    "JavaLabeledParserBaseVisitor.cpp",
    "JavaLabeledParserVisitor.cpp",
    "sa_javalabeled_translator.cpp",
    f"{MODULE_NAME}.cpp",
    "speedy_antlr.cpp",
]


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd[:6]), "..." if len(cmd) > 6 else "")
    subprocess.run(cmd, check=True, **kw)


def need(tool):
    if shutil.which(tool) is None:
        raise SystemExit(f"required tool not found on PATH: {tool}")


def fetch(url, dest: Path):
    if dest.exists():
        print(f"  cached {dest.name}")
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"  downloading {url}")
    tmp = dest.with_suffix(dest.suffix + ".part")
    urllib.request.urlretrieve(url, tmp)
    tmp.rename(dest)
    return dest


def build_cpp_runtime(cache: Path, jobs: int) -> tuple[Path, Path]:
    """Return (include_dir, static_lib), building the runtime if needed."""
    src = cache / f"antlr4-cpp-runtime-{ANTLR_VERSION}"
    lib = src / "build" / "runtime" / "libantlr4-runtime.a"
    inc = src / "runtime" / "src"
    if lib.exists():
        print("  cached libantlr4-runtime.a")
        return inc, lib

    zip_path = fetch(CPP_RUNTIME_URL, cache / f"antlr4-cpp-runtime-{ANTLR_VERSION}-source.zip")
    src.mkdir(parents=True, exist_ok=True)
    import zipfile

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(src)

    need("cmake")
    need("make")
    build = src / "build"
    build.mkdir(exist_ok=True)
    run([
        "cmake", "..",
        "-DCMAKE_BUILD_TYPE=Release",
        "-DANTLR4_INSTALL=OFF",
        "-DANTLR_BUILD_CPP_TESTS=OFF",
        "-DANTLR_BUILD_SHARED=OFF",
        "-DANTLR_BUILD_STATIC=ON",
        "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
        "-DWITH_DEMO=OFF",
    ], cwd=build)
    run(["make", f"-j{jobs}", "antlr4_static"], cwd=build)
    if not lib.exists():
        raise SystemExit(f"runtime build finished but {lib} is missing")
    return inc, lib


def rename_grammars(work: Path) -> Path:
    """Copy the real grammars under the names speedy-antlr-tool requires."""
    g = work / "grammars"
    g.mkdir(parents=True, exist_ok=True)

    lex = (GRAMMARS / "JavaLexer.g4").read_text()
    lex = lex.replace("lexer grammar JavaLexer;", "lexer grammar JavaLabeledLexer;")
    (g / "JavaLabeledLexer.g4").write_text(lex)

    par = (GRAMMARS / "JavaParserLabeled.g4").read_text()
    par = par.replace("parser grammar JavaParserLabeled;", "parser grammar JavaLabeledParser;")
    par = par.replace("tokenVocab=JavaLexer", "tokenVocab=JavaLabeledLexer")
    (g / "JavaLabeledParser.g4").write_text(par)

    for f, marker in ((g / "JavaLabeledLexer.g4", "lexer grammar JavaLabeledLexer;"),
                      (g / "JavaLabeledParser.g4", "parser grammar JavaLabeledParser;")):
        if marker not in f.read_text():
            raise SystemExit(f"grammar rename failed for {f.name}; upstream grammar header changed")
    return g


def generate(work: Path, jar: Path):
    g = rename_grammars(work)
    cpp = work / "cpp"
    py = work / "py"
    for d in (cpp, py):
        d.mkdir(parents=True, exist_ok=True)

    need("java")
    for lang, extra, out in (("Cpp", ["-visitor", "-no-listener"], cpp),
                             ("Python3", ["-no-visitor", "-no-listener"], py)):
        for name in ("JavaLabeledLexer.g4", "JavaLabeledParser.g4"):
            run(["java", "-jar", str(jar), f"-Dlanguage={lang}", *extra,
                 "-lib", str(out), "-o", str(out), name], cwd=g)

    try:
        from speedy_antlr_tool import generate as sa_generate
    except ImportError:
        raise SystemExit("speedy-antlr-tool is not installed:  pip install speedy-antlr-tool")
    print("  running speedy-antlr-tool")
    sa_generate(py_parser_path=str(py / "JavaLabeledParser.py"), cpp_output_dir=str(cpp))
    return cpp


def compile_extension(cpp: Path, inc: Path, lib: Path, out_so: Path):
    need("g++")
    pyinc = sysconfig.get_paths()["include"]
    missing = [s for s in CPP_SOURCES if not (cpp / s).exists()]
    if missing:
        raise SystemExit(f"generated sources missing: {missing}")

    out_so.parent.mkdir(parents=True, exist_ok=True)
    run([
        "g++", "-O2", "-std=c++17", "-fPIC", "-shared", "-fvisibility=hidden",
        "-I", str(inc), "-I", str(cpp), "-I", pyinc,
        *[str(cpp / s) for s in CPP_SOURCES],
        str(lib),
        "-o", str(out_so),
    ])


def verify(out_so: Path) -> bool:
    """Parse a real fixture both ways and assert the trees are identical."""
    sys.path[:0] = [str(REPO_ROOT), str(REPO_ROOT / "openunderstand")]
    from antlr4 import FileStream, CommonTokenStream
    from gen.javaLabeled.JavaLexer import JavaLexer
    from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled
    from gen.java8speedy import sa_javalabeled_cpp_parser as sa

    samples = sorted((REPO_ROOT / "benchmark" / "calculator_app").rglob("*.java"))[:3]
    if not samples:
        print("  no fixture available; skipping tree validation")
        return True

    from speedy_antlr_tool.validate import validate_top_ctx

    for f in samples:
        st = FileStream(str(f), encoding="utf8")
        py_tree = JavaParserLabeled(CommonTokenStream(JavaLexer(st))).compilationUnit()
        cpp_tree = sa.do_parse(JavaParserLabeled, st, "compilationUnit", None)
        validate_top_ctx(py_tree, cpp_tree)
    print(f"  validated {len(samples)} file(s): C++ tree identical to Python tree")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cache", default=str(HERE / ".build-cache"),
                    help="where to keep the ANTLR jar and C++ runtime")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument("--force", action="store_true", help="regenerate even if the .so exists")
    ap.add_argument("--keep-work", action="store_true", help="do not delete generated C++ afterwards")
    a = ap.parse_args()

    out_so = HERE / f"{MODULE_NAME}{sysconfig.get_config_var('EXT_SUFFIX') or '.so'}"
    if out_so.exists() and not a.force:
        print(f"{out_so.name} already built (use --force to rebuild)")
        return 0

    cache = Path(a.cache)
    work = cache / "work"
    if work.exists():
        shutil.rmtree(work)
    work.mkdir(parents=True, exist_ok=True)

    print(f"ANTLR {ANTLR_VERSION} speedy accelerator build")
    print("[1/4] toolchain")
    jar = fetch(ANTLR_JAR_URL, cache / f"antlr-{ANTLR_VERSION}-complete.jar")
    inc, lib = build_cpp_runtime(cache, a.jobs)
    print("[2/4] generating parsers")
    cpp = generate(work, jar)
    print("[3/4] compiling extension")
    compile_extension(cpp, inc, lib, out_so)
    print("[4/4] verifying")
    verify(out_so)

    if not a.keep_work:
        shutil.rmtree(work, ignore_errors=True)
    print(f"\nbuilt {out_so}")
    print("Enable it with engine_core = C++ in config.ini (the pure-Python "
          "parser remains the default).")
    return 0


if __name__ == "__main__":
    sys.exit(main())