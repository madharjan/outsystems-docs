"""Wiring tests for the FastMCP server: tools/resource delegate to the DocStore."""

import numpy as np

import osdocs.server as server
from osdocs.index import VectorIndex
from osdocs.store import DocStore


def _fake_store():
    return DocStore(
        combined_index="COMBINED INDEX",
        source_indexes={"odc": "ODC INDEX"},
        docs={"odc": {"a.md": "Full body."}},
        index=VectorIndex(
            np.array([[1.0, 0.0]], dtype=np.float32),
            [{"text": "a", "source": "odc", "source_path": "a.md", "section": "S",
              "title": "A", "url": "u"}],
        ),
        synced_at="2026-05-29T12:00:00+00:00",
    )


def test_server_resource_and_tools_delegate_to_store(monkeypatch):
    # Pre-load the module globals so nothing touches disk/network/model.
    monkeypatch.setattr(server, "_store", _fake_store())
    monkeypatch.setattr(server, "_embed", lambda texts: np.array([[1.0, 0.0]], dtype=np.float32))

    assert server.llms_index() == "COMBINED INDEX"

    doc = server.get_doc("odc", "a.md")
    assert doc["content"] == "Full body."
    assert doc["url"] == "u"
    assert doc["last_updated"] == "2026-05-29T12:00:00+00:00"

    missing = server.get_doc("odc", "missing.md")
    assert "not found" in missing["content"].lower()
    assert missing["url"] is None
    assert missing["last_updated"] is None

    payload = server.search_docs("anything", k=1)
    assert payload["results"][0]["source_path"] == "a.md"
    assert payload["results"][0]["url"] == "u"
    assert payload["results"][0]["last_updated"] == "2026-05-29T12:00:00+00:00"
    assert "last_updated" not in payload
    assert server.last_updated() == "2026-05-29T12:00:00+00:00"
