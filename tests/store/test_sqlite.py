"""SQLite store invariants for entity / claim / decision (Phase 14).

The store is the persistent home for the entity-claim graph that Phase 14
introduces. Tests assert:

1. Schema is applied idempotently (first call creates tables; subsequent
   calls are no-ops).
2. Upsert semantics — re-persisting the same Entity / Claim by id is a
   no-op, not a constraint violation.
3. Query by entity + attribute returns claims grouped correctly.
4. Decisions persist with audit fields (timestamp + verdict).
5. Round-trip survives process restart (file-backed SQLite).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from interlock.extract.entities import Claim, Entity
from interlock.extract.parameters import ParameterRecord


@pytest.fixture(autouse=True)
def _isolated_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Each test gets its own SQLite file so tests don't interfere."""
    db_path = tmp_path / "test_interlock.db"
    monkeypatch.setenv("INTERLOCK_DB_PATH", str(db_path))
    # Drop the cost_ledger module too — it also uses INTERLOCK_DB_PATH.
    import sys

    sys.modules.pop("interlock.store.sqlite", None)
    sys.modules.pop("interlock.cache.cost_ledger", None)
    yield


def _import_store():
    from interlock.store import sqlite as store

    return store


def _record(name: str, raw: str, doc: str = "doc_a", span: str | None = None) -> ParameterRecord:
    return ParameterRecord(
        doc_id=doc,
        page=1,
        bbox=(10.0, 20.0, 110.0, 30.0),
        section="2.1 Spec",
        span_text=span if span is not None else f"{name}: {raw}",
        name=name,
        raw_value=raw,
        normalized_magnitude=None,
        normalized_unit=None,
    )


def _claim(entity_id: str = "xfmr_001", attribute: str = "imp_pct", value: str = "5.75 %") -> Claim:
    return Claim(
        entity=Entity(id=entity_id, type="transformer", label=entity_id.upper()),
        attribute=attribute,
        raw_value=value,
        source_record=_record("Impedance", value),
    )


# ----- Entity persistence -----


def test_persist_entity_inserts_row() -> None:
    store = _import_store()
    e = Entity(id="xfmr_001", type="transformer", label="XFMR-001")
    store.upsert_entity(e)
    stored = store.get_entity("xfmr_001")
    assert stored == e


def test_upsert_entity_is_idempotent() -> None:
    store = _import_store()
    e = Entity(id="xfmr_001", type="transformer", label="XFMR-001")
    store.upsert_entity(e)
    store.upsert_entity(e)
    store.upsert_entity(e)
    assert store.entity_count() == 1


def test_get_missing_entity_returns_none() -> None:
    store = _import_store()
    assert store.get_entity("nonexistent") is None


# ----- Claim persistence -----


def test_persist_claim_inserts_row_and_implicit_entity() -> None:
    """Persisting a Claim must also persist its entity (FK requirement)."""
    store = _import_store()
    c = _claim()
    store.upsert_claim(c)
    stored = store.get_entity(c.entity.id)
    assert stored == c.entity


def test_claim_id_is_deterministic() -> None:
    """Same logical claim produces the same id — required for upsert."""
    store = _import_store()
    c1 = _claim()
    c2 = _claim()
    id1 = store.claim_id(c1)
    id2 = store.claim_id(c2)
    assert id1 == id2


def test_upsert_claim_is_idempotent() -> None:
    store = _import_store()
    c = _claim()
    store.upsert_claim(c)
    store.upsert_claim(c)
    assert store.claim_count() == 1


def test_claims_for_entity_returns_all() -> None:
    store = _import_store()
    store.upsert_claim(_claim(attribute="imp_pct", value="5.75 %"))
    store.upsert_claim(_claim(attribute="rated_kva", value="1000 kVA"))
    # Different entity, same attribute — should not appear
    store.upsert_claim(
        Claim(
            entity=Entity(id="xfmr_002", type="transformer", label="XFMR-002"),
            attribute="imp_pct",
            raw_value="6.0 %",
            source_record=_record("Impedance", "6.0 %"),
        )
    )
    out = store.claims_for_entity("xfmr_001")
    assert len(out) == 2
    assert {c.attribute for c in out} == {"imp_pct", "rated_kva"}


def test_claims_for_attribute_returns_across_entities() -> None:
    """For tolerance/comparison checks the caller wants all claims about a
    given (canonical) attribute across all entities — Phase 16 leverages this."""
    store = _import_store()
    store.upsert_claim(_claim(entity_id="xfmr_001", attribute="imp_pct", value="5.75 %"))
    store.upsert_claim(_claim(entity_id="xfmr_002", attribute="imp_pct", value="6.0 %"))
    store.upsert_claim(_claim(entity_id="xfmr_001", attribute="rated_kva", value="1000 kVA"))
    out = store.claims_for_attribute("imp_pct")
    assert len(out) == 2
    assert {c.entity.id for c in out} == {"xfmr_001", "xfmr_002"}


# ----- Decision persistence -----


def test_record_decision_inserts_row_with_timestamp() -> None:
    store = _import_store()
    store.record_decision(
        fixture_pair_id="option_1",
        flag_id="flag_abc",
        verdict="accepted",
        reviewer="kc",
    )
    decisions = store.decisions_for_pair("option_1")
    assert len(decisions) == 1
    d = decisions[0]
    assert d.flag_id == "flag_abc"
    assert d.verdict == "accepted"
    assert d.reviewer == "kc"
    assert d.created_at  # populated


def test_decisions_filter_by_pair() -> None:
    store = _import_store()
    store.record_decision(fixture_pair_id="pair_a", flag_id="f1", verdict="accepted")
    store.record_decision(fixture_pair_id="pair_b", flag_id="f1", verdict="dismissed")
    assert len(store.decisions_for_pair("pair_a")) == 1
    assert len(store.decisions_for_pair("pair_b")) == 1


# ----- Schema idempotency -----


def test_schema_applies_idempotently() -> None:
    """Re-importing the store (which applies schema) on an existing DB
    must not raise."""
    store = _import_store()
    store.upsert_entity(Entity(id="x", type="implicit", label="x"))
    # Force re-init
    store.init_schema()
    assert store.get_entity("x") is not None


# ----- Persistence across process boundary -----


def test_data_survives_db_close_and_reopen() -> None:
    """The store is file-backed; explicit close + re-import returns the same
    data. This is the 'survives across process restart' invariant."""
    store = _import_store()
    e = Entity(id="xfmr_001", type="transformer", label="XFMR-001")
    store.upsert_entity(e)
    # Force the module to forget its cached connection (if any) — we don't
    # cache connections in this implementation but the test pins that
    # behavior regardless.
    import sys

    sys.modules.pop("interlock.store.sqlite", None)
    store2 = _import_store()
    assert store2.get_entity("xfmr_001") == e
