"""Tests for Develco/Frient."""

from unittest import mock

import zigpy.types as t
import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.develco.air_quality import (
    AQSZB110PowerConfiguration,
    RelativeHumidityCustom,
    TemperatureMeasurementCustom,
    measured_value_converter,
    value_to_caqi,
)

zhaquirks.setup()


async def test_frient_emi(zigpy_device_from_v2_quirk):
    """Test that the EMI correctly forwards custom attributes."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "EMIZB-141",
        cluster_ids={2: {Metering.cluster_id: ClusterType.Server}},
    )

    metering_cluster = device.endpoints[2].smartenergy_metering
    manufacturer_cluster = device.endpoints[2].in_clusters[0xFD10]
    pulse_config_attr_id = manufacturer_cluster.AttributeDefs.pulse_configuration.id

    request_patch = mock.patch("zigpy.device.Device.request", mock.AsyncMock())
    with request_patch as request_mock:
        # this is not the correct answer for write/read attributes, so they fail,
        # but we only care about the request to the device here
        request_mock.return_value = (foundation.Status.SUCCESS, "done")

        # the device uses manufacturer code 4117, but tests fake it as 1234,
        # as it is normally read from the node description

        # read custom attribute
        await manufacturer_cluster.read_attributes([pulse_config_attr_id])

        # verify the request
        assert request_mock.call_count == 1
        assert request_mock.call_args[0] == ()  # no args
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id
        assert request_mock.call_args[1]["data"] == b"\x04\xd2\x04\x01\x00\x00\x03"

        zcl_header, attr_data = foundation.ZCLHeader.deserialize(
            request_mock.call_args[1]["data"]
        )
        assert (
            zcl_header.frame_control.frame_type == foundation.FrameType.GLOBAL_COMMAND
        )
        assert zcl_header.frame_control.is_manufacturer_specific == 1
        assert zcl_header.manufacturer == 1234  # manufacturer id used by mock device
        assert zcl_header.command_id == foundation.GeneralCommand.Read_Attributes
        assert attr_data == b"\x00\x03"

        request_mock.reset_mock()

        # write custom attribute
        await manufacturer_cluster.write_attributes({pulse_config_attr_id: "42"})

        # verify the request
        assert request_mock.call_count == 1
        assert request_mock.call_args[0] == ()  # no args
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id
        assert (
            request_mock.call_args[1]["data"] == b"\x04\xd2\x04\x02\x02\x00\x03!*\x00"
        )

        zcl_header, attr_data = foundation.ZCLHeader.deserialize(
            request_mock.call_args[1]["data"]
        )
        assert (
            zcl_header.frame_control.frame_type == foundation.FrameType.GLOBAL_COMMAND
        )
        assert zcl_header.frame_control.is_manufacturer_specific == 1
        assert zcl_header.manufacturer == 1234  # manufacturer id used by mock device
        assert zcl_header.command_id == foundation.GeneralCommand.Write_Attributes
        assert attr_data == b"\x00\x03!*\x00"

        request_mock.reset_mock()

        # read non-custom attribute
        await metering_cluster.read_attributes(
            [metering_cluster.AttributeDefs.current_summ_delivered.id]
        )

        # verify the request
        assert request_mock.call_count == 1
        assert request_mock.call_args[0] == ()  # no args
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id
        assert request_mock.call_args[1]["data"] == b"\x00\x03\x00\x00\x00"

        zcl_header, attr_data = foundation.ZCLHeader.deserialize(
            request_mock.call_args[1]["data"]
        )
        assert (
            zcl_header.frame_control.frame_type == foundation.FrameType.GLOBAL_COMMAND
        )
        assert zcl_header.frame_control.is_manufacturer_specific == 0
        assert zcl_header.manufacturer is None
        assert zcl_header.command_id == foundation.GeneralCommand.Read_Attributes
        assert attr_data == b"\x00\x00"

        request_mock.reset_mock()

        # write non-custom attribute
        await metering_cluster.write_attributes(
            {metering_cluster.AttributeDefs.current_summ_delivered.id: 100}
        )

        # verify the request
        assert request_mock.call_count == 1
        assert request_mock.call_args[0] == ()  # no args
        assert request_mock.call_args[1]["cluster"] == Metering.cluster_id
        assert (
            request_mock.call_args[1]["data"]
            == b"\x00\x04\x02\x00\x00%d\x00\x00\x00\x00\x00"
        )

        zcl_header, attr_data = foundation.ZCLHeader.deserialize(
            request_mock.call_args[1]["data"]
        )
        assert (
            zcl_header.frame_control.frame_type == foundation.FrameType.GLOBAL_COMMAND
        )
        assert zcl_header.frame_control.is_manufacturer_specific == 0
        assert zcl_header.manufacturer is None
        assert zcl_header.command_id == foundation.GeneralCommand.Write_Attributes
        assert attr_data == b"\x00\x00%d\x00\x00\x00\x00\x00"


async def test_mfg_cluster_events(zigpy_device_from_v2_quirk):
    """Test Frient EMI Norwegian HAN ignoring incorrect divisor attribute reports."""
    device = zigpy_device_from_v2_quirk("frient A/S", "EMIZB-132", endpoint_ids=[1, 2])

    metering_cluster = device.endpoints[2].smartenergy_metering
    metering_listener = ClusterListener(metering_cluster)

    # divisor already fixed at 1000
    assert metering_cluster.get(Metering.AttributeDefs.divisor.id) == 1000

    # send incorrect divisor attribute report
    # Frame: 0x18 (non-mfr-specific, server-to-client, disable-default-rsp),
    #        TSN=1, cmd=0x0a (Report_Attributes), attr=0x0302 (divisor), value=512
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=Metering.cluster_id,
            src_ep=2,
            dst_ep=2,
            data=t.SerializableBytes(b"\x18\x01\x0a\x02\x03\x22\x00\x02\x00"),
        )
    )

    # attribute_updated event should not be emitted
    assert len(metering_listener.attribute_updates) == 0

    # divisor should still be fixed at 1000
    assert metering_cluster.get(Metering.AttributeDefs.divisor.id) == 1000

    # send current_summ_delivered attribute report
    # Frame: 0x18, TSN=1, cmd=0x0a, attr=0x0000, value=1234 (uint48)
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=Metering.cluster_id,
            src_ep=2,
            dst_ep=2,
            data=t.SerializableBytes(
                b"\x18\x01\x0a\x00\x00\x25\xd2\x04\x00\x00\x00\x00"
            ),
        )
    )

    # attribute_updated event should be emitted
    assert len(metering_listener.attribute_updates) == 1
    assert (
        metering_cluster.get(Metering.AttributeDefs.current_summ_delivered.id) == 1234
    )


async def test_aqszb110_power_config_battery_percent(zigpy_device_from_v2_quirk):
    """Test battery percent is derived from cached voltage."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {PowerConfiguration.cluster_id: ClusterType.Server}},
    )

    power = device.endpoints[38].power
    assert isinstance(power, AQSZB110PowerConfiguration)

    power.update_attribute(PowerConfiguration.AttributeDefs.battery_voltage.id, 28)
    expected = power._calculate_battery_percentage(28)

    with mock.patch(
        "zigpy.quirks.CustomCluster.read_attributes_raw",
        new=mock.AsyncMock(),
    ) as read_mock:
        (records,) = await power.read_attributes_raw(
            [power.BATTERY_PERCENTAGE_REMAINING]
        )

    read_mock.assert_not_called()
    assert len(records) == 1
    record = records[0]
    assert record.attrid == power.BATTERY_PERCENTAGE_REMAINING
    assert record.status == foundation.Status.SUCCESS
    assert record.value.value == expected


async def test_aqszb110_power_config_battery_percent_unsupported(
    zigpy_device_from_v2_quirk,
):
    """Test battery percent remains unsupported without cached voltage."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {PowerConfiguration.cluster_id: ClusterType.Server}},
    )

    power = device.endpoints[38].power
    (records,) = await power.read_attributes_raw(
        [power.BATTERY_PERCENTAGE_REMAINING]
    )

    assert len(records) == 1
    record = records[0]
    assert record.attrid == power.BATTERY_PERCENTAGE_REMAINING
    assert record.status == foundation.Status.UNSUPPORTED_ATTRIBUTE


async def test_aqszb110_power_config_read_attributes_passthrough(
    zigpy_device_from_v2_quirk,
):
    """Test read_attributes_raw delegates remaining attributes to base."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {PowerConfiguration.cluster_id: ClusterType.Server}},
    )

    power = device.endpoints[38].power
    power.update_attribute(PowerConfiguration.AttributeDefs.battery_voltage.id, 28)

    battery_voltage_id = PowerConfiguration.AttributeDefs.battery_voltage.id
    passthrough_record = foundation.ReadAttributeRecord(
        battery_voltage_id,
        foundation.Status.SUCCESS,
        foundation.TypeValue(),
    )
    passthrough_record.value.value = 28

    with mock.patch(
        "zigpy.quirks.CustomCluster.read_attributes_raw",
        new=mock.AsyncMock(return_value=([passthrough_record],)),
    ) as read_mock:
        records, = await power.read_attributes_raw(
            [power.BATTERY_PERCENTAGE_REMAINING, battery_voltage_id]
        )

    read_mock.assert_called_once()
    assert read_mock.call_args.args[0] == [battery_voltage_id]
    assert {record.attrid for record in records} == {
        power.BATTERY_PERCENTAGE_REMAINING,
        battery_voltage_id,
    }


async def test_aqszb110_power_config_read_attributes_name_and_attrdef(
    zigpy_device_from_v2_quirk,
):
    """Test power config reads name and ZCLAttributeDef inputs."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {PowerConfiguration.cluster_id: ClusterType.Server}},
    )

    power = device.endpoints[38].power
    power.update_attribute(PowerConfiguration.AttributeDefs.battery_voltage.id, 28)

    battery_pct_name = (
        PowerConfiguration.AttributeDefs.battery_percentage_remaining.name
    )
    battery_voltage_def = PowerConfiguration.AttributeDefs.battery_voltage
    passthrough_record = foundation.ReadAttributeRecord(
        battery_voltage_def.id,
        foundation.Status.SUCCESS,
        foundation.TypeValue(),
    )
    passthrough_record.value.value = 28

    with mock.patch(
        "zigpy.quirks.CustomCluster.read_attributes_raw",
        new=mock.AsyncMock(return_value=([passthrough_record],)),
    ) as read_mock:
        (records,) = await power.read_attributes_raw(
            [battery_pct_name, battery_voltage_def]
        )

    read_mock.assert_called_once()
    assert read_mock.call_args.args[0] == [battery_voltage_def.id]
    assert {record.attrid for record in records} == {
        power.BATTERY_PERCENTAGE_REMAINING,
        battery_voltage_def.id,
    }


async def test_air_quality_temperature_offset_write_attributes(
    zigpy_device_from_v2_quirk,
):
    """Test temperature offset writes are handled locally."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {TemperatureMeasurement.cluster_id: ClusterType.Server}},
    )

    temp = device.endpoints[38].temperature
    offset_id = TemperatureMeasurementCustom.AttributeDefs.temperature_offset.id
    offset_name = TemperatureMeasurementCustom.AttributeDefs.temperature_offset.name

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(),
    ) as write_mock:
        result = await temp.write_attributes({offset_id: 2})
        assert temp.get(offset_id) == 2
        assert result == [
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]

        result = await temp.write_attributes({offset_name: 3})
        assert temp.get(offset_id) == 3
        assert result == [
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]

    write_mock.assert_not_called()


async def test_air_quality_temperature_offset_passthrough(
    zigpy_device_from_v2_quirk,
):
    """Test non-offset temperature writes pass through to base."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {TemperatureMeasurement.cluster_id: ClusterType.Server}},
    )

    temp = device.endpoints[38].temperature
    status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    attrs = {
        TemperatureMeasurementCustom.AttributeDefs.temperature_offset.id: 1,
        TemperatureMeasurement.AttributeDefs.measured_value.id: 2250,
    }

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=[status]),
    ) as write_mock:
        result = await temp.write_attributes(attrs, timeout=5)

    write_mock.assert_called_once()
    assert write_mock.call_args.args[0] == {
        TemperatureMeasurement.AttributeDefs.measured_value.id: 2250
    }
    assert write_mock.call_args.kwargs["timeout"] == 5
    assert result == [status]


async def test_air_quality_temperature_offset_updates_measured_value(
    zigpy_device_from_v2_quirk,
):
    """Test temperature offset adjusts cached measured value."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {TemperatureMeasurement.cluster_id: ClusterType.Server}},
    )

    temp = device.endpoints[38].temperature
    measured_id = TemperatureMeasurement.AttributeDefs.measured_value.id
    offset_id = TemperatureMeasurementCustom.AttributeDefs.temperature_offset.id

    temp.update_attribute(measured_id, 2300)
    temp.update_attribute(offset_id, 2)

    assert temp.get(measured_id) == 2500


async def test_air_quality_temperature_invalid_does_not_apply_offset(
    zigpy_device_from_v2_quirk,
):
    """Test invalid temperature sentinel is not adjusted by offset."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {TemperatureMeasurement.cluster_id: ClusterType.Server}},
    )

    temp = device.endpoints[38].temperature
    measured_id = TemperatureMeasurement.AttributeDefs.measured_value.id
    offset_id = TemperatureMeasurementCustom.AttributeDefs.temperature_offset.id

    temp.update_attribute(measured_id, 0x8000)
    temp.update_attribute(offset_id, 1)

    assert temp.get(measured_id) == 0x8000


async def test_air_quality_temperature_offset_without_measured_value(
    zigpy_device_from_v2_quirk,
):
    """Test offset write does not touch measured value when unset."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {TemperatureMeasurement.cluster_id: ClusterType.Server}},
    )

    temp = device.endpoints[38].temperature
    measured_id = TemperatureMeasurement.AttributeDefs.measured_value.id
    offset_id = TemperatureMeasurementCustom.AttributeDefs.temperature_offset.id

    assert temp.get(measured_id) is None
    temp.update_attribute(offset_id, 2)
    assert temp.get(measured_id) is None


async def test_air_quality_humidity_offset_write_attributes(
    zigpy_device_from_v2_quirk,
):
    """Test humidity offset writes are handled locally."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {RelativeHumidity.cluster_id: ClusterType.Server}},
    )

    humidity = device.endpoints[38].humidity
    offset_id = RelativeHumidityCustom.AttributeDefs.humidity_offset.id
    offset_name = RelativeHumidityCustom.AttributeDefs.humidity_offset.name

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(),
    ) as write_mock:
        result = await humidity.write_attributes({offset_id: 5})
        assert humidity.get(offset_id) == 5
        assert result == [
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]

        result = await humidity.write_attributes({offset_name: 6})
        assert humidity.get(offset_id) == 6
        assert result == [
            [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
        ]

    write_mock.assert_not_called()


async def test_air_quality_humidity_offset_passthrough(
    zigpy_device_from_v2_quirk,
):
    """Test non-offset humidity writes pass through to base."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {RelativeHumidity.cluster_id: ClusterType.Server}},
    )

    humidity = device.endpoints[38].humidity
    status = [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
    attrs = {
        RelativeHumidityCustom.AttributeDefs.humidity_offset.id: 2,
        RelativeHumidity.AttributeDefs.measured_value.id: 4500,
    }

    with mock.patch(
        "zigpy.quirks.CustomCluster.write_attributes",
        new=mock.AsyncMock(return_value=[status]),
    ) as write_mock:
        result = await humidity.write_attributes(attrs, priority=1)

    write_mock.assert_called_once()
    assert write_mock.call_args.args[0] == {
        RelativeHumidity.AttributeDefs.measured_value.id: 4500
    }
    assert write_mock.call_args.kwargs["priority"] == 1
    assert result == [status]


async def test_air_quality_humidity_offset_updates_measured_value(
    zigpy_device_from_v2_quirk,
):
    """Test humidity offset adjusts cached measured value."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {RelativeHumidity.cluster_id: ClusterType.Server}},
    )

    humidity = device.endpoints[38].humidity
    measured_id = RelativeHumidity.AttributeDefs.measured_value.id
    offset_id = RelativeHumidityCustom.AttributeDefs.humidity_offset.id

    humidity.update_attribute(measured_id, 4000)
    humidity.update_attribute(offset_id, 3)

    assert humidity.get(measured_id) == 4300


async def test_air_quality_humidity_invalid_does_not_apply_offset(
    zigpy_device_from_v2_quirk,
):
    """Test invalid humidity sentinel is not adjusted by offset."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {RelativeHumidity.cluster_id: ClusterType.Server}},
    )

    humidity = device.endpoints[38].humidity
    measured_id = RelativeHumidity.AttributeDefs.measured_value.id
    offset_id = RelativeHumidityCustom.AttributeDefs.humidity_offset.id

    humidity.update_attribute(measured_id, 0x8000)
    humidity.update_attribute(offset_id, 1)

    assert humidity.get(measured_id) == 0x8000


async def test_air_quality_humidity_offset_without_measured_value(
    zigpy_device_from_v2_quirk,
):
    """Test offset write does not touch measured value when unset."""
    device = zigpy_device_from_v2_quirk(
        "frient A/S",
        "AQSZB-110",
        endpoint_ids=[38],
        cluster_ids={38: {RelativeHumidity.cluster_id: ClusterType.Server}},
    )

    humidity = device.endpoints[38].humidity
    measured_id = RelativeHumidity.AttributeDefs.measured_value.id
    offset_id = RelativeHumidityCustom.AttributeDefs.humidity_offset.id

    assert humidity.get(measured_id) is None
    humidity.update_attribute(offset_id, 2)
    assert humidity.get(measured_id) is None


def test_air_quality_measured_value_converter():
    """Test VOC measured value converter returns None for sentinel."""
    assert measured_value_converter(0xFFFF) is None
    assert measured_value_converter(123) == 123


@pytest.mark.parametrize(
    "value,expected",
    [
        (65, "Excellent"),
        (66, "Good"),
        (220, "Good"),
        (221, "Moderate"),
        (660, "Moderate"),
        (661, "Poor"),
        (2200, "Poor"),
        (2201, "Bad"),
    ],
)
def test_air_quality_value_to_caqi(value, expected):
    """Test VOC value to CAQI mapping thresholds."""
    assert value_to_caqi(value) == expected
