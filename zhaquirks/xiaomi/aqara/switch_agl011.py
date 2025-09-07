"""Quirk for Aqara Dimmer Switch H2 EU (lumi.switch.agl011)."""

from zigpy import types
from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.xiaomi import DeviceTemperatureCluster, XiaomiAqaraE1Cluster


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


class OppleCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer-specific cluster for the dimmer switch H2 EU."""

    class AttributeDefs(BaseAttributeDefs):
        """Attribute Definitions."""

        flip_indicator_light = ZCLAttributeDef(
            id=0x00F0, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        led_indicator = ZCLAttributeDef(
            id=0x0203, type=types.Bool, access="rw", is_manufacturer_specific=True
        )
        max_brightness = ZCLAttributeDef(
            id=0x0516, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        min_brightness = ZCLAttributeDef(
            id=0x0515, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        mode_switch = ZCLAttributeDef(
            id=0x0004, type=types.uint16_t, access="rw", is_manufacturer_specific=True
        )
        operation_mode = ZCLAttributeDef(
            id=0x0200, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        phase = ZCLAttributeDef(
            id=0x030A, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        power_on_state = ZCLAttributeDef(
            id=0x0517, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        reporting_interval = ZCLAttributeDef(
            id=0x00F6, type=types.uint16_t, access="rw", is_manufacturer_specific=True
        )
        sensitivity = ZCLAttributeDef(
            id=0x0234, type=types.uint16_t, access="rw", is_manufacturer_specific=True
        )


(
    QuirkBuilder("Aqara", "lumi.switch.agl011")
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    .adds(DeviceTemperatureCluster)
    .adds(OppleCluster)
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
        OppleCluster.AttributeDefs.sensitivity.name,
        OppleCluster.cluster_id,
        min_value=1,
        max_value=65535,
        step=1,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    .add_to_registry()
)
