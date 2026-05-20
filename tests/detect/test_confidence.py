import pytest

from interlock.detect.confidence import flag_confidence


def test_perfect_inputs_give_unit_confidence() -> None:
    assert flag_confidence(extraction=1.0, match=1.0, authority=1.0) == 1.0


def test_components_multiply() -> None:
    assert flag_confidence(extraction=0.7, match=0.8, authority=1.0) == pytest.approx(0.56)


def test_clamps_above_unit() -> None:
    assert flag_confidence(extraction=1.5, match=1.0, authority=1.0) == 1.0


def test_clamps_below_zero() -> None:
    assert flag_confidence(extraction=-0.1, match=1.0, authority=1.0) == 0.0


def test_zero_input_gives_zero() -> None:
    assert flag_confidence(extraction=0.0, match=1.0, authority=1.0) == 0.0
