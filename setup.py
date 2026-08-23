"""Attach the optional speedy-antlr C++ parse accelerator to the build.

All packaging metadata lives in ``pyproject.toml``. This file exists only to
build ``openunderstand.gen.java8speedy.sa_javalabeled_cpp_parser`` when the
toolchain to do so is present, and to get out of the way when it is not.

The accelerator parses Java about 7.8x faster than the pure-Python ANTLR
runtime -- 2.5s against 19.7s over benchmark/JSON's 85 files -- while producing
a structurally identical parse tree. It is still optional by design: a wheel
without it is a complete, working package, because ``utils/antler_parser``
falls back to the Python runtime and logs one warning.

Building it needs a JDK, cmake, a C++17 compiler and ``speedy-antlr-tool``.
Most people installing from an sdist have none of those, so the decision is
made by probing, before the extension is ever declared:

* toolchain present  -> the extension is declared and a failure to build it is
  a hard error, because a half-configured toolchain should be loud;
* toolchain absent    -> no extension is declared and the result is the
  pure-Python wheel this project shipped before.

``OPENUNDERSTAND_BUILD_ACCELERATOR`` overrides the probe: ``1`` requires the
extension and fails the build if the toolchain is incomplete, which is what CI
sets so a silently pure wheel can never be published under a platform tag.
``0`` skips it even where it would work.
"""

from __future__ import annotations

import importlib.util
import os
import pathlib
import shutil
import sys

from setuptools import Extension, setup
from setuptools.command.build_ext import build_ext

HERE = pathlib.Path(__file__).resolve().parent
SPEEDY = HERE / "openunderstand" / "gen" / "java8speedy"
EXT_NAME = "openunderstand.gen.java8speedy.sa_javalabeled_cpp_parser"


def _load_build_module():
    """Import ``java8speedy/build.py`` by path -- it is not an installed module."""
    spec = importlib.util.spec_from_file_location(
        "_ou_speedy_build", SPEEDY / "build.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _missing_tools() -> list[str]:
    """What the accelerator build needs and this machine does not have."""
    missing = [t for t in ("java", "cmake") if shutil.which(t) is None]
    if importlib.util.find_spec("speedy_antlr_tool") is None:
        missing.append("speedy-antlr-tool (pip install speedy-antlr-tool)")
    if not (SPEEDY / "build.py").is_file():
        missing.append("openunderstand/gen/java8speedy/build.py")
    if not (HERE / "grammars" / "JavaParserLabeled.g4").is_file():
        missing.append("grammars/JavaParserLabeled.g4")
    return missing


def _wanted() -> bool:
    forced = os.environ.get("OPENUNDERSTAND_BUILD_ACCELERATOR")
    missing = _missing_tools()
    if forced == "0":
        return False
    if forced == "1":
        if missing:
            raise SystemExit(
                "OPENUNDERSTAND_BUILD_ACCELERATOR=1 but the toolchain is "
                "incomplete: " + ", ".join(missing)
            )
        return True
    if missing:
        print(
            "openunderstand: building without the C++ parse accelerator "
            "(missing " + ", ".join(missing) + "). The pure-Python ANTLR "
            "runtime will be used; nothing else changes.",
            file=sys.stderr,
        )
        return False
    return True


class BuildAccelerator(build_ext):
    """Hand the whole extension build to ``java8speedy/build.py``.

    Not a normal ``Extension`` compile: the C++ sources do not exist until
    ANTLR has generated them from ``grammars/*.g4``, and they link against an
    ANTLR C++ runtime that has to be fetched and cmake-built first. build.py
    is the one place that knows that sequence, and it is also what a developer
    runs by hand, so there is a single recipe rather than two that drift.
    """

    def build_extension(self, ext):
        if ext.name != EXT_NAME:
            return super().build_extension(ext)

        build = _load_build_module()
        out = pathlib.Path(self.get_ext_fullpath(ext.name))
        out.parent.mkdir(parents=True, exist_ok=True)

        cache = pathlib.Path(
            os.environ.get("OPENUNDERSTAND_BUILD_CACHE", SPEEDY / ".build-cache")
        )
        work = cache / "work"
        if work.exists():
            shutil.rmtree(work, ignore_errors=True)
        work.mkdir(parents=True, exist_ok=True)

        jar = build.fetch(
            build.ANTLR_JAR_URL, cache / f"antlr-{build.ANTLR_VERSION}-complete.jar"
        )
        inc, lib = build.build_cpp_runtime(cache, os.cpu_count() or 4)
        cpp = build.generate(work, jar)
        build.compile_extension(cpp, inc, lib, out)
        shutil.rmtree(work, ignore_errors=True)


# Sources are listed for setuptools' benefit only -- BuildAccelerator never
# compiles them, because they are generated. The list must be non-empty or
# setuptools declines to build the extension at all.
ext_modules = (
    [Extension(EXT_NAME, sources=[str(SPEEDY / "build.py")], optional=False)]
    if _wanted()
    else []
)

setup(ext_modules=ext_modules, cmdclass={"build_ext": BuildAccelerator})
