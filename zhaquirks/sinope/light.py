"""Module to handle quirks of the Sinopé Technologies light.

Supported devices SW2500ZB, SW2500ZB-G2 dimmer DM2500ZB, DM2500ZB-G2, DM2550ZB,
DM2550ZB-G2.
"""

import logging
from typing import Any, Final, Optional, Union

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseCommandDefs

from zhaquirks import EventableCluster
from zhaquirks.const import (
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    BUTTON,
    COMMAND_M_INITIAL_PRESS,
    COMMAND_M_LONG_RELEASE,
    COMMAND_M_MULTI_PRESS_COMPLETE,
    COMMAND_M_SHORT_RELEASE,
    DESCRIPTION,
    TURN_OFF,
    TURN_ON,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.sinope import (
    ATTRIBUTE_ACTION,
    LIGHT_DEVICE_TRIGGERS,
    SINOPE,
    SINOPE_MANUFACTURER_CLUSTER_ID,
    ButtonAction,
    CustomDeviceTemperatureCluster,
)

_LOGGER = logging.getLogger(__name__)


class KeypadLock(t.enum8):
    """Keypad_lockout values."""

    Unlocked = 0x00
    Locked = 0x01
    Partial_lock = 0x02


class PhaseControl(t.enum8):
    """Phase control value, reverse / forward."""

    Forward = 0x00
    Reverse = 0x01


class DoubleFull(t.enum8):
    """Double click up set full intensity."""

    Off = 0x00
    On = 0x01


class SinopeTechnologiesManufacturerCluster(CustomCluster):
    """SinopeTechnologiesManufacturerCluster manufacturer cluster."""

    KeypadLock: Final = KeypadLock
    PhaseControl: Final = PhaseControl
    DoubleFull: Final = DoubleFull
    Action: Final = ButtonAction

    cluster_id: Final[t.uint16_t] = SINOPE_MANUFACTURER_CLUSTER_ID
    name: Final = "SinopeTechnologiesManufacturerCluster"
    ep_attribute: Final = "sinope_manufacturer_specific"

    class AttributeDefs(foundation.BaseAttributeDefs):
        """Sinope Manufacturer Cluster Attributes."""

        keypad_lockout: Final = foundation.ZCLAttributeDef(
            id=0x0002, type=KeypadLock, access="rw", is_manufacturer_specific=True
        )
        firmware_number: Final = foundation.ZCLAttributeDef(
            id=0x0003, type=t.uint16_t, access="r", is_manufacturer_specific=True
        )
        firmware_version: Final = foundation.ZCLAttributeDef(
            id=0x0004, type=t.CharacterString, access="r", is_manufacturer_specific=True
        )
        on_intensity: Final = foundation.ZCLAttributeDef(
            id=0x0010, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        on_led_color: Final = foundation.ZCLAttributeDef(
            id=0x0050, type=t.uint24_t, access="rw", is_manufacturer_specific=True
        )
        off_led_color: Final = foundation.ZCLAttributeDef(
            id=0x0051, type=t.uint24_t, access="rw", is_manufacturer_specific=True
        )
        on_led_intensity: Final = foundation.ZCLAttributeDef(
            id=0x0052, type=t.uint8_t, access="rw", is_manufacturer_specific=True
        )
        off_led_intensity: Final = foundation.ZCLAttributeDef(
            id=0x0053, type=t.uint8_t, access="rw", is_manufacturer_specific=True
        )
        action_report: Final = foundation.ZCLAttributeDef(
            id=0x0054, type=ButtonAction, access="rp", is_manufacturer_specific=True
        )
        min_intensity: Final = foundation.ZCLAttributeDef(
            id=0x0055, type=t.uint16_t, access="rw", is_manufacturer_specific=True
        )
        phase_control: Final = foundation.ZCLAttributeDef(
            id=0x0056, type=PhaseControl, access="rw", is_manufacturer_specific=True
        )
        double_up_full: Final = foundation.ZCLAttributeDef(
            id=0x0058, type=DoubleFull, access="rw", is_manufacturer_specific=True
        )
        current_summation_delivered: Final = foundation.ZCLAttributeDef(
            id=0x0090, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        timer: Final = foundation.ZCLAttributeDef(
            id=0x00A0, type=t.uint32_t, access="rw", is_manufacturer_specific=True
        )
        timer_countdown: Final = foundation.ZCLAttributeDef(
            id=0x00A1, type=t.uint32_t, access="r", is_manufacturer_specific=True
        )
        connected_load: Final = foundation.ZCLAttributeDef(
            id=0x0119, type=t.uint16_t, access="rw", is_manufacturer_specific=True
        )
        status: Final = foundation.ZCLAttributeDef(
            id=0x0200, type=t.bitmap32, access="rp", is_manufacturer_specific=True
        )
        cluster_revision: Final = foundation.ZCL_CLUSTER_REVISION_ATTR

    class ServerCommandDefs(BaseCommandDefs):
        """Server command definitions."""

        button_press = foundation.ZCLCommandDef(
            id=0x54,
            schema={"command": t.uint8_t},
            is_manufacturer_specific=True,
        )

    def handle_cluster_general_request(
        self,
        hdr: foundation.ZCLHeader,
        args: list[Any],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ):
        """Handle the cluster command."""
        self.debug(
            "SINOPE cluster general request: hdr: %s - args: [%s]",
            hdr,
            args,
        )

        if hdr.command_id != foundation.GeneralCommand.Report_Attributes:
            return super().handle_cluster_general_request(
                hdr, args, dst_addressing=dst_addressing
            )

        attr = args[0][0]

        if attr.attrid != self.AttributeDefs.action_report.id:
            return super().handle_cluster_general_request(
                hdr, args, dst_addressing=dst_addressing
            )

        action = self.Action(attr.value.value)

        command, button = self._get_command_from_action(action)
        if not command or not button:
            return

        event_args = {
            ATTRIBUTE_ID: 84,
            ATTRIBUTE_NAME: ATTRIBUTE_ACTION,
            BUTTON: button,
            DESCRIPTION: action.name,
            VALUE: action.value,
        }

        self.debug(
            "SINOPE ZHA_SEND_EVENT command: '%s' event_args: %s",
            command,
            event_args,
        )

        self.listener_event(ZHA_SEND_EVENT, command, event_args)

    def _get_command_from_action(
        self, action: ButtonAction
    ) -> tuple[str | None, str | None]:
        # const lookup = {1: 'up_single', 2: 'up_single_released', 3: 'up_hold', 4: 'up_double',
        #             17: 'down_single, 18: 'down_single_released', 19: 'down_hold', 20: 'down_double'};
        match action:
            case self.Action.Pressed_off:
                return COMMAND_M_INITIAL_PRESS, TURN_OFF
            case self.Action.Pressed_on:
                return COMMAND_M_INITIAL_PRESS, TURN_ON
            case self.Action.Released_off:
                return COMMAND_M_SHORT_RELEASE, TURN_OFF
            case self.Action.Released_on:
                return COMMAND_M_SHORT_RELEASE, TURN_ON
            case self.Action.Double_off:
                return COMMAND_M_MULTI_PRESS_COMPLETE, TURN_OFF
            case self.Action.Double_on:
                return COMMAND_M_MULTI_PRESS_COMPLETE, TURN_ON
            case self.Action.Long_off:
                return COMMAND_M_LONG_RELEASE, TURN_OFF
            case self.Action.Long_on:
                return COMMAND_M_LONG_RELEASE, TURN_ON
            case _:
                self.debug("SINOPE unhandled action: %s", action)
                return None, None


class LightManufacturerCluster(EventableCluster, SinopeTechnologiesManufacturerCluster):
    """LightManufacturerCluster: fire events corresponding to press type."""


(
    QuirkBuilder(SINOPE, "SW2500ZB")
    .applies_to(SINOPE, "SW2500ZB-G2")
    .replaces_endpoint(
        1, device_type=zha_p.DeviceType.ON_OFF_LIGHT
    )  # Was ON_OFF_LIGHT_SWITCH
    .replaces(LightManufacturerCluster, endpoint_id=1)
    .device_automation_triggers(LIGHT_DEVICE_TRIGGERS)
    .add_to_registry()
)

(
    QuirkBuilder(SINOPE, "DM2500ZB")
    .applies_to(SINOPE, "DM2500ZB-G2")
    .replaces_endpoint(
        1, device_type=zha_p.DeviceType.DIMMABLE_LIGHT
    )  # Was DIMMER_SWITCH
    .replaces(CustomDeviceTemperatureCluster, endpoint_id=1)
    .replaces(LightManufacturerCluster, endpoint_id=1)
    .device_automation_triggers(LIGHT_DEVICE_TRIGGERS)
    .add_to_registry()
)

(
    QuirkBuilder(SINOPE, "DM2550ZB")
    .applies_to(SINOPE, "DM2550ZB-G2")
    .replaces_endpoint(
        1, device_type=zha_p.DeviceType.DIMMABLE_LIGHT
    )  # Was DIMMER_SWITCH
    .replaces(CustomDeviceTemperatureCluster, endpoint_id=1)
    .replaces(LightManufacturerCluster, endpoint_id=1)
    .device_automation_triggers(LIGHT_DEVICE_TRIGGERS)
    .add_to_registry()
)
