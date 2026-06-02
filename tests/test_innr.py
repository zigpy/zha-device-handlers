"""Tests for Innr quirks."""

import pytest
from zigpy.quirks.v2 import CustomDeviceV2
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.innr import ElectricalMeasurementClusterInnr, MeteringClusterInnrOld
from zhaquirks.quirk_ids import SE_POLL_SUMMATION

zhaquirks.setup()


@pytest.fixture
def innr_sp120(zigpy_device_from_v2_quirk):
    """Create an Innr SP 120 plug device."""
    return zigpy_device_from_v2_quirk(
        "innr",
        "SP 120",
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Server,
                Metering.cluster_id: ClusterType.Server,
                ElectricalMeasurement.cluster_id: ClusterType.Server,
            },
            2: {LightLink.cluster_id: ClusterType.Server},
        },
    )


def test_sp120_is_v2_quirked(innr_sp120):
    """Test that the SP 120 is quirked to the new v2 entry."""
    assert isinstance(innr_sp120, CustomDeviceV2)
    assert innr_sp120.quirk_metadata is not None
    assert innr_sp120.manufacturer == "innr"
    assert innr_sp120.model == "SP 120"


def test_sp120_replaced_clusters(innr_sp120):
    """Test that the metering and electrical measurement clusters are replaced."""
    metering = innr_sp120.endpoints[1].in_clusters[Metering.cluster_id]
    elec = innr_sp120.endpoints[1].in_clusters[ElectricalMeasurement.cluster_id]

    assert isinstance(metering, MeteringClusterInnrOld)
    assert isinstance(elec, ElectricalMeasurementClusterInnr)

    # MeteringClusterInnrOld pins divisor to 100 (old firmware fix)
    assert metering._CONSTANT_ATTRIBUTES[Metering.AttributeDefs.divisor.id] == 100
    assert metering._CONSTANT_ATTRIBUTES[Metering.AttributeDefs.multiplier.id] == 1


def test_sp120_exposes_poll_summation(innr_sp120):
    """Test that the SP 120 exposes the SE_POLL_SUMMATION feature for polling."""
    exposed_features = {
        feature.feature for feature in innr_sp120.quirk_metadata.exposes_features
    }
    assert SE_POLL_SUMMATION in exposed_features
