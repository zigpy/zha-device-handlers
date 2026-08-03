"""Tests for Stelpro/Stello quirks."""

from zigpy.zcl import ClusterType, foundation

import zhaquirks
from zhaquirks.stelpro.stlo23 import STELLO_MANUFACTURER_ID, STLO23TemperatureCluster

zhaquirks.setup()


def test_stlo23_temperature_cluster_replaced(zigpy_device_from_v2_quirk):
    """Ensure STLO-23 uses the custom manufacturer temperature cluster."""

    device = zigpy_device_from_v2_quirk(
        manufacturer="Stello",
        model="STLO-23",
        cluster_ids={1: {STLO23TemperatureCluster.cluster_id: ClusterType.Server}},
    )
    cluster = device.endpoints[1].in_clusters[STLO23TemperatureCluster.cluster_id]

    assert isinstance(cluster, STLO23TemperatureCluster)
    assert cluster.ep_attribute == "stlo23_temperature_cluster"
    assert cluster.manufacturer_id_override == STELLO_MANUFACTURER_ID
    assert cluster.find_attribute("current_temp") == cluster.AttributeDefs.current_temp
    assert (
        cluster.AttributeDefs.current_temp.access
        == foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Report
    )
    assert (
        cluster.AttributeDefs.current_temp.manufacturer_code == STELLO_MANUFACTURER_ID
    )
