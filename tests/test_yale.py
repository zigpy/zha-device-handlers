"""Tests for Yale locks."""

import pytest

import zhaquirks
from zhaquirks.yale.lock import lang_converter, sound_volume_converter

zhaquirks.setup()


@pytest.mark.parametrize(
    ("raw_lang", "expected"),
    [
        # accounted for mappings
        ("en", "English"),
        ("fr", "French"),
        ("es", "Spanish"),
        # fallback
        ("de", "de"),
        ("unknown_code", "unknown_code"),
    ],
)
def test_lang_converter(raw_lang: str, expected: str):
    """Test language converter."""
    assert lang_converter(raw_lang) == expected


@pytest.mark.parametrize(
    ("raw_level", "expected"),
    [
        # accounted for mappings
        (0, "Silent"),
        (1, "Low volume"),
        (2, "High volume"),
        # fallback
        (3, "Unknown (3)"),
        (-1, "Unknown (-1)"),
        (None, "Unknown (None)"),
    ],
)
def test_sound_volume_converter(raw_level: int | None, expected: str):
    """Test sound volume level conversions."""
    assert sound_volume_converter(raw_level) == expected
