"""Tests for LiXee ZLinky_TIC quirks."""

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.lixee import LIXEE, ZLINKY_MANUFACTURER_CLUSTER_ID
from zhaquirks.lixee.zlinky import ZLinkyTICManufacturerCluster, ZLinkyTICMetering
from zhaquirks.tuya import TuyaManufCluster


def test_zlinky_clusters_replaced(zigpy_device_from_v2_quirk) -> None:
    """Test that the ZLinky_TIC quirk replaces the expected clusters."""
    device = zigpy_device_from_v2_quirk(
        LIXEE,
        "ZLinky_TIC",
        cluster_ids={
            1: {
                Metering.cluster_id: ClusterType.Server,
                ZLINKY_MANUFACTURER_CLUSTER_ID: ClusterType.Server,
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


@pytest.mark.parametrize("cluster_type", [ClusterType.Server, ClusterType.Client])
def test_zlinky_tuya_cluster_removed(zigpy_device_from_v2_quirk, cluster_type) -> None:
    """Test that the Tuya cluster firmware v14+ reports is removed.

    The v1 quirk dropped it implicitly, by listing it in the FWV14 and FWV15
    signatures but not in their replacements. That is what the two ZLinky
    entries in test_suspicious_cluster_moves recorded; this test replaces them.

    Parametrized over both directions: the device reports the cluster as an
    input and an output cluster, and each removal has to be exercised on its
    own or the assertion for the other direction passes vacuously.
    """
    device = zigpy_device_from_v2_quirk(
        LIXEE,
        "ZLinky_TIC",
        cluster_ids={
            1: {
                ZLINKY_MANUFACTURER_CLUSTER_ID: ClusterType.Server,
                TuyaManufCluster.cluster_id: cluster_type,
            }
        },
    )
    endpoint = device.endpoints[1]

    assert TuyaManufCluster.cluster_id not in endpoint.in_clusters
    assert TuyaManufCluster.cluster_id not in endpoint.out_clusters
