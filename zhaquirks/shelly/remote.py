"""Device handler for Shelly BLU Remote Control ZB.

The remote has a left and right ring button, a scroll wheel, and four channels
selected with the arrow buttons. Since firmware v1.2.13 it sends manufacturer
specific On/Off and Level Control commands that carry the selected channel
(0-3) as the last payload byte:

- On/Off 0x80 (right button), 0x81 (left button), 0x82 (toggle)
- Level Control 0x86 (wheel step, sent with manufacturer code 0x1490)

ZHA fires a ``zha_event`` for every decoded command, with the payload fields as
``params``, so the device triggers below only need to match on them.

https://shelly-api-docs.shelly.cloud/docs-ble/Devices/BLU_ZB/blu_remote
"""

from __future__ import annotations

from typing import Final

import zigpy.types as t
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import LevelControl, OnOff, StepMode
from zigpy.zcl.foundation import ZCLCommandDef

from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster
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

CHANNELS: Final = range(4)


class ShellyRemoteOnOff(CustomCluster, OnOff):
    """On/Off client cluster with the channel-aware button commands."""

    class ServerCommandDefs(OnOff.ServerCommandDefs):
        """Server command definitions."""

        off_with_channel: Final = ZCLCommandDef(
            id=0x80, schema={"channel": t.uint8_t}, manufacturer_code=None
        )
        on_with_channel: Final = ZCLCommandDef(
            id=0x81, schema={"channel": t.uint8_t}, manufacturer_code=None
        )
        toggle_with_channel: Final = ZCLCommandDef(
            id=0x82, schema={"channel": t.uint8_t}, manufacturer_code=None
        )


class ShellyRemoteLevelControl(CustomCluster, LevelControl):
    """Level Control client cluster with the channel-aware wheel command."""

    class ServerCommandDefs(LevelControl.ServerCommandDefs):
        """Server command definitions."""

        # Shelly's docs list this as 0x80 (with manufacturer code 0x80), but
        # firmware v1.2.13 sends command 0x86 with manufacturer code 0x1490.
        step_with_channel: Final = ZCLCommandDef(
            id=0x86,
            schema={
                "step_mode": StepMode,
                "step_size": t.uint8_t,
                "transition_time": t.uint16_t,
                "channel": t.uint8_t,
            },
            manufacturer_code=SHELLY_MANUFACTURER_CODE,
        )


def _trigger(command: ZCLCommandDef, cluster_id: int, **params: int) -> dict:
    """Build a device automation trigger for a channel-aware command."""
    return {
        COMMAND: command.name,
        CLUSTER_ID: cluster_id,
        ENDPOINT_ID: 1,
        PARAMS: params,
    }


_ON_OFF = ShellyRemoteOnOff.ServerCommandDefs
_LEVEL = ShellyRemoteLevelControl.ServerCommandDefs

# Channels are reported as 0-3; the remote's LEDs and the subtypes count 1-4.
SHELLY_REMOTE_TRIGGERS: Final = {
    trigger: value
    for channel in CHANNELS
    for trigger, value in (
        (
            (SHORT_PRESS, f"{LEFT}_channel_{channel + 1}"),
            _trigger(_ON_OFF.on_with_channel, OnOff.cluster_id, channel=channel),
        ),
        (
            (SHORT_PRESS, f"{RIGHT}_channel_{channel + 1}"),
            _trigger(_ON_OFF.off_with_channel, OnOff.cluster_id, channel=channel),
        ),
        (
            (ROTATED, f"{DIM_UP}_channel_{channel + 1}"),
            _trigger(
                _LEVEL.step_with_channel,
                LevelControl.cluster_id,
                step_mode=StepMode.Up,
                channel=channel,
            ),
        ),
        (
            (ROTATED, f"{DIM_DOWN}_channel_{channel + 1}"),
            _trigger(
                _LEVEL.step_with_channel,
                LevelControl.cluster_id,
                step_mode=StepMode.Down,
                channel=channel,
            ),
        ),
    )
}


(
    QuirkBuilder("Shelly", "BLU Remote Control ZB")
    .replaces(ShellyRemoteOnOff, cluster_type=ClusterType.Client)
    .replaces(ShellyRemoteLevelControl, cluster_type=ClusterType.Client)
    .device_automation_triggers(SHELLY_REMOTE_TRIGGERS)
    .add_to_registry()
)
