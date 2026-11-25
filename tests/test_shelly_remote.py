"""Tests for the Shelly BLU Remote Control ZB quirk."""

from unittest import mock

import pytest
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff, StepMode

import zhaquirks
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LEFT,
    PARAMS,
    RIGHT,
    ROTATED,
    SHORT_PRESS,
)
from zhaquirks.shelly import SHELLY_MANUFACTURER_CODE
from zhaquirks.shelly.remote import ShellyRemoteLevelControl, ShellyRemoteOnOff

zhaquirks.setup()


@pytest.fixture
def remote(zigpy_device_from_v2_quirk):
    """Shelly BLU Remote Control ZB with its real cluster layout."""
    return zigpy_device_from_v2_quirk(
        "Shelly",
        "BLU Remote Control ZB",
        cluster_ids={
            1: {
                OnOff.cluster_id: ClusterType.Client,
                LevelControl.cluster_id: ClusterType.Client,
            }
        },
    )


def _receive(cluster, frame: bytes):
    """Decode a raw ZCL frame on a cluster and return the decoded command."""
    listener = mock.MagicMock()
    cluster.add_listener(listener)

    hdr, args = cluster.deserialize(frame)
    cluster.handle_message(hdr, args)

    listener.cluster_command.assert_called_once()
    _tsn, command_id, args = listener.cluster_command.call_args.args
    return cluster.server_commands[command_id], args


def _matching_triggers(device, cluster, command, args) -> set[tuple[str, str]]:
    """Return the triggers that ZHA would fire for a decoded command.

    ZHA fires a `zha_event` with the command name and the payload as `params`;
    a device trigger fires when all of its keys match that event.
    """
    params = args.as_dict()
    return {
        trigger
        for trigger, match in device.device_automation_triggers.items()
        if match[COMMAND] == command.name
        and match[CLUSTER_ID] == cluster.cluster_id
        and match[ENDPOINT_ID] == cluster.endpoint.endpoint_id
        and all(params.get(key) == value for key, value in match[PARAMS].items())
    }


def test_shelly_remote_clusters_replaced(remote) -> None:
    """The remote's On/Off and Level Control client clusters are replaced."""
    out_clusters = remote.endpoints[1].out_clusters

    assert isinstance(out_clusters[OnOff.cluster_id], ShellyRemoteOnOff)
    assert isinstance(out_clusters[LevelControl.cluster_id], ShellyRemoteLevelControl)


@pytest.mark.parametrize("channel", range(4))
@pytest.mark.parametrize(
    ("command_id", "command_name", "button"),
    [
        (0x81, "on_with_channel", LEFT),
        (0x80, "off_with_channel", RIGHT),
    ],
)
async def test_shelly_remote_buttons(
    remote, channel, command_id, command_name, button
) -> None:
    """Ring buttons decode with their channel and fire one trigger per channel."""
    cluster = remote.endpoints[1].out_clusters[OnOff.cluster_id]

    command, args = _receive(cluster, bytes([0x01, 0x2A, command_id, channel]))

    assert command.name == command_name
    assert args.channel == channel
    assert _matching_triggers(remote, cluster, command, args) == {
        (SHORT_PRESS, f"{button}_channel_{channel + 1}")
    }


async def test_shelly_remote_toggle(remote) -> None:
    """The toggle command decodes, even though no trigger is mapped to it."""
    cluster = remote.endpoints[1].out_clusters[OnOff.cluster_id]

    command, args = _receive(cluster, bytes([0x01, 0x2B, 0x82, 0x02]))

    assert command.name == "toggle_with_channel"
    assert args.channel == 2
    assert _matching_triggers(remote, cluster, command, args) == set()


async def test_shelly_remote_wheel_real_frame(remote) -> None:
    """A wheel step captured from firmware v1.2.13 decodes with its channel."""
    cluster = remote.endpoints[1].out_clusters[LevelControl.cluster_id]

    # Manufacturer specific (0x1490), step up by 9, transition 3, channel 3
    frame = bytes.fromhex("05 90 14 24 86 00 09 03 00 03")
    hdr, _ = cluster.deserialize(frame)
    assert hdr.manufacturer == SHELLY_MANUFACTURER_CODE

    command, args = _receive(cluster, frame)

    assert command.name == "step_with_channel"
    assert args.step_mode == StepMode.Up
    assert args.step_size == 9
    assert args.transition_time == 3
    assert args.channel == 3
    assert _matching_triggers(remote, cluster, command, args) == {
        (ROTATED, f"{DIM_UP}_channel_4")
    }


@pytest.mark.parametrize("channel", range(4))
@pytest.mark.parametrize(
    ("step_mode", "direction"),
    [(StepMode.Up, DIM_UP), (StepMode.Down, DIM_DOWN)],
)
async def test_shelly_remote_wheel(remote, channel, step_mode, direction) -> None:
    """Wheel steps fire one trigger per direction and channel."""
    cluster = remote.endpoints[1].out_clusters[LevelControl.cluster_id]

    frame = bytes([0x05, 0x90, 0x14, 0x30, 0x86, step_mode, 0x03, 0x03, 0x00, channel])
    command, args = _receive(cluster, frame)

    assert args.step_mode == step_mode
    assert args.channel == channel
    assert _matching_triggers(remote, cluster, command, args) == {
        (ROTATED, f"{direction}_channel_{channel + 1}")
    }


def test_shelly_remote_triggers(remote) -> None:
    """Every button and wheel direction has a trigger on all four channels."""
    assert len(remote.device_automation_triggers) == 16
