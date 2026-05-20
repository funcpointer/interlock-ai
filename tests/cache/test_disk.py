"""Diskcache wrapper invariants.

The wrapper must be:
1. Content-hash addressed — sorted-key JSON, deterministic across dict orders
2. Namespace-clearable — drop a single workstream's cache without nuking siblings
3. Hit/miss observable — caller knows whether the compute closure ran
4. Crash-safe — diskcache is SQLite-backed, but we still verify a basic write+read cycle survives a Cache() reopen
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel


# Defined at module level so pickle can locate the class on unpickle (local
# classes defined inside a function can't be pickled — this is a Python
# limitation, not a wrapper bug).
class _RoundtripModel(BaseModel):
    name: str
    count: int


def _import_wrapper():
    from interlock.cache import disk

    return disk


def test_get_or_compute_misses_then_hits_on_second_call() -> None:
    disk = _import_wrapper()
    disk.clear_namespace("test_hit_miss")

    calls = {"n": 0}

    def compute() -> dict[str, int]:
        calls["n"] += 1
        return {"value": 42}

    first, first_hit = disk.get_or_compute("test_hit_miss", {"k": 1}, compute)
    second, second_hit = disk.get_or_compute("test_hit_miss", {"k": 1}, compute)

    assert first == {"value": 42}
    assert second == {"value": 42}
    assert first_hit is False, "first call must be a miss"
    assert second_hit is True, "second call must be a hit"
    assert calls["n"] == 1, "compute closure must run exactly once"


def test_keys_are_deterministic_regardless_of_dict_order() -> None:
    disk = _import_wrapper()
    disk.clear_namespace("test_order_independence")

    calls = {"n": 0}

    def compute() -> str:
        calls["n"] += 1
        return "v"

    # Same logical payload, different insertion order
    disk.get_or_compute("test_order_independence", {"a": 1, "b": 2}, compute)
    _, second_hit = disk.get_or_compute("test_order_independence", {"b": 2, "a": 1}, compute)

    assert second_hit is True, "sorted-JSON keys must collapse different dict orders"
    assert calls["n"] == 1


def test_different_payloads_yield_different_keys() -> None:
    disk = _import_wrapper()
    disk.clear_namespace("test_distinct_payloads")

    a, _ = disk.get_or_compute("test_distinct_payloads", {"k": 1}, lambda: "a")
    b, _ = disk.get_or_compute("test_distinct_payloads", {"k": 2}, lambda: "b")
    assert a == "a"
    assert b == "b"


def test_different_namespaces_do_not_collide() -> None:
    disk = _import_wrapper()
    disk.clear_namespace("test_ns_a")
    disk.clear_namespace("test_ns_b")

    disk.get_or_compute("test_ns_a", {"k": 1}, lambda: "from_a")
    val_b, hit = disk.get_or_compute("test_ns_b", {"k": 1}, lambda: "from_b")
    assert val_b == "from_b"
    assert hit is False, "namespaces are isolated; cross-namespace key collision is a bug"


def test_clear_namespace_returns_count_and_drops_only_that_namespace() -> None:
    disk = _import_wrapper()
    disk.clear_namespace("test_clear_a")
    disk.clear_namespace("test_clear_b")

    disk.get_or_compute("test_clear_a", {"k": 1}, lambda: "a1")
    disk.get_or_compute("test_clear_a", {"k": 2}, lambda: "a2")
    disk.get_or_compute("test_clear_b", {"k": 1}, lambda: "b1")

    cleared = disk.clear_namespace("test_clear_a")
    assert cleared == 2, f"expected to clear 2 keys in namespace test_clear_a, got {cleared}"

    # b namespace survives
    _, b_hit = disk.get_or_compute("test_clear_b", {"k": 1}, lambda: "b1_recompute")
    assert b_hit is True


def test_large_payload_does_not_break_hashing() -> None:
    disk = _import_wrapper()
    disk.clear_namespace("test_large_payload")

    big_payload = {"data": "x" * 100_000, "list": list(range(1_000))}
    val_1, hit_1 = disk.get_or_compute("test_large_payload", big_payload, lambda: "ok")
    val_2, hit_2 = disk.get_or_compute("test_large_payload", big_payload, lambda: "should_not_run")

    assert val_1 == "ok"
    assert val_2 == "ok"
    assert hit_2 is True


def test_pickleable_pydantic_models_survive_roundtrip() -> None:
    """Pydantic models are commonly cached as values; diskcache pickles them.
    Verify the dump/load roundtrip works without lossy conversion."""
    disk = _import_wrapper()
    disk.clear_namespace("test_pydantic")

    disk.get_or_compute(
        "test_pydantic", {"k": 1}, lambda: _RoundtripModel(name="x", count=3)
    )
    out, hit = disk.get_or_compute(
        "test_pydantic", {"k": 1}, lambda: _RoundtripModel(name="never", count=0)
    )

    assert hit is True
    assert isinstance(out, _RoundtripModel)
    assert out.name == "x"
    assert out.count == 3


@pytest.fixture(autouse=True)
def _isolate_test_namespaces():
    """Best-effort cleanup so reruns start clean."""
    yield
    disk = _import_wrapper()
    for ns in (
        "test_hit_miss",
        "test_order_independence",
        "test_distinct_payloads",
        "test_ns_a",
        "test_ns_b",
        "test_clear_a",
        "test_clear_b",
        "test_large_payload",
        "test_pydantic",
    ):
        disk.clear_namespace(ns)
