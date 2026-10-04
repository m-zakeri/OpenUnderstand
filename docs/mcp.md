# MCP server

OpenUnderstand ships an [MCP](https://modelcontextprotocol.io) server, so an
assistant can analyse a Java project and ask structural questions about it
without shelling out or knowing the database schema.

```bash
pip install "openunderstand[mcp]"
```

## Register it

Any MCP client works. A client's configuration looks like this:

```json
{
  "mcpServers": {
    "openunderstand": { "command": "openunderstand-mcp" }
  }
}
```

Run it directly to check it starts: `openunderstand-mcp`. It speaks over
stdio, so it will sit waiting for a client -- that is correct behaviour.

## Tools

| Tool | Does |
| --- | --- |
| `analyze(source_dir, database="")` | Parse a Java project and open the result |
| `open_database(path)` | Open an existing `.udb` |
| `update(paths, source_root="")` | Re-analyse changed files, without a full rebuild |
| `list_entities(kind="", limit=100)` | The symbol table: entities with kind, type, parent and declaring file and line, optionally filtered by kind |
| `entity_references(longname, reference_kind="", limit=100)` | References scoped to an entity, with file, line and column |
| `entity_metrics(longname, metrics=None)` | Metric values; omit `metrics` for all |
| `list_kinds(kind_filter="", references=False)` | The kind vocabulary |

`analyze` or `open_database` has to come first -- the others operate on
whichever database is open.

After editing source, call `update` rather than `analyze` again. It re-analyses
only the files named and the files that depend on them, which is about ten
times quicker on a mid-sized project -- one file of the 85-file `org.json`
benchmark takes 1.2s against 14s for the whole thing. Each file's previous
contribution is deleted first, so a renamed method does not linger under both
names, and the result is what a rebuild of the same source would have written.
`source_root` defaults to the root the open database recorded when it was
built, so it is usually not needed. A path that no longer exists is purged and
not re-analysed, which is how you record a deleted file.

## Resources

Reference data the client can read without spending a tool call.

| URI | Contents |
| --- | --- |
| `openunderstand://kinds/entity` | the 237 entity kind names |
| `openunderstand://kinds/reference` | the 106 reference kind names |
| `openunderstand://metrics` | metric names this database answers |
| `openunderstand://database` | what is open, and how many entities |

The kind resources matter more than they look. Every filter argument in this
server is a kind string, and a wrong filter returns an **empty list rather
than an error** -- so an assistant guessing at names fails silently. Reading the
vocabulary first removes the guess.

## Prompts

| Prompt | Does |
| --- | --- |
| `review_class(longname)` | size, complexity, what it declares and couples to |
| `complexity_hotspots(limit=10)` | the most complex methods, ranked |
| `trace_callers(longname)` | the call graph into a method |

Each names the tools it needs, so the model does not have to rediscover the
sequence. They also tell it what the numbers do *not* mean -- `trace_callers`
says an empty result means "none found", not "none exist": this analysis
reproduces 90 to 98% of Understand's references at the exact position, so an
empty result is usually but not always complete.

`kind` and `reference_kind` take [Understand's filter
grammar](api.md#filter-strings): tokens are ANDed, `~` excludes, `,` ors. So
`"Class ~Unknown"`, `"Method ~Static"` and `"Class,Interface"` all work.

## Example exchange

```
analyze(source_dir="~/projects/myapp/src")
  → {"database": ".../src/src.udb", "files_analyzed": 128, "entities": 3114}

list_entities(kind="Class ~Unknown", limit=3)
  → com.myapp.Server   Java Class Type Public Member   src/com/myapp/Server.java:12
    com.myapp.Router   Java Class Type Public Member   src/com/myapp/Router.java:9
    com.myapp.Handler  Java Class Type Default Member  src/com/myapp/Handler.java:5

entity_metrics(longname="com.myapp.Server",
               metrics=["CountLine", "CountDeclMethod", "SumCyclomatic"])
  → {"CountLine": 214, "CountDeclMethod": 12, "SumCyclomatic": 31}
```

## Notes

The analysis layer prints progress and pass failures to stdout, and stdout is
the MCP transport -- anything written there corrupts the protocol. Every tool
runs its work with stdout and stderr captured for that reason.

Accuracy is whatever [Parity](parity.md) reports. The tools are a faithful view
of the database; they do not paper over what the analysis missed.
