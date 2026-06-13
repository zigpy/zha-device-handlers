"""Tests for Innr quirks."""

import pytest
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.innr import MeteringClusterInnrNew, MeteringClusterInnrOld

zhaquirks.setup()

# firmware version that fixed the metering divisor bug (max_version is exclusive)
SP240_DIVISOR_FIX_FW_VERSION = 0x191B3685


@pytest.mark.parametrize(
    ("firmware_version", "expected_cluster", "expected_divisor"),
    [
        # firmware before the fix uses the old override (divisor 100)
        (
            SP240_DIVISOR_FIX_FW_VERSION - 1,
            MeteringClusterInnrOld,
            100,
        ),
        # the fixed firmware and newer use the new override (divisor 1000)
        (
            SP240_DIVISOR_FIX_FW_VERSION,
            MeteringClusterInnrNew,
            1000,
        ),
        (
            SP240_DIVISOR_FIX_FW_VERSION + 1,
            MeteringClusterInnrNew,
            1000,
        ),
        # a device that does not report a firmware version is treated as new
        # (the new quirk has allow_missing=True, the old one allow_missing=False)
        (
            None,
            MeteringClusterInnrNew,
            1000,
        ),
    ],
)
def test_innr_sp240_firmware_version_metering(
    zigpy_device_from_v2_quirk,
    firmware_version,
    expected_cluster,
    expected_divisor,
):
    """Test the correct Innr SP 240 quirk is selected based on firmware version."""
    device = zigpy_device_from_v2_quirk(
        "innr", "SP 240", firmware_version=firmware_version
    )

    metering_cluster = device.endpoints[1].smartenergy_metering
    assert isinstance(metering_cluster, expected_cluster)

    # the constant divisor override is applied regardless of what the device reports
    assert metering_cluster.get(Metering.AttributeDefs.divisor.id) == expected_divisor
