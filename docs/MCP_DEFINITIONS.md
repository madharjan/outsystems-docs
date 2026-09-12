# MCP Definitions

The functions, tools, and resources this MCP server exposes to an AI agent. Source of truth:
`src/osdocs/server.py`.

## Resources

### `llms://index`

Combined OutSystems ODC + O11 documentation index (the generated `llms.txt`), tagged by
platform. Use this to browse available docs before calling `get_doc`.

- Params: none
- Returns: `str` - the combined navigation index (Markdown)

## Tools

### `search_docs(query, k=5, source=None, category=None)`

Semantic search over the local docs index. Embeds `query` locally and ranks chunks by cosine
similarity.

- Params:
  - `query: str` - natural-language search text
  - `k: int = 5` - max number of results
  - `source: str | None = None` - limit to `"odc"` or `"o11"`; omit for both
  - `category: str | None = None` - exact-match filter on a result's `category` (a document's
    top-level TOC section, e.g. `"Getting Started"`); omit for all categories
- Returns: `dict`
  
  ```json
  {
    "results": [
      {
        "text": "...",
        "source": "odc",
        "source_path": "gs/intro.md",
        "section": "Getting Started",
        "title": "Intro",
        "url": "https://success.outsystems.com/...",
        "category": "Getting Started",
        "score": 0.83,
        "last_updated": "2026-05-29T12:00:00+00:00"
      }
    ]
  }
  ```

- Notes:
  - `last_updated` on every result is the ISO timestamp of your last local `--sync` (not a
    per-document source-change date - the fetch is a shallow clone with no git history to
    derive that from). No top-level `last_updated` here - call the `last_updated` tool
    directly if you need freshness with an empty (or no) result set.
  - `url` is a verified link resolved against the official sitemap during `--sync` (or the raw
    doc href if `--no-links` was used).
  - Empty `results` means no matching chunks (empty/missing index, or an over-narrow `source`
    filter), not an error.

### `get_doc(source, path)`

Full Markdown of one document, by its `source`/`path` (as returned in a `search_docs` result's
`source`/`source_path`, or from the `llms://index` navigation).

- Params:
  - `source: str` - `"odc"` or `"o11"`
  - `path: str` - the document's href, e.g. `"gs/intro.md"`
- Returns: `dict`
  
  ```json
  {
    "content": "# Intro\n\n...",
    "url": "https://success.outsystems.com/...",
    "last_updated": "2026-05-29T12:00:00+00:00"
  }
  ```

- Not found: `content` holds a human-readable message instead of Markdown, `url` and
  `last_updated` are both `null`:

  ```json
  {"content": "Document not found: odc/does-not-exist.md", "url": null, "last_updated": null}
  ```

### `last_updated()`

Timestamp of the last local sync, with no other data attached - use this for a quick
freshness check without pulling search results.

- Params: none
- Returns: `str` - ISO 8601 timestamp, or `"unknown"` if `data/` has never been synced

## Chunk fields (search_docs results)

Every entry in `search_docs`'s `results` list, defined in `src/osdocs/chunk.py`:

| Field          | Type    | Meaning                                                            |
| -------------- | ------- | ------------------------------------------------------------------ |
| `text`         | `str`   | The chunk's content (a section, or a windowed slice of a long one) |
| `source`       | `str`   | Platform tag: `"odc"` or `"o11"`                                   |
| `source_path`  | `str`   | The document's href - pass to `get_doc` as `path`                  |
| `section`      | `str`   | Heading this chunk belongs to                                      |
| `title`        | `str`   | Document title                                                     |
| `url`          | `str`   | Verified link to the document                                      |
| `category`     | `str`   | Document's top-level TOC section (e.g. "Getting Started")          |
| `score`        | `float` | Cosine similarity to the query (higher is more relevant)           |
| `last_updated` | `str`   | ISO timestamp of your last local `--sync`                          |

## Not exposed as MCP tools

- `--sync`, `--agent-*`, `--version`, `--help` are CLI-only (`osdocs-mcp`), not MCP
  tools/resources - see [Commands](COMMANDS.md).
