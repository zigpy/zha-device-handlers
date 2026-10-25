"""Tests for Aqara FP300 (lumi.sensor_occupy.agl8)."""

from unittest import mock

import pytest
import zigpy.types as t
from zigpy.zcl import Cluster, foundation
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
    """Test battery voltage from tag 23 and percentage from tag 24 of the E1 TLV report."""
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
        create_aqara_attr_report({23: 3012, 24: 100}),
    )

    assert len(power_listener.attribute_updates) == 2
    assert power_listener.attribute_updates[0][0] == zcl_power_voltage_id
    assert power_listener.attribute_updates[0][1] == pytest.approx(30.1)
    assert power_listener.attribute_updates[1][0] == zcl_power_percent_id
    assert power_listener.attribute_updates[1][1] == 200


def test_aqara_fp300_ignores_standard_battery_reports(zigpy_device_from_v2_quirk):
    """Test that standard PowerConfiguration reports can't overwrite the TLV values."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu
    power_cluster = device.endpoints[1].power

    voltage_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    percent_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    manu_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE_E1, create_aqara_attr_report({23: 2950, 24: 75})
    )
    assert power_cluster.get(voltage_id) == pytest.approx(29.5)
    assert power_cluster.get(percent_id) == 150

    # Contradicting reports on the standard cluster are dropped
    power_cluster.update_attribute(percent_id, 0)
    power_cluster.update_attribute(voltage_id, 0)
    assert power_cluster.get(voltage_id) == pytest.approx(29.5)
    assert power_cluster.get(percent_id) == 150

    # The next TLV report still updates both
    manu_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE_E1, create_aqara_attr_report({23: 2900, 24: 70})
    )
    assert power_cluster.get(voltage_id) == pytest.approx(29.0)
    assert power_cluster.get(percent_id) == 140


def test_aqara_fp300_no_battery_without_tlv(zigpy_device_from_v2_quirk):
    """Test that nothing is cached from standard reports before the first TLV report."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    power_cluster = device.endpoints[1].power

    power_cluster.update_attribute(
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.id, 0
    )

    assert (
        power_cluster.get(
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
        )
        is None
    )


async def test_aqara_fp300_bind_reads_tlv_struct(zigpy_device_from_v2_quirk):
    """Test that binding also reads the Aqara TLV struct and that the response updates the battery."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu
    power_cluster = device.endpoints[1].power

    record = foundation.ReadAttributeRecord(
        attrid=XIAOMI_AQARA_ATTRIBUTE_E1,
        status=foundation.Status.SUCCESS,
        value=foundation.TypeValue(
            type=foundation.DataTypeId.octstr,
            value=create_aqara_attr_report({23: 2987, 24: 91}),
        ),
    )

    with (
        mock.patch.object(
            Cluster, "bind", new_callable=mock.AsyncMock, return_value=[0]
        ),
        mock.patch.object(
            manu_cluster,
            "read_attributes_raw",
            new_callable=mock.AsyncMock,
            return_value=[[record]],
        ) as mock_read,
    ):
        assert await manu_cluster.bind() == [0]

    mock_read.assert_awaited_once()
    assert mock_read.mock_calls[0].args[0] == [XIAOMI_AQARA_ATTRIBUTE_E1]
    assert mock_read.mock_calls[0].kwargs["manufacturer"] == 0x115F
    assert power_cluster.get(
        PowerConfiguration.AttributeDefs.battery_voltage.id
    ) == pytest.approx(29.9)
    assert (
        power_cluster.get(
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
        )
        == 182
    )


async def test_aqara_fp300_bind_survives_read_failure(zigpy_device_from_v2_quirk):
    """Test that a failing TLV read doesn't fail the bind."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu

    with (
        mock.patch.object(
            Cluster, "bind", new_callable=mock.AsyncMock, return_value=[0]
        ),
        mock.patch.object(
            manu_cluster,
            "read_attributes_raw",
            new_callable=mock.AsyncMock,
            side_effect=TimeoutError,
        ),
    ):
        assert await manu_cluster.bind() == [0]


def test_fp300_presence_binary_sensor_updates(zigpy_device_from_v2_quirk):
    """Test that presence reports update the occupancy attribute."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu

    manu_cluster.update_attribute(AqaraFP300ManuCluster.AttributeDefs.presence.id, True)

    assert manu_cluster.get(AqaraFP300ManuCluster.AttributeDefs.presence.id) is True
