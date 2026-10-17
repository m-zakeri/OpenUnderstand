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

- Smart casts through assignments (a narrowed `var` reassigned), `as` statements, and stable member chains
  (`a.b is Foo`); only simple names are narrowed.
- The forwarding methods that class delegation (`: I by x`) generates; the delegate itself is read.
- Libraries no index covers (kotlinx.*, third-party): their members are unresolved placeholders, and the free
  names in a lambda whose receiver cannot be typed are dropped.
- Gradle's generated per-build accessors (`sourceSets`, `kotlin`); the Gradle index is pinned to 8.14.2.
- Java code calling Kotlin: the Java symbol table does not see `.kt` files.
- Variance and bounds as inference constraints, and composite JDK generic returns such as `entrySet()`.

## Working on it

```bash
for t in tests/test_kotlin_*.py; do .venv/bin/python -W ignore "$t"; done
```

The two real corpora are fetched by hand and git-ignored (`scripts/compare/out/kotlin/`). Compare a change by
the **call rows** (file, line, column, callee) of a before and after database, never by totals. The
`kotlin-check` skill has the procedure. Regenerate an index with `scripts/gen_kotlin_index.py`,
`scripts/gen_jdk_index.py` (also for jars: `--jar ... --prefix ...`) or `scripts/gen_gradle_dsl_index.py`.
After a grammar change, regenerate `openunderstand/gen/kotlin` and rebuild the accelerator.
