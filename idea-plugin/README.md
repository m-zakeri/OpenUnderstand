# OpenUnderstand IDEA plugin

A **Java Metrics** tool window that runs OpenUnderstand over the open project
and lists Cyclomatic, CountLine, MaxNesting, CountDeclMethod,
PercentLackOfCohesion and CountClassCoupled per class and method. Sortable;
double-click a row to jump to the declaration.

The analyser is Python, so the plugin shells out to it — it does not bundle an
interpreter. Users need Python 3.9+ with `pip install openunderstand`, and set
the path with the **Python…** button. Unset, it uses `$VIRTUAL_ENV`, else the
nearest `.venv/bin/python` at or above the analysed project, else `python3`.

Working from a source checkout, `pip install -e .` it: the plugin runs the
script from a temp directory, so having the repo as your working directory is
not enough to import the package.

**Export CSV…** writes the table to a file, in analysis order rather than the
column you sorted by.

## Build and install

```bash
gradle runIde                      # sandbox IDE with the plugin loaded
gradle runIde -PrunProject=/a/java/project   # ... with that project open
gradle buildPlugin                 # build/distributions/openunderstand-idea-0.1.0.zip
```

Install the zip with Settings → Plugins → ⚙ → Install Plugin from Disk.

`gradle.properties` carries two local paths: `ideaHome`, the IDE to build
against (unset it to download IDEA Community 2024.2 instead — a 1.2 GB fetch),
and `runProject`, what the sandbox opens.

## Requirements, installed on demand

The analyser is Python and the plugin does not bundle an interpreter. On
**Analyse Project** it first checks `python -c "import openunderstand"`. If that
fails it offers to build a virtualenv under the IDE's system directory
(`PathManager.getSystemPath()/openunderstand-venv`), `pip install
openunderstand` into it, and remember that interpreter — so a user who has
Python at all needs no setup, and one who does not gets a dialog naming the
problem rather than an empty table.

A virtualenv rather than `pip install --user` because a distro Python is
externally managed (PEP 668) and refuses to install into itself.

## Publishing

Not set up. The Marketplace needs `signPlugin` (a certificate chain and private
key) and `publishPlugin` (a token) in `build.gradle.kts`; add them when you
have the credentials, and keep them in environment variables rather than the
build file. Until then the zip installs from disk.

The Python side is `../scripts/idea_metrics.py`, copied into the plugin jar at
build time. Run it directly for the same data without any plugin:

```bash
python -m scripts.idea_metrics /path/to/java/project [Metric ...]
```

Publishing to the JetBrains Marketplace needs `signPlugin`/`publishPlugin`
config and a certificate — not set up here.