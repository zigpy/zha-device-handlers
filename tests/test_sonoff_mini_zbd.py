"""Tests for Sonoff MINI-ZBD inching support."""

from unittest import mock

from zigpy.zcl import ClusterType, foundation

from tests.common import ClusterListener
import zhaquirks
from zhaquirks.sonoff.mini_zbd import (
    EWELINK_MANUFACTURER_CODE,
    PROTOCOL_DATA_COMMAND_ID,
    InchingPayload,
    SonoffInchingCluster,
    SonoffInchingMode,
)

zhaquirks.setup()


async def test_inching_write_sends_protocol_data(zigpy_device_from_v2_quirk):
    """Writing inching attributes sends the protocolData command."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBD",
        cluster_ids={
            1: {SonoffInchingCluster.cluster_id: ClusterType.Server},
        },
    )

    cluster = device.endpoints[1].sonoff_cluster

    with mock.patch.object(
        cluster,
        "request",
        mock.AsyncMock(),
    ) as mock_request:
        await cluster.write_attributes(
            {
                SonoffInchingCluster.AttributeDefs.inching_control.name: True,
                SonoffInchingCluster.AttributeDefs.inching_time.name: 4,  # 2 seconds
                SonoffInchingCluster.AttributeDefs.inching_mode.name: 0,  # Turn_OFF
            }
        )

        mock_request.assert_called_once()
        args = mock_request.call_args

        assert args[0][0] is False  # general=False
        assert args[0][1] == PROTOCOL_DATA_COMMAND_ID
        assert args[0][2] is InchingPayload

        # Verify payload bytes
        payload_args = args[0][3:]
        assert payload_args[0] == 0x01  # Cmd
        assert payload_args[1] == 0x17  # SubCmd
        assert payload_args[2] == 0x07  # Length
        assert payload_args[3] == 0x80  # SeqNum
        assert payload_args[4] == 0x80  # Mode: enabled (0x80), Turn_OFF (no 0x01)
        assert payload_args[5] == 0x00  # Channel 1
        assert payload_args[6] == 0x04  # Time low byte (4 half-seconds)
        assert payload_args[7] == 0x00  # Time high byte

        assert args[1]["manufacturer"] == EWELINK_MANUFACTURER_CODE


async def test_inching_mode_on_sets_bit(zigpy_device_from_v2_quirk):
    """Inching mode Turn_ON sets bit 0 in mode byte."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBD",
        cluster_ids={
            1: {SonoffInchingCluster.cluster_id: ClusterType.Server},
        },
    )

    cluster = device.endpoints[1].sonoff_cluster

    with mock.patch.object(
        cluster,
        "request",
        mock.AsyncMock(),
    ) as mock_request:
        await cluster.write_attributes(
            {
                SonoffInchingCluster.AttributeDefs.inching_control.name: True,
                SonoffInchingCluster.AttributeDefs.inching_mode.name: SonoffInchingMode.Turn_ON,
            }
        )

        payload_args = mock_request.call_args[0][3:]
        assert payload_args[4] == 0x81  # Mode: enabled (0x80) + Turn_ON (0x01)


async def test_inching_disabled_clears_enable_bit(zigpy_device_from_v2_quirk):
    """Disabling inching clears the enable bit."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBD",
        cluster_ids={
            1: {SonoffInchingCluster.cluster_id: ClusterType.Server},
        },
    )

    cluster = device.endpoints[1].sonoff_cluster

    with mock.patch.object(
        cluster,
        "request",
        mock.AsyncMock(),
    ) as mock_request:
        await cluster.write_attributes(
            {SonoffInchingCluster.AttributeDefs.inching_control.name: False}
        )

        payload_args = mock_request.call_args[0][3:]
        assert payload_args[4] == 0x00  # Mode: disabled


async def test_inching_time_large_value(zigpy_device_from_v2_quirk):
    """Large inching time encodes as little-endian uint16."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBD",
        cluster_ids={
            1: {SonoffInchingCluster.cluster_id: ClusterType.Server},
        },
    )

    cluster = device.endpoints[1].sonoff_cluster

    with mock.patch.object(
        cluster,
        "request",
        mock.AsyncMock(),
    ) as mock_request:
        # 3599.5 seconds = 7199 half-seconds = 0x1C1F
        await cluster.write_attributes(
            {SonoffInchingCluster.AttributeDefs.inching_time.name: 7199}
        )

        payload_args = mock_request.call_args[0][3:]
        assert payload_args[6] == 0x1F  # Time low byte
        assert payload_args[7] == 0x1C  # Time high byte


async def test_inching_checksum(zigpy_device_from_v2_quirk):
    """Checksum is XOR of bytes 0 through 9."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBD",
        cluster_ids={
            1: {SonoffInchingCluster.cluster_id: ClusterType.Server},
        },
    )

    cluster = device.endpoints[1].sonoff_cluster

    with mock.patch.object(
        cluster,
        "request",
        mock.AsyncMock(),
    ) as mock_request:
        await cluster.write_attributes(
            {SonoffInchingCluster.AttributeDefs.inching_control.name: True}
        )

        payload_args = mock_request.call_args[0][3:]
        expected_checksum = 0
        for b in payload_args[:10]:
            expected_checksum ^= b
        assert payload_args[10] == expected_checksum


async def test_regular_attrs_pass_through(zigpy_device_from_v2_quirk):
    """Non-inching attributes are written via standard write_attributes."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBD",
        cluster_ids={
            1: {SonoffInchingCluster.cluster_id: ClusterType.Server},
        },
    )

    cluster = device.endpoints[1].sonoff_cluster

    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]
    with mock.patch.object(
        cluster,
        "write_attributes_raw",
        mock.AsyncMock(return_value=write_response),
    ) as mock_write_raw:
        result = await cluster.write_attributes(
            {SonoffInchingCluster.AttributeDefs.detach_relay.name: True}
        )

        mock_write_raw.assert_called_once()
        assert result[0][0].status == foundation.Status.SUCCESS


async def test_inching_updates_attr_cache(zigpy_device_from_v2_quirk):
    """Writing inching attributes updates the cluster attribute cache."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBD",
        cluster_ids={
            1: {SonoffInchingCluster.cluster_id: ClusterType.Server},
        },
    )

    cluster = device.endpoints[1].sonoff_cluster
    listener = ClusterListener(cluster)

    with mock.patch.object(
        cluster,
        "request",
        mock.AsyncMock(),
    ):
        await cluster.write_attributes(
            {SonoffInchingCluster.AttributeDefs.inching_control.name: True}
        )

    inching_control_id = SonoffInchingCluster.AttributeDefs.inching_control.id
    assert any(
        attr_id == inching_control_id for attr_id, _ in listener.attribute_updates
    )


async def test_mixed_attrs_writes_regular_and_sends_inching(
    zigpy_device_from_v2_quirk,
):
    """Writing both regular and inching attributes handles both."""
    device = zigpy_device_from_v2_quirk(
        manufacturer="SONOFF",
        model="MINI-ZBD",
        cluster_ids={
            1: {SonoffInchingCluster.cluster_id: ClusterType.Server},
        },
    )

    cluster = device.endpoints[1].sonoff_cluster

    write_response = [
        [foundation.WriteAttributesStatusRecord(status=foundation.Status.SUCCESS)]
    ]
    with (
        mock.patch.object(
            cluster,
            "write_attributes_raw",
            mock.AsyncMock(return_value=write_response),
        ) as mock_write_raw,
        mock.patch.object(
            cluster,
            "request",
            mock.AsyncMock(),
        ) as mock_request,
    ):
        await cluster.write_attributes(
            {
                SonoffInchingCluster.AttributeDefs.detach_relay.name: True,
                SonoffInchingCluster.AttributeDefs.inching_control.name: True,
            }
        )

        mock_write_raw.assert_called_once()
        mock_request.assert_called_once()
