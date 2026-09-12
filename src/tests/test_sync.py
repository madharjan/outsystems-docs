"""Tests for Use Case #7: orchestrate the sync pipeline (fetch + embed injected)."""

from datetime import datetime, timezone

import numpy as np

import osdocs.sync as sync_module
from osdocs.fetch import DocSource, FetchResult
from osdocs.index import load_index
from osdocs.sync import main as sync_main
from osdocs.sync import sync_sources


def fake_embed(texts):
    return np.array([[float(len(t))] for t in texts], dtype=np.float32)


def make_fetch(results):
    def fetch(source):
        return results[source.name]

    return fetch


def test_sync_writes_per_source_and_combined_artifacts(tmp_path):
    toc = "# Getting Started\n- href: getting-started/intro.md\n"
    docs = {"getting-started/intro.md": "# Intro\n\nWelcome to ODC.\n"}
    source = DocSource(
        name="odc", repo="r", branch="main",
        label="OutSystems Developer Cloud (ODC)", summary="ODC docs.",
    )
    fetch = make_fetch({"odc": FetchResult(toc=toc, docs=docs)})

    report = sync_sources([source], tmp_path, fetch=fetch, embed=fake_embed)

    # Per-source index uses the real comment-derived section title.
    odc_llms = (tmp_path / "odc" / "llms.txt").read_text(encoding="utf-8")
    assert odc_llms.startswith("# OutSystems Developer Cloud (ODC)")
    assert "## Getting Started" in odc_llms
    assert (tmp_path / "odc" / "llms-full.txt").exists()

    # Combined top-level index labels the platform.
    combined = (tmp_path / "llms.txt").read_text(encoding="utf-8")
    assert "## OutSystems Developer Cloud (ODC)" in combined

    # Vector index built from the source-tagged chunks.
    index = load_index(tmp_path / "vectors.npz")
    assert len(index.chunks) >= 1
    assert index.chunks[0]["source"] == "odc"
    assert index.chunks[0]["category"] == "Getting Started"

    assert report.num_sources == 1


def test_sync_combines_multiple_sources_keeping_platforms_tagged(tmp_path):
    odc = DocSource(name="odc", repo="r1", label="OutSystems Developer Cloud (ODC)")
    o11 = DocSource(name="o11", repo="r2", branch="master", label="OutSystems 11 (O11)")
    fetch = make_fetch({
        "odc": FetchResult(toc="# A\n- href: a/intro.md\n", docs={"a/intro.md": "ODC body\n"}),
        "o11": FetchResult(toc="# B\n- href: b/intro.md\n", docs={"b/intro.md": "O11 body\n"}),
    })

    report = sync_sources([odc, o11], tmp_path, fetch=fetch, embed=fake_embed)

    combined = (tmp_path / "llms.txt").read_text(encoding="utf-8")
    assert "## OutSystems Developer Cloud (ODC)" in combined
    assert "## OutSystems 11 (O11)" in combined
    assert (tmp_path / "odc" / "llms.txt").exists()
    assert (tmp_path / "o11" / "llms.txt").exists()

    index = load_index(tmp_path / "vectors.npz")
    assert {c["source"] for c in index.chunks} == {"odc", "o11"}
    assert report.num_sources == 2


def test_sync_reports_progress(tmp_path):
    msgs = []
    source = DocSource(name="odc", repo="r", label="ODC", summary="s.")
    toc = "# GS\n- href: a/intro.md\n"
    docs = {"a/intro.md": "# Intro\n\nbody\n"}

    sync_sources(
        [source], tmp_path, fetch=lambda s: FetchResult(toc=toc, docs=docs),
        embed=fake_embed, progress=msgs.append,
    )

    joined = "\n".join(msgs)
    assert "odc" in joined  # per-source stage reported
    assert any("embed" in m.lower() for m in msgs)  # the slow step is announced


def test_sync_writes_synced_at_timestamp(tmp_path):
    source = DocSource(name="odc", repo="r", label="ODC", summary="s.")
    fixed = datetime(2026, 5, 29, 12, 0, 0, tzinfo=timezone.utc)

    report = sync_sources(
        [source], tmp_path,
        fetch=lambda s: FetchResult(toc="# A\n- href: a.md\n", docs={"a.md": "# A\n\nb\n"}),
        embed=fake_embed, now=lambda: fixed,
    )

    assert (tmp_path / "synced_at.txt").read_text(encoding="utf-8").strip() == fixed.isoformat()
    assert report.synced_at == fixed.isoformat()


def test_sync_resolves_canonical_urls_from_sitemap(tmp_path):
    source = DocSource(name="odc", repo="r", label="ODC", summary="s.")
    toc = "# GS\n- href: getting-started/sample-app.md\n"
    docs = {"getting-started/sample-app.md": "# Build a basic Web app\n\nbody\n"}
    sitemap = [
        "https://success.outsystems.com/documentation/outsystems_developer_cloud/"
        "getting_started/build_a_basic_web_app/",
    ]

    sync_sources(
        [source], tmp_path, fetch=lambda s: FetchResult(toc=toc, docs=docs),
        embed=fake_embed, sitemap_urls=sitemap,
    )

    index = load_index(tmp_path / "vectors.npz")
    # The chunk's url is the verified canonical URL resolved from the H1 title.
    assert index.chunks[0]["url"] == sitemap[0]


def _stub_fetch_and_embed(monkeypatch, docs_by_source):
    """Replace the real git clone and fastembed model load with fakes."""

    def fake_git_fetch(source):
        return docs_by_source[source.name]

    monkeypatch.setattr(sync_module, "_git_fetch", fake_git_fetch)
    monkeypatch.setattr("osdocs.embed.fastembed_embedder", lambda: fake_embed)


class TestSyncMainCli:
    """Tests for main()'s argparse dispatch: --data-dir, --source, --no-links."""

    def _docs(self):
        return {
            "odc": FetchResult(toc="# A\n- href: a.md\n", docs={"a.md": "# A\n\nodc body\n"}),
            "o11": FetchResult(toc="# B\n- href: b.md\n", docs={"b.md": "# B\n\no11 body\n"}),
        }

    def test_defaults_to_all_sources(self, tmp_path, monkeypatch):
        _stub_fetch_and_embed(monkeypatch, self._docs())

        report = sync_main(["--data-dir", str(tmp_path), "--no-links"])

        assert report.num_sources == 2
        assert (tmp_path / "odc").exists()
        assert (tmp_path / "o11").exists()

    def test_source_flag_filters_to_one_source(self, tmp_path, monkeypatch):
        _stub_fetch_and_embed(monkeypatch, self._docs())

        report = sync_main(["--data-dir", str(tmp_path), "--source", "odc", "--no-links"])

        assert report.num_sources == 1
        assert (tmp_path / "odc").exists()
        assert not (tmp_path / "o11").exists()

    def test_data_dir_defaults_to_data_under_app_root(self, tmp_path, monkeypatch):
        """--data-dir's default ("data") resolves relative to the app/repo root, not cwd
        -- an MCP client launches the server from an unrelated cwd, so this must match
        wherever the server itself looks (see osdocs.config.resolve_path)."""
        monkeypatch.setattr("osdocs.config.get_app_root", lambda: tmp_path)
        _stub_fetch_and_embed(monkeypatch, self._docs())

        sync_main(["--source", "odc", "--no-links"])

        assert (tmp_path / "data" / "odc").exists()

    def test_no_links_skips_sitemap_fetch(self, tmp_path, monkeypatch):
        _stub_fetch_and_embed(monkeypatch, self._docs())

        def fail_if_called(cache_path, warn=None):
            raise AssertionError("fetch_sitemap_with_cache should not be called with --no-links")

        monkeypatch.setattr(sync_module, "fetch_sitemap_with_cache", fail_if_called)

        sync_main(["--data-dir", str(tmp_path), "--source", "odc", "--no-links"])

    def test_sync_continues_when_sitemap_fetch_fails(self, tmp_path, monkeypatch):
        """Link resolution is best-effort: a sitemap failure must not fail the sync."""
        _stub_fetch_and_embed(monkeypatch, self._docs())

        def raise_error(cache_path, warn=None):
            raise RuntimeError("network unavailable")

        monkeypatch.setattr(sync_module, "fetch_sitemap_with_cache", raise_error)

        report = sync_main(["--data-dir", str(tmp_path), "--source", "odc"])

        assert report.num_sources == 1
