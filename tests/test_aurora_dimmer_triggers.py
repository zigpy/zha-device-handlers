"""Tests for the Aurora two-gang battery dimmer device automation triggers."""

import pytest
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl
from zigpy.zcl.clusters.lighting import Color

from tests.common import ClusterListener
from zhaquirks.aurora.aurora_dimmer import (
    COLOR_DOWN,
    COLOR_UP,
    AuroraDimmerBatteryPowered,
)
from zhaquirks.const import (
    CLUSTER_ID,
    COMMAND,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    LEFT,
    PARAMS,
    RIGHT,
)


def _matching_triggers(endpoint_id, cluster_id, command, args):
    """Return the device automation triggers a received command would fire.

    ZHA turns a command received on a client cluster into a zha_event with the
    endpoint id, cluster id, command name and the command's fields as params, and
    a device trigger fires when those match its definition.
    """
    matches = []
    for key, trigger in AuroraDimmerBatteryPowered.device_automation_triggers.items():
        if (
            trigger[ENDPOINT_ID] == endpoint_id
            and trigger[CLUSTER_ID] == cluster_id
            and trigger.get(COMMAND) == command
            and all(
                getattr(args, name) == value
                for name, value in trigger.get(PARAMS, {}).items()
            )
        ):
            matches.append(key)
    return matches


@pytest.mark.parametrize(
    ("endpoint_id", "side"),
    [(1, RIGHT), (2, LEFT)],
)
@pytest.mark.parametrize(
    ("cluster", "command", "step_mode", "action"),
    [
        (LevelControl, "step", LevelControl.StepMode.Up, DIM_UP),
        (LevelControl, "step", LevelControl.StepMode.Down, DIM_DOWN),
        (Color, "step_color_temp", Color.StepMode.Down, COLOR_UP),
        (Color, "step_color_temp", Color.StepMode.Up, COLOR_DOWN),
    ],
)
async def test_knob_triggers(
    zigpy_device_from_quirk,
    endpoint_id,
    side,
    cluster,
    command,
    step_mode,
    action,
):
    """Each knob's step commands fire that knob's trigger, and only that one."""
    device = zigpy_device_from_quirk(AuroraDimmerBatteryPowered)
    client_cluster = device.endpoints[endpoint_id].out_clusters[cluster.cluster_id]
    listener = ClusterListener(client_cluster)

    command_def = getattr(cluster.ServerCommandDefs, command)
    if command == "step":
        args = command_def.schema(step_mode=step_mode, step_size=26, transition_time=3)
    else:
        args = command_def.schema(
            step_mode=step_mode,
            step_size=47,
            transition_time=3,
            color_temp_min_mireds=153,
            color_temp_max_mireds=454,
        )
    hdr = foundation.ZCLHeader.cluster(tsn=1, command_id=command_def.id)

    # The knob sends the command from its endpoint's client cluster
    device.packet_received(
        t.ZigbeePacket(
            profile_id=260,
            cluster_id=cluster.cluster_id,
            src_ep=endpoint_id,
            dst_ep=1,
            data=t.SerializableBytes(hdr.serialize() + args.serialize()),
        )
    )

    assert len(listener.cluster_commands) == 1
    _, command_id, received_args = listener.cluster_commands[0]
    received_command = client_cluster.server_commands[command_id].name
    assert received_command == command

    assert _matching_triggers(
        endpoint_id, cluster.cluster_id, received_command, received_args
    ) == [(action, side)]


def test_trigger_endpoints():
    """Left knob triggers use endpoint 2, right knob triggers endpoint 1."""
    triggers = AuroraDimmerBatteryPowered.device_automation_triggers
    for (_, side), trigger in triggers.items():
        assert trigger[ENDPOINT_ID] == {RIGHT: 1, LEFT: 2}[side]
