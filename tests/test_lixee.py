"""Tests for LiXee ZLinky_TIC quirks."""

from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.lixee import LIXEE, ZLINKY_MANUFACTURER_CLUSTER_ID
from zhaquirks.lixee.zlinky import ZLinkyTICManufacturerCluster, ZLinkyTICMetering


def test_zlinky_clusters_replaced(zigpy_device_from_v2_quirk) -> None:
    """Test that the ZLinky_TIC quirk replaces the expected clusters."""
    device = zigpy_device_from_v2_quirk(
        LIXEE,
        "ZLinky_TIC",
        cluster_ids={
            1: {
                Metering.cluster_id: None,
                ZLINKY_MANUFACTURER_CLUSTER_ID: None,
            }
        },
    )
    endpoint = device.endpoints[1]

    assert isinstance(endpoint.smartenergy_metering, ZLinkyTICMetering)
    assert isinstance(
        endpoint.zlinky_manufacturer_specific, ZLinkyTICManufacturerCluster
    )
    # Not all firmware variants report it, the quirk adds it unconditionally
    assert PowerConfiguration.cluster_id in endpoint.in_clusters
