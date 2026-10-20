# Kotlin

OpenUnderstand also analyses Kotlin (`.kt` and `.kts`) into the same database, under Understand's
Java kinds. **There is no Understand oracle for Kotlin**: its Python API refuses the language, and a
Kotlin class seen from Java is an unresolved name. Nothing here is measured against the real tool.
The rules were taken from Understand's Java behaviour and checked by reading samples on two real
projects (kotlinx.coroutines, 1,082 files; detekt, 1,160 files) and by the tests in `tests/test_kotlin_*.py`.

## What is written

| Area | References and entities |
| --- | --- |
| Declarations | packages, classes, interfaces, enums, objects, companions, type aliases, functions, constructors, properties, parameters, type parameters, locals; `Declare`, `Define`, `Contain`, `Begin`/`End`, `Typed` |
| Lambdas and accessors | a `(lambda_expr_N)` entity per lambda and anonymous function with its parameters, the implicit `it` when read, and its locals; a property's `get` and `set` with the setter's parameter |
| Calls and uses | `Call`, `Call Nondynamic`, `Create`, `Use`, `Use Deref Partial`, `Set`, `Modify` (and their Deref Partial forms), `Use Return`, operators and infix calls, delegated properties, destructuring, callable references |
| Types | `Typed`, `Typed GenericArgument`, `Use GenericArgument`, `Use Cast`, `Use Annotation`, `DotRef`, `Importby`, `Use Constrains Couple` |
| Hierarchy | `Extend Couple`, `Implement Couple`, `Extend Couple Implicit External` (to `kotlin.Any` and `kotlin.Enum`), `Overrides` |
| Other | `Throw` (from `@Throws`), `Set Init`, `Couple`, `Define Implicit` and `Typed Implicit` for enum `values`/`valueOf` and data class `componentN`/`copy` |

An inverse reference exists only for a target the project declares, as for Java.

## How names are resolved

The rule is the project's rule: **refuse before guessing.** A reference is written only when exactly one
declaration fits. Resolution follows Kotlin's order (local scopes, implicit receivers, top level, imports,
default imports) and uses four sources of declarations: the project's Kotlin, the project's Java (through
`symbol_table`), the JDK (`oudb/jdk_index.txt.gz`) and the Kotlin standard library
(`oudb/kotlin_index.txt.gz`). Gradle's API and Kotlin DSL are indexed too (`gradle_index.txt.gz`,
`gradle_dsl_index.txt.gz`), so build scripts resolve.

Generic types are tracked (`Ty` carries its arguments): calls bind their type parameters from the receiver,
the explicit `<T>`, the arguments and the lambdas, an expected type fills what is left, and a lambda's
receiver (`T.() -> R`, Gradle's `Action<T>`) types its free names. A single-type import names its class
exactly, so a type written through one is referenced even when no index covers the library. Smart casts
narrow a name by flow (`if (x is T)`, `x !is T` then `return`, `&&`/`||`, `when (x) { is T -> }`).

## Metrics

The metrics computed from the reference graph (fan, coupling, cohesion, declaration counts) read the
references and need no Kotlin code. The text metrics have Kotlin versions in
`openunderstand/metrics/kotlin_metrics.py`: `CountLine`, `CountLineBlank`, `CountLineCode`,
`CountLineComment`, `CountLineCodeDecl`, `CountLineCodeExe`, `CountSemicolon`, `CountStmt*`,
`Cyclomatic*`, `MaxNesting`, `RatioCommentToCode`. They transpose Java's definitions and are not
measured. `Essential`, `Knots` and `CountPath*` answer `None` for Kotlin.

## What is not covered

- A narrowed `var` that is reassigned inside a loop before the test, and smart casts through function calls
  other than `require`/`check`. Names and dotted paths (`a.b is Foo`) are narrowed; an assignment ends the cast.
- Class delegation to a **library** interface and delegated properties: only the forwarding methods of a project
  interface are declared (`Define Implicit`).
- Libraries without an index. Indexed: the stdlib, the JDK, the Gradle API and Kotlin DSL, JUnit 3/4/5, AssertJ,
  reactive-streams, JMH, the Kotlin compiler's PSI, kotlinx.coroutines, kotlinx.serialization and Ktor's
  serialization (`library_index`, `kotlin_library_index`). Anything else is unresolved.
- Gradle's generated accessors: `java { }`, `sourceSets { }`, `base`, `application`, `publishing`, `reporting`
  and `testing` give their lambda the extension as receiver (`GRADLE_ACCESSORS`); the accessor call itself and
  per-configuration ones (`implementation(...)`) name no declaration. The Gradle index is pinned to 8.14.2.
  A `.gradle.kts` script runs with `Project`/`Settings`/`Gradle` as `this`.
- Java calling Kotlin works for classes, constructors, member functions, companions, `INSTANCE` and top-level
  functions through the facade (`FooKt.helper()`); property accessors (`getName()`), `@JvmStatic` shortcuts,
  `internal` members and an implicit default constructor stay unresolved.
- Variance (`in`/`out`) and bounds as inference constraints; the bounds of the stdlib's own type parameters.
- `MaxEssentialKnots` and `MinEssentialKnots` are `None` for Kotlin. `Essential`, `Knots`, `CountPath` and
  `CountPathLog` are Java's rules transposed over a neutral statement tree (`metrics/kotlin_flow.py`; a `when` entry
  never falls through and a `break` in a `when` leaves the loop). No Kotlin metric is measured against Understand.

## Working on it

```bash
for t in tests/test_kotlin_*.py; do .venv/bin/python -W ignore "$t"; done
```

The two real corpora are fetched by hand and git-ignored (`scripts/compare/out/kotlin/`). Compare a change by
the **call rows** (file, line, column, callee) of a before and after database, never by totals. The
`kotlin-check` skill has the procedure. Regenerate an index with `scripts/gen_kotlin_index.py`,
`scripts/gen_jdk_index.py` (also for jars: `--jar ... --prefix ...`) or `scripts/gen_gradle_dsl_index.py`.
After a grammar change, regenerate `openunderstand/gen/kotlin` and rebuild the accelerator.
