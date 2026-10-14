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

## Second corpus and scripts

Eight further repositories (compose-multiplatform, detekt, koin, nowinandroid,
sqldelight, kotlinx-datetime, leakcanary, gradle-build-action: 4,975 `.kt` and
419 `.kts` files) first parsed 5,337 of 5,394. Real defects found and fixed:

* a `.kts` script needed a separator after its last statement, so a file with
  no final newline failed;
* a trailing comma in a function type's parameters and in an index `a[x,]`;
* a lambda on the line after a call's `)` (`f(x)\n{ ... }`) is a trailing
  lambda in Kotlin; the speed edit that dropped it was wrong and is restored
  for the `valueArguments` case only.

Now 5,387 of 5,394. The other seven are not Kotlin: Groovy-style `group "x"`,
a `%JAVA_VERSION%` template, and five test-data files holding several modules
under `// @Module` comments. Earlier corpora are unchanged.

## Kotlin's own parser tests

`compiler/psi/psi-impl/testData/psi` in JetBrains/kotlin holds the compiler
parser's test files with expected trees. Files whose expected tree has no
`PsiErrorElement` (449 of 763) were run as the conformance set: 394 parsed at
first, 407 now. Fixed: annotated, `_`-named and `noinline` context parameters,
type parameters on an anonymous function, `contract [...]` on functions and
accessors (before or after `where`), a trailing comma in a setter parameter, a
catch clause and a lambda's parameters, `fun` and `interface` split across a
newline, and a parenthesised function type as a supertype.

The other 42 are not accepted, on purpose: the Kotlin parser tolerates them and
the compiler rejects them (`object Foo()`, `fun name()` as an expression,
`error class`, `private init`, old `a.{ ... }` and `fun f<T>()` syntax, `val x1`
as a `when` subject without an initialiser, `1l`), or the file is several
modules glued together under `// FILE:` comments. This grammar describes valid
Kotlin, so it is stricter than the compiler's parser there. Not covered: a
function type with annotated receiver written without parentheses
(`fun @A () -> Unit?.f()`).

## Tree shape against Kotlin's PSI

A file that parses can still be grouped wrongly, so `scripts/kotlin_shape/`
compares trees. `psi_spans.py` reads a PSI dump (`*.txt` beside each test file
in `compiler/psi/psi-impl/testData/psi`) into typed source spans;
`antlr_spans.py` produces the same spans from this grammar's tree (unrolling
left-nested binary chains, prefix/postfix wrapping, dot/call/index folding);
`compare.py` diffs them per element type. Setup: `gen_py.sh` builds a Python
parser, the Kotlin repo's PSI test data is cloned sparsely, and the files whose
expected tree has no error are copied to `pv/`.

On 391 comparable files and 41 element types (binary/unary/postfix
expressions, calls, dot and safe access, indexing, callable references and class
literals, lambdas, `if`/`when`/`try`/loops, `return`/`throw`, annotated and
labelled expressions, destructuring, classes, objects, functions, properties,
accessors, constructors, type aliases, type and value arguments, value
parameters, user, nullable and function types) every file is identical: recall
1.0000, precision 1.0000.

Grammar defects this found and fixed: a newline before `::` glued a callable
reference to the line above; an annotation ending its line did not cover the
whole assignment or `as` expression that follows (`statementAnnotation`); a
bare `dynamic` parsed as a user type (`typeReference` now lists it first); a
labelled or annotated lambda on the next line was not one more argument of the
call (`labeledLambda`).

Where the trees differ in form and the check normalises it, so a consumer must
know: the receiver of a callable reference or class literal is a type here
(`Map<String, Int>::size`, `a?::b`) and an expression in PSI (a call with type
arguments and no parentheses); a statement label covers its first operand
(`l@ a + b` is `(l@ a) + b`); an annotation on an anonymous function or a
destructuring statement sits inside that node; a `when` subject `val` is a
property.

Two PSI shapes are kept out on purpose: a bare `h<baz>` (type arguments with no
call) is not valid Kotlin, though PSI reads it as a call.

Not checked: element types not listed above (modifier lists, annotation
entries, string template entries, constants, imports), the exact nesting of
each node (only its source span), and anything outside the 391 files.

## Using it from OpenUnderstand

`openunderstand.utils.kotlin_parser` parses `.kt`/`.kts` with this grammar (see
`CLAUDE.md`). The committed Python parser is `openunderstand/gen/kotlin/`,
generated with the listener enabled; regenerate it and rebuild the accelerator
(`openunderstand/gen/kotlinspeedy/build.py <files>`) after editing a `.g4`.
The first entity pass (declarations and `Typed`) is `analysis_passes/kotlin_declarations.py`; calls and uses are `kotlin_expressions.py` / `kotlin_symbols.py` (resolving against the project, Java, the JDK and a generated Kotlin stdlib index); there is no metric for Kotlin yet.
