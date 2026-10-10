"""Lutron Aurora Z3-1BRL smart bulb dimmer.

Recent Aurora firmware (observed on 0x00000c12) does not send standard
OnOff / LevelControl commands to its bound coordinator. Instead it reports
both the button and the rotary dial on the Philips manufacturer-specific
cluster 0xFC00 (manufacturer code 0x100B), using the same notification
frames as the Philips Hue Tap Dial (RDM002). Without a quirk zigpy logs
"Unknown cluster command 0" and ZHA never raises a ``zha_event``.

Frame layout of command 0x00 (server -> client), little endian:

* button: ``01 | u24 | press_type u8 | 0x21 | duration u16`` (8 bytes)
* dial:   ``14 | u24 | phase u8 | 0x29 | rotation int16 | ...`` (22 bytes)

The button frames are handled by :class:`PhilipsRemoteCluster` unchanged
(press, hold, short/long release, multi-press). Dial frames carry a signed
16-bit rotation in the slot the Philips schema calls ``param5``; the
trailing bytes (elapsed time, cumulative position) are ignored. The ``phase``
byte is 1 on the first frame of a twist and 2 while it continues.
"""

from __future__ import annotations

import logging
from typing import Any

import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import ARGS, COMMAND, COMMAND_ID, ZHA_SEND_EVENT
from zhaquirks.philips import Button, PhilipsRemoteCluster

_LOGGER = logging.getLogger(__name__)

LUTRON = "Lutron"
AURORA_MODEL = "Z3-1BRL"

DIAL_BUTTON_ID = 0x14
KNOB = "knob"
DIAL_ROTATE_CW = "dial_rotate_cw"
DIAL_ROTATE_CCW = "dial_rotate_ccw"
DIAL_ROTATED = "dial_rotated"
CLOCKWISE = "clockwise"
COUNTERCLOCKWISE = "counterclockwise"
DIAL_PHASES = {1: "start", 2: "rotate"}


def dial_speed(magnitude: int) -> str:
    """Bucket a rotation magnitude the way Zigbee2MQTT does for the Tap Dial."""
    if magnitude <= 25:
        return "step"
    if magnitude <= 75:
        return "slow"
    return "fast"


class AuroraRemoteCluster(PhilipsRemoteCluster):
    """Lutron Aurora button and dial reported on the Philips 0xFC00 cluster."""

    BUTTONS = {1: Button(KNOB)}

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Route dial frames to the rotation handler, everything else to Philips."""
        if args[0] != DIAL_BUTTON_ID:
            super().handle_cluster_request(hdr, args, dst_addressing=dst_addressing)
            return

        rotation = int(args[4])
        if rotation > 0x7FFF:
            rotation -= 0x10000
        if rotation == 0:
            return

        clockwise = rotation > 0
        event_args = {
            "rotation": rotation,
            "direction": "cw" if clockwise else "ccw",
            "speed": dial_speed(abs(rotation)),
            "phase": DIAL_PHASES.get(int(args[2]), str(int(args[2]))),
            COMMAND_ID: hdr.command_id,
            ARGS: [int(a) for a in args],
        }
        action = DIAL_ROTATE_CW if clockwise else DIAL_ROTATE_CCW
        _LOGGER.debug(
            "%s - dial rotation action: [%s] event_args: %s",
            self.__class__.__name__,
            action,
            event_args,
        )
        self.listener_event(ZHA_SEND_EVENT, action, event_args)


DIAL_TRIGGERS = {
    (DIAL_ROTATED, CLOCKWISE): {COMMAND: DIAL_ROTATE_CW},
    (DIAL_ROTATED, COUNTERCLOCKWISE): {COMMAND: DIAL_ROTATE_CCW},
}

(
    QuirkBuilder(LUTRON, AURORA_MODEL)
    .replaces(AuroraRemoteCluster)
    .device_automation_triggers(
        AuroraRemoteCluster.generate_device_automation_triggers(DIAL_TRIGGERS)
    )
    .add_to_registry()
)
