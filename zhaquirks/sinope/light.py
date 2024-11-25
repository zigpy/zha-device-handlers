"""Module to handle quirks of the Sinopé Technologies light.

Supported devices SW2500ZB, SW2500ZB-G2 dimmer DM2500ZB, DM2500ZB-G2, DM2550ZB,
DM2550ZB-G2.
"""

import logging
from typing import Any, Final, Optional, Union

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    DeviceTemperature,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

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
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
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

    server_commands = {
        0x54: foundation.ZCLCommandDef(
            "button_press",
            {"command": t.uint8_t},
            direction=foundation.Direction.Server_to_Client,
            is_manufacturer_specific=True,
        )
    }

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


class SinopeTechnologieslight(CustomDevice):
    """SinopeTechnologiesLight custom device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=259
        # device_version=0 input_clusters=[0, 2, 3, 4, 5, 6, 1794, 2821, 65281]
        # output_clusters=[3, 4, 25]>
        MODELS_INFO: [
            (SINOPE, "SW2500ZB"),
            (SINOPE, "SW2500ZB-G2"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomDeviceTemperatureCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    LightManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = LIGHT_DEVICE_TRIGGERS


class SinopeDM2500ZB(CustomDevice):
    """DM2500ZB, DM2500ZB-G2 Dimmers."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=260 device_version=1
        # input_clusters=[0, 2, 3, 4, 5, 6, 8, 1794, 2821, 65281]
        # output_clusters=[3, 4, 25]>
        MODELS_INFO: [
            (SINOPE, "DM2500ZB"),
            (SINOPE, "DM2500ZB-G2"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomDeviceTemperatureCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    Diagnostic.cluster_id,
                    LightManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = LIGHT_DEVICE_TRIGGERS


class SinopeDM2550ZB(CustomDevice):
    """DM2550ZB, DM2550ZB-G2 Dimmers."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=260 device_version=1
        # input_clusters=[0, 2, 3, 4, 5, 6, 8, 1794, 2820, 2821, 65281]
        # output_clusters=[3, 4, 10, 25]>
        MODELS_INFO: [
            (SINOPE, "DM2550ZB"),
            (SINOPE, "DM2550ZB-G2"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    SINOPE_MANUFACTURER_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha_p.PROFILE_ID,
                DEVICE_TYPE: zha_p.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomDeviceTemperatureCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    Diagnostic.cluster_id,
                    LightManufacturerCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = LIGHT_DEVICE_TRIGGERS
