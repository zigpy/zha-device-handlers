"""Tests for Aqara FP300 (lumi.sensor_occupy.agl8)."""

from unittest import mock

import pytest
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import PowerConfiguration

from tests.common import ClusterListener
from zhaquirks.const import BatterySize
from zhaquirks.xiaomi import AQARA, XIAOMI_AQARA_ATTRIBUTE_E1
from zhaquirks.xiaomi.aqara.motion_agl8 import AqaraFP300ManuCluster


def create_aqara_attr_report(attributes):
    """Create an Aqara E1 TLV report payload."""
    serialized_data = b""
    for key, value in attributes.items():
        tv = foundation.TypeValue(0x39, t.Single(value))
        serialized_data += bytes([key]) + tv.serialize()
    return serialized_data


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


def send_battery_report(
    device, attr_id: int, value: int, *, disable_default_response: bool = True
) -> None:
    """Deliver a standard PowerConfiguration attribute report from the device."""
    cluster = device.endpoints[1].power
    hdr = foundation.ZCLHeader.general(
        tsn=1,
        command_id=foundation.GeneralCommand.Report_Attributes,
        direction=foundation.Direction.Server_to_Client,
    )
    hdr.frame_control = hdr.frame_control.replace(
        disable_default_response=disable_default_response
    )
    command = foundation.GENERAL_COMMANDS[
        foundation.GeneralCommand.Report_Attributes
    ].schema(
        attribute_reports=[
            foundation.Attribute(
                attrid=attr_id,
                value=foundation.TypeValue(
                    type=foundation.DataTypeId.uint8, value=t.uint8_t(value)
                ),
            )
        ]
    )
    device.packet_received(
        t.ZigbeePacket(
            profile_id=zha.PROFILE_ID,
            cluster_id=cluster.cluster_id,
            src_ep=1,
            dst_ep=1,
            data=t.SerializableBytes(hdr.serialize() + command.serialize()),
        )
    )


async def test_aqara_fp300_ignores_standard_battery_reports(zigpy_device_from_v2_quirk):
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
    send_battery_report(device, percent_id, 0)
    send_battery_report(device, voltage_id, 0)
    assert power_cluster.get(voltage_id) == pytest.approx(29.5)
    assert power_cluster.get(percent_id) == 150

    # The next TLV report still updates both
    manu_cluster.update_attribute(
        XIAOMI_AQARA_ATTRIBUTE_E1, create_aqara_attr_report({23: 2900, 24: 70})
    )
    assert power_cluster.get(voltage_id) == pytest.approx(29.0)
    assert power_cluster.get(percent_id) == 140


async def test_aqara_fp300_ignored_battery_report_gets_default_response(
    zigpy_device_from_v2_quirk,
):
    """Test that a dropped standard report is still answered when the device asks for it."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    power_cluster = device.endpoints[1].power
    percent_id = PowerConfiguration.AttributeDefs.battery_percentage_remaining.id

    with mock.patch.object(power_cluster, "send_default_rsp") as mock_rsp:
        send_battery_report(device, percent_id, 0, disable_default_response=False)
        assert mock_rsp.call_count == 1
        assert mock_rsp.call_args.args[0].command_id == (
            foundation.GeneralCommand.Report_Attributes
        )

        send_battery_report(device, percent_id, 0, disable_default_response=True)
        assert mock_rsp.call_count == 1

    assert power_cluster.get(percent_id) is None


def test_aqara_fp300_battery_metadata(zigpy_device_from_v2_quirk):
    """Test that the battery size and quantity match the device's two CR2450 cells."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    power_cluster = device.endpoints[1].power

    assert power_cluster.get(PowerConfiguration.AttributeDefs.battery_quantity.id) == 2
    assert (
        power_cluster.get(PowerConfiguration.AttributeDefs.battery_size.id)
        == BatterySize.CR2450
    )


async def test_aqara_fp300_no_battery_without_tlv(zigpy_device_from_v2_quirk):
    """Test that nothing is cached from standard reports before the first TLV report."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    power_cluster = device.endpoints[1].power

    send_battery_report(
        device, PowerConfiguration.AttributeDefs.battery_percentage_remaining.id, 0
    )

    assert (
        power_cluster.get(
            PowerConfiguration.AttributeDefs.battery_percentage_remaining.id
        )
        is None
    )


async def test_aqara_fp300_configuration_reads_tlv_struct(zigpy_device_from_v2_quirk):
    """Test that (re)configuration reads the Aqara TLV struct and that the response updates the battery."""
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
            manu_cluster,
            "read_attributes_raw",
            new_callable=mock.AsyncMock,
            return_value=[[record]],
        ) as mock_read,
        mock.patch.object(
            power_cluster,
            "battery_percent_reported",
            wraps=power_cluster.battery_percent_reported,
        ) as mock_percent,
    ):
        await device.apply_custom_configuration()

    mock_read.assert_awaited_once()
    # The read response is parsed exactly once
    mock_percent.assert_called_once_with(91)
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


async def test_aqara_fp300_configuration_survives_read_failure(
    zigpy_device_from_v2_quirk,
):
    """Test that a failing TLV read doesn't fail the configuration."""
    device = zigpy_device_from_v2_quirk(AQARA, "lumi.sensor_occupy.agl8")
    manu_cluster = device.endpoints[1].aqara_fp300_manu

    with mock.patch.object(
        manu_cluster,
        "read_attributes_raw",
        new_callable=mock.AsyncMock,
        side_effect=TimeoutError,
    ):
        await device.apply_custom_configuration()
