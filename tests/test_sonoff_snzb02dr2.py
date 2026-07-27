"""Tests for the Sonoff SNZB-02DR2 temperature and humidity sensor."""

from unittest import mock

import pytest
from zha.quirks import DEVICE_REGISTRY
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation

import zhaquirks
from zhaquirks.builder.metadata import WriteAttributeButtonMetadata
from zhaquirks.sonoff.snzb02dr2 import (
    CONFIGURATION_TIP,
    REMOTE_ATTRIBUTE_TYPE_SENSOR_DATA,
    REMOTE_SENSOR_STATE_OFFLINE,
    REMOTE_SENSOR_STATE_ONLINE,
    REMOTE_SENSOR_TYPE_HUMIDITY,
    REMOTE_SENSOR_TYPE_TEMPERATURE,
    CustomSonoffCluster,
    TemperatureUnit,
    configuration_tip_converter,
)

zhaquirks.setup()


@pytest.fixture
def sonoff_cluster(zigpy_device_from_v2_quirk):
    """Return the custom cluster from a quirked SNZB-02DR2 device."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SNZB-02DR2",
        cluster_ids={
            1: {CustomSonoffCluster.cluster_id: ClusterType.Server},
        },
    )
    return next(
        cluster
        for cluster in device.endpoints[1].in_clusters.values()
        if isinstance(cluster, CustomSonoffCluster)
    )


def _sensor_tlv(sensor_type, sensor_id, state, raw_value=None):
    """Build one sensor-data TLV for parser tests."""
    if raw_value is None:
        value = b""
    elif sensor_type == REMOTE_SENSOR_TYPE_TEMPERATURE:
        value = int(raw_value).to_bytes(2, "little", signed=True)
    else:
        value = int(raw_value).to_bytes(2, "little", signed=False)
    sensor_item = bytes((sensor_type, sensor_id, state, len(value))) + value
    sensor_data = bytes((1,)) + sensor_item
    return bytes((REMOTE_ATTRIBUTE_TYPE_SENSOR_DATA, len(sensor_data))) + sensor_data


def _packet(attributes, packet_count=1, packet_index=0):
    """Build a remote attribute packet from raw TLVs."""
    payload = bytes((len(attributes), packet_count, packet_index)) + b"".join(
        attributes
    )
    return CustomSonoffCluster._make_remote_attribute_array(payload)


def test_snzb02dr2_attribute_and_entity_configuration(sonoff_cluster):
    """Expose the firmware reset attribute and the configured sensor attributes."""
    reset_attr = CustomSonoffCluster.AttributeDefs.reset_max_min_record
    assert reset_attr.id == 0x2013
    assert reset_attr.type is t.uint8_t
    assert sonoff_cluster.get(reset_attr.name) is None
    assert TemperatureUnit.Celsius == 0
    assert configuration_tip_converter(None) == CONFIGURATION_TIP


def test_snzb02dr2_reset_button_metadata():
    """Expose the firmware reset attribute as a configuration button."""
    raw_device = mock.Mock(
        manufacturer="SONOFF",
        model="SNZB-02DR2",
    )
    entry = DEVICE_REGISTRY.match_entry(raw_device)
    assert entry is not None
    metadata = entry.zha_device_factory.quirk_definition.entity_metadata
    reset_button = next(
        item for item in metadata if isinstance(item, WriteAttributeButtonMetadata)
    )
    assert reset_button.attribute_name == "reset_max_min_record"
    assert reset_button.attribute_value == 1
    assert reset_button.fallback_name == "Reset min/max records"


def test_remote_array_helpers(sonoff_cluster):
    """Encode and decode the ZCL uint8 array representation."""
    value = sonoff_cluster._make_remote_attribute_array(b"\x01\x02")
    assert sonoff_cluster._array_payload(value) == b"\x01\x02"
    assert sonoff_cluster._array_payload([1, 2]) == b"\x01\x02"

    with pytest.raises(ValueError, match="must be uint8"):
        sonoff_cluster._array_payload(
            foundation.Array(type=foundation.DataTypeId.uint16, value=[1])
        )


@pytest.mark.parametrize(
    ("sensor_type", "raw_value"),
    [
        (REMOTE_SENSOR_TYPE_TEMPERATURE, -123),
        (REMOTE_SENSOR_TYPE_HUMIDITY, 4567),
    ],
)
def test_remote_sensor_packet_round_trip(sonoff_cluster, sensor_type, raw_value):
    """Encode online sensor data into the firmware packet format."""
    packet = sonoff_cluster._encode_remote_sensor_packet(sensor_type, 1, raw_value)
    payload = sonoff_cluster._array_payload(packet)
    _, _, attributes = sonoff_cluster._parse_packet(payload)
    assert sonoff_cluster._parse_sensor_tlv(attributes[0][1]) == [
        (sensor_type, 1, REMOTE_SENSOR_STATE_ONLINE, raw_value)
    ]

    with pytest.raises(ValueError, match="unsupported remote sensor type"):
        sonoff_cluster._encode_remote_sensor_packet(9, 1, 0)


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"\x00\x00",
        b"\x00\x00\x01",
        b"\x00\x02\x02",
        b"\x01\x01\x00\x03\x05\x01\x02\x03\x04",
    ],
)
def test_remote_packet_parser_rejects_malformed_packets(sonoff_cluster, payload):
    """Reject truncated, invalid, and inconsistent packet headers."""
    with pytest.raises(ValueError):
        sonoff_cluster._parse_packet(payload)


@pytest.mark.parametrize(
    "value",
    [
        b"",
        b"\x01\x00\x01",
        b"\x01\x00\x01\x01\x02",
        b"\x01\x00\x01\x04\x00",
        b"\x01\x00\x01\x01\x02\x04\x02\x00",
        b"\x01\x00\x01\x04\x02\x00\x00",
    ],
)
def test_sensor_tlv_parser_rejects_malformed_values(sonoff_cluster, value):
    """Reject invalid sensor counts, states, lengths, and trailing bytes."""
    with pytest.raises(ValueError):
        sonoff_cluster._parse_sensor_tlv(value)


def test_sensor_tlv_parser_accepts_offline_and_empty_online_values(sonoff_cluster):
    """Accept firmware offline records and online records without a value."""
    value = bytes((2,)) + bytes(
        (
            REMOTE_SENSOR_TYPE_TEMPERATURE,
            1,
            REMOTE_SENSOR_STATE_OFFLINE,
            0,
            REMOTE_SENSOR_TYPE_HUMIDITY,
            2,
            REMOTE_SENSOR_STATE_ONLINE,
            0,
        )
    )
    assert sonoff_cluster._parse_sensor_tlv(value) == [
        (REMOTE_SENSOR_TYPE_TEMPERATURE, 1, REMOTE_SENSOR_STATE_OFFLINE, None),
        (REMOTE_SENSOR_TYPE_HUMIDITY, 2, REMOTE_SENSOR_STATE_ONLINE, None),
    ]


def test_remote_values_are_hidden_until_source_is_enabled(sonoff_cluster):
    """Only expose cached remote values while the firmware source is enabled."""
    cluster = sonoff_cluster
    temperature = cluster.AttributeDefs.remote_temperature_data
    source_status = cluster.AttributeDefs.temp_humi_source_status

    cluster._apply_remote_attributes(
        [
            (
                REMOTE_ATTRIBUTE_TYPE_SENSOR_DATA,
                _sensor_tlv(
                    REMOTE_SENSOR_TYPE_TEMPERATURE,
                    1,
                    REMOTE_SENSOR_STATE_ONLINE,
                    1234,
                )[2:],
            )
        ]
    )
    assert cluster.get(temperature.name) is None

    cluster._update_attribute(source_status.id, 1)
    assert cluster.get(temperature.name) == 1234

    cluster._update_attribute(source_status.id, 0)
    assert cluster.get(temperature.name) is None


async def test_remote_packet_reassembly(sonoff_cluster):
    """Reassemble a two-packet report before updating the virtual sensor."""
    cluster = sonoff_cluster
    cluster._update_attribute(cluster.AttributeDefs.temp_humi_source_status.id, 1)
    tlv = _sensor_tlv(
        REMOTE_SENSOR_TYPE_TEMPERATURE, 1, REMOTE_SENSOR_STATE_ONLINE, 2500
    )
    first = _packet([tlv], packet_count=2, packet_index=0)
    second = _packet([], packet_count=2, packet_index=1)

    cluster._handle_remote_attribute_packet(first)
    assert cluster.get(cluster.AttributeDefs.remote_temperature_data.name) is None
    cluster._handle_remote_attribute_packet(second)
    assert cluster.get(cluster.AttributeDefs.remote_temperature_data.name) == 2500


def test_remote_packet_reassembly_discards_invalid_sequences(sonoff_cluster):
    """Discard incomplete, out-of-order, and mismatched packet sequences."""
    cluster = sonoff_cluster
    tlv = _sensor_tlv(
        REMOTE_SENSOR_TYPE_TEMPERATURE, 1, REMOTE_SENSOR_STATE_ONLINE, 2500
    )

    cluster._handle_remote_attribute_packet(_packet([], 2, 1))
    assert cluster._remote_packet_count is None
    cluster._handle_remote_attribute_packet(_packet([tlv], 2, 0))
    cluster._handle_remote_attribute_packet(_packet([], 3, 1))
    assert cluster._remote_packet_count is None

    cluster._remote_packet_count = 2
    cluster._remote_packet_parts = {1: []}
    cluster._handle_remote_attribute_packet(_packet([], 2, 0))
    assert cluster._remote_packet_count == 2
    cluster._clear_remote_packet_assembly()
    assert cluster._remote_packet_count is None


async def test_remote_virtual_attribute_write(sonoff_cluster):
    """Validate virtual bindings and route valid values to the firmware array."""
    cluster = sonoff_cluster
    temp_id = cluster.AttributeDefs.remote_temperature_sensor_id.name
    temp_data = cluster.AttributeDefs.remote_temperature_data.name

    result = await cluster.write_attributes({temp_id: 1})
    assert result[0][0].status == foundation.Status.SUCCESS
    assert cluster.get(temp_id) == 1

    invalid = await cluster.write_attributes({temp_id: 3})
    assert invalid[0][0].status == foundation.Status.INVALID_VALUE

    humidity_data = cluster.AttributeDefs.remote_humidity_data.name
    missing_binding = await cluster.write_attributes({humidity_data: 1234})
    assert missing_binding[0][0].status == foundation.Status.INVALID_VALUE

    with mock.patch.object(
        cluster,
        "_write_remote_sensor_value",
        mock.AsyncMock(return_value=foundation.Status.SUCCESS),
    ) as write_value:
        result = await cluster.write_attributes({temp_data: 2345})
    assert result[0][0].status == foundation.Status.SUCCESS
    write_value.assert_awaited_once()


async def test_remote_virtual_attribute_write_failures(sonoff_cluster):
    """Return invalid status for unsupported values and failed firmware writes."""
    cluster = sonoff_cluster
    temp_binding = cluster.AttributeDefs.remote_temperature_sensor_id.name
    temp_data = cluster.AttributeDefs.remote_temperature_data.name
    await cluster.write_attributes({temp_binding: 1})

    invalid = await cluster.write_attributes({temp_data: 40000})
    assert invalid[0][-1].status == foundation.Status.INVALID_VALUE

    with mock.patch.object(
        cluster,
        "_write_remote_sensor_value",
        mock.AsyncMock(return_value=foundation.Status.FAILURE),
    ):
        failed = await cluster.write_attributes({temp_data: 2000})
    assert failed[0][-1].status == foundation.Status.FAILURE


async def test_physical_attribute_write_updates_source_status(sonoff_cluster):
    """Pass physical writes through and refresh virtual values after success."""
    cluster = sonoff_cluster
    status_id = cluster.AttributeDefs.temp_humi_source_status.id
    response = [
        [
            foundation.WriteAttributesStatusRecord(
                status=foundation.Status.SUCCESS,
                attrid=status_id,
            )
        ]
    ]
    with mock.patch.object(
        cluster, "write_attributes_raw", mock.AsyncMock(return_value=response)
    ):
        result = await cluster.write_attributes({status_id: 1})
    assert result[0][0].status == foundation.Status.SUCCESS
    assert cluster.get(status_id) == 1


async def test_remote_sensor_value_write_handles_firmware_responses(sonoff_cluster):
    """Normalize successful, failed, and empty firmware write responses."""
    cluster = sonoff_cluster
    success = [
        [
            foundation.WriteAttributesStatusRecord(
                status=foundation.Status.SUCCESS,
                attrid=cluster.AttributeDefs.remote_attributes.id,
            )
        ]
    ]
    with mock.patch.object(
        cluster, "write_attributes_raw", mock.AsyncMock(return_value=success)
    ):
        assert (
            await cluster._write_remote_sensor_value(
                REMOTE_SENSOR_TYPE_TEMPERATURE, 1, 100, None
            )
            == foundation.Status.SUCCESS
        )

    with mock.patch.object(
        cluster,
        "write_attributes_raw",
        mock.AsyncMock(
            return_value=[
                [
                    foundation.WriteAttributesStatusRecord(
                        status=foundation.Status.FAILURE,
                        attrid=cluster.AttributeDefs.remote_attributes.id,
                    )
                ]
            ]
        ),
    ):
        assert (
            await cluster._write_remote_sensor_value(
                REMOTE_SENSOR_TYPE_TEMPERATURE, 1, 100, None
            )
            == foundation.Status.FAILURE
        )

    assert (
        await cluster._write_remote_sensor_value(
            REMOTE_SENSOR_TYPE_TEMPERATURE, 1, 40000, None
        )
        == foundation.Status.INVALID_VALUE
    )


def test_malformed_remote_report_is_ignored(sonoff_cluster):
    """Ignore malformed physical remote reports without raising."""
    cluster = sonoff_cluster
    cluster._update_attribute(cluster.AttributeDefs.remote_attributes.id, b"\x00")
    assert cluster.get(cluster.AttributeDefs.remote_attributes.name) == b"\x00"
