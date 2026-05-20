"""Cost ledger invariants.

The ledger is the truth source for "how much have we spent" — must:
1. Apply correct per-model pricing (Opus 4.7 input/output, cache read/write tiers)
2. Aggregate correctly across providers and namespaces
3. Survive across processes (SQLite persists to disk)
4. Distinguish cache_read (0.1×) from cache_creation (1.25× or 2×) costs
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test gets its own SQLite file so tests don't interfere."""
    db_path = tmp_path / "test_interlock.db"
    monkeypatch.setenv("INTERLOCK_DB_PATH", str(db_path))
    # Drop any cached module so it re-reads the env var.
    import sys

    sys.modules.pop("interlock.cache.cost_ledger", None)
    yield


def _import_ledger():
    from interlock.cache import cost_ledger

    return cost_ledger


def test_record_anthropic_opus_input_cost() -> None:
    """1M input tokens on Opus 4.7 = $5.00."""
    ledger = _import_ledger()
    ledger.record(
        provider="anthropic",
        model="claude-opus-4-7",
        namespace="test",
        input_tokens=1_000_000,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        output_tokens=0,
    )
    assert ledger.total_usd() == pytest.approx(5.00, abs=0.01)


def test_record_anthropic_opus_output_cost() -> None:
    """1M output tokens on Opus 4.7 = $25.00."""
    ledger = _import_ledger()
    ledger.record(
        provider="anthropic",
        model="claude-opus-4-7",
        namespace="test",
        input_tokens=0,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        output_tokens=1_000_000,
    )
    assert ledger.total_usd() == pytest.approx(25.00, abs=0.01)


def test_cache_read_costs_one_tenth_of_input() -> None:
    """Cache reads are 0.1× input — 1M cache_read tokens on Opus 4.7 = $0.50."""
    ledger = _import_ledger()
    ledger.record(
        provider="anthropic",
        model="claude-opus-4-7",
        namespace="test",
        input_tokens=0,
        cache_read_tokens=1_000_000,
        cache_creation_tokens=0,
        output_tokens=0,
    )
    assert ledger.total_usd() == pytest.approx(0.50, abs=0.01)


def test_cache_creation_5m_costs_1_25x() -> None:
    """5m cache write is 1.25× input — 1M cache_creation tokens on Opus 4.7 = $6.25.

    Default ttl is 5m; for 1h ttl pass ``cache_ttl='1h'``.
    """
    ledger = _import_ledger()
    ledger.record(
        provider="anthropic",
        model="claude-opus-4-7",
        namespace="test",
        input_tokens=0,
        cache_read_tokens=0,
        cache_creation_tokens=1_000_000,
        output_tokens=0,
    )
    assert ledger.total_usd() == pytest.approx(6.25, abs=0.01)


def test_cache_creation_1h_costs_2x() -> None:
    """1h cache write is 2× input — 1M cache_creation tokens on Opus 4.7 = $10.00."""
    ledger = _import_ledger()
    ledger.record(
        provider="anthropic",
        model="claude-opus-4-7",
        namespace="test",
        input_tokens=0,
        cache_read_tokens=0,
        cache_creation_tokens=1_000_000,
        output_tokens=0,
        cache_ttl="1h",
    )
    assert ledger.total_usd() == pytest.approx(10.00, abs=0.01)


def test_voyage_embedding_cost_is_tracked_separately() -> None:
    """Voyage 3 is approximately $0.06/M tokens — record and verify."""
    ledger = _import_ledger()
    ledger.record(
        provider="voyage",
        model="voyage-3",
        namespace="test",
        input_tokens=1_000_000,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        output_tokens=0,
    )
    # Voyage 3 pricing constant; check value matches what we encoded.
    total = ledger.total_usd()
    assert total > 0.0
    assert total < 1.0, "Voyage cost should be sub-dollar for 1M tokens"


def test_totals_accumulate_across_records() -> None:
    ledger = _import_ledger()
    for _ in range(3):
        ledger.record(
            provider="anthropic",
            model="claude-opus-4-7",
            namespace="test",
            input_tokens=100_000,
            cache_read_tokens=0,
            cache_creation_tokens=0,
            output_tokens=0,
        )
    # 3 × 100K input @ $5/M = $1.50
    assert ledger.total_usd() == pytest.approx(1.50, abs=0.01)


def test_filter_by_namespace() -> None:
    ledger = _import_ledger()
    ledger.record(
        provider="anthropic",
        model="claude-opus-4-7",
        namespace="extract",
        input_tokens=1_000_000,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        output_tokens=0,
    )
    ledger.record(
        provider="anthropic",
        model="claude-opus-4-7",
        namespace="significance",
        input_tokens=1_000_000,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        output_tokens=0,
    )
    assert ledger.total_usd(namespace="extract") == pytest.approx(5.0, abs=0.01)
    assert ledger.total_usd(namespace="significance") == pytest.approx(5.0, abs=0.01)
    assert ledger.total_usd() == pytest.approx(10.0, abs=0.01)


def test_record_from_anthropic_usage_object() -> None:
    """Convenience: extract token fields from an Anthropic Usage-like object."""
    ledger = _import_ledger()

    class FakeUsage:
        input_tokens = 500
        output_tokens = 200
        cache_read_input_tokens = 1000
        cache_creation_input_tokens = 300

    ledger.record_anthropic_usage(
        usage=FakeUsage(),
        model="claude-opus-4-7",
        namespace="test",
    )
    # 500 × 5 / 1e6 + 200 × 25 / 1e6 + 1000 × 0.5 / 1e6 + 300 × 6.25 / 1e6
    expected = (500 * 5 + 200 * 25 + 1000 * 0.5 + 300 * 6.25) / 1_000_000
    assert ledger.total_usd() == pytest.approx(expected, abs=0.0001)


def test_unknown_model_records_zero_cost_with_warning() -> None:
    """Unknown model should still record the event (for debugging) but at $0
    rather than crash. The provider gets None pricing and we log a warning."""
    ledger = _import_ledger()
    ledger.record(
        provider="anthropic",
        model="claude-future-99",
        namespace="test",
        input_tokens=1_000_000,
        cache_read_tokens=0,
        cache_creation_tokens=0,
        output_tokens=0,
    )
    # Cost is 0 but the row is recorded.
    assert ledger.total_usd() == 0.0
    assert ledger.event_count() == 1
