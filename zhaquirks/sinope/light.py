"""Module to handle quirks of the Sinopé Technologies light.

Supported devices SW2500ZB, SW2500ZB-G2 dimmer DM2500ZB, DM2500ZB-G2, DM2550ZB,
DM2550ZB-G2.
"""

import logging
from typing import Any, Final, Optional, Union

import zigpy.profiles.zha as zha_p
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityType, QuirkBuilder, SensorStateClass
from zigpy.quirks.v2.homeassistant import UnitOfEnergy, UnitOfTime
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic, ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import (
    ZCL_CLUSTER_REVISION_ATTR,
    BaseAttributeDefs,
    Direction,
    GeneralCommand,
    ZCLAttributeDef,
    ZCLCommandDef,
    ZCLHeader,
)

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


class DeviceStatus(t.bitmap32):
    """Device general status."""

    Ok = 0x00000000
    Temp_sensor = 0x00000040


class SinopeLightLedColors(t.enum32):
    """Color values for Sinope light switch status LEDs."""

    Lim = 0x0AFFDC
    Amber = 0x000A4B
    Fushia = 0x0100A5
    Perle = 0x64FFFF
    Blue = 0xFFFF00
    Green = 0x00FF00
    Red = 0xFF0000


class SinopeTechnologiesManufacturerCluster(CustomCluster):
    """SinopeTechnologiesManufacturerCluster manufacturer cluster."""

    KeypadLock: Final = KeypadLock
    PhaseControl: Final = PhaseControl
    DoubleFull: Final = DoubleFull
    Action: Final = ButtonAction
    DeviceStatus: Final = DeviceStatus

    cluster_id: Final[t.uint16_t] = SINOPE_MANUFACTURER_CLUSTER_ID
    name: Final = "SinopeTechnologiesManufacturerCluster"
    ep_attribute: Final = "sinope_manufacturer_specific"

    class AttributeDefs(BaseAttributeDefs):
        """Sinope Manufacturer Cluster Attributes."""

        keypad_lockout: Final = ZCLAttributeDef(
            id=0x0002, type=KeypadLock, access="rw", is_manufacturer_specific=True
        )
        firmware_number: Final = ZCLAttributeDef(
            id=0x0003, type=t.uint16_t, access="r", is_manufacturer_specific=True
        )
        firmware_version: Final = ZCLAttributeDef(
            id=0x0004, type=t.CharacterString, access="r", is_manufacturer_specific=True
        )
        on_intensity: Final = ZCLAttributeDef(
            id=0x0010, type=t.int16s, access="rw", is_manufacturer_specific=True
        )
        on_led_color: Final = ZCLAttributeDef(
            id=0x0050, type=t.uint24_t, access="rw", is_manufacturer_specific=True
        )
        off_led_color: Final = ZCLAttributeDef(
            id=0x0051, type=t.uint24_t, access="rw", is_manufacturer_specific=True
        )
        on_led_intensity: Final = ZCLAttributeDef(
            id=0x0052, type=t.uint8_t, access="rw", is_manufacturer_specific=True
        )
        off_led_intensity: Final = ZCLAttributeDef(
            id=0x0053, type=t.uint8_t, access="rw", is_manufacturer_specific=True
        )
        action_report: Final = ZCLAttributeDef(
            id=0x0054, type=ButtonAction, access="rp", is_manufacturer_specific=True
        )
        min_intensity: Final = ZCLAttributeDef(
            id=0x0055, type=t.uint16_t, access="rw", is_manufacturer_specific=True
        )
        phase_control: Final = ZCLAttributeDef(
            id=0x0056, type=PhaseControl, access="rw", is_manufacturer_specific=True
        )
        double_up_full: Final = ZCLAttributeDef(
            id=0x0058, type=DoubleFull, access="rw", is_manufacturer_specific=True
        )
        current_summation_delivered: Final = ZCLAttributeDef(
            id=0x0090, type=t.uint32_t, access="rp", is_manufacturer_specific=True
        )
        timer: Final = ZCLAttributeDef(
            id=0x00A0, type=t.uint32_t, access="rw", is_manufacturer_specific=True
        )
        timer_countdown: Final = ZCLAttributeDef(
            id=0x00A1, type=t.uint32_t, access="r", is_manufacturer_specific=True
        )
        connected_load: Final = ZCLAttributeDef(
            id=0x0119, type=t.uint16_t, access="rw", is_manufacturer_specific=True
        )
        status: Final = ZCLAttributeDef(
            id=0x0200, type=DeviceStatus, access="rp", is_manufacturer_specific=True
        )
        cluster_revision: Final = ZCL_CLUSTER_REVISION_ATTR

    server_commands = {
        0x54: ZCLCommandDef(
            "button_press",
            {"command": t.uint8_t},
            direction=Direction.Server_to_Client,
            is_manufacturer_specific=True,
        )
    }

    def handle_cluster_general_request(
        self,
        hdr: ZCLHeader,
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

        if hdr.command_id != GeneralCommand.Report_Attributes:
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

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.current_summation_delivered.id:
            value = value / 100
        super()._update_attribute(attrid, value)


(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=259
    # device_version=0 input_clusters=[0, 2, 3, 4, 5, 6, 1794, 2821, 65281]
    # output_clusters=[3, 4, 25]>
    QuirkBuilder(SINOPE, "SW2500ZB")
    .applies_to(SINOPE, "SW2500ZB-G2")
    .replaces_endpoint(1, device_type=zha_p.DeviceType.ON_OFF_LIGHT)
    .adds(Basic, endpoint_id=1)
    .adds(Identify, endpoint_id=1)
    .adds(Groups, endpoint_id=1)
    .adds(Scenes, endpoint_id=1)
    .adds(OnOff, endpoint_id=1)
    .adds(Metering, endpoint_id=1)
    .adds(Diagnostic, endpoint_id=1)
    .replaces(CustomDeviceTemperatureCluster)
    .replaces(LightManufacturerCluster)
    .device_automation_triggers(LIGHT_DEVICE_TRIGGERS)
    .enum(  # Keypad lock
        attribute_name=LightManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.STANDARD,
    )
    .enum(  # On led color
        attribute_name=LightManufacturerCluster.AttributeDefs.on_led_color.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        enum_class=SinopeLightLedColors,
        translation_key="on_led_color",
        fallback_name="On led color",
        entity_type=EntityType.CONFIG,
    )
    .enum(  # Off led color
        attribute_name=LightManufacturerCluster.AttributeDefs.off_led_color.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        enum_class=SinopeLightLedColors,
        translation_key="off_led_color",
        fallback_name="Off led color",
        entity_type=EntityType.CONFIG,
    )
    .number(  # Connected load
        attribute_name=LightManufacturerCluster.AttributeDefs.connected_load.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        step=1,
        min_value=0,
        max_value=5000,
        unit=UnitOfEnergy.WATT_HOUR,
        translation_key="connected_load",
        fallback_name="Connected load",
    )
    .number(  # Timer
        attribute_name=LightManufacturerCluster.AttributeDefs.timer.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        step=1,
        min_value=0,
        max_value=86400,
        unit=UnitOfTime.SECONDS,
        translation_key="timer",
        fallback_name="Timer",
    )
    .sensor(  # Timer countdown
        attribute_name=LightManufacturerCluster.AttributeDefs.timer_countdown.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.SECONDS,
        translation_key="timer_countdown",
        fallback_name="Timer countdown",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Device status
        attribute_name=LightManufacturerCluster.AttributeDefs.status.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=260 device_version=1
    # input_clusters=[0, 2, 3, 4, 5, 6, 8, 1794, 2821, 65281]
    # output_clusters=[3, 4, 25]>
    QuirkBuilder(SINOPE, "DM2500ZB")
    .applies_to(SINOPE, "DM2500ZB-G2")
    .replaces_endpoint(1, device_type=zha_p.DeviceType.DIMMABLE_LIGHT)
    .adds(Basic, endpoint_id=1)
    .adds(Identify, endpoint_id=1)
    .adds(Groups, endpoint_id=1)
    .adds(Scenes, endpoint_id=1)
    .adds(OnOff, endpoint_id=1)
    .adds(LevelControl, endpoint_id=1)
    .adds(Metering, endpoint_id=1)
    .adds(Diagnostic, endpoint_id=1)
    .replaces(CustomDeviceTemperatureCluster)
    .replaces(LightManufacturerCluster)
    .device_automation_triggers(LIGHT_DEVICE_TRIGGERS)
    .enum(  # Keypad lock
        attribute_name=LightManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.STANDARD,
    )
    .enum(  # On led color
        attribute_name=LightManufacturerCluster.AttributeDefs.on_led_color.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        enum_class=SinopeLightLedColors,
        translation_key="on_led_color",
        fallback_name="On led color",
        entity_type=EntityType.CONFIG,
    )
    .enum(  # Off led color
        attribute_name=LightManufacturerCluster.AttributeDefs.off_led_color.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        enum_class=SinopeLightLedColors,
        translation_key="off_led_color",
        fallback_name="Off led color",
        entity_type=EntityType.CONFIG,
    )
    .number(  # Connected load
        attribute_name=LightManufacturerCluster.AttributeDefs.connected_load.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        step=1,
        min_value=0,
        max_value=5000,
        unit=UnitOfEnergy.WATT_HOUR,
        translation_key="connected_load",
        fallback_name="Connected load",
        entity_type=EntityType.STANDARD,
    )
    .number(  # Timer
        attribute_name=LightManufacturerCluster.AttributeDefs.timer.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        step=1,
        min_value=0,
        max_value=86400,
        unit=UnitOfTime.SECONDS,
        translation_key="timer",
        fallback_name="Timer",
    )
    .sensor(  # Timer countdown
        attribute_name=LightManufacturerCluster.AttributeDefs.timer_countdown.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.SECONDS,
        translation_key="timer_countdown",
        fallback_name="Timer countdown",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Device status
        attribute_name=LightManufacturerCluster.AttributeDefs.status.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)

(
    # <SimpleDescriptor endpoint=1 profile=260 device_type=260 device_version=1
    # input_clusters=[0, 2, 3, 4, 5, 6, 8, 1794, 2820, 2821, 65281]
    # output_clusters=[3, 4, 10, 25]>
    QuirkBuilder(SINOPE, "DM2550ZB")
    .applies_to(SINOPE, "DM2550ZB-G2")
    .replaces_endpoint(1, device_type=zha_p.DeviceType.DIMMABLE_LIGHT)
    .adds(Basic, endpoint_id=1)
    .adds(Identify, endpoint_id=1)
    .adds(Groups, endpoint_id=1)
    .adds(Scenes, endpoint_id=1)
    .adds(OnOff, endpoint_id=1)
    .adds(LevelControl, endpoint_id=1)
    .adds(Metering, endpoint_id=1)
    .adds(ElectricalMeasurement, endpoint_id=1)
    .adds(Diagnostic, endpoint_id=1)
    .replaces(CustomDeviceTemperatureCluster)
    .replaces(LightManufacturerCluster)
    .device_automation_triggers(LIGHT_DEVICE_TRIGGERS)
    .enum(  # Keypad lock
        attribute_name=LightManufacturerCluster.AttributeDefs.keypad_lockout.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        enum_class=KeypadLock,
        translation_key="keypad_lockout",
        fallback_name="Keypad lockout",
        entity_type=EntityType.STANDARD,
    )
    .enum(  # Phase control
        attribute_name=LightManufacturerCluster.AttributeDefs.phase_control.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        enum_class=PhaseControl,
        translation_key="phase_control",
        fallback_name="Phase control",
        entity_type=EntityType.STANDARD,
    )
    .enum(  # On led color
        attribute_name=LightManufacturerCluster.AttributeDefs.on_led_color.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        enum_class=SinopeLightLedColors,
        translation_key="on_led_color",
        fallback_name="On led color",
        entity_type=EntityType.CONFIG,
    )
    .enum(  # Off led color
        attribute_name=LightManufacturerCluster.AttributeDefs.off_led_color.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        enum_class=SinopeLightLedColors,
        translation_key="off_led_color",
        fallback_name="Off led color",
        entity_type=EntityType.CONFIG,
    )
    .number(  # Minimum intensity
        attribute_name=LightManufacturerCluster.AttributeDefs.min_intensity.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        step=1,
        min_value=1,
        max_value=255,
        translation_key="min_intensity",
        fallback_name="Minimum on level",
    )
    .number(  # Timer
        attribute_name=LightManufacturerCluster.AttributeDefs.timer.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        step=1,
        min_value=0,
        max_value=86400,
        unit=UnitOfTime.SECONDS,
        translation_key="timer",
        fallback_name="Timer",
    )
    .sensor(  # Timer countdown
        attribute_name=LightManufacturerCluster.AttributeDefs.timer_countdown.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfTime.SECONDS,
        translation_key="timer_countdown",
        fallback_name="Timer countdown",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(  # Device status
        attribute_name=LightManufacturerCluster.AttributeDefs.status.name,
        cluster_id=LightManufacturerCluster.cluster_id,
        state_class=SensorStateClass.MEASUREMENT,
        translation_key="status",
        fallback_name="Device status",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)
