# speedy-antlr C++ parse accelerator

Optional. Parses Java ~8.6x faster than the pure-Python ANTLR runtime while
producing a structurally identical parse tree, so the existing listeners walk it
unchanged.

**Set expectations: parsing is not the bottleneck.** On the 22-file
`benchmark/JSON` fixture, parse-only drops from 3.79s to 0.44s, but a full
analysis run takes ~43s — the 23 listener passes and the database writes
dominate. Enabling the accelerator is worth roughly 9% end-to-end. Measured
per-pass costs after each build are in `build.log`; aggregate the
`timer_decorator` lines to see where the time actually goes.

## Build

```bash
python openunderstand/gen/java8speedy/build.py
```

Needs a JDK, cmake, make, a C++17 g++, Python development headers, and
`pip install speedy-antlr-tool`. The ANTLR tool jar and C++ runtime source are
downloaded into `.build-cache/` on first run.

## Enable

```ini
[Config]
engine_core = C++
```

`Python` (the default) keeps the pure-Python parser. If `C++` is requested but
the extension was never built, the parser logs a warning once and falls back
rather than failing.

## What is and is not in git

Only `build.py`, `__init__.py`, and this file. The generated C++, the ANTLR
runtime, and the compiled `.so` are all build artifacts and are gitignored.
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

## Known behavioural differences

The C++ translator flattens error nodes to plain `TerminalNodeImpl`, so
`visitErrorNode` never fires and `ctx.exception` is always `None`. It also sets
`ctx.parser = None`. No analysis pass reads any of those today. On
syntactically valid input the trees are identical -- `build.py` asserts this
with `speedy_antlr_tool.validate`.
