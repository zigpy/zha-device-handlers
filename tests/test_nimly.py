"""Tests for Nimly lock quirks."""

import zhaquirks
from zhaquirks.nimly.lock import (
    last_action_converter,
    last_action_source_converter,
    last_action_user_converter,
)

zhaquirks.setup()


def test_last_action_source_converter() -> None:
    """Test the last action source converter for Nimly Door Lock cluster."""
    assert last_action_source_converter(0x00020001) == "zigbee", (
        "Expected 'zigbee' for value 0x00010001"
    )
    assert last_action_source_converter(0x03010001) == "fingerprint", (
        "Expected 'fingerprint' for value 0x03010001"
    )
    assert last_action_source_converter(0x99010001) is None, (
        "Expected None for value 0x99010001"
    )


def test_last_action_converter() -> None:
    """Test the last action converter for Nimly Door Lock cluster."""
    assert last_action_converter(0x0A010001) == "lock", (
        "Expected 'lock' for value 0x0a010001"
    )
    assert last_action_converter(0x00020001) == "unlock", (
        "Expected 'unlock' for value 0x00020001"
    )
    assert last_action_converter(0x01030001) is None, (
        "Expected None for value 0x01030001"
    )


def test_last_action_user_converter() -> None:
    """Test the last action user converter for Nimly Door Lock cluster."""
    assert last_action_user_converter(0x01020001) == 1, (
        "Expected user ID 1 for value 0x01020001"
    )
    assert last_action_user_converter(0x02020010) == 16, (
        "Expected user ID 16 for value 0x02020010"
    )
