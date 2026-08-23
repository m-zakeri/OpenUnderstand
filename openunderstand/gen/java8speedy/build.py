#!/usr/bin/env python3
"""Build the speedy-antlr C++ parse accelerator.

Everything here is derived from ``grammars/*.g4``. Nothing generated is kept in
version control -- not the C++ sources, not the ANTLR runtime, not the compiled
extension. Run this script and you get all of it; delete the build directory
and you are back to a clean tree. The pure-Python parser stays the fallback, so
skipping this build only costs speed.

    python openunderstand/gen/java8speedy/build.py

Measured on benchmark/JSON's 85 files: 7.8x faster at parsing (2.53s against
19.72s) and about 17% off a full analysis (187.4s against 225.8s), producing a
structurally identical parse tree -- verified with speedy_antlr_tool.validate,
which asserts equality of every context type, child list, token and source
position, and confirmed by both engines reaching the same database
fingerprint.

``setup.py`` calls the functions below to build the extension into a wheel, so
this is the single recipe rather than one that drifts from the packaging.

Requirements: a JDK (for the ANTLR tool), cmake, a C++17 compiler, Python
development headers, and the ``speedy-antlr-tool`` package. The compiler is
whichever one Python was built with -- setuptools' abstraction picks it, which
is what makes MSVC work without a separate code path. The ANTLR tool jar and
the C++ runtime source are downloaded into the cache directory on first run.

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
CPP_RUNTIME_URL = (
    f"https://www.antlr.org/download/antlr4-cpp-runtime-{ANTLR_VERSION}-source.zip"
)

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


def _static_lib(build: Path) -> Path | None:
    """The runtime's static library, wherever this generator put it.

    Makefile generators write ``runtime/libantlr4-runtime.a``; the Visual
    Studio generator writes ``runtime/Release/antlr4-runtime-static.lib``, and
    Ninja on Windows drops the same name without the config directory. Search
    rather than assume, so a generator change surfaces as "not found" instead
    of linking something stale.
    """
    for pattern in (
        "runtime/libantlr4-runtime.a",
        "runtime/**/antlr4-runtime-static.lib",
        "runtime/**/libantlr4-runtime.a",
    ):
        hits = sorted(build.glob(pattern))
        if hits:
            return hits[0]
    return None


def patch_runtime_sources(src: Path) -> None:
    """Fix the one upstream source that will not compile on a strict toolchain.

    ANTLR 4.13.2's ``ProfilingATNSimulator.cpp`` writes ``using namespace
    std::chrono`` and calls ``high_resolution_clock::now()`` without ever
    including ``<chrono>``. It compiles only where some other header happens to
    drag that in, which gcc and libc++ both do -- so Linux and macOS never see
    it. MSVC 19.51 (Visual Studio 2026, on the windows-latest runner) does not,
    and every Windows wheel died with::

        error C2653: 'high_resolution_clock': is not a class or namespace name

    Upstream's bug, not ours, and the runtime version is pinned to the Python
    runtime's 4.13.2, so patching the extracted copy is the fix rather than
    moving to a release that has it corrected.
    """
    f = src / "runtime" / "src" / "atn" / "ProfilingATNSimulator.cpp"
    if not f.is_file():
        raise SystemExit(f"expected upstream source is missing: {f}")
    text = f.read_text(encoding="utf8")
    if "#include <chrono>" in text:
        return
    # Anchor on the file's first include rather than a line number, and refuse
    # rather than guess if upstream reshuffles them.
    marker = '#include "atn/PredicateEvalInfo.h"'
    if marker not in text:
        raise SystemExit(
            "ProfilingATNSimulator.cpp no longer opens with the include this "
            "patch anchors on; re-check the <chrono> fix against the runtime"
        )
    f.write_text(
        text.replace(marker, "#include <chrono>\n\n" + marker, 1), encoding="utf8"
    )
    print("  patched ProfilingATNSimulator.cpp: added #include <chrono>")


def build_cpp_runtime(cache: Path, jobs: int) -> tuple[Path, Path]:
    """Return (include_dir, static_lib), building the runtime if needed."""
    src = cache / f"antlr4-cpp-runtime-{ANTLR_VERSION}"
    build = src / "build"
    inc = src / "runtime" / "src"
    lib = _static_lib(build) if build.is_dir() else None
    if lib is not None:
        print(f"  cached {lib.name}")
        return inc, lib

    zip_path = fetch(
        CPP_RUNTIME_URL, cache / f"antlr4-cpp-runtime-{ANTLR_VERSION}-source.zip"
    )
    src.mkdir(parents=True, exist_ok=True)
    import zipfile

    with zipfile.ZipFile(zip_path) as z:
        z.extractall(src)
    patch_runtime_sources(src)

    need("cmake")
    build.mkdir(exist_ok=True)
    run(
        [
            "cmake",
            "..",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DANTLR4_INSTALL=OFF",
            "-DANTLR_BUILD_CPP_TESTS=OFF",
            "-DANTLR_BUILD_SHARED=OFF",
            "-DANTLR_BUILD_STATIC=ON",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=ON",
            "-DWITH_DEMO=OFF",
            # ANTLR defaults WITH_STATIC_CRT to On, which builds the runtime /MT.
            # A CPython extension must be /MD, because Python itself links the
            # dynamic CRT and every object in one image has to agree. Without this
            # the compile succeeds and the *link* fails with 146 LNK2038s --
            # "'MT_StaticRelease' doesn't match value 'MD_DynamicRelease'" -- one
            # per runtime object. Ignored by every generator that is not MSVC.
            "-DWITH_STATIC_CRT=OFF",
        ],
        cwd=build,
    )
    # `cmake --build`, not `make`: the same line drives Makefiles, Ninja and
    # MSBuild, and --config is what the Visual Studio generator needs to
    # produce a Release library rather than a Debug one.
    run(
        [
            "cmake",
            "--build",
            ".",
            "--config",
            "Release",
            "--target",
            "antlr4_static",
            "--parallel",
            str(jobs),
        ],
        cwd=build,
    )
    lib = _static_lib(build)
    if lib is None:
        raise SystemExit(
            f"runtime build finished but no static library was found under {build}"
        )
    return inc, lib


def rename_grammars(work: Path) -> Path:
    """Copy the real grammars under the names speedy-antlr-tool requires."""
    g = work / "grammars"
    g.mkdir(parents=True, exist_ok=True)

    lex = (GRAMMARS / "JavaLexer.g4").read_text()
    lex = lex.replace("lexer grammar JavaLexer;", "lexer grammar JavaLabeledLexer;")
    (g / "JavaLabeledLexer.g4").write_text(lex)

    par = (GRAMMARS / "JavaParserLabeled.g4").read_text()
    par = par.replace(
        "parser grammar JavaParserLabeled;", "parser grammar JavaLabeledParser;"
    )
    par = par.replace("tokenVocab=JavaLexer", "tokenVocab=JavaLabeledLexer")
    (g / "JavaLabeledParser.g4").write_text(par)

    for f, marker in (
        (g / "JavaLabeledLexer.g4", "lexer grammar JavaLabeledLexer;"),
        (g / "JavaLabeledParser.g4", "parser grammar JavaLabeledParser;"),
    ):
        if marker not in f.read_text():
            raise SystemExit(
                f"grammar rename failed for {f.name}; upstream grammar header changed"
            )
    return g


def generate(work: Path, jar: Path):
    g = rename_grammars(work)
    cpp = work / "cpp"
    py = work / "py"
    for d in (cpp, py):
        d.mkdir(parents=True, exist_ok=True)

    need("java")
    for lang, extra, out in (
        ("Cpp", ["-visitor", "-no-listener"], cpp),
        ("Python3", ["-no-visitor", "-no-listener"], py),
    ):
        for name in ("JavaLabeledLexer.g4", "JavaLabeledParser.g4"):
            run(
                [
                    "java",
                    "-jar",
                    str(jar),
                    f"-Dlanguage={lang}",
                    *extra,
                    "-lib",
                    str(out),
                    "-o",
                    str(out),
                    name,
                ],
                cwd=g,
            )

    try:
        from speedy_antlr_tool import generate as sa_generate
    except ImportError:
        raise SystemExit(
            "speedy-antlr-tool is not installed:  pip install speedy-antlr-tool"
        )
    print("  running speedy-antlr-tool")
    sa_generate(
        py_parser_path=str(py / "JavaLabeledParser.py"), cpp_output_dir=str(cpp)
    )
    return cpp


def compile_extension(cpp: Path, inc: Path, lib: Path, out_so: Path):
    """Compile and link the extension with whatever compiler Python was built with.

    This used to shell out to ``g++`` with a hand-written flag list, which is
    correct on Linux and macOS and cannot work on Windows. setuptools already
    carries the compiler abstraction -- it knows MSVC's flags, the object
    suffix, where ``pythonXY.lib`` lives and what a shared object is called on
    each platform -- so the flag matrix is two lines instead of a port.

    ``ANTLR4CPP_STATIC`` is required: without it the runtime headers declare
    their symbols ``__declspec(dllimport)`` on Windows and the link fails
    against the static library we just built.
    """
    missing = [s for s in CPP_SOURCES if not (cpp / s).exists()]
    if missing:
        raise SystemExit(f"generated sources missing: {missing}")

    # setuptools' vendored copy, not stdlib ``distutils``: that module is gone
    # in Python 3.12 and deprecated before it. setuptools has shipped
    # ``_distutils`` since v60 and pyproject pins >=64, so there is no version
    # this project supports where the fallback would fire -- and a dead except
    # branch importing a module that cannot exist is worse than no branch.
    from setuptools._distutils.ccompiler import new_compiler
    from setuptools._distutils.sysconfig import customize_compiler

    cc = new_compiler()
    customize_compiler(cc)
    msvc = cc.compiler_type == "msvc"

    out_so.parent.mkdir(parents=True, exist_ok=True)
    objs_dir = cpp / "obj"
    objs_dir.mkdir(exist_ok=True)

    # /bigobj is insurance, not a fix for anything observed: MSVC caps a COFF
    # object at 65,536 sections and ANTLR's C++ target documents the flag for
    # large grammars, but this one compiles without it. Kept because it costs
    # nothing and the grammar only grows.
    cflags = (
        ["/O2", "/std:c++17", "/EHsc", "/bigobj"]
        if msvc
        else ["-O2", "-std=c++17", "-fvisibility=hidden"]
    )
    objects = cc.compile(
        [str(cpp / s) for s in CPP_SOURCES],
        output_dir=str(objs_dir),
        include_dirs=[str(inc), str(cpp), sysconfig.get_paths()["include"]],
        macros=[("ANTLR4CPP_STATIC", None)],
        extra_postargs=cflags,
    )

    # MSVC finds pythonXY.lib through a pragma in pyconfig.h, but only if the
    # directory holding it is on the library path.
    lib_dirs = [
        d
        for d in (
            sysconfig.get_config_var("LIBDIR"),
            os.path.join(sys.base_prefix, "libs"),
        )
        if d and os.path.isdir(d)
    ]
    # target_lang="c++" is load-bearing: without it distutils links with the C
    # driver and the extension imports with an undefined `__cxxabiv1` symbol
    # because libstdc++ was never pulled in.
    cc.link_shared_object(
        objects + [str(lib)],
        str(out_so),
        library_dirs=lib_dirs,
        extra_postargs=[] if msvc else ["-std=c++17"],
        target_lang="c++",
    )


def verify(out_so: Path) -> bool:
    """Parse a real fixture both ways and assert the trees are identical.

    The extension is loaded from ``out_so`` rather than imported by name. The
    file just built is the thing under test, and importing
    ``gen.java8speedy.sa_javalabeled_cpp_parser`` would happily pick up a stale
    copy from somewhere else on sys.path -- including, when setup.py drives
    this, the one already installed in the environment doing the building.
    """
    import importlib.util

    sys.path[:0] = [str(REPO_ROOT), str(REPO_ROOT / "openunderstand")]
    from antlr4 import FileStream, CommonTokenStream
    from gen.javaLabeled.JavaLexer import JavaLexer
    from gen.javaLabeled.JavaParserLabeled import JavaParserLabeled

    if not out_so.is_file():
        raise SystemExit(f"nothing to verify: {out_so} was not produced")
    spec = importlib.util.spec_from_file_location(MODULE_NAME, out_so)
    sa = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(sa)

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
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument(
        "--cache",
        default=str(HERE / ".build-cache"),
        help="where to keep the ANTLR jar and C++ runtime",
    )
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 4)
    ap.add_argument(
        "--force", action="store_true", help="regenerate even if the .so exists"
    )
    ap.add_argument(
        "--keep-work",
        action="store_true",
        help="do not delete generated C++ afterwards",
    )
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
    print(
        "Nothing to enable: engine_core defaults to `auto`, which uses this "
        "when it is present. `Python` in config.ini pins the pure-Python "
        "parser."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
