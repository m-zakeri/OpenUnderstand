# OpenUnderstand IDEA plugin

A **Java Metrics** tool window that runs OpenUnderstand over the open project
and lists Cyclomatic, CountLine, MaxNesting, CountDeclMethod,
PercentLackOfCohesion and CountClassCoupled per class and method. Sortable;
double-click a row to jump to the declaration.

The analyser is Python, so the plugin shells out to it — it does not bundle an
interpreter. Users need Python 3.9+ with `pip install openunderstand`, and set
the path with the **Python…** button (stored per IDE, default `python3`).

```bash
gradle runIde        # sandbox IDE with the plugin loaded
gradle buildPlugin   # build/distributions/openunderstand-idea-0.1.0.zip
```

Install the zip with Settings → Plugins → ⚙ → Install Plugin from Disk.

The Python side is `../scripts/idea_metrics.py`, copied into the plugin jar at
build time. Run it directly for the same data without any plugin:

```bash
python -m scripts.idea_metrics /path/to/java/project [Metric ...]
```

Publishing to the JetBrains Marketplace needs `signPlugin`/`publishPlugin`
config and a certificate — not set up here.