"""SQLite-backed cost ledger for LLM and embedding API calls.

Every call records one row. Aggregation is at query time so we can
reconstruct spend by provider, model, namespace, or time window without
denormalization.

Pricing
-------
Pricing constants are inline with citations. Anthropic publishes per-1M-token
prices for input + output, plus cache_read (0.1× input) and cache_creation
multipliers (1.25× for 5-minute TTL, 2× for 1-hour TTL). Voyage 3 has a flat
per-token rate for embeddings.

Database path is set via ``INTERLOCK_DB_PATH`` env var (defaults to
``data/interlock.db``). The DB file is created on first use; the schema
in ``data/interlock.schema.sql`` is applied idempotently.
"""

from __future__ import annotations

import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Anthropic Claude pricing per 1M tokens (USD).
# Source: https://platform.claude.com/docs/en/pricing (May 2026)
# Input/output rates; cache_read = 0.1× input; cache_creation_5m = 1.25× input;
# cache_creation_1h = 2× input.
_ANTHROPIC_PRICING: dict[str, dict[str, float]] = {
    "claude-opus-4-7": {"input": 5.00, "output": 25.00},
    "claude-opus-4-6": {"input": 5.00, "output": 25.00},
    "claude-sonnet-4-6": {"input": 3.00, "output": 15.00},
    "claude-haiku-4-5": {"input": 1.00, "output": 5.00},
}

# Voyage AI embedding pricing per 1M tokens (USD).
# Source: https://docs.voyageai.com/docs/pricing
_VOYAGE_PRICING: dict[str, float] = {
    "voyage-3": 0.06,
    "voyage-3-large": 0.18,
    "voyage-3-lite": 0.02,
}


def _db_path() -> Path:
    return Path(os.environ.get("INTERLOCK_DB_PATH", "data/interlock.db"))


def _schema_path() -> Path:
    return Path("data/interlock.schema.sql")


def _connect() -> sqlite3.Connection:
    db = _db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db)
    # Apply schema idempotently. Schema file uses CREATE IF NOT EXISTS.
    if _schema_path().exists():
        conn.executescript(_schema_path().read_text())
    conn.commit()
    return conn


def _anthropic_cost(
    model: str,
    input_tokens: int,
    cache_read_tokens: int,
    cache_creation_tokens: int,
    output_tokens: int,
    cache_ttl: str = "5m",
) -> float:
    pricing = _ANTHROPIC_PRICING.get(model)
    if pricing is None:
        logger.warning("Unknown Anthropic model %r; recording at $0.00", model)
        return 0.0
    in_rate = pricing["input"]
    out_rate = pricing["output"]
    cache_write_mult = 2.0 if cache_ttl == "1h" else 1.25
    total = (
        input_tokens * in_rate
        + output_tokens * out_rate
        + cache_read_tokens * in_rate * 0.1
        + cache_creation_tokens * in_rate * cache_write_mult
    ) / 1_000_000.0
    return total


def _voyage_cost(model: str, input_tokens: int) -> float:
    rate = _VOYAGE_PRICING.get(model)
    if rate is None:
        logger.warning("Unknown Voyage model %r; recording at $0.00", model)
        return 0.0
    return input_tokens * rate / 1_000_000.0


def _estimate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    cache_read_tokens: int,
    cache_creation_tokens: int,
    output_tokens: int,
    cache_ttl: str,
) -> float:
    if provider == "anthropic":
        return _anthropic_cost(
            model,
            input_tokens,
            cache_read_tokens,
            cache_creation_tokens,
            output_tokens,
            cache_ttl,
        )
    if provider == "voyage":
        return _voyage_cost(model, input_tokens)
    logger.warning("Unknown provider %r; recording at $0.00", provider)
    return 0.0


def record(
    *,
    provider: str,
    model: str,
    namespace: str,
    input_tokens: int = 0,
    cache_read_tokens: int = 0,
    cache_creation_tokens: int = 0,
    output_tokens: int = 0,
    cache_ttl: str = "5m",
) -> float:
    """Record one API call's cost. Returns the estimated USD cost stored.

    ``cache_ttl`` is only used to pick the cache-creation multiplier; pass
    ``"1h"`` when the corresponding ``cache_control`` block on the API call
    used the 1-hour TTL.
    """
    cost = _estimate_cost(
        provider,
        model,
        input_tokens,
        cache_read_tokens,
        cache_creation_tokens,
        output_tokens,
        cache_ttl,
    )
    conn = _connect()
    try:
        conn.execute(
            """
            INSERT INTO cost_event(
                provider, model, namespace,
                input_tokens, cache_read_tokens, cache_creation_tokens, output_tokens,
                est_cost_usd
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                provider,
                model,
                namespace,
                int(input_tokens),
                int(cache_read_tokens),
                int(cache_creation_tokens),
                int(output_tokens),
                float(cost),
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return cost


def record_anthropic_usage(
    *,
    usage: Any,
    model: str,
    namespace: str,
    cache_ttl: str = "5m",
) -> float:
    """Convenience: extract token counts from an Anthropic SDK Usage object."""
    return record(
        provider="anthropic",
        model=model,
        namespace=namespace,
        input_tokens=int(getattr(usage, "input_tokens", 0) or 0),
        cache_read_tokens=int(getattr(usage, "cache_read_input_tokens", 0) or 0),
        cache_creation_tokens=int(getattr(usage, "cache_creation_input_tokens", 0) or 0),
        output_tokens=int(getattr(usage, "output_tokens", 0) or 0),
        cache_ttl=cache_ttl,
    )


def total_usd(
    *,
    namespace: str | None = None,
    provider: str | None = None,
    since: str | None = None,
) -> float:
    """Aggregate cost. Filters are AND-combined."""
    where_parts: list[str] = []
    params: list[Any] = []
    if namespace is not None:
        where_parts.append("namespace = ?")
        params.append(namespace)
    if provider is not None:
        where_parts.append("provider = ?")
        params.append(provider)
    if since is not None:
        where_parts.append("ts >= ?")
        params.append(since)
    where = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    conn = _connect()
    try:
        row = conn.execute(
            f"SELECT COALESCE(SUM(est_cost_usd), 0.0) FROM cost_event {where}",
            params,
        ).fetchone()
    finally:
        conn.close()
    return float(row[0])


def event_count() -> int:
    conn = _connect()
    try:
        row = conn.execute("SELECT COUNT(*) FROM cost_event").fetchone()
    finally:
        conn.close()
    return int(row[0])


@dataclass(frozen=True)
class Summary:
    total_usd: float
    n_events: int
    by_provider: dict[str, float]
    by_namespace: dict[str, float]


def summary(since: str | None = None) -> Summary:
    """Pull a single aggregate snapshot for the UI footer."""
    conn = _connect()
    try:
        where = "WHERE ts >= ?" if since is not None else ""
        params: list[Any] = [since] if since is not None else []

        total = float(
            conn.execute(
                f"SELECT COALESCE(SUM(est_cost_usd), 0.0) FROM cost_event {where}",
                params,
            ).fetchone()[0]
        )
        n = int(
            conn.execute(
                f"SELECT COUNT(*) FROM cost_event {where}",
                params,
            ).fetchone()[0]
        )
        by_provider = {
            r[0]: float(r[1])
            for r in conn.execute(
                f"SELECT provider, COALESCE(SUM(est_cost_usd), 0.0) "
                f"FROM cost_event {where} GROUP BY provider",
                params,
            ).fetchall()
        }
        by_namespace = {
            r[0]: float(r[1])
            for r in conn.execute(
                f"SELECT namespace, COALESCE(SUM(est_cost_usd), 0.0) "
                f"FROM cost_event {where} GROUP BY namespace",
                params,
            ).fetchall()
        }
    finally:
        conn.close()
    return Summary(total_usd=total, n_events=n, by_provider=by_provider, by_namespace=by_namespace)
