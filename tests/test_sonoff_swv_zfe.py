"""Tests for Sonoff SWV-ZFE smart water valve quirk."""

import pytest
from zigpy.zcl import ClusterType

import zhaquirks
from zhaquirks.sonoff.swv_zfe import (
    SWVZFECluster,
    swvzfe_be_swap,
    swvzfe_fail_safe,
    swvzfe_frost_protection,
    swvzfe_water_leakage,
    swvzfe_water_shortage,
)

zhaquirks.setup()


def test_swvzfe_be_swap() -> None:
    """Test that swvzfe_be_swap correctly reverses the byte order of a uint32."""
    # Device sends 300 as big-endian bytes; zigpy reads it as little-endian
    assert swvzfe_be_swap(0x2C010000) == 300
    # Round-trip: swapping twice should return the original value
    assert swvzfe_be_swap(swvzfe_be_swap(0xDEADBEEF)) == 0xDEADBEEF
    # Zero is invariant under byte-swap
    assert swvzfe_be_swap(0) == 0
    assert swvzfe_be_swap(None) is None


@pytest.mark.parametrize(
    ("value", "water_shortage", "water_leakage", "frost_protection", "fail_safe"),
    [
        (0x00, False, False, False, False),
        (0x01, True, False, False, False),
        (0x02, False, True, False, False),
        (0x04, False, False, True, False),
        (0x08, False, False, False, True),
        (0x0F, True, True, True, True),
        (0x05, True, False, True, False),
    ],
    ids=["none", "shortage", "leakage", "frost", "failsafe", "all", "shortage+frost"],
)
def test_swvzfe_valve_abnormal_state_converters(
    value, water_shortage, water_leakage, frost_protection, fail_safe
) -> None:
    """Test all valve_abnormal_state bit-extraction converter functions."""
    assert swvzfe_water_shortage(value) == water_shortage
    assert swvzfe_water_leakage(value) == water_leakage
    assert swvzfe_frost_protection(value) == frost_protection
    assert swvzfe_fail_safe(value) == fail_safe


def test_swvzfe_converters_handle_none() -> None:
    """All converter functions must return None when given None."""
    assert swvzfe_water_shortage(None) is None
    assert swvzfe_water_leakage(None) is None
    assert swvzfe_frost_protection(None) is None
    assert swvzfe_fail_safe(None) is None


def test_swvzfe_quirk_applies(zigpy_device_from_v2_quirk) -> None:
    """Verify the SWV-ZFE quirk is registered and replaces cluster 0xFC11."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SWV-ZFE",
        cluster_ids={1: {SWVZFECluster.cluster_id: ClusterType.Server}},
    )
    assert SWVZFECluster.cluster_id in device.endpoints[1].in_clusters
    assert isinstance(
        device.endpoints[1].in_clusters[SWVZFECluster.cluster_id], SWVZFECluster
    )
