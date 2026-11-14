"""Lutron Aurora Z3-1BRL smart bulb dimmer.

Recent Aurora firmware (observed on 0x00000c12) does not send standard
OnOff / LevelControl commands to its bound coordinator. Instead it reports
both the button and the rotary dial on the Philips manufacturer-specific
cluster 0xFC00 (manufacturer code 0x100B), using the same notification
frames as the Philips Hue Tap Dial (RDM002). Without a quirk zigpy logs
"Unknown cluster command 0" and ZHA never raises a ``zha_event``.

Frame layout of command 0x00 (server -> client), little endian:

* button: ``01 | u24 | press_type u8 | 0x21 | duration u16`` (8 bytes)
* dial:   ``14 | u24 | phase u8 | 0x29 | adjusted int16 | 0x21 | u16 |
  0x29 | counter int16 | ...`` (23 bytes)

The button frames are handled by :class:`PhilipsRemoteCluster` unchanged
(press, hold, short/long release, multi-press).

Dial frames carry two amounts. ``adjusted`` (the slot the Philips schema
calls ``param5``) is not a plain delta: on the first frame of a twist
(``phase`` 1) it is 7/4 of the real movement, and the following frame gives
the excess back. ``counter`` is a signed cumulative position, so the rotation
reported here is the difference between consecutive counters. The device
restarts the counter when a twist begins after a pause; such a frame has
``phase`` 1 and ``4 * adjusted == 7 * counter``, and its counter is the
movement itself. This reset signature is empirical (captures on 0x00000c12).

Older firmware sends LevelControl ``move_to_level_with_on_off`` instead, for
the button and the dial alike, which ZHA already relays as a ``zha_event``.
"""

from __future__ import annotations

import logging
from typing import Any

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks.builder import QuirkBuilder
from zhaquirks.const import (
    ARGS,
    CLUSTER_ID,
    COMMAND,
    COMMAND_ID,
    COMMAND_MOVE_TO_LEVEL_ON_OFF,
    ENDPOINT_ID,
    LEFT,
    RIGHT,
    ROTARY_KNOB,
    ROTATED,
    ZHA_SEND_EVENT,
)
from zhaquirks.philips import Button, PhilipsRemoteCluster

_LOGGER = logging.getLogger(__name__)

LUTRON = "Lutron"
AURORA_MODEL = "Z3-1BRL"

DIAL_BUTTON_ID = 0x14
DIAL_MARKER = foundation.DataTypeId.int16  # 0x29; button frames carry 0x21
KNOB = "knob"
DIAL_ROTATE_CW = "dial_rotate_cw"
DIAL_ROTATE_CCW = "dial_rotate_ccw"
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

    BUTTONS = {1: Button(KNOB, ROTARY_KNOB)}

    class ClientCommandDefs(PhilipsRemoteCluster.ClientCommandDefs):
        """Client command definitions."""

        # The Philips schema plus the dial's cumulative counter. The extra
        # fields are absent from button frames.
        notification = foundation.ZCLCommandDef(
            id=0x0000,
            schema={
                "button": t.uint8_t,
                "param2": t.uint24_t,
                "press_type": t.uint8_t,
                "param4": t.uint8_t,
                "param5": t.uint16_t,
                "param6?": t.uint8_t,
                "param7?": t.uint16_t,
                "param8?": t.uint8_t,
                "counter?": t.int16s,
            },
            is_manufacturer_specific=True,
        )

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Track the dial's cumulative counter between frames."""
        super().__init__(*args, **kwargs)
        self._dial_counter: int | None = None

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
    ) -> None:
        """Route dial frames to the rotation handler, everything else to Philips."""
        if args[0] != DIAL_BUTTON_ID:
            # Hand the Philips handler the fields of its own schema, so the
            # button events are the same as on any other Philips remote.
            super().handle_cluster_request(
                hdr,
                PhilipsRemoteCluster.ClientCommandDefs.notification.schema(*args[:5]),
                dst_addressing=dst_addressing,
            )
            return

        counter = args[8]
        if args[3] != DIAL_MARKER or counter is None:
            _LOGGER.debug(
                "%s - ignoring dial frame with an unknown layout: %s",
                self.__class__.__name__,
                args,
            )
            return

        phase = int(args[2])
        adjusted = int(args[4])
        if adjusted > 0x7FFF:
            adjusted -= 0x10000
        counter = int(counter)

        previous = self._dial_counter
        self._dial_counter = counter
        if phase == 1 and 4 * adjusted == 7 * counter:
            # The counter restarted with this twist.
            rotation = counter
        elif previous is not None:
            rotation = (counter - previous + 0x8000) % 0x10000 - 0x8000
        else:
            # Mid-twist with no earlier frame to compare against (for example
            # right after a restart): take this frame as the baseline.
            _LOGGER.debug(
                "%s - no dial baseline yet, counter is %s",
                self.__class__.__name__,
                counter,
            )
            return
        if rotation == 0:
            return

        clockwise = rotation > 0
        event_args = {
            "rotation": rotation,
            "direction": "cw" if clockwise else "ccw",
            "speed": dial_speed(abs(rotation)),
            "phase": DIAL_PHASES.get(phase, str(phase)),
            COMMAND_ID: hdr.command_id,
            ARGS: [int(a) for a in args[:5]],
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
    (ROTATED, RIGHT): {COMMAND: DIAL_ROTATE_CW},
    (ROTATED, LEFT): {COMMAND: DIAL_ROTATE_CCW},
    # Older firmware: one LevelControl command for the button and the dial.
    (ROTATED, ROTARY_KNOB): {
        COMMAND: COMMAND_MOVE_TO_LEVEL_ON_OFF,
        CLUSTER_ID: LevelControl.cluster_id,
        ENDPOINT_ID: 1,
    },
}

(
    QuirkBuilder(LUTRON, AURORA_MODEL)
    .replaces(AuroraRemoteCluster)
    .device_automation_triggers(
        AuroraRemoteCluster.generate_device_automation_triggers(DIAL_TRIGGERS)
    )
    .add_to_registry()
)
