# speedy-antlr C++ parse accelerator

Parses Java 7.8x faster than the pure-Python ANTLR runtime while producing a
structurally identical parse tree, so the existing listeners walk it unchanged.

**It is worth about 17% of a full analysis.** Measured on `benchmark/JSON`, 85
files, three runs back to back on an otherwise idle machine:

| engine | total | fingerprint |
| --- | ---: | --- |
| C++ | 187.4s, 189.2s | `0a7d28a303441ba1` |
| Python | 225.8s | `0a7d28a303441ba1` |

37.5s saved against the Python run, and the two C++ runs agree within 1%, so
the machine was stable. Parse-only over the same files is 2.53s against 19.72s;
the end-to-end saving is about twice that because the pipeline parses more than
once per file. The fingerprints are identical, which is the point: the
accelerator changes how long the analysis takes and nothing about what it
produces.

This file used to say the accelerator was worth "roughly 9%" and `CLAUDE.md`
used to say parsing was "only ~1% of runtime". Both were wrong. Beware
measuring this with anything else running -- an earlier attempt at the same
comparison, taken while other jobs were on the box, read 2.5%.

## Getting it

`pip install openunderstand` is enough on Linux x86_64, macOS (Intel and Apple
silicon) and Windows x64 for CPython 3.9 through 3.13: those wheels ship the
compiled extension. Everything else falls back to the sdist, which builds the
pure-Python package.

There is no abi3 shortcut, which is why the matrix is that shape.
`speedy-antlr-tool` generates raw CPython C API code with no `Py_LIMITED_API`,
so a wheel is specific to one Python minor *and* one platform.

## Building it yourself

```bash
python openunderstand/gen/java8speedy/build.py
```

Needs a JDK, cmake, a C++17 compiler, Python development headers, and
`pip install speedy-antlr-tool`. The ANTLR tool jar and C++ runtime source are
downloaded into `.build-cache/` on first run. `setup.py` runs exactly this when
it builds a wheel, so there is one recipe rather than two that drift.

## Enabling it

Nothing to do: `engine_core` defaults to `auto`, which uses the accelerator
when the installed package has one and the Python runtime when it does not.

```ini
[Config]
engine_core = auto     ; the default
```

`C++` forces it and warns once, then falls back, if it was never built.
`Python` pins the pure-Python runtime, which is what the comparison harness
passes when it wants to measure one engine specifically.

## What is and is not in git

Only `build.py`, `__init__.py`, and this file. The generated C++, the ANTLR
runtime, and the compiled extension are all build artifacts and are gitignored.
This replaced a vendored tree that mixed ANTLR 4.9 and 4.13 headers, shipped no
runtime `.cpp` at all (so it could never have linked), and named the extension
`sa_javalabeled` while its init symbol was `PyInit_sa_javalabeled_cpp_parser`.

## Why the grammars get renamed during the build

`speedy-antlr-tool` takes its grammar name by stripping `Parser` from the parser
filename and then assumes a matching `<X>Lexer`. Our grammars are
`JavaParserLabeled` and `JavaLexer`, so `build.py` copies them to
`JavaLabeledParser` / `JavaLabeledLexer` for the accelerator build only. The
rename is cosmetic: the generated translator resolves every context class by
name off the `parser_cls` passed in at runtime, and we pass the real
`gen.javaLabeled.JavaParserLabeled`. Both grammars yield the same 218 context
classes.

## Two things that will bite a port

The link step needs `target_lang="c++"`. Without it setuptools links with the C
driver and the extension imports with an undefined `__cxxabiv1` symbol, having
compiled without complaint.

The compile needs `ANTLR4CPP_STATIC` defined. Without it the runtime headers
declare their symbols `__declspec(dllimport)` on Windows and the link fails
against the static library the build just produced.

## Known behavioural differences

The C++ translator flattens error nodes to plain `TerminalNodeImpl`, so
`visitErrorNode` never fires and `ctx.exception` is always `None`. It also sets
`ctx.parser = None`. No analysis pass reads any of those today. On
syntactically valid input the trees are identical -- `build.py` asserts this
with `speedy_antlr_tool.validate`.
