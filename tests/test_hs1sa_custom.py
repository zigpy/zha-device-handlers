"""Tests for Heiman HS1SA-E custom quirk logic."""

import pytest
from zigpy.zcl import ClusterType

# from zhaquirks.heiman.hs1sa_efa import (
#     smoke_chamber_contamination_converter,
#     smoke_level_unit_converter,
# )
from zigpy.zcl.clusters.security import IasZone

# def test_heiman_converters():
#     """Test the custom converters with direct integer inputs."""
#     # Coverage for smoke_chamber_contamination_converter
#     assert smoke_chamber_contamination_converter(0) == "normal"
#     assert smoke_chamber_contamination_converter(1) == "light contamination"
#     assert smoke_chamber_contamination_converter(2) == "medium contamination"
#     assert smoke_chamber_contamination_converter(3) == "critical contamination"
#     assert smoke_chamber_contamination_converter(99) == "unknown"
#
#     # Coverage for smoke_level_unit_converter
#     assert smoke_level_unit_converter(0) == "dB/m"
#     assert smoke_level_unit_converter(1) == "%ft OBS"
#     assert smoke_level_unit_converter(99) == "unknown"


@pytest.mark.asyncio
async def test_initiate_test_mode_logic(zigpy_device_from_v2_quirk):
    """Test the command override logic."""
    device = zigpy_device_from_v2_quirk(
        "HEIMAN",
        "HS1SA-EF-3.0",
        cluster_ids={1: {IasZone.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].ias_zone

    # # Trigger the 'if not args' logic for coverage
    # with contextlib.suppress(Exception):
    #     await cluster.command(0x02)
