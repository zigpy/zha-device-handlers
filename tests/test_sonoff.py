"""Tests for Sonoff quirks."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import OnOff
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.const import COMMAND_DOUBLE, COMMAND_HOLD, COMMAND_SINGLE, COMMAND_TRIPLE
from zhaquirks.sonoff.snzb01m import SonoffButtonCluster
from zhaquirks.sonoff.snzb02b import (
    SonoffCalculatedClimateCluster as SNZB02BCalculatedClimateCluster,
)
from zhaquirks.sonoff.snzb02ul import (
    REMOTE_SENSOR_TYPE_TEMPERATURE,
    SNZB02ULCluster,
    SonoffCalculatedClimateCluster as SNZB02ULCalculatedClimateCluster,
)
from zhaquirks.sonoff.zbm5 import (
    SonoffCluster,
    SonoffDetachedRelayMask,
    SonoffInputConfigCluster,
)

zhaquirks.setup()


@pytest.mark.parametrize(
    ("mask", "expected_states"),
    [
        (SonoffDetachedRelayMask.Relay1, (True, False, False)),
        (
            SonoffDetachedRelayMask.Relay1 | SonoffDetachedRelayMask.Relay2,
            (True, True, False),
        ),
        (
            SonoffDetachedRelayMask.Relay1
            | SonoffDetachedRelayMask.Relay2
            | SonoffDetachedRelayMask.Relay3,
            (True, True, True),
        ),
    ],
    ids=["relay1", "relay1+2", "relay1+2+3"],
)
async def test_sonoff_zbm5_relay_mask_propagation(
    zigpy_device_from_v2_quirk, mask, expected_states
):
    """Test relay mask updates propagate to local cluster."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-3C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
                OnOff.cluster_id: ClusterType.Server,
            },
            2: {OnOff.cluster_id: ClusterType.Server},
            3: {OnOff.cluster_id: ClusterType.Server},
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    sonoff_listener = ClusterListener(sonoff_cluster)
    local_listener = ClusterListener(local_cluster)

    detach_mask_attr = sonoff_cluster.AttributeDefs.detach_relay_mask.id
    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

    sonoff_cluster.update_attribute(detach_mask_attr, mask)

    assert len(sonoff_listener.attribute_updates) == 1
    assert sonoff_listener.attribute_updates[0][0] == detach_mask_attr

    assert len(local_listener.attribute_updates) == 3
    assert local_listener.attribute_updates[0] == (relay_1_attr, expected_states[0])
    assert local_listener.attribute_updates[1] == (relay_2_attr, expected_states[1])
    assert local_listener.attribute_updates[2] == (relay_3_attr, expected_states[2])


async def test_sonoff_cluster_write_attributes_logic(zigpy_device_from_v2_quirk):
    """Test writing relay attributes translates to mask write and updates local state."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    local_listener = ClusterListener(local_cluster)

    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ) as mock_write:
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: True}
        )

        assert mock_write.call_count == 1
        written_attrs = mock_write.call_args[0][0]
        assert len(written_attrs) == 1
        assert (
            written_attrs[0].attrid == SonoffCluster.AttributeDefs.detach_relay_mask.id
        )

        relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
        relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
        relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

        assert local_listener.attribute_updates[0] == (relay_1_attr, True)
        assert local_listener.attribute_updates[1] == (relay_2_attr, False)
        assert local_listener.attribute_updates[2] == (relay_3_attr, False)

        local_listener.attribute_updates.clear()
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: False}
        )

        written_attrs = mock_write.call_args[0][0]
        assert written_attrs[0].value.value == SonoffDetachedRelayMask(0)

        assert local_listener.attribute_updates[0] == (relay_1_attr, False)
        assert local_listener.attribute_updates[1] == (relay_2_attr, False)
        assert local_listener.attribute_updates[2] == (relay_3_attr, False)


async def test_sonoff_cluster_failed_write_does_not_propagate(
    zigpy_device_from_v2_quirk,
):
    """Test that a failed mask write does not update local relay states."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    local_listener = ClusterListener(local_cluster)

    write_response = [
        [
            foundation.WriteAttributesStatusRecord(
                status=foundation.Status.FAILURE,
                attrid=SonoffCluster.AttributeDefs.detach_relay_mask.id,
            )
        ]
    ]
    with mock.patch.object(
        sonoff_cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ):
        await local_cluster.write_attributes(
            {SonoffInputConfigCluster.AttributeDefs.relay_1_detached.name: True}
        )

    assert len(local_listener.attribute_updates) == 0


async def test_sonoff_cluster_apply_custom_configuration(zigpy_device_from_v2_quirk):
    """Test apply_custom_configuration reads mask and populates local relay states."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="ZBM5-1C-80/86",
        cluster_ids={
            1: {
                SonoffCluster.cluster_id: ClusterType.Server,
                SonoffInputConfigCluster.cluster_id: ClusterType.Server,
            }
        },
    )

    sonoff_cluster = device.endpoints[1].sonoff_cluster
    local_cluster = device.endpoints[1].sonoff_input_config
    local_listener = ClusterListener(local_cluster)

    mask_attr = SonoffCluster.AttributeDefs.detach_relay_mask
    mask = SonoffDetachedRelayMask.Relay1 | SonoffDetachedRelayMask.Relay2

    read_response = foundation.ReadAttributeRecord(
        attrid=mask_attr.id,
        status=foundation.Status.SUCCESS,
        value=foundation.TypeValue(type=mask_attr.zcl_type, value=mask),
    )
    with mock.patch.object(
        sonoff_cluster,
        "_read_attributes",
        mock.AsyncMock(return_value=[[read_response]]),
    ):
        await sonoff_cluster.apply_custom_configuration()

    relay_1_attr = local_cluster.AttributeDefs.relay_1_detached.id
    relay_2_attr = local_cluster.AttributeDefs.relay_2_detached.id
    relay_3_attr = local_cluster.AttributeDefs.relay_3_detached.id

    assert local_listener.attribute_updates[0] == (relay_1_attr, True)
    assert local_listener.attribute_updates[1] == (relay_2_attr, True)
    assert local_listener.attribute_updates[2] == (relay_3_attr, False)


@pytest.mark.parametrize("endpoint_id", [1, 2, 3, 4])
@pytest.mark.parametrize(
    ("value", "expected_command"),
    [
        (1, COMMAND_SINGLE),
        (2, COMMAND_DOUBLE),
        (3, COMMAND_HOLD),
        (4, COMMAND_TRIPLE),
    ],
)
async def test_snzb01m_button_events(
    zigpy_device_from_v2_quirk, endpoint_id, value, expected_command
):
    """Correct events are emitted for each endpoint and action."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SNZB-01M",
        endpoint_ids=[1, 2, 3, 4],
    )
    cluster = device.endpoints[endpoint_id].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(
        SonoffButtonCluster.AttributeDefs.key_action_event.id,
        value,
    )

    assert listener.zha_send_event.call_count == 1
    listener.zha_send_event.assert_called_with(expected_command, {})


async def test_snzb01m_invalid_attribute_update(zigpy_device_from_v2_quirk):
    """Invalid attribute values should not emit events."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SNZB-01M",
        endpoint_ids=[1, 2, 3, 4],
    )
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(SonoffButtonCluster.AttributeDefs.key_action_event.id, 99)

    assert listener.zha_send_event.call_count == 0


async def test_snzb01m_non_button_attribute_update(zigpy_device_from_v2_quirk):
    """Non-button attributes must not generate button events."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SNZB-01M",
        endpoint_ids=[1, 2, 3, 4],
    )
    cluster = device.endpoints[1].sonoff_button_cluster
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    cluster.update_attribute(0x0001, 1)

    assert listener.zha_send_event.call_count == 0


@pytest.mark.parametrize(
    ("temperature", "humidity", "dew_point", "vpd"),
    [
        (20.0, 50.0, 9.255, 11.66),
        (25.0, 100.0, 25.0, 0.0),
    ],
)
def test_snzb02b_calculated_climate_formulas(
    temperature, humidity, dew_point, vpd
):
    """Test SNZB-02B calculated climate values."""
    assert SNZB02BCalculatedClimateCluster.calculate_dew_point(
        temperature,
        humidity,
    ) == pytest.approx(dew_point, abs=0.01)

    assert SNZB02BCalculatedClimateCluster.calculate_vpd(
        temperature,
        humidity,
    ) == pytest.approx(vpd, abs=0.02)


@pytest.mark.parametrize("humidity", [None, 0, -1, 101])
def test_snzb02b_rejects_invalid_humidity(humidity):
    """Invalid measurements must not produce derived values."""
    assert SNZB02BCalculatedClimateCluster.calculate_dew_point(20, humidity) is None
    assert SNZB02BCalculatedClimateCluster.calculate_vpd(20, humidity) is None


def test_snzb02ul_remote_sensor_packet_round_trip():
    """A remote-temperature packet is encoded and parsed without data loss."""
    array = SNZB02ULCluster._encode_remote_sensor_packet(
        REMOTE_SENSOR_TYPE_TEMPERATURE,
        -123,
    )

    packet_count, packet_index, attributes = SNZB02ULCluster._parse_packet(
        SNZB02ULCluster._array_payload(array)
    )

    assert (packet_count, packet_index) == (1, 0)
    assert SNZB02ULCluster._parse_sensor_tlv(attributes[0][1]) == [
        (REMOTE_SENSOR_TYPE_TEMPERATURE, 1, 1, -123)
    ]


def test_snzb02ul_rejects_malformed_remote_packets():
    """Malformed remote packets must not be accepted."""
    with pytest.raises(ValueError, match="header is truncated"):
        SNZB02ULCluster._parse_packet(b"\x01\x01")

    with pytest.raises(ValueError, match="invalid remote attribute packet index"):
        SNZB02ULCluster._parse_packet(b"\x00\x01\x01")

    with pytest.raises(ValueError, match="SensorCount"):
        SNZB02ULCluster._parse_sensor_tlv(b"")


async def test_snzb02ul_remote_sensor_report_updates_entities(
    zigpy_device_from_v2_quirk,
):
    """A physical 0x601E report updates the local remote-temperature value."""
    device = zigpy_device_from_v2_quirk(
        "SONOFF",
        "SNZB-02UL",
        cluster_ids={
            1: {
                SNZB02ULCluster.cluster_id: ClusterType.Server,
                TemperatureMeasurement.cluster_id: ClusterType.Server,
                RelativeHumidity.cluster_id: ClusterType.Server,
            }
        },
    )

    cluster = device.endpoints[1].in_clusters[SNZB02ULCluster.cluster_id]
    report = SNZB02ULCluster._encode_remote_sensor_packet(
        REMOTE_SENSOR_TYPE_TEMPERATURE,
        2150,
    )

    cluster.update_attribute(
        SNZB02ULCluster.AttributeDefs.remote_attributes.id,
        report,
    )

    assert cluster._attr_cache[
        SNZB02ULCluster.AttributeDefs.remote_temperature_data.id
    ] == 2150


def test_snzb02ul_calculated_climate_handles_missing_measurements():
    """No calculation is emitted from incomplete measurements."""
    assert SNZB02ULCalculatedClimateCluster.calculate_dew_point(None, 50) is None
    assert (
        SNZB02ULCalculatedClimateCluster.calculate_saturation_vapor_pressure(None)
        is None
    )
    assert SNZB02ULCalculatedClimateCluster.calculate_vpd(20, None) is None
