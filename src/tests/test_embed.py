"""Tests for the fastembed adapter with cache recovery."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from osdocs.embed import (
    DEFAULT_CACHE_DIR,
    _fastembed_cache_path,
    _provider_name,
    _to_ort_provider,
    fastembed_embedder,
)


class _FakeConfig:
    """Minimal stand-in for AppConfig.get(key, default)."""

    def __init__(self, values=None):
        self._values = values or {}

    def get(self, key, default=None):
        return self._values.get(key, default)


def test_fastembed_handles_corrupt_cache():
    """When model cache is corrupt (file missing), clear cache and retry.

    Simulates: fastembed detects file-size mismatch, fails to re-download,
    then TextEmbedding raises NoSuchFile on __init__. Our embedder should
    recover by clearing the cache and retrying.
    """
    call_count = 0

    class NoSuchFile(Exception):
        """Simulate onnxruntime.capi.onnxruntime_pybind11_state.NoSuchFile."""
        pass

    def mock_text_embedding(model_name, providers=None):
        """Simulate: first call fails (corrupt cache), second call succeeds."""
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            # First call: corrupt cache
            raise NoSuchFile("Load model .../model_optimized.onnx failed. File doesn't exist")
        else:
            # Second call: cache was cleared, model loads
            mock_model = MagicMock()
            mock_model.embed = lambda texts: [[0.1, 0.2, 0.3]] * len(texts)
            return mock_model

    # Patch at the point of import (inside the embed function)
    with patch("fastembed.TextEmbedding", side_effect=mock_text_embedding):
        embedder = fastembed_embedder("BAAI/bge-small-en-v1.5")
        result = embedder(["hello world"])

        # Should have succeeded on retry
        assert result.shape == (1, 3)
        assert call_count == 2  # First call failed, second succeeded


def test_fastembed_retry_still_fails():
    """When cache clear + retry still fails, raise the original error."""
    class NoSuchFile(Exception):
        """Simulate onnxruntime.capi.onnxruntime_pybind11_state.NoSuchFile."""
        pass

    def mock_text_embedding_always_fails(model_name, providers=None):
        """Always fail — even after cache clear."""
        raise NoSuchFile("Load model failed (unrecoverable)")

    with patch("fastembed.TextEmbedding", side_effect=mock_text_embedding_always_fails):
        embedder = fastembed_embedder("BAAI/bge-small-en-v1.5")
        with pytest.raises(NoSuchFile, match="unrecoverable"):
            embedder(["hello world"])


def test_embed_returns_result_on_every_call_not_just_the_first():
    """Regression: embed() must return real embeddings on every call, not just the first.

    The model-loading success path used to `return` from inside `if model is None:`, so once
    the model was cached, every later call fell through the function with no return
    statement and silently returned None. index.py's np.vstack then choked on a batch of
    shape (1,) mixed in with real (n, dim) batches.
    """
    construct_count = 0

    def mock_text_embedding(model_name, providers=None):
        nonlocal construct_count
        construct_count += 1
        mock_model = MagicMock()
        mock_model.embed = lambda texts: [[0.1, 0.2, 0.3]] * len(texts)
        return mock_model

    with patch("fastembed.TextEmbedding", side_effect=mock_text_embedding):
        embedder = fastembed_embedder("BAAI/bge-small-en-v1.5")

        first = embedder(["batch one"])
        second = embedder(["batch two", "another text"])
        third = embedder(["batch three"])

        assert first.shape == (1, 3)
        assert second.shape == (2, 3)  # would previously be a corrupt (1,) scalar array
        assert third.shape == (1, 3)
        assert construct_count == 1  # model loaded once, reused on later calls


def test_embed_falls_back_to_cpu_on_runtime_inference_crash(monkeypatch):
    """A GPU provider can build a session fine and still crash mid-inference (e.g.
    DXGI_ERROR_DEVICE_HUNG on some AMD/DirectML driver+model combos). embed() should
    rebuild the model on CPU and retry once rather than propagate the crash."""
    monkeypatch.setattr("onnxruntime.get_available_providers", lambda: ["CPUExecutionProvider"])
    construct_count = 0

    def mock_text_embedding(model_name, providers=None):
        nonlocal construct_count
        construct_count += 1
        mock_model = MagicMock()
        if construct_count == 1:
            def crash(texts):
                raise RuntimeError("DXGI_ERROR_DEVICE_HUNG")

            mock_model.embed = crash
        else:
            mock_model.embed = lambda texts: [[0.1, 0.2, 0.3]] * len(texts)
        return mock_model

    with patch("fastembed.TextEmbedding", side_effect=mock_text_embedding):
        embedder = fastembed_embedder("BAAI/bge-small-en-v1.5")
        result = embedder(["hello"])

    assert result.shape == (1, 3)
    assert construct_count == 2  # first (crashing) model + CPU rebuild


def test_embed_raises_when_cpu_fallback_also_fails(monkeypatch):
    """If the CPU rebuild also crashes, the error must propagate, not loop or swallow."""
    monkeypatch.setattr("onnxruntime.get_available_providers", lambda: ["CPUExecutionProvider"])

    def mock_text_embedding(model_name, providers=None):
        mock_model = MagicMock()

        def crash(texts):
            raise RuntimeError("still broken")

        mock_model.embed = crash
        return mock_model

    with patch("fastembed.TextEmbedding", side_effect=mock_text_embedding):
        embedder = fastembed_embedder("BAAI/bge-small-en-v1.5")
        with pytest.raises(RuntimeError, match="still broken"):
            embedder(["hello"])


class TestProviderEntries:
    """A configured provider is a plain name or {name, options} for onnxruntime options
    (e.g. DirectML's disable_metacommands, a workaround for AMD DXGI device hangs)."""

    def test_provider_name_plain_string(self):
        assert _provider_name("CPUExecutionProvider") == "CPUExecutionProvider"

    def test_provider_name_dict_entry(self):
        entry = {"name": "DmlExecutionProvider", "options": {"disable_metacommands": True}}
        assert _provider_name(entry) == "DmlExecutionProvider"

    def test_to_ort_provider_plain_string_passthrough(self):
        assert _to_ort_provider("CPUExecutionProvider") == "CPUExecutionProvider"

    def test_to_ort_provider_dict_entry_becomes_tuple(self):
        entry = {"name": "DmlExecutionProvider", "options": {"disable_metacommands": True}}
        assert _to_ort_provider(entry) == ("DmlExecutionProvider", {"disable_metacommands": True})

    def test_to_ort_provider_dict_entry_without_options_defaults_to_empty_dict(self):
        assert _to_ort_provider({"name": "DmlExecutionProvider"}) == ("DmlExecutionProvider", {})


def test_fastembed_embedder_passes_provider_options_to_text_embedding(monkeypatch):
    """DmlExecutionProvider configured with options must reach TextEmbedding as a
    (name, options) tuple, e.g. disable_metacommands to work around AMD DXGI device hangs."""
    monkeypatch.setattr(
        "onnxruntime.get_available_providers",
        lambda: ["DmlExecutionProvider", "CPUExecutionProvider"],
    )
    monkeypatch.setattr(
        "osdocs.config.get_app_config",
        lambda: _FakeConfig(
            {
                "embeddings.providers": [
                    {"name": "DmlExecutionProvider", "options": {"disable_metacommands": True}},
                    "CPUExecutionProvider",
                ]
            }
        ),
    )

    captured = {}

    def mock_text_embedding(model_name, providers=None):
        captured["providers"] = providers
        mock_model = MagicMock()
        mock_model.embed = lambda texts: [[0.1, 0.2, 0.3]] * len(texts)
        return mock_model

    with patch("fastembed.TextEmbedding", side_effect=mock_text_embedding):
        embedder = fastembed_embedder("BAAI/bge-small-en-v1.5")
        embedder(["hello"])

    assert captured["providers"] == [
        ("DmlExecutionProvider", {"disable_metacommands": True}),
        "CPUExecutionProvider",
    ]


def test_fastembed_embedder_skips_unavailable_configured_provider_by_name(monkeypatch):
    """A dict-form provider not in onnxruntime's available list must be dropped like a
    plain-string one -- filtering matches on name, not on the whole entry."""
    monkeypatch.setattr(
        "onnxruntime.get_available_providers",
        lambda: ["CPUExecutionProvider"],
    )
    monkeypatch.setattr(
        "osdocs.config.get_app_config",
        lambda: _FakeConfig(
            {
                "embeddings.providers": [
                    {"name": "DmlExecutionProvider", "options": {"disable_metacommands": True}},
                    "CPUExecutionProvider",
                ]
            }
        ),
    )

    captured = {}

    def mock_text_embedding(model_name, providers=None):
        captured["providers"] = providers
        mock_model = MagicMock()
        mock_model.embed = lambda texts: [[0.1, 0.2, 0.3]] * len(texts)
        return mock_model

    with patch("fastembed.TextEmbedding", side_effect=mock_text_embedding):
        embedder = fastembed_embedder("BAAI/bge-small-en-v1.5")
        embedder(["hello"])

    assert captured["providers"] == ["CPUExecutionProvider"]


class TestFastembedCachePath:
    """Tests for _fastembed_cache_path()'s env-var > config > default precedence."""

    def test_env_var_takes_priority_over_config(self, monkeypatch):
        monkeypatch.setenv("FASTEMBED_CACHE_PATH", "env-cache-dir")
        monkeypatch.setattr(
            "osdocs.config.get_app_config",
            lambda: _FakeConfig({"embeddings.cache_dir": "config-cache-dir"}),
        )

        result = _fastembed_cache_path()

        assert result == Path("env-cache-dir").expanduser().resolve()

    def test_falls_back_to_config_cache_dir_when_no_env_var(self, monkeypatch):
        monkeypatch.delenv("FASTEMBED_CACHE_PATH", raising=False)
        monkeypatch.setattr(
            "osdocs.config.get_app_config",
            lambda: _FakeConfig({"embeddings.cache_dir": "config-cache-dir"}),
        )

        result = _fastembed_cache_path()

        assert result == Path("config-cache-dir").expanduser().resolve()

    def test_uses_builtin_default_when_no_env_var_or_config_value(self, monkeypatch):
        monkeypatch.delenv("FASTEMBED_CACHE_PATH", raising=False)
        monkeypatch.setattr("osdocs.config.get_app_config", lambda: _FakeConfig({}))

        result = _fastembed_cache_path()

        assert result == Path(DEFAULT_CACHE_DIR).expanduser().resolve()
