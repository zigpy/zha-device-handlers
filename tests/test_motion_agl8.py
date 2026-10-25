"""Tests for Aqara FP300 (lumi.sensor_occupy.agl8)."""

import pytest
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, PowerConfiguration

from tests.common import ClusterListener
from zhaquirks.xiaomi import AQARA, XIAOMI_AQARA_ATTRIBUTE_E1
from zhaquirks.xiaomi.aqara.motion_agl8 import (
    AqaraFP300ManuCluster,
    FP300PowerConfigurationVoltage,
)


def create_aqara_attr_report(attributes):
    """Create an Aqara E1 TLV report payload."""
    serialized_data = b""
    for key, value in attributes.items():
        tv = foundation.TypeValue(0x39, t.Single(value))
        serialized_data += bytes([key]) + tv.serialize()
    return serialized_data


def test_fp300_device_creation(zigpy_device_from_v2_quirk):
    """Test that the FP300 quirked device is created as expected."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")

    assert device.manufacturer == AQARA
    assert device.model == "lumi.sensor_occupy.agl8"
    assert 1 in device.endpoints
    assert Basic.cluster_id in device.endpoints[1].in_clusters


def test_fp300_endpoint_clusters_present(zigpy_device_from_v2_quirk):
    """Test that endpoint 1 contains the FP300 manufacturer cluster."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    endpoint = device.endpoints[1]

    assert AqaraFP300ManuCluster.cluster_id in endpoint.in_clusters
    assert isinstance(endpoint.aqara_fp300_manu, AqaraFP300ManuCluster)


def test_fp300_power_configuration_cluster_present(zigpy_device_from_v2_quirk):
    """Test that endpoint 1 exposes the FP300 power configuration cluster."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    endpoint = device.endpoints[1]

    assert PowerConfiguration.cluster_id in endpoint.in_clusters
    assert isinstance(
        endpoint.in_clusters[PowerConfiguration.cluster_id],
        FP300PowerConfigurationVoltage,
    )


def test_aqara_fp300_battery_from_e1_tlv(zigpy_device_from_v2_quirk):
    """Test battery updates from Aqara E1 TLV report."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")

    manu_cluster = device.endpoints[1].in_clusters[AqaraFP300ManuCluster.cluster_id]
    power_cluster = device.endpoints[1].power
    power_listener = ClusterListener(power_cluster)

    zcl_power_voltage_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    zcl_power_percent_id = (
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
    )

    manu_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE_E1,
        create_aqara_attr_report({23: 2950, 24: 87}),
    )

    assert len(power_listener.attribute_updates) == 2
    assert power_listener.attribute_updates[0][0] == zcl_power_voltage_id
    assert power_listener.attribute_updates[0][1] == pytest.approx(29.5)
    assert power_listener.attribute_updates[1][0] == zcl_power_percent_id
    assert power_listener.attribute_updates[1][1] == 150


def test_aqara_fp300_ignores_device_reported_percentage(zigpy_device_from_v2_quirk):
    """Test that the device's own battery percentage report is ignored in favor of voltage."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    power_cluster = device.endpoints[1].power

    power_cluster.battery_percent_reported(50)

    assert (
        power_cluster.get(
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
        )
        is None
    )


def test_fp300_presence_binary_sensor_updates(zigpy_device_from_v2_quirk):
    """Test that presence reports update the occupancy attribute."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu

    manu_cluster.update_attribute(AqaraFP300ManuCluster.AttributeDefs.presence.id, True)

    assert manu_cluster.get(AqaraFP300ManuCluster.AttributeDefs.presence.id) is True
