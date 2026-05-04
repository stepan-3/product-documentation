# Wallarm Docs MCP Server

A small [Model Context Protocol](https://modelcontextprotocol.io) server that
makes the markdown docs in this repo browsable, searchable, and readable from
any MCP-aware client (Claude Desktop, Claude Code, Cursor, Continue, custom
agents, etc.).

The server runs locally over stdio and reads files directly from the
`docs/` tree. No build step, no network calls.

## Tools

| Tool | Description |
| --- | --- |
| `list_versions()` | List doc versions/locales available under `docs/` (e.g. `latest`, `6.x`, `5.0`, `ja`, `ar`, `tr`, `pt-BR`). |
| `list_docs(version, subdir?, max_results?)` | List markdown files under `docs/<version>/<subdir>`. Returns repo-relative paths. |
| `search_docs(query, version?, limit?, subdir?)` | Full-text search; ranks files by term frequency and heading hits, returns paths + snippets. |
| `read_doc(path)` | Return the full markdown content for a repo-relative path such as `latest/sla.md`. |
| `get_doc_url(path)` | Map a repo path to its public `docs.wallarm.com` URL. |

## Install

Requires Python 3.10+.

```bash
cd mcp-server
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

## Run

```bash
wallarm-docs-mcp
# or
python server.py
```

By default the server resolves `docs/` relative to the repository root. To
point it at a docs checkout in a different location, set
`WALLARM_DOCS_ROOT` to the repo root.

## Client configuration

### Claude Desktop / Claude Code

Add an entry to your MCP config (`~/.claude/mcp.json` or
`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "wallarm-docs": {
      "command": "wallarm-docs-mcp",
      "env": {
        "WALLARM_DOCS_ROOT": "/absolute/path/to/product-documentation"
      }
    }
  }
}
```

If you prefer not to install the package, point `command` at `python` and
pass the script path:

```json
{
  "mcpServers": {
    "wallarm-docs": {
      "command": "python",
      "args": ["/absolute/path/to/product-documentation/mcp-server/server.py"],
      "env": {
        "WALLARM_DOCS_ROOT": "/absolute/path/to/product-documentation"
      }
    }
  }
}
```

### Cursor / Continue / other clients

Any MCP client that supports stdio servers works the same way — point it at
the `wallarm-docs-mcp` command (or `python server.py`) and it will discover
the tools above.

## Example agent flow

1. Call `search_docs("api discovery risk score")` to find relevant pages.
2. Call `read_doc("latest/api-discovery/risk-score.md")` on the top hit to
   pull the full content into context.
3. Call `get_doc_url("latest/api-discovery/risk-score.md")` to cite the
   public URL in the answer.
