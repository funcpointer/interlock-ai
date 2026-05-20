"""Persistent on-disk cache wrapper.

Wraps diskcache with content-hash-based keys so cache invalidation is
automatic when inputs change. Values are pickled by diskcache, so any
picklable object (including Pydantic models) round-trips intact.

Design notes
------------
- ``namespace`` is a logical scope (``"llm-significance"``, ``"voyage-embeddings"``,
  ``"ingest-spans"``) so a single workstream's cache can be cleared without
  touching siblings.
- ``payload`` is the cache key material — anything that identifies the
  semantic input. We serialize with ``json.dumps(sort_keys=True)`` so dict
  insertion order doesn't matter and the resulting bytes are deterministic.
- Compute closures only run on a cache miss. The returned ``(value, hit)``
  tuple lets callers observe and report hit rate.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, TypeVar

import diskcache

T = TypeVar("T")

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# 2 GB cap; eviction strategy is LRU per diskcache default.
_cache: diskcache.Cache = diskcache.Cache(str(CACHE_DIR), size_limit=int(2e9))


def _key(namespace: str, payload: dict[str, Any]) -> str:
    """Build a stable cache key from namespace + sorted-JSON payload.

    Same logical payload → same key regardless of dict insertion order.
    Different namespace → different key even with identical payload.
    """
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    digest = hashlib.sha256(blob).hexdigest()
    return f"{namespace}:{digest}"


def get_or_compute(
    namespace: str,
    payload: dict[str, Any],
    compute: Callable[[], T],
) -> tuple[T, bool]:
    """Return ``(value, hit)``. ``compute`` runs only on cache miss.

    ``hit`` is True when the value was served from the cache.
    """
    key = _key(namespace, payload)
    if key in _cache:
        value = _cache[key]
        return value, True
    value = compute()
    _cache[key] = value
    return value, False


def clear_namespace(namespace: str) -> int:
    """Drop every key whose namespace prefix matches. Returns count cleared.

    Iterating ``_cache`` returns all keys; we filter to the namespace prefix
    and delete in a single pass. For small caches this is cheap; for very
    large caches we may want a secondary index, but that's premature now.
    """
    prefix = f"{namespace}:"
    n = 0
    for k in list(_cache):
        if isinstance(k, str) and k.startswith(prefix):
            del _cache[k]
            n += 1
    return n


def stats() -> dict[str, int]:
    """Lifetime hit / miss counters since the cache was created."""
    hits, misses = _cache.stats(enable=False)
    return {"hits": int(hits), "misses": int(misses)}
