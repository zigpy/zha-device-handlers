"""Tests for Nous quirks."""

import zhaquirks

zhaquirks.setup()


def test_nous_e10_quirk_loads():
    """Test that the Nous E10 CO2 sensor quirk file loads and registers without errors."""
    # The quirk is auto-registered when the module is imported
    # This test ensures the file has no syntax/import errors and registers successfully
    import zhaquirks.tuya.nous_e10_co2  # noqa: F401
