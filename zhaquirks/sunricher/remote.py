"""Sunricher remote device."""

import logging
from typing import Any, Final, NamedTuple, Optional, Union

from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks import CustomCluster
from zhaquirks.const import (
    BUTTON,
    COMMAND,
    DOUBLE_PRESS,
    LONG_PRESS,
    LONG_RELEASE,
    PRESS_TYPE,
    SHORT_PRESS,
    ZHA_SEND_EVENT,
)

_LOGGER = logging.getLogger(__name__)
SUNRICHER = "Sunricher"


class Button(NamedTuple):
    """Button class."""

    id: int
    action: str
    trigger: str


class PressType(NamedTuple):
    """Button press type."""

    name: str
    action: str
    trigger: str = None


class ZG9002KR12ProRemoteCluster(CustomCluster):
    """Sunricher manufacturer specific cluster for remote."""

    cluster_id: Final[t.uint16_t] = 0xFF03
    name: Final = "Sunricher remote cluster"
    ep_attribute: Final = "sunricher_remote_cluster"

    # Button mapping
    BUTTONS: dict[int, Button] = {
        1: Button(1, "k1", "K1"),
        2: Button(2, "k2", "K2"),
        3: Button(3, "k3", "K3"),
        4: Button(4, "k4", "K4"),
        5: Button(5, "k5", "K5"),
        6: Button(6, "k6", "K6"),
        7: Button(7, "k7", "K7"),
        8: Button(8, "k8", "K8"),
        9: Button(9, "knob", "Knob"),
        11: Button(11, "k9", "K9"),
        12: Button(12, "k10", "K10"),
        15: Button(15, "k11", "K11"),
        16: Button(16, "k12", "K12"),
    }

    # Press types
    PRESS_TYPES: dict[int, PressType] = {
        1: PressType(SHORT_PRESS, "short_press", "Short Press"),
        2: PressType(DOUBLE_PRESS, "double_press", "Double Press"),
        3: PressType(LONG_PRESS, "hold", "Hold"),
        4: PressType(LONG_RELEASE, "hold_released", "Hold Released"),
    }

    # Knob directions
    KNOB_DIRECTIONS: dict[int, PressType] = {
        1: PressType("clockwise", "clockwise_rotation", "Clockwise Rotation"),
        2: PressType(
            "anti_clockwise", "anti_clockwise_rotation", "Anti-clockwise Rotation"
        ),
    }

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

        message_type = args[0]
        if message_type == 0x01:
            # Button press event
            press_type_mask = args[3]
            button_mask = (args[1] << 8) | args[2]

            press_type = self.PRESS_TYPES.get(press_type_mask)
            action_buttons = []
            for i in range(16):
                if (button_mask >> i) & 1:
                    button_id = i + 1
                    button = self.BUTTONS.get(button_id)
                    action_buttons.append(button)

            _LOGGER.debug(
                "Button event: action=%s, action_buttons=%s",
                press_type.action,
                [b.action for b in action_buttons],
            )

            for button in action_buttons:
                action = f"{button.action}_{press_type.action}"
                event_data = {
                    BUTTON: button.id,
                    PRESS_TYPE: press_type.action,
                    COMMAND: "button_press",
                }
                self.listener_event(ZHA_SEND_EVENT, action, event_data)

        elif message_type == 0x03:
            # Knob rotation event
            direction_mask = args[1]
            action_speed = args[3]
            direction = self.KNOB_DIRECTIONS.get(direction_mask)

            _LOGGER.debug(
                "Knob event: action=%s, action_speed=%s", direction.action, action_speed
            )

            event_data = {
                BUTTON: 9,  # knob
                PRESS_TYPE: direction.action,
                "speed": action_speed,
            }
            self.listener_event(ZHA_SEND_EVENT, direction.action, event_data)

    @classmethod
    def generate_device_automation_triggers(cls):
        """Generate automation triggers based on device buttons and press-types."""
        triggers = {}
        # Generate button triggers
        for button in cls.BUTTONS.values():
            for press_type in cls.PRESS_TYPES.values():
                triggers[(press_type.trigger, button.trigger)] = {
                    COMMAND: f"{button.action}_{press_type.action}"
                }

        # Generate knob triggers
        button = cls.BUTTONS.get(9)  # knob
        if button:
            for direction in cls.KNOB_DIRECTIONS.values():
                triggers[(direction.trigger, button.trigger)] = {
                    COMMAND: direction.action
                }

        _LOGGER.debug("Generated triggers: %s", triggers)
        return triggers


(
    QuirkBuilder(SUNRICHER, "HK-ZRC-K12&RS-E")
    .friendly_name(
        model="SR-ZG9002KR12-Pro",
        manufacturer=SUNRICHER,
    )
    .replaces(ZG9002KR12ProRemoteCluster, endpoint_id=1)
    .device_automation_triggers(
        ZG9002KR12ProRemoteCluster.generate_device_automation_triggers()
    )
    .add_to_registry()
)
