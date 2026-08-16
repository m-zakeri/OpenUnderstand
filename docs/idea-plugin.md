# IntelliJ IDEA plugin

`idea-plugin/` is a JetBrains IDE plugin that runs the analysis over the open
project and lists per-entity metrics in a tool window. It is a thin shell: all
of the work happens in `scripts/idea_metrics.py`, which the plugin ships as a
resource and runs in a virtualenv the plugin builds for itself.

## Using it

**Java Metrics**, bottom dock.

| Button | Does |
| --- | --- |
| Analyse Project | Runs the analysis over the project root and fills the table |
| Export CSV... | Writes the table to a file, in analysis order |

One column per metric `Ent.metrics()` reports -- around 70 of Understand's
names, whichever the library implements -- so the table scrolls sideways.
Columns are sortable, and double-clicking a row opens the declaration. Classes
and methods are listed together, so class-only metrics such as
`CountDeclMethod` and `PercentLackOfCohesion` read 0 on every method row.

Passing metric names as arguments to `scripts/idea_metrics.py` narrows the set;
the plugin passes none.

## The interpreter

The analyser is Python and the plugin does not bundle one. It runs in a
virtualenv it owns, under
`PathManager.getSystemPath()/openunderstand-venv-<analyser version>`, built with
`python3` and populated from the bundled wheel the first time **Analyse
Project** is pressed. `python -c "import openunderstand"` guards it, so the
install happens once and every later run skips straight to the analysis.

There is deliberately no interpreter setting and no search of the machine. An
interpreter found on `PATH` or in the project carries whatever version of the
analyser happens to be installed there, which defeats the reason the wheel is
bundled at all. The version in the directory name is what makes a plugin update
build a new venv rather than reuse one holding the old analyser.

The dumper is written to a **private temp directory**, never a shared one:
Python puts a script's own directory first on `sys.path`, so a leftover
`/tmp/openunderstand.py` from an earlier run shadows the installed package and
the dumper dies with `'openunderstand' is not a package`.

It installs the **wheel bundled in the plugin** when there is one, falling back
to `pip install openunderstand` otherwise. Bundling matters because the plugin
and the analyser ship separately: without it, a user who installs the plugin
gets whatever version PyPI currently serves, which is not necessarily the one
the plugin was built and tested against. Build the wheel before the plugin and
it is picked up automatically:

```bash
python -m build --wheel      # writes dist/*.whl, ~430 KB
cd idea-plugin && gradle buildPlugin
```

The wheel pins the analyser, not the install: its two dependencies
(`antlr4-python3-runtime`, `peewee`) still come from PyPI, so the bootstrap
needs a network. Vendoring those as well and installing with `--find-links`
would make it offline; nothing does that today.

Bump the package version before bundling a changed wheel. A wheel that carries
different code under a version string already published is the kind of thing
that wastes an afternoon.

A virtualenv rather than `pip install --user`, because a distribution Python is
externally managed (PEP 668) and refuses to install into itself. Working from a
source checkout, `pip install -e .`: the plugin runs the script from a
temporary directory, so having the repository as the working directory is not
enough for the import to resolve.

## Building it

```bash
cd idea-plugin
gradle runIde                                 # sandbox IDE with the plugin loaded
gradle runIde -PrunProject=/a/java/project    # ... with that project open
gradle buildPlugin                            # build/distributions/*.zip
```

`gradle.properties` carries two machine-local paths. `ideaHome` is the IDE to
build against; unset it and the build downloads IDEA Community 2025.1 instead,
which is a 1.2 GB fetch. `runProject` is what the sandbox opens. Neither
belongs in a pull request.

Three things the build needs, each learned the hard way:

- **The Gradle plugin has to be new enough for the IDE it builds against.**
  `org.jetbrains.intellij.platform` 2.1 throws `IndexOutOfBoundsException` in
  `resolveIdeHomeVariable` when parsing a 2025.x `product-info.json`. 2.5
  handles it, and drops `instrumentationTools()`, which 2.2 and later add
  themselves.
- **`buildSearchableOptions` is disabled.** It starts a headless IDE to index
  settings, which fails while a sandbox IDE holds the lock, and nothing here
  registers searchable settings for it to find.
- **The Python script is copied in by `processResources`**, not duplicated.
  `scripts/idea_metrics.py` is the one copy; run it directly for the same data
  without any IDE.

## Publishing

Not configured. The JetBrains Marketplace requires the zip to be signed
(`signPlugin`: a certificate chain, a private key and its password) and
uploaded with a permanent token (`publishPlugin`). Add both to
`build.gradle.kts` reading from environment variables -- never the build file --
when the credentials exist. Until then, install the zip through Settings →
Plugins → ⚙ → Install Plugin from Disk.

A first upload to the Marketplace is manual and goes through moderation, which
takes a couple of business days; `publishPlugin` only helps for updates after
that.