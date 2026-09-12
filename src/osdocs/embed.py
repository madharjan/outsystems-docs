"""Real embedder adapter backed by ``fastembed`` (ONNX, fully local).

``fastembed`` is imported lazily and the model is constructed on first use, so the ~100MB
model downloads only when an actual embed happens — never at import or in the test suite.
On corrupt cache (NoSuchFile), clears the cache and retries once.
"""

from __future__ import annotations

import os
import shutil
import warnings
from pathlib import Path

import numpy as np

from osdocs.logging_util import get_logger

logger = get_logger(__name__)

DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
DEFAULT_CACHE_DIR = ".cache/fastembed"


def _fastembed_cache_path() -> Path:
    """Resolve the fastembed model cache directory.

    Priority: ``FASTEMBED_CACHE_PATH`` env var (fastembed's own convention) > ``embeddings.cache_dir``
    in config.yaml > built-in default.
    """
    from osdocs.config import get_app_config, resolve_path

    env_override = os.getenv("FASTEMBED_CACHE_PATH")
    if env_override:
        return resolve_path(env_override).resolve()

    cache_dir = get_app_config().get("embeddings.cache_dir", DEFAULT_CACHE_DIR)
    return resolve_path(cache_dir).resolve()


def _clear_fastembed_cache():
    """Clear the fastembed model cache to recover from corruption."""
    cache_dir = _fastembed_cache_path()
    if cache_dir.exists():
        shutil.rmtree(cache_dir, ignore_errors=True)


def _provider_name(entry) -> str:
    """A configured provider entry is either a plain name or ``{name, options}``."""
    return entry if isinstance(entry, str) else entry["name"]


def _to_ort_provider(entry):
    """Convert a configured provider entry to onnxruntime's expected form.

    onnxruntime accepts a plain provider name, or a ``(name, options_dict)`` tuple for
    provider-specific options (e.g. DirectML's ``disable_metacommands``, a workaround for
    ``DXGI_ERROR_DEVICE_HUNG`` crashes some AMD driver/model combinations hit on the default
    metacommand path).
    """
    if isinstance(entry, str):
        return entry
    return (entry["name"], entry.get("options", {}))


def fastembed_embedder(model_name: str = DEFAULT_MODEL):
    """Return an ``embed(list[str]) -> np.ndarray`` callable backed by ``fastembed``.

    The model is loaded lazily on the first call (this is when the download happens).
    On corrupt cache (NoSuchFile), clears the cache and retries once.
    Supports GPU/CPU configuration via config.yaml.
    """
    from osdocs.config import get_app_config

    model = None
    cache_path = _fastembed_cache_path()
    cache_path.mkdir(parents=True, exist_ok=True)
    os.environ["FASTEMBED_CACHE_PATH"] = str(cache_path)

    if get_app_config().get("embeddings.disable_hf_symlinks", False):
        os.environ["HF_HUB_DISABLE_SYMLINKS"] = "1"

    # huggingface_hub's own tqdm progress bar for the model download ("Download complete:
    # 100%|..."); --sync already reports its own progress, so this is just noise.
    os.environ.setdefault("HF_HUB_DISABLE_PROGRESS_BARS", "1")

    # fastembed calls huggingface_hub's enable_progress_bars() internally, which warns
    # because the env var above wins over that call -- expected, so silence it.
    warnings.filterwarnings(
        "ignore",
        message="Cannot enable progress bars.*",
        category=UserWarning,
        module="huggingface_hub.*",
    )

    def embed(texts):
        nonlocal model
        if model is None:
            import onnxruntime as ort
            from fastembed import TextEmbedding
            from osdocs.config import get_app_config

            config = get_app_config()
            providers = config.get("embeddings.providers", ["CUDAExecutionProvider", "CPUExecutionProvider"])

            # Drop providers onnxruntime doesn't have compiled in *before* constructing
            # TextEmbedding: it raises on an unavailable provider rather than skipping it,
            # so a naive CPU-only retry would also discard a later, available GPU provider
            # (e.g. configured [CUDA, Dml, CPU] on a DirectML-only install would skip Dml).
            available = set(ort.get_available_providers())
            provider_list = [
                _to_ort_provider(p) for p in providers if _provider_name(p) in available
            ] or ["CPUExecutionProvider"]
            skipped = [_provider_name(p) for p in providers if _provider_name(p) not in available]
            if skipped:
                logger.warning(f"Providers not available, skipping: {skipped}. Using: {provider_list}")

            # Try with the filtered providers, fall back to CPU only on a genuine runtime failure
            for attempt, attempt_providers in enumerate([provider_list, ["CPUExecutionProvider"]]):
                try:
                    model = TextEmbedding(model_name, providers=attempt_providers)
                    if attempt > 0:
                        logger.info("Successfully loaded model with CPU provider")
                    break
                except Exception as e:
                    error_msg = str(e)

                    # If it's a provider availability/runtime error, try CPU
                    if ("not available" in error_msg or "CUDA" in error_msg) and attempt == 0:
                        logger.warning(f"GPU not available: {error_msg}. Falling back to CPU...")
                        continue

                    # If it's a model loading error, clear cache and retry once
                    if ("Load model" in error_msg or "InvalidArgument" in error_msg) and attempt == 0:
                        logger.warning(f"Model loading failed: {error_msg}")
                        logger.info("Clearing cache and retrying...")
                        _clear_fastembed_cache()
                        try:
                            model = TextEmbedding(model_name, providers=["CPUExecutionProvider"])
                            logger.info("Model loaded successfully after cache clear")
                            break
                        except Exception as retry_error:
                            logger.error(f"Model loading failed again: {retry_error}")
                            raise

                    # If cache is corrupt (NoSuchFile), clear and retry
                    if "NoSuchFile" in e.__class__.__name__ or "File doesn't exist" in error_msg:
                        logger.warning("Cache corruption detected. Clearing and retrying...")
                        _clear_fastembed_cache()
                        try:
                            model = TextEmbedding(model_name, providers=["CPUExecutionProvider"])
                            break
                        except Exception as retry_error:
                            raise retry_error

                    # All fallbacks exhausted
                    raise e

        try:
            return np.array(list(model.embed(list(texts))), dtype=np.float32)
        except Exception as e:
            # A GPU provider can construct a session fine and still crash mid-inference
            # (e.g. DXGI_ERROR_DEVICE_HUNG on some AMD/DirectML driver+model combos).
            # Rebuild on CPU and retry once; if CPU also fails, let it raise.
            logger.error(f"Embedding inference failed: {e}. Rebuilding model on CPU and retrying...")
            from fastembed import TextEmbedding

            model = TextEmbedding(model_name, providers=["CPUExecutionProvider"])
            return np.array(list(model.embed(list(texts))), dtype=np.float32)

    return embed
