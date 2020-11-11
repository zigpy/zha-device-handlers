"""Module for Philips quirks implementations."""
import asyncio
import logging
import time

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, LevelControl, OnOff
from zigpy.zcl.clusters.lighting import Color

from ..const import (
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

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821
PHILIPS = "Philips"
_LOGGER = logging.getLogger(__name__)

HUE_REMOTE_DEVICE_TRIGGERS = {
    (SHORT_PRESS, TURN_ON): {COMMAND: "on_press"},
    (SHORT_PRESS, TURN_OFF): {COMMAND: "off_press"},
    (SHORT_PRESS, DIM_UP): {COMMAND: "up_press"},
    (SHORT_PRESS, DIM_DOWN): {COMMAND: "down_press"},
    (LONG_PRESS, TURN_ON): {COMMAND: "on_hold"},
    (LONG_PRESS, TURN_OFF): {COMMAND: "off_hold"},
    (LONG_PRESS, DIM_UP): {COMMAND: "up_hold"},
    (LONG_PRESS, DIM_DOWN): {COMMAND: "down_hold"},
    (DOUBLE_PRESS, TURN_ON): {COMMAND: "on_double_press"},
    (DOUBLE_PRESS, TURN_OFF): {COMMAND: "off_double_press"},
    (DOUBLE_PRESS, DIM_UP): {COMMAND: "up_double_press"},
    (DOUBLE_PRESS, DIM_DOWN): {COMMAND: "down_double_press"},
    (TRIPLE_PRESS, TURN_ON): {COMMAND: "on_triple_press"},
    (TRIPLE_PRESS, TURN_OFF): {COMMAND: "off_triple_press"},
    (TRIPLE_PRESS, DIM_UP): {COMMAND: "up_triple_press"},
    (TRIPLE_PRESS, DIM_DOWN): {COMMAND: "down_triple_press"},
    (QUADRUPLE_PRESS, TURN_ON): {COMMAND: "on_quadruple_press"},
    (QUADRUPLE_PRESS, TURN_OFF): {COMMAND: "off_quadruple_press"},
    (QUADRUPLE_PRESS, DIM_UP): {COMMAND: "up_quadruple_press"},
    (QUADRUPLE_PRESS, DIM_DOWN): {COMMAND: "down_quadruple_press"},
    (QUINTUPLE_PRESS, TURN_ON): {COMMAND: "on_quintuple_press"},
    (QUINTUPLE_PRESS, TURN_OFF): {COMMAND: "off_quintuple_press"},
    (QUINTUPLE_PRESS, DIM_UP): {COMMAND: "up_quintuple_press"},
    (QUINTUPLE_PRESS, DIM_DOWN): {COMMAND: "down_quintuple_press"},
    (SHORT_RELEASE, TURN_ON): {COMMAND: "on_short_release"},
    (SHORT_RELEASE, TURN_OFF): {COMMAND: "off_short_release"},
    (SHORT_RELEASE, DIM_UP): {COMMAND: "up_short_release"},
    (SHORT_RELEASE, DIM_DOWN): {COMMAND: "down_short_release"},
    (LONG_RELEASE, TURN_ON): {COMMAND: "on_long_release"},
    (LONG_RELEASE, TURN_OFF): {COMMAND: "off_long_release"},
    (LONG_RELEASE, DIM_UP): {COMMAND: "up_long_release"},
    (LONG_RELEASE, DIM_DOWN): {COMMAND: "down_long_release"},
}


class PowerOnState(t.enum8):
    """Philips power on state enum."""

    Off = 0x00
    On = 0x01
    LastState = 0xFF


class PhilipsOnOffCluster(CustomCluster, OnOff):
    """Philips OnOff cluster."""

    attributes = OnOff.attributes.copy()
    attributes.update({0x4003: ("power_on_state", PowerOnState)})


class PhilipsLevelControlCluster(CustomCluster, LevelControl):
    """Philips LevelControl cluster."""

    attributes = LevelControl.attributes.copy()
    attributes.update({0x4000: ("power_on_level", t.uint8_t)})


class PhilipsColorCluster(CustomCluster, Color):
    """Philips Color cluster."""

    attributes = Color.attributes.copy()
    attributes.update({0x4010: ("power_on_color_temperature", t.uint16_t)})


class PhilipsBasicCluster(CustomCluster, Basic):
    """Philips Basic cluster."""

    manufacturer_attributes = {0x0031: ("philips", t.bitmap16)}

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

    cluster_id = 64512
    name = "PhilipsRemoteCluster"
    ep_attribute = "philips_remote_cluster"
    manufacturer_client_commands = {
        0x0000: (
            "notification",
            (t.uint8_t, t.uint24_t, t.uint8_t, t.uint8_t, t.uint8_t, t.uint8_t),
            False,
        )
    }
    BUTTONS = {1: "on", 2: "up", 3: "down", 4: "off"}
    PRESS_TYPES = {0: "press", 1: "hold", 2: "short_release", 3: "long_release"}

    button_press_queue = ButtonPressQueue()

    def handle_cluster_request(self, tsn, command_id, args):
        """Handle the cluster command."""
        _LOGGER.debug(
            "PhilipsRemoteCluster - handle_cluster_request tsn: [%s] command id: %s - args: [%s]",
            tsn,
            command_id,
            args,
        )

        button = self.BUTTONS.get(args[0], args[0])
        press_type = self.PRESS_TYPES.get(args[2], args[2])

        event_args = {
            BUTTON: button,
            PRESS_TYPE: press_type,
            COMMAND_ID: command_id,
            ARGS: args,
        }

        def send_press_event(click_count):
            _LOGGER.debug(
                "PhilipsRemoteCluster - send_press_event click_count: [%s]", click_count
            )
            press_type = None
            if click_count == 1:
                press_type = "press"
            elif click_count == 2:
                press_type = "double_press"
            elif click_count == 3:
                press_type = "triple_press"
            elif click_count == 4:
                press_type = "quadruple_press"
            elif click_count > 4:
                press_type = "quintuple_press"

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
