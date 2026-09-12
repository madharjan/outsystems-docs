"""FastMCP server exposing the OutSystems documentation store over stdio.

Serves the combined ``llms.txt`` as a navigation resource and ``get_doc`` / ``search_docs``
as tools. The store and the (local) query embedder are loaded lazily on first use, so the
model downloads only when a search actually runs — never at import.
"""

from __future__ import annotations

import os
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from osdocs.config import load_app_config, get_app_config, resolve_path
from osdocs.embed import fastembed_embedder
from osdocs.logging_util import get_logger
from osdocs.store import load_store

# Load configuration at startup
load_app_config()
_config = get_app_config()
logger = get_logger(__name__)

# Set HF_TOKEN from config if available
hf_token = _config.get("secrets.hf_token", "")
if hf_token:
    os.environ["HF_TOKEN"] = hf_token

DATA_DIR = resolve_path(os.environ.get("OSDOCS_INDEX_DATA_DIR", None) or _config.get("index.data_dir", "data"))

mcp = FastMCP("outsystems-docs")
_store = None
_embed = None


def _ensure_loaded():
    global _store, _embed
    if _store is None:
        _store = load_store(DATA_DIR)
    if _embed is None:
        _embed = fastembed_embedder()
    return _store, _embed


@mcp.resource("llms://index")
def llms_index() -> str:
    """The combined OutSystems ODC + O11 documentation index (llms.txt)."""
    store, _ = _ensure_loaded()
    return store.navigation()


@mcp.tool()
def get_doc(source: str, path: str) -> dict:
    """Return ``{"content", "url", "last_updated"}`` for a document. ``source`` is ``odc`` or
    ``o11``. ``content`` explains the problem instead of Markdown when not found."""
    store, _ = _ensure_loaded()
    doc = store.get_doc(source, path)
    if doc is None:
        return {"content": f"Document not found: {source}/{path}", "url": None, "last_updated": None}
    return doc


@mcp.tool()
def search_docs(
    query: str, k: int = 5, source: str | None = None, category: str | None = None
) -> dict:
    """Semantic search over the docs. Optionally scope to one platform (``odc``/``o11``)
    and/or one ``category`` (a document's top-level TOC section, e.g. "Getting Started" -
    see a result's ``category`` field for exact values to filter on).

    Returns ``{"results": [...]}``. Each result carries its own ``url`` (verified link to the
    source doc) and ``last_updated``, so the caller can cite and link every result without a
    separate lookup. Call the ``last_updated`` tool directly for freshness with no results.
    """
    store, embed = _ensure_loaded()
    query_vector = embed([query])[0]
    return {"results": store.search(query_vector, k=k, source=source, category=category)}


@mcp.tool()
def last_updated() -> str:
    """Return the ISO timestamp of the last docs sync (when the local data was built)."""
    store, _ = _ensure_loaded()
    return store.synced_at or "unknown"


def main() -> None:
    """Run the MCP server over stdio (entry point: ``osdocs-server``)."""
    mcp.run()


if __name__ == "__main__":
    main()
