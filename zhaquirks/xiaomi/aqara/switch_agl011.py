"""Quirk for Aqara Dimmer Switch H2 EU (lumi.switch.agl011).

Knob button and rotation events follow the attribute mapping from
Zigbee2MQTT's lumi converter, verified against captured frames.
"""

from typing import Final

from zigpy import types
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import MultistateInput
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks import CustomCluster
from zhaquirks.builder import DEGREE, QuirkBuilder
from zhaquirks.const import (
    ATTR_ID,
    BUTTON,
    COMMAND,
    COMMAND_CONTINUED_ROTATING,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    COMMAND_SINGLE,
    COMMAND_STARTED_ROTATING,
    COMMAND_STOPPED_ROTATING,
    CONTINUED_ROTATING,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    LONG_PRESS,
    LONG_RELEASE,
    PRESS_TYPE,
    ROTARY_KNOB,
    SHORT_PRESS,
    STARTED_ROTATING,
    STOPPED_ROTATING,
    VALUE,
    ZHA_SEND_EVENT,
)
from zhaquirks.xiaomi import (
    DeviceTemperatureCluster,
    ElectricalMeasurementCluster as XiaomiElectricalMeasurementCluster,
    XiaomiAqaraE1Cluster,
)

# Knob presses are reported as MultistateInput present_value on endpoint 1
BUTTON_ACTIONS = {
    0: COMMAND_HOLD,
    1: COMMAND_SINGLE,
    2: COMMAND_DOUBLE,
    255: COMMAND_RELEASE,
}

# Knob rotation is reported on the manufacturer cluster of endpoint 71, or of
# endpoint 72 when the knob is held down while turning. A press that comes with
# a rotation is not reported as a press at all.
ROTATION_ENDPOINT = 71
ROTATION_PRESSED_ENDPOINT = 72
# alternative way of flagging a held knob, documented by Zigbee2MQTT
ROTATION_PRESSED_BIT = 0x80

ROTATION_ACTIONS = {
    # firmware 0x1018 starts with 0, Zigbee2MQTT documents 1
    0: COMMAND_STARTED_ROTATING,
    1: COMMAND_STARTED_ROTATING,
    2: COMMAND_CONTINUED_ROTATING,
    3: COMMAND_STOPPED_ROTATING,
}


class ModeSwitch(types.enum16):
    """Enum for dimmer mode switch."""

    Quick = 0x01
    Anti_Flicker = 0x04


class OperationMode(types.enum8):
    """Enum for dimmer operation mode."""

    Decoupled = 0x00
    Relay = 0x01


class Phase(types.enum8):
    """Enum for dimmer phase."""

    Leading = 0x00
    Trailing = 0x01


class PowerOnState(types.enum8):
    """Enum for dimmer power-on state."""

    On = 0x00
    Previous = 0x01
    Off = 0x02
    Inverted = 0x03


class MultiClick(types.enum8):
    """Enum for multi-click mode.

    Single only reports single presses. Multi also reports hold, double and
    release, at the cost of a short delay before the switch acts.
    """

    Single = 0x01
    Multi = 0x02


class ElectricalMeasurementCluster(XiaomiElectricalMeasurementCluster):
    """Local electrical measurement cluster fed by the Xiaomi attribute report.

    The device answers direct rms_voltage reads with UNSUPPORTED_ATTRIBUTE,
    which would make ZHA drop the voltage sensor, so reads are served locally.
    The report sends voltage in 0.01 V and the shared handler scales it by 0.1,
    so the cached rms_voltage is in 0.1 V.
    """

    _CONSTANT_ATTRIBUTES = {
        **XiaomiElectricalMeasurementCluster._CONSTANT_ATTRIBUTES,
        ElectricalMeasurement.AttributeDefs.ac_voltage_multiplier.id: 1,
        ElectricalMeasurement.AttributeDefs.ac_voltage_divisor.id: 10,
    }


class MultistateInputCluster(CustomCluster, MultistateInput):
    """Multistate input cluster emitting knob press events."""

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == MultistateInput.AttributeDefs.present_value.id:
            action = BUTTON_ACTIONS.get(value)
            if action is not None:
                self.listener_event(
                    ZHA_SEND_EVENT,
                    action,
                    {
                        ENDPOINT_ID: self.endpoint.endpoint_id,
                        PRESS_TYPE: action,
                        ATTR_ID: attrid,
                        VALUE: value,
                    },
                )


class RotationCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer cluster on the knob endpoint emitting rotation events."""

    # whether this endpoint reports rotation with the knob held down
    _knob_pressed: bool = False

    class AttributeDefs(BaseAttributeDefs):
        """Attribute Definitions."""

        # 1=started, 2=continued, 3=stopped; sent last in the report frame
        rotation_action: Final = ZCLAttributeDef(
            id=0x023A, type=types.uint8_t, access="rp", manufacturer_code=0x115F
        )
        # degrees, negative = counter-clockwise
        rotation_angle: Final = ZCLAttributeDef(
            id=0x022E, type=types.Single, access="rp", manufacturer_code=0x115F
        )
        rotation_angle_speed: Final = ZCLAttributeDef(
            id=0x0230, type=types.Single, access="rp", manufacturer_code=0x115F
        )
        # milliseconds
        rotation_time: Final = ZCLAttributeDef(
            id=0x0231, type=types.uint32_t, access="rp", manufacturer_code=0x115F
        )
        # sign is unreliable, don't use it for the direction
        rotation_percent_speed: Final = ZCLAttributeDef(
            id=0x0232, type=types.Single, access="rp", manufacturer_code=0x115F
        )
        rotation_percent: Final = ZCLAttributeDef(
            id=0x0233, type=types.Single, access="rp", manufacturer_code=0x115F
        )

    # event argument names, matching Zigbee2MQTT
    ROTATION_ARGS = {
        AttributeDefs.rotation_angle.id: "action_rotation_angle",
        AttributeDefs.rotation_angle_speed.id: "action_rotation_angle_speed",
        AttributeDefs.rotation_time.id: "action_rotation_time",
        AttributeDefs.rotation_percent_speed.id: "action_rotation_percent_speed",
        AttributeDefs.rotation_percent.id: "action_rotation_percent",
    }

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self._rotation: dict[str, float] = {}

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)

        # the action is sent last, so buffer the telemetry until it arrives
        if attrid in self.ROTATION_ARGS:
            self._rotation[self.ROTATION_ARGS[attrid]] = value
            return

        if attrid == self.AttributeDefs.rotation_action.id:
            rotation, self._rotation = self._rotation, {}
            action = ROTATION_ACTIONS.get(value & ~ROTATION_PRESSED_BIT)
            if action is None:
                return
            pressed = self._knob_pressed or bool(value & ROTATION_PRESSED_BIT)
            event_args = {
                **rotation,
                "action_rotation_button_state": "pressed" if pressed else "released",
            }
            self.listener_event(ZHA_SEND_EVENT, action, event_args)


class PressedRotationCluster(RotationCluster):
    """Rotation cluster of the endpoint used while the knob is held down."""

    _knob_pressed = True


class OppleCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer-specific cluster for the dimmer switch H2 EU."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute Definitions."""

        flip_indicator_light: Final = ZCLAttributeDef(
            id=0x00F0, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        led_indicator: Final = ZCLAttributeDef(
            id=0x0203, type=types.Bool, access="rw", is_manufacturer_specific=True
        )
        max_brightness: Final = ZCLAttributeDef(
            id=0x0516, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        min_brightness: Final = ZCLAttributeDef(
            id=0x0515, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        multi_click: Final = ZCLAttributeDef(
            id=0x0286, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        mode_switch: Final = ZCLAttributeDef(
            id=0x0004, type=types.uint16_t, access="rw", is_manufacturer_specific=True
        )
        operation_mode: Final = ZCLAttributeDef(
            id=0x0200, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        phase: Final = ZCLAttributeDef(
            id=0x030A, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        power_on_state: Final = ZCLAttributeDef(
            id=0x0517, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        reporting_interval: Final = ZCLAttributeDef(
            id=0x00F6, type=types.uint16_t, access="rw", is_manufacturer_specific=True
        )
        # degrees of knob rotation that map to 0-100 % (Z2M: high=180, low=720)
        rotation_sensitivity: Final = ZCLAttributeDef(
            id=0x0234, type=types.uint16_t, access="rw", is_manufacturer_specific=True
        )


(
    QuirkBuilder("Aqara", "lumi.switch.agl011")
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    .adds(DeviceTemperatureCluster)
    .adds(OppleCluster)
    .replace_cluster_occurrences(MultistateInputCluster, replace_client_instances=False)
    .replaces(ElectricalMeasurementCluster)
    .adds_endpoint(ROTATION_ENDPOINT)
    .adds(RotationCluster, endpoint_id=ROTATION_ENDPOINT)
    .adds_endpoint(ROTATION_PRESSED_ENDPOINT)
    .adds(PressedRotationCluster, endpoint_id=ROTATION_PRESSED_ENDPOINT)
    .switch(
        OppleCluster.AttributeDefs.flip_indicator_light.name,
        OppleCluster.cluster_id,
        translation_key="flip_indicator_light",
        fallback_name="Flip indicator light",
    )
    .switch(
        OppleCluster.AttributeDefs.led_indicator.name,
        OppleCluster.cluster_id,
        translation_key="led_indicator",
        fallback_name="LED indicator",
    )
    .number(
        OppleCluster.AttributeDefs.max_brightness.name,
        OppleCluster.cluster_id,
        min_value=1,
        max_value=100,
        step=1,
        translation_key="max_brightness",
        fallback_name="Maximum brightness",
    )
    .number(
        OppleCluster.AttributeDefs.min_brightness.name,
        OppleCluster.cluster_id,
        min_value=0,
        max_value=99,
        step=1,
        translation_key="min_brightness",
        fallback_name="Minimum brightness",
    )
    .enum(
        OppleCluster.AttributeDefs.mode_switch.name,
        ModeSwitch,
        OppleCluster.cluster_id,
        translation_key="mode_switch",
        fallback_name="Mode switch",
    )
    .enum(
        OppleCluster.AttributeDefs.multi_click.name,
        MultiClick,
        OppleCluster.cluster_id,
        translation_key="multi_click",
        fallback_name="Multi click",
    )
    .enum(
        OppleCluster.AttributeDefs.operation_mode.name,
        OperationMode,
        OppleCluster.cluster_id,
        translation_key="operation_mode",
        fallback_name="Operation mode",
    )
    .enum(
        OppleCluster.AttributeDefs.phase.name,
        Phase,
        OppleCluster.cluster_id,
        translation_key="phase",
        fallback_name="Phase",
    )
    .enum(
        OppleCluster.AttributeDefs.power_on_state.name,
        PowerOnState,
        OppleCluster.cluster_id,
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .number(
        OppleCluster.AttributeDefs.reporting_interval.name,
        OppleCluster.cluster_id,
        min_value=1,
        max_value=3600,
        step=1,
        translation_key="reporting_interval",
        fallback_name="Reporting interval",
    )
    .number(
        OppleCluster.AttributeDefs.rotation_sensitivity.name,
        OppleCluster.cluster_id,
        min_value=180,
        max_value=720,
        step=10,
        unit=DEGREE,
        mode="slider",
        # keep the unique_id from before the attribute was renamed
        unique_id_suffix="sensitivity",
        translation_key="rotation_sensitivity",
        fallback_name="Rotation sensitivity",
    )
    .device_automation_triggers(
        {
            (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_SINGLE},
            (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_DOUBLE},
            (LONG_PRESS, BUTTON): {COMMAND: COMMAND_HOLD},
            (LONG_RELEASE, BUTTON): {COMMAND: COMMAND_RELEASE},
            (STARTED_ROTATING, ROTARY_KNOB): {COMMAND: COMMAND_STARTED_ROTATING},
            (CONTINUED_ROTATING, ROTARY_KNOB): {COMMAND: COMMAND_CONTINUED_ROTATING},
            (STOPPED_ROTATING, ROTARY_KNOB): {COMMAND: COMMAND_STOPPED_ROTATING},
        }
    )
    .add_to_registry()
)
