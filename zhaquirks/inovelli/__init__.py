"""Module for Inovelli quirks implementations."""

import logging
from typing import Any, List, Optional, Union

import zigpy.types as t
from zhaquirks.const import (
    BUTTON,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_ID,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_PRESS,
    COMMAND_QUAD,
    COMMAND_RELEASE,
    COMMAND_TRIPLE,
    DOUBLE_PRESS,
    PRESS_TYPE,
    QUADRUPLE_PRESS,
    QUINTUPLE_PRESS,
    TRIPLE_PRESS,
    ZHA_SEND_EVENT,
)
from zigpy.quirks import CustomCluster
from zigpy.zcl import foundation

_LOGGER = logging.getLogger(__name__)
INOVELLI_VZM31SN_CLUSTER_ID = 64561

# Press Types
# 0 - pressed
# 1 - released
# 2 - held
# 3 - 2x
# 4 - 3x
# 5 - 4x
# 6 - 5x
COMMAND_QUINTUPLE = "quintuple"
PRESS_TYPES = {
    0: COMMAND_PRESS,
    1: COMMAND_RELEASE,
    2: COMMAND_HOLD,
    3: COMMAND_DOUBLE,
    4: COMMAND_TRIPLE,
    5: COMMAND_QUAD,
    6: COMMAND_QUINTUPLE,
}

# Buttons
# 1 - down button
# 2 - up button
# 3 - config button

BUTTONS = {1: BUTTON_1, 2: BUTTON_2, 3: BUTTON_3}
ON = "Up"
OFF = "Down"
CONFIG = "Config"


class ButtonPressQueue:
    """Inovelli button queue to derive multiple press events."""

    def __init__(self):
        """Init."""
        self._ms_threshold = 300
        self._ms_last_click = 0
        self._click_counter = 1
        self._button = None
        self._callback = lambda x: None
        self._task = None

    async def _job(self):
        await asyncio.sleep(self._ms_threshold / 1000)
        self._callback(self._click_counter)

    def _reset(self, button):
        if self._task:
            self._task.cancel()
        self._click_counter = 1
        self._button = button

    def press(self, callback, button):
        """Process a button press."""
        self._callback = callback
        now_ms = time.time() * 1000
        if self._button != button:
            self._reset(button)
        elif now_ms - self._ms_last_click > self._ms_threshold:
            self._click_counter = 1
        else:
            self._task.cancel()
            self._click_counter += 1
        self._ms_last_click = now_ms
        self._task = asyncio.ensure_future(self._job())


class Inovelli_VZM31SN_Cluster(CustomCluster):

    """Inovelli VZM31-SN custom cluster."""

    cluster_id = 0xFC31
    name = "InovelliVZM31SNCluster"
    ep_attribute = "inovelli_vzm31sn_cluster"

    manufacturer_attributes = {
        0x0001: ("Dimming Speed Up (Remote)", t.uint8_t),
        0x0002: ("Dimming Speed Up (Local)", t.uint8_t),
        0x0003: ("Ramp Rate - Off to On (Local)", t.uint8_t),
        0x0004: ("Ramp Rate - Off to On (Remote)", t.uint8_t),
        0x0005: ("Dimming Speed Down (Remote)", t.uint8_t),
        0x0006: ("Dimming Speed Down (Local)", t.uint8_t),
        0x0007: ("Ramp Rate - On to Off (Local)", t.uint8_t),
        0x0008: ("Ramp Rate - On to Off (Remote)", t.uint8_t),
        0x0009: ("Minimum Level", t.uint8_t),
        0x000A: ("Maximum Level", t.uint8_t),
        0x000B: ("Invert Switch", t.Bool),
        0x000C: ("Auto Off Timer", t.uint16_t),
        0x000D: ("Default Level (Local)", t.uint8_t),
        0x000E: ("Default Level (Remote)", t.uint8_t),
        0x000F: ("State After Power Restored", t.uint8_t),
        0x0011: ("Load Level Indicateor Timeout", t.uint8_t),
        0x0012: ("Active Power Reports", t.uint16_t),
        0x0013: ("Periodic Power and Energy Reports", t.uint8_t),
        0x0014: ("Active Energy Reports", t.uint16_t),
        0x0015: ("Power Type", t.uint8_t),
        0x0016: ("Switch Type", t.uint8_t),
        0x0032: ("Button Delay", t.uint8_t),
        0x003C: ("Default LED1 Strip Color (When On)", t.uint8_t),
        0x003D: ("Default LED1 Strip Color (When Off)", t.uint8_t),
        0x003E: ("Default LED1 Strip Intensity (When On)", t.uint8_t),
        0x003F: ("Default LED1 Strip Intensity (When Off)", t.uint8_t),
        0x0041: ("Default LED2 Strip Color (When On)", t.uint8_t),
        0x0042: ("Default LED2 Strip Color (When Off)", t.uint8_t),
        0x0043: ("Default LED2 Strip Intensity (When On)", t.uint8_t),
        0x0044: ("Default LED2 Strip Intensity (When Off)", t.uint8_t),
        0x0046: ("Default LED3 Strip Color (When On)", t.uint8_t),
        0x0047: ("Default LED3 Strip Color (When Off)", t.uint8_t),
        0x0048: ("Default LED3 Strip Intensity (When On)", t.uint8_t),
        0x0049: ("Default LED3 Strip Intensity (When Off)", t.uint8_t),
        0x004B: ("Default LED4 Strip Color (When On)", t.uint8_t),
        0x004C: ("Default LED4 Strip Color (When Off)", t.uint8_t),
        0x004D: ("Default LED4 Strip Intensity (When On)", t.uint8_t),
        0x004E: ("Default LED4 Strip Intensity (When Off)", t.uint8_t),
        0x0050: ("Default LED5 Strip Color (When On)", t.uint8_t),
        0x0051: ("Default LED5 Strip Color (When Off)", t.uint8_t),
        0x0052: ("Default LED5 Strip Intensity (When On)", t.uint8_t),
        0x0053: ("Default LED5 Strip Intensity (When Off)", t.uint8_t),
        0x0055: ("Default LED6 Strip Color (When On)", t.uint8_t),
        0x0056: ("Default LED6 Strip Color (When Off)", t.uint8_t),
        0x0057: ("Default LED6 Strip Intensity (When On)", t.uint8_t),
        0x0058: ("Default LED6 Strip Intensity (When Off)", t.uint8_t),
        0x005A: ("Default LED7 Strip Color (When On)", t.uint8_t),
        0x005B: ("Default LED7 Strip Color (When Off)", t.uint8_t),
        0x005C: ("Default LED7 Strip Intensity (When On)", t.uint8_t),
        0x005D: ("Default LED7 Strip Intensity (When Off)", t.uint8_t),
        0x0034: ("Smart Bulb Mode", t.Bool),
        0x005F: ("LED Color (When On)", t.uint8_t),
        0x0060: ("LED Color (When Off)", t.uint8_t),
        0x0061: ("LED Intensity (When On)", t.uint8_t),
        0x0062: ("LED Intensity (When Off)", t.uint8_t),
        0x0100: ("Local Protection", t.Bool),
        0x0101: ("Remote Protection", t.Bool),
        0x0102: ("Output Mode", t.Bool),
        0x0103: ("On/Off LED Mode", t.Bool),
        0x0104: ("Firmware Progress LED", t.Bool),
    }

    manufacturer_server_commands = {
        0x00: ("button_event", (t.uint8_t, t.uint8_t), False),
        0x01: (
            "led_effect",
            (t.uint8_t, t.uint8_t, t.uint8_t, t.uint8_t),
            False,
        ),  # LED Effect
        0x03: (
            "individual_led_effect",
            (t.uint8_t, t.uint8_t, t.uint8_t, t.uint8_t, t.uint8_t),
            False,
        ),  # individual LED Effect
    }

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle a cluster request."""
        _LOGGER.debug(
            "%s: handle_cluster_request - Command: %s Data: %s",
            self.name,
            hdr.command_id,
            args,
        )
        if hdr.command_id == 0x00:

            button = BUTTONS.get(args[0])
            press_type = PRESS_TYPES.get(args[1])
            action = f"{button}_{press_type}"

            event_args = {
                BUTTON: button,
                PRESS_TYPE: press_type,
                COMMAND_ID: hdr.command_id,
            }

            self.listener_event(ZHA_SEND_EVENT, action, event_args)
            return


INOVELLI_AUTOMATION_TRIGGERS = {
    (COMMAND_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_PRESS}"},
    (COMMAND_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_PRESS}"},
    (COMMAND_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_PRESS}"},
    (COMMAND_HOLD, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_HOLD}"},
    (COMMAND_HOLD, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_HOLD}"},
    (DOUBLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_DOUBLE}"},
    (DOUBLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_DOUBLE}"},
    (DOUBLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_DOUBLE}"},
    (TRIPLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_TRIPLE}"},
    (TRIPLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_TRIPLE}"},
    (TRIPLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_TRIPLE}"},
    (QUADRUPLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_QUAD}"},
    (QUADRUPLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_QUAD}"},
    (QUADRUPLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_QUAD}"},
    (QUINTUPLE_PRESS, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_QUINTUPLE}"},
    (QUINTUPLE_PRESS, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_QUINTUPLE}"},
    (QUINTUPLE_PRESS, CONFIG): {COMMAND: f"{BUTTON_3}_{COMMAND_QUINTUPLE}"},
    (COMMAND_RELEASE, ON): {COMMAND: f"{BUTTON_2}_{COMMAND_RELEASE}"},
    (COMMAND_RELEASE, OFF): {COMMAND: f"{BUTTON_1}_{COMMAND_RELEASE}"},
}
