"""Tests for the Innr RC 210 and RC 250 remotes."""

from unittest import mock

import pytest
from zha.application import Platform
from zha.quirks import DEVICE_REGISTRY
import zigpy.device
import zigpy.profiles.zha
import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import LevelControl

from tests.zha_helpers import join_device_from_diagnostics, zha_gateway
import zhaquirks
from zhaquirks.innr.rc2x0_remote import (
    INNR_MANUFACTURER_CODE,
    InnrDeviceConfigurationCluster,
    KeyEvent,
    KeyEventReport,
    KeyId,
)

zhaquirks.setup()

CLUSTER = InnrDeviceConfigurationCluster.cluster_id
KEY_REPORT_MASK = InnrDeviceConfigurationCluster.AttributeDefs.key_report_mask
KEY_EVENT_REPORT = InnrDeviceConfigurationCluster.ClientCommandDefs.key_event_report

# Cluster specific, manufacturer specific, server to client, no default response
FRAME_CONTROL = 0x1D


def key_event_frame(
    key: int,
    event: int,
    sequence: int = 0,
    *,
    frame_control: int = FRAME_CONTROL,
) -> bytes:
    """Return the ZCL frame of a key event report."""
    manufacturer = (
        INNR_MANUFACTURER_CODE.to_bytes(2, "little") if frame_control & 0x04 else b""
    )
    return (
        bytes([frame_control])
        + manufacturer
        + bytes([sequence, KEY_EVENT_REPORT.id, 0x00, key, event, sequence])
    )


def send(device: zigpy.device.Device, cluster_id: int, payload: bytes) -> None:
    """Receive a ZCL frame from endpoint 1 of the remote."""
    device.packet_received(
        t.ZigbeePacket(
            src_ep=1,
            dst_ep=1,
            profile_id=zigpy.profiles.zha.PROFILE_ID,
            cluster_id=cluster_id,
            data=t.SerializableBytes(payload),
        )
    )


@pytest.fixture
def rc250(zigpy_device_from_v2_quirk) -> zigpy.device.Device:
    """Return a quirked RC 250."""
    return zigpy_device_from_v2_quirk(
        "innr", "RC 250", cluster_ids={1: {CLUSTER: ClusterType.Server}}
    )


@pytest.mark.parametrize(
    "frame_control",
    [
        FRAME_CONTROL,
        # Without the manufacturer code
        FRAME_CONTROL & ~0x04,
        # Marked as sent from a client
        FRAME_CONTROL & ~0x08,
        # With a default response requested
        FRAME_CONTROL & ~0x10,
    ],
)
async def test_key_event_report(rc250, frame_control):
    """Test that key event reports become `<key>_<event>` events."""
    cluster = rc250.endpoints[1].in_clusters[CLUSTER]
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    send(
        rc250,
        CLUSTER,
        key_event_frame(
            KeyId.center, KeyEvent.short_release, 7, frame_control=frame_control
        ),
    )

    assert listener.zha_send_event.mock_calls == [
        mock.call(
            "center_short_release",
            KeyEventReport(
                group_id=0,
                key_id=KeyId.center,
                key_event=KeyEvent.short_release,
                sequence=7,
            ),
        )
    ]


async def test_unknown_key_event(rc250):
    """Test that keys and events the spec does not list still get an event."""
    cluster = rc250.endpoints[1].in_clusters[CLUSTER]
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    send(rc250, CLUSTER, key_event_frame(0x0A, 0x40))

    assert listener.zha_send_event.mock_calls[0].args[0] == (
        "undefined_0x0a_undefined_0x40"
    )


async def test_key_event_keeps_custom_mask(rc250):
    """Test that key events keep a mask written by hand, e.g. with all events."""
    cluster = rc250.endpoints[1].in_clusters[CLUSTER]
    cluster.update_attribute(KEY_REPORT_MASK.id, 0x3B)

    send(rc250, CLUSTER, key_event_frame(KeyId.center, KeyEvent.press))

    assert cluster.get(KEY_REPORT_MASK.name) == 0x3B


async def test_other_write_errors_raise(rc250):
    """Test that only the mask write is taken as done without a response."""
    cluster = rc250.endpoints[1].in_clusters[CLUSTER]

    with (
        mock.patch.object(cluster, "write_attributes_raw", side_effect=TimeoutError),
        pytest.raises(TimeoutError),
    ):
        await cluster.write_attributes(
            {InnrDeviceConfigurationCluster.AttributeDefs.device_information.name: 1}
        )


async def test_rc250_remote_mode():
    """Test binding, switching modes, and following the mode the remote is in.

    The remote refuses the mask as any type other than uint8. It switches modes, but
    its write response often does not arrive.
    """
    async with zha_gateway() as gateway:
        zha_device = await join_device_from_diagnostics(
            gateway, "innr-rc-250-scan.json", DEVICE_REGISTRY
        )
        device = zha_device.device
        cluster = device.endpoints[1].in_clusters[CLUSTER]
        select = zha_device.get_platform_entity(
            Platform.SELECT,
            unique_id=f"{zha_device.ieee}-1-{KEY_REPORT_MASK.name}",
        )

        # Binding lets the remote send its key events to the coordinator
        cluster.bind.assert_awaited()

        for option, mask in [("Hub mode", 0x1A), ("Touchlink mode", 0x00)]:
            with mock.patch.object(
                cluster,
                "write_attributes_raw",
                return_value=[
                    [foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]
                ],
            ) as write:
                await select.async_select_option(option)

            (records,) = write.await_args.args
            assert (
                write.await_args.kwargs["manufacturer_code"] == INNR_MANUFACTURER_CODE
            )
            assert records[0].attrid == KEY_REPORT_MASK.id
            assert records[0].value.type == foundation.DataTypeId.uint8
            assert records[0].value.value == mask
            assert select.current_option == option

        # A write without response is taken as done
        with mock.patch.object(
            cluster, "write_attributes_raw", side_effect=TimeoutError
        ):
            await select.async_select_option("Hub mode")
        assert select.current_option == "Hub mode"

        # Standard commands show Touchlink mode, e.g. after a reset: move up
        move = LevelControl.ServerCommandDefs.move.id
        send(device, LevelControl.cluster_id, bytes([0x01, 0x01, move, 0x00, 0x32]))
        assert select.current_option == "Touchlink mode"

        # And key events show Hub mode
        send(device, CLUSTER, key_event_frame(KeyId.up, KeyEvent.long_press))
        assert select.current_option == "Hub mode"
        assert cluster.get(KEY_REPORT_MASK.name) == 0x1A
