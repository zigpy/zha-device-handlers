"""Module for Philips quirks implementations."""

import asyncio
import itertools
import logging
import time
from typing import Any, Final, Optional, Union

from zigpy.quirks import CustomCluster
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    ARGS,
    BUTTON,
    COMMAND,
    COMMAND_HOLD,
    COMMAND_ID,
    COMMAND_M_LONG_RELEASE,
    COMMAND_M_SHORT_RELEASE,
    COMMAND_PRESS,
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

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        philips: Final = ZCLAttributeDef(
            id=0x0031, type=t.bitmap16, is_manufacturer_specific=True
        )

    attr_config = {AttributeDefs.philips.id: 0x000B}

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


class Button:
    """Represents a remote button, including string literals used in triggers and actions."""

    def __init__(
        self, id: str, trigger: str | None = None, action: str | None = None
    ) -> None:
        """Init."""
        self.id = id
        self.trigger = trigger or id
        self.action = action or id

    def __repr__(self) -> str:
        """Repr."""
        return f"<Button id={self.id}, trigger={self.trigger}, action={self.action}>"


class PressType:
    """Represents a remote button press-type, including string literals used in triggers and actions."""

    def __init__(
        self, name: str, action: str, arg: str | None = None, trigger: str | None = None
    ) -> None:
        """Init."""
        self.name = name
        self.action = action
        self.arg = arg or action
        self.trigger = trigger or name

    def __repr__(self) -> str:
        """Repr."""
        return f"<PressType name={self.name}, action={self.action}, trigger={self.trigger}, arg={self.arg}>"


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
                "param5": t.uint16_t,
            },
            False,
            is_manufacturer_specific=True,
        )
    }

    BUTTONS: dict[int, Button] = {}

    PRESS_TYPES: dict[int, PressType] = {
        # We omit "short_press" and "short_release" on purpose, so it
        # won't interfere with simulated multi-press events. We emit
        # them in the multi-press code later on.
        # 0: SHORT_PRESS,
        1: PressType(LONG_PRESS, COMMAND_HOLD),
        # 2: SHORT_RELEASE,
        3: PressType(LONG_RELEASE, COMMAND_M_LONG_RELEASE),
    }

    MULTI_PRESS_EVENTS: dict[int, PressType] = {
        2: PressType(DOUBLE_PRESS, "double_press"),
        3: PressType(TRIPLE_PRESS, "triple_press"),
        4: PressType(QUADRUPLE_PRESS, "quadruple_press"),
        5: PressType(QUINTUPLE_PRESS, "quintuple_press"),
    }
    SIMULATE_SHORT_EVENTS = [
        PressType(SHORT_PRESS, COMMAND_PRESS),
        PressType(SHORT_RELEASE, COMMAND_M_SHORT_RELEASE),
    ]

    button_press_queue = ButtonPressQueue()

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
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
        _LOGGER.debug(
            "%s - handle_cluster_request button id: [%s], button name: [%s]",
            self.__class__.__name__,
            args[0],
            button,
        )
        # Bail on unknown buttons. (This gets rid of dial button "presses")
        if button is None:
            return

        press_type = self.PRESS_TYPES.get(args[2])
        if (
            press_type is None
            and self.SIMULATE_SHORT_EVENTS is not None
            and args[2] == 2
        ):
            press_type = self.SIMULATE_SHORT_EVENTS[1]
        if press_type is None:
            return

        duration = args[4]
        _LOGGER.debug(
            "%s - handle_cluster_request button press type: [%s], duration: [%s]",
            self.__class__.__name__,
            press_type,
            duration,
        )

        event_args = {
            BUTTON: button.id,
            PRESS_TYPE: press_type.arg,
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
                press_type = self.PRESS_TYPES.get(0) or self.SIMULATE_SHORT_EVENTS[0]
            elif click_count > 1:
                press_type = self.MULTI_PRESS_EVENTS[min(click_count, 5)]

            _LOGGER.debug(
                "%s - send_press_event evaluated press_type: [%s]",
                self.__class__.__name__,
                press_type,
            )
            if press_type is not None:
                # Override PRESS_TYPE
                event_args[PRESS_TYPE] = press_type.arg
                event_args[ARGS] = list(event_args[ARGS])
                event_args[ARGS][2] = 0 if click_count < 2 else 2 + min(click_count, 5)
                action = f"{button.action}_{press_type.action}"
                _LOGGER.debug(
                    "%s - send_press_event emitting action: [%s] event_args: %s",
                    self.__class__.__name__,
                    action,
                    event_args,
                )
                self.listener_event(ZHA_SEND_EVENT, action, event_args)

            # simulate short release event, if needed for this device type
            if (
                press_type.name == SHORT_PRESS
                and self.SIMULATE_SHORT_EVENTS is not None
            ):
                press_type = self.PRESS_TYPES.get(2) or self.SIMULATE_SHORT_EVENTS[1]
                sim_event_args = event_args.copy()
                sim_event_args[PRESS_TYPE] = press_type.arg
                sim_event_args[ARGS] = sim_event_args[ARGS].copy()
                sim_event_args[ARGS][2] = 2
                action = f"{button.action}_{press_type.action}"
                _LOGGER.debug(
                    "%s - send_press_event emitting simulated action: [%s]",
                    self.__class__.__name__,
                    action,
                )
                self.listener_event(ZHA_SEND_EVENT, action, sim_event_args)

        # Derive Multiple Presses
        if press_type.name == SHORT_RELEASE:
            self.button_press_queue.press(send_press_event, button.id)
        else:
            action = f"{button.action}_{press_type.action}"
            self.listener_event(ZHA_SEND_EVENT, action, event_args)

    @classmethod
    def generate_device_automation_triggers(cls, additional=None):
        """Generate automation triggers based on device buttons and press-types."""
        triggers = {}
        for button in cls.BUTTONS.values():
            press_types = [cls.PRESS_TYPES.values()]
            if cls.SIMULATE_SHORT_EVENTS is not None:
                press_types.append(cls.SIMULATE_SHORT_EVENTS)
                press_types.append(cls.MULTI_PRESS_EVENTS.values())
            for press_type in itertools.chain(*press_types):
                triggers[(press_type.trigger, button.trigger)] = {
                    COMMAND: f"{button.action}_{press_type.action}"
                }

        if additional:
            triggers.update(additional)

        return triggers


class PhilipsRwlRemoteCluster(PhilipsRemoteCluster):
    """Philips remote cluster for RWL devices."""

    BUTTONS = {
        1: Button("on", TURN_ON),
        2: Button("up", DIM_UP),
        3: Button("down", DIM_DOWN),
        4: Button("off", TURN_OFF),
    }
