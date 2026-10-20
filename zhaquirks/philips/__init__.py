"""Module for Philips quirks implementations."""

import asyncio
import itertools
import logging
import time
from typing import Any, Final

import zigpy.types as t
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic
from zigpy.zcl.clusters.measurement import OccupancySensing
from zigpy.zcl.foundation import BaseCommandDefs, ZCLAttributeDef, ZCLCommandDef

from zhaquirks.builder import ButtonEvent, ButtonEventMetadata, ButtonEventType
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    ARGS,
    BUTTON,
    COMMAND,
    COMMAND_HOLD,
    COMMAND_ID,
    COMMAND_M_INITIAL_PRESS,
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

# The release of a short press, as the device reports it
COMMAND_PRESS_RELEASE = "press_release"


class PhilipsOccupancySensing(CustomCluster, OccupancySensing):
    """Philips occupancy cluster."""

    class AttributeDefs(OccupancySensing.AttributeDefs):
        """Attribute definitions."""

        sensitivity: Final = ZCLAttributeDef(
            id=0x0030, type=t.uint8_t, manufacturer_code=0x100B
        )
        sensitivity_max: Final = ZCLAttributeDef(
            id=0x0031, type=t.uint8_t, manufacturer_code=0x100B
        )


class PhilipsBasicCluster(CustomCluster, Basic):
    """Philips Basic cluster."""

    class AttributeDefs(Basic.AttributeDefs):
        """Attribute definitions."""

        philips: Final = ZCLAttributeDef(
            id=0x0031, type=t.bitmap16, is_manufacturer_specific=True
        )

    attr_config = {AttributeDefs.philips.id: 0x000B}

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration."""
        await self.write_attributes(self.attr_config, manufacturer=0x100B)


class ButtonPressQueue:
    """Philips button queue to derive multiple press events."""

    def __init__(self):
        """Init."""
        self._ms_threshold = 300
        self._ms_last_click = 0
        self._click_counter = 1
        self._callback = lambda x: None
        self._task = None

    async def _job(self):
        await asyncio.sleep(self._ms_threshold / 1000)
        self._callback(self._click_counter)

    def press(self, callback):
        """Process a button press."""
        self._callback = callback
        now_ms = time.time() * 1000
        if now_ms - self._ms_last_click > self._ms_threshold:
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

    class ClientCommandDefs(BaseCommandDefs):
        """Client command definitions."""

        notification = foundation.ZCLCommandDef(
            id=0x0000,
            schema={
                "button": t.uint8_t,
                "param2": t.uint24_t,
                "press_type": t.uint8_t,
                "param4": t.uint8_t,
                "param5": t.uint16_t,
            },
            is_manufacturer_specific=True,
        )

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

    # The press types the device reports when the button goes down (0) and when it
    # is released after a short press (2). They are sent as they arrive, under their
    # own names, as the press and short release events are only sent once the
    # multi-press window has passed. Press types in `PRESS_TYPES` are sent already.
    NATIVE_PRESS_TYPES: dict[int, str] = {
        0: COMMAND_M_INITIAL_PRESS,
        2: COMMAND_PRESS_RELEASE,
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

    def __init__(self, endpoint, is_server=True):
        """Initialize button press queue for each button."""
        super().__init__(endpoint, is_server)
        self.button_press_queue = {k: ButtonPressQueue() for k in self.BUTTONS}

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: t.AddrMode | None = None,
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
            _LOGGER.debug(
                "%s - handle_cluster_request unknown button id [%s]",
                self.__class__.__name__,
                args[0],
            )
            return
        _LOGGER.debug(
            "%s - handle_cluster_request button id: [%s], button name: [%s]",
            self.__class__.__name__,
            args[0],
            button,
        )

        native_press_type = self.NATIVE_PRESS_TYPES.get(args[2])
        if native_press_type is not None and args[2] not in self.PRESS_TYPES:
            self.listener_event(
                ZHA_SEND_EVENT,
                f"{button.action}_{native_press_type}",
                {
                    BUTTON: button.id,
                    PRESS_TYPE: native_press_type,
                    COMMAND_ID: hdr.command_id,
                    "duration": args[4],
                    ARGS: args,
                },
            )

        press_type = self.PRESS_TYPES.get(args[2])
        if (
            press_type is None
            and self.SIMULATE_SHORT_EVENTS is not None
            and args[2] == 2
        ):
            press_type = self.SIMULATE_SHORT_EVENTS[1]
        if press_type is None:
            _LOGGER.debug(
                "%s - handle_cluster_request unknown button press type: [%s]",
                self.__class__.__name__,
                press_type,
            )
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
                    "%s - send_press_event emitting simulated action: [%s], event_args: %s",
                    self.__class__.__name__,
                    action,
                    sim_event_args,
                )
                self.listener_event(ZHA_SEND_EVENT, action, sim_event_args)

        # Derive Multiple Presses
        if press_type.name == SHORT_RELEASE:
            _LOGGER.debug(
                "%s - handle_cluster_request handling short release. Push to button press queue for button %s",
                self.__class__.__name__,
                args[0],
            )
            self.button_press_queue[args[0]].press(send_press_event)
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

    @classmethod
    def generate_button_event_entities(
        cls, endpoint_id: int, names: dict[int, dict[str, Any]]
    ) -> tuple[ButtonEventMetadata, ...]:
        """Generate a button event entity for each button of the device.

        The device reports when a button goes down, when it is released after a
        short press, while it is held (repeatedly) and when it is released after
        being held. The press and multi-press events derived with the press queue
        are not used, as they are only sent after a delay.

        `names` holds the entity naming (`unique_id_suffix`, `translation_key`,
        `fallback_name` and `translation_placeholders`) of each button.
        """
        long_press = cls.PRESS_TYPES[1]
        long_release = cls.PRESS_TYPES[3]

        # The native events are not sent for press types the subclass maps itself
        native_events = [
            (event_type, press_type)
            for event_type, press_type in (
                (ButtonEventType.PRESS_START, 0),
                (ButtonEventType.PRESS_END, 2),
            )
            if press_type not in cls.PRESS_TYPES
        ]

        return tuple(
            ButtonEventMetadata(
                events=[
                    *(
                        ButtonEvent(
                            event_type=event_type,
                            event_data={
                                COMMAND: (
                                    f"{button.action}"
                                    f"_{cls.NATIVE_PRESS_TYPES[press_type]}"
                                )
                            },
                        )
                        for event_type, press_type in native_events
                    ),
                    ButtonEvent(
                        event_type=ButtonEventType.LONG_PRESS_START,
                        trigger=(long_press.trigger, button.trigger),
                        repeats=True,
                    ),
                    ButtonEvent(
                        event_type=ButtonEventType.LONG_PRESS_END,
                        trigger=(long_release.trigger, button.trigger),
                    ),
                ],
                cluster_id=cls.cluster_id,
                cluster_type=ClusterType.Server,
                endpoint_id=endpoint_id,
                **names[button_id],
            )
            for button_id, button in cls.BUTTONS.items()
        )


class PhilipsRwlRemoteCluster(PhilipsRemoteCluster):
    """Philips remote cluster for RWL devices."""

    BUTTONS = {
        1: Button("on", TURN_ON),
        2: Button("up", DIM_UP),
        3: Button("down", DIM_DOWN),
        4: Button("off", TURN_OFF),
    }


# Button event entity naming of the RWL dimmer switch buttons
RWL_BUTTON_NAMES: dict[int, dict[str, Any]] = {
    1: {
        "unique_id_suffix": "button_on",
        "translation_key": "on_button",
        "fallback_name": "On button",
    },
    2: {
        "unique_id_suffix": "button_dim_up",
        "translation_key": "dim_up_button",
        "fallback_name": "Dim up button",
    },
    3: {
        "unique_id_suffix": "button_dim_down",
        "translation_key": "dim_down_button",
        "fallback_name": "Dim down button",
    },
    4: {
        "unique_id_suffix": "button_off",
        "translation_key": "off_button",
        "fallback_name": "Off button",
    },
}


class PhilipsHueLightCluster(CustomCluster):
    """Philips Hue manufacturer cluster."""

    cluster_id: Final[t.uint16_t] = 0xFC03
    ep_attribute: Final[str] = "philips_hue_light_cluster"
    name: Final[str] = "PhilipsHueLightCluster"

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        multicolor: Final = ZCLCommandDef(
            id=0x00,
            schema={"data": t.SerializableBytes},
            is_manufacturer_specific=True,
        )
