"""Tests for the SONOFF MINI-ZB1GP device."""

from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

import zhaquirks
from zhaquirks.sonoff.mini_zb1gp import (
    SonoffMiniZb1gpCluster,
    milli_to_value,
    signed_int32_milli_to_value,
)

zhaquirks.setup()


def test_mini_zb1gp_cluster_replaced(zigpy_device_from_v2_quirk):
    """Test that the Sonoff manufacturer cluster is replaced."""

    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "MINI-ZB1GP",
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Server,
                Metering.cluster_id: ClusterType.Server,
                ElectricalMeasurement.cluster_id: ClusterType.Server,
                SonoffMiniZb1gpCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    assert isinstance(
        device.endpoints[1].in_clusters[SonoffMiniZb1gpCluster.cluster_id],
        SonoffMiniZb1gpCluster,
    )


def test_mini_zb1gp_attribute_definitions():
    """Test Sonoff manufacturer-specific attribute definitions."""

    assert SonoffMiniZb1gpCluster.AttributeDefs.current.id == 0x7004
    assert SonoffMiniZb1gpCluster.AttributeDefs.voltage.id == 0x7005
    assert SonoffMiniZb1gpCluster.AttributeDefs.power.id == 0x7006
    assert SonoffMiniZb1gpCluster.AttributeDefs.energy_today.id == 0x7009
    assert SonoffMiniZb1gpCluster.AttributeDefs.energy_month.id == 0x700A
    assert SonoffMiniZb1gpCluster.AttributeDefs.total_energy.id == 0x701E


def test_mini_zb1gp_milli_value_converters():
    """Test converters for raw Sonoff milli-unit values."""

    assert milli_to_value(483) == 0.483
    assert milli_to_value(238678) == 238.678
    assert signed_int32_milli_to_value(93255) == 93.255
    assert signed_int32_milli_to_value(0xFFFFFC18) == -1.0
