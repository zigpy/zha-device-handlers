"""Module for Philips quirks implementations."""
import asyncio
import logging
import time
from typing import Any, List, Optional, Union

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.measurement import OccupancySensing

from zhaquirks.const import (
    ARGS,
    BUTTON,
    COMMAND,
    COMMAND_ID,
    DIM_DOWN,
    DIM_UP,
    DOUBLE_PRESS,
    LONG_PRESS,
    LONG_RELEASE,
    PRESS_TYPE,
    QUADRUPLE_PRESS,
    QUINTUPLE_PRESS,
    SHORT_PRESS,
    SHORT_RELEASE,
    TRIPLE_PRESS,
    TURN_OFF,
    TURN_ON,
    ZHA_SEND_EVENT,
)

PHILIPS = "Philips"
SIGNIFY = "Signify Netherlands B.V."
_LOGGER = logging.getLogger(__name__)


class PhilipsOccupancySensing(CustomCluster):
    """Philips occupancy cluster."""

    cluster_id = OccupancySensing.cluster_id
    ep_attribute = "philips_occupancy"

    attributes = OccupancySensing.attributes.copy()
    attributes[0x0030] = ("sensitivity", t.uint8_t, True)
    attributes[0x0031] = ("sensitivity_max", t.uint8_t, True)

    server_commands = OccupancySensing.server_commands.copy()
    client_commands = OccupancySensing.client_commands.copy()


class PhilipsBasicCluster(CustomCluster, Basic):
    """Philips Basic cluster."""

    attributes = Basic.attributes.copy()
    attributes[0x0031] = ("philips", t.bitmap16, True)

    attr_config = {0x0031: 0x000B}

    async def bind(self):
        """Bind cluster."""
        result = await super().bind()
        await self.write_attributes(self.attr_config, manufacturer=0x100B)
        return result


class ButtonPressQueue:
    """Philips button queue to derive multiple press events."""

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


class PhilipsRemoteCluster(CustomCluster):
    """Philips remote cluster."""

    cluster_id = 0xFC00
    name = "PhilipsRemoteCluster"
    ep_attribute = "philips_remote_cluster"
    client_commands = {
        0x0000: foundation.ZCLCommandDef(
            "notification",
            {
                "button": t.uint8_t,
                "param2": t.uint24_t,
                "press_type": t.uint8_t,
                "param4": t.uint8_t,
                "duration": t.uint16_t,
            },
            False,
            is_manufacturer_specific=True,
        )
    }
    BUTTONS = {1: TURN_ON, 2: DIM_UP, 3: DIM_DOWN, 4: TURN_OFF}
    PRESS_TYPES = {
        0: SHORT_PRESS,
        1: LONG_PRESS,
        2: SHORT_RELEASE,
        3: LONG_RELEASE,
        4: DOUBLE_PRESS,
        5: TRIPLE_PRESS,
        6: QUADRUPLE_PRESS,
        7: QUINTUPLE_PRESS,
    }

    button_press_queue = ButtonPressQueue()

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: List[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle the cluster command."""
        _LOGGER.debug(
            "%s - handle_cluster_request tsn: [%s] command id: %s - args: [%s]",
            self.__class__.__name__,
            hdr.tsn,
            hdr.command_id,
            args,
        )

        button = self.BUTTONS.get(args[0])
        # Bail on unknown buttons. (This gets rid of dial button "presses")
        if button is None:
            return

        press_type = self.PRESS_TYPES.get(args[2], args[2])
        duration = args[4]

        event_args = {
            BUTTON: button,
            PRESS_TYPE: press_type,
            COMMAND_ID: hdr.command_id,
            "duration": duration,
            ARGS: args,
        }

        def send_press_event(click_count):
            _LOGGER.debug(
                "%s - send_press_event click_count: [%s]",
                self.__class__.__name__,
                click_count,
            )
            press_type = None
            if click_count == 1:
                press_type = SHORT_PRESS
            elif click_count == 2:
                press_type = DOUBLE_PRESS
            elif click_count == 3:
                press_type = TRIPLE_PRESS
            elif click_count == 4:
                press_type = QUADRUPLE_PRESS
            elif click_count > 4:
                press_type = QUINTUPLE_PRESS

            if press_type:
                # Override PRESS_TYPE
                event_args[PRESS_TYPE] = press_type
                action = f"{button}_{press_type}"
                self.listener_event(ZHA_SEND_EVENT, action, event_args)

        # Derive Multiple Presses
        if press_type == "press":
            self.button_press_queue.press(send_press_event, button)
        else:
            action = f"{button}_{press_type}"
            self.listener_event(ZHA_SEND_EVENT, action, event_args)

    @classmethod
    def generate_device_automation_triggers(cls, additional=None):
        triggers = {}
        for button in cls.BUTTONS.values():
            for press_type in cls.PRESS_TYPES.values():
                triggers[(press_type, button)] = {COMMAND: f"{button}_{press_type}"}

        if additional:
            triggers.update(additional)

        return triggers
