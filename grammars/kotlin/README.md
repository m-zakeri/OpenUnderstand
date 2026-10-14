# Kotlin grammar (Kotlin 2.4)

Not wired into the analysis yet: nothing imports it. It is the parsing half of a
possible Kotlin front end, kept here so the work is not lost.

Base: `antlr/grammars-v4` `kotlin/kotlin-formal` (the spec-derived grammar; the
other upstream grammar, `kotlin/kotlin`, parsed only 82% of real files against
94% for this one before any change). MIT, see `LICENSE`.

## What was added

Lexer: `..<`, `&`, `value`, `context`, `field` and `@all` tokens; unsigned literals
(`1u`, `0xFFu`, `1uL`); `$$"..."` and `$$$"..."` strings (own lexer modes, so only
the right number of `$` starts a template); the keywords `by`, `class`, `this`,
`interface`, `import`, `package`, `where`, `get`, `set`, `init`, `companion`,
`constructor`, `dynamic`, `typealias` and `typeof` were missing from the
inside-parentheses mode, so `object : S by s as S { }` in an argument list
lexed `by` and `as` as identifiers.

Parser: `context(a: A, b: B)` on functions, properties and in function types;
anonymous context functions and untyped anonymous-function parameters;
explicit backing fields (`field = x`, `field: T = x`, `field: T`); `when` guards
(`is A if cond ->`), `when (val x = e)` subjects, trailing commas in `when`
conditions and in type parameter / argument lists; `fun interface`; `value`
classes; `T & Any`; `..<`; chained `as`; `@all:`; `suspend`/`context` on
supertypes; newlines inside `"${ ... }"`; name-based destructuring (`val [a, b]`,
`[a, b]` in `for` and lambda parameters, `(val a = x, var b = y) = obj`);
companion blocks and companion extensions (experimental, test-data only).

Collection literals (`["a", "b"]`, nested, trailing comma) were already in the
upstream grammar.

## Measured

Java target, ANTLR 4.13.2, every file that is valid Kotlin:

| Corpus | Files | Parse with no error |
| --- | ---: | ---: |
| kotlinx.coroutines, Exposed (tuned on) | 2,089 | 2,087 |
| Kotlin compiler `codegen/box` + stdlib sources (tuned on) | 5,840 | 5,813 |
| arrow, kotlinx.serialization, ktor, okio, turbine (held out) | 4,474 | 4,474 |

The two misses in the first row are `package {{packageName}}` template files.
The 27 in the second are test files with `<!DIAGNOSTIC!>` markers or an
unbalanced parenthesis, i.e. not Kotlin. Hand-written probe files covering the
2.0 to 2.4 syntax parse too. A file that parses is not proof the tree has the
right shape; spot-checked for guards, backing fields, `$$` templates, `T & Any`
and destructuring assignment only.

## Speed

The upstream grammar was slow because ANTLR's context-free first pass (SLL)
read far ahead before it could rule a path out, often to the end of a class
body. Each change below removes a path that is grammatical but never real Kotlin:

* `controlStructureBody` no longer takes a declaration (`if (c) class A` made
  every class and function ambiguous with a trailing lambda).
* `return`/`throw`/`break` are not primary expressions, so `return a.b` is no
  longer ambiguous with `(return a).b`.
* An assignment is an expression with an optional `= expr` tail, so no scan to
  find the `=`.
* A delegate (`by expr`) cannot end in a lambda, which would be the class body.
* `callSuffix` is left-factored; property accessors, `when` entries and `semi`
  have no empty-or-newline alternatives; a trailing lambda must start on the
  call's line, as in the compiler.

Same 400 files (kotlinx.coroutines), same machine, Java target, one process:

| | before | after |
| --- | ---: | ---: |
| first pass (cold), seconds | 76 | 19.5 |
| later passes (warm), seconds | 15 | 6.5 |
| tokens looked ahead | 8.3M | 5.2M |

Parse success is unchanged on every corpus above. Tried and dropped: semantic
predicates to forbid a `{` after a bodiless declaration. They made the first
pass slower (ANTLR does not use them to prune the SLL pass) and need target
specific code.

## Caveats

* Pure-Python ANTLR is slow on this grammar (3 to 12 s a file). Use the C++
  accelerator before relying on it.
* ANTLR reports a failure inside a class body at the `{` of the class when every
  alternative inside fails, not at the real error. Bisect by truncating the file
  at member boundaries to find it.
* Understand 7.0 has no Kotlin language, so there is no oracle to score against.
