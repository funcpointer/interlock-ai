from pathlib import Path

import yaml

GOLD = Path("fixtures/eval/gold.yaml")
REQUIRED_IDS = {"TP-1", "TP-2", "TP-3", "FP-1", "FP-2", "FN-1"}


def test_gold_set_complete_and_schema_valid() -> None:
    data = yaml.safe_load(GOLD.read_text())
    assert "flags" in data
    ids = {f["id"] for f in data["flags"]}
    assert REQUIRED_IDS <= ids, f"missing flag ids: {REQUIRED_IDS - ids}"
    for f in data["flags"]:
        assert {"id", "category", "expected", "doc_a", "doc_b"} <= set(
            f
        ), f"{f['id']} missing required keys"
        if f["expected"] == "surfaced":
            assert "min_confidence" in f, f"{f['id']} expected surfaced needs min_confidence"
        if f["expected"] == "suppressed":
            assert "max_confidence" in f, f"{f['id']} expected suppressed needs max_confidence"
