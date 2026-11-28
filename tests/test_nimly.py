"""Tests for Nimly lock quirks."""

import pytest

import zhaquirks
from zhaquirks.nimly.lock import (
    last_action_converter,
    last_action_source_converter,
    last_action_user_converter,
)

zhaquirks.setup()


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0x00020001, "zigbee"),
        (0x02020003, "keypad"),
        (0x03010001, "fingerprint"),
        (0x04020005, "rfid"),
        (0x05010000, "unattributed"),
        (0x0A010000, "auto"),
        (0x99010001, "unknown"),
    ],
)
def test_last_action_source_converter(value: int, expected: str) -> None:
    """Test the last action source converter for Nimly Door Lock cluster."""
    assert last_action_source_converter(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0x0A010000, "lock"),
        (0x00020001, "unlock"),
        (0x02020003, "unlock"),
        (0x01030001, "unknown"),
    ],
)
def test_last_action_converter(value: int, expected: str) -> None:
    """Test the last action converter for Nimly Door Lock cluster."""
    assert last_action_converter(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0x01020001, 1),
        (0x02020010, 16),
        (0x02020003, 3),
        (0x0A010000, 0),
    ],
)
def test_last_action_user_converter(value: int, expected: int) -> None:
    """Test the last action user converter for Nimly Door Lock cluster."""
    assert last_action_user_converter(value) == expected
