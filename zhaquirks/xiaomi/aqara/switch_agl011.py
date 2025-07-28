"""Quirk for Aqara Dimmer Switch H2 EU (lumi.switch.agl011)."""

from typing import Any

from zigpy import types
from zigpy.profiles import zha
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.xiaomi import DeviceTemperatureCluster, XiaomiCluster


class OperationMode(types.enum8):
    """Enum for dimmer operation mode."""

    Decoupled = 0x00
    Relay = 0x01


class Phase(types.enum8):
    """Enum for dimmer phase."""

    Leading = 0x00
    Trailing = 0x01


class PowerOnBehaviour(types.enum8):
    """Enum for dimmer power-on behaviour."""

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
        operation_mode = ZCLAttributeDef(
            id=0x0200, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        phase = ZCLAttributeDef(
            id=0x030A, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        power_on_behaviour = ZCLAttributeDef(
            id=0x0517, type=types.uint8_t, access="rw", is_manufacturer_specific=True
        )
        reporting_interval = ZCLAttributeDef(
            id=0x00F6, type=types.uint16_t, access="rw", is_manufacturer_specific=True
        )
        sensitivity = ZCLAttributeDef(
            id=0x0234, type=types.uint16_t, access="rw", is_manufacturer_specific=True
        )

    def _update_attribute(self, attrid: int, value: Any) -> None:
        if value is not None:
            super()._update_attribute(attrid, value)


(
    QuirkBuilder("Aqara", "lumi.switch.agl011")
    .replaces_endpoint(1, device_type=zha.DeviceType.DIMMABLE_LIGHT)
    .adds(DeviceTemperatureCluster)
    .adds(OppleCluster)
    .switch(
        OppleCluster.AttributeDefs.flip_indicator_light.name,
        OppleCluster.cluster_id,
        translation_key="flip_indicator_light",
        fallback_name="Flip Indicator Light",
    )
    .switch(
        OppleCluster.AttributeDefs.led_indicator.name,
        OppleCluster.cluster_id,
        translation_key="led_indicator",
        fallback_name="LED Indicator",
    )
    .number(
        OppleCluster.AttributeDefs.max_brightness.name,
        OppleCluster.cluster_id,
        min_value=1,
        max_value=100,
        step=1,
        translation_key="max_brightness",
        fallback_name="Maximum Brightness",
    )
    .number(
        OppleCluster.AttributeDefs.min_brightness.name,
        OppleCluster.cluster_id,
        min_value=0,
        max_value=99,
        step=1,
        translation_key="min_brightness",
        fallback_name="Minimum Brightness",
    )
    .enum(
        OppleCluster.AttributeDefs.operation_mode.name,
        OperationMode,
        OppleCluster.cluster_id,
        translation_key="operation_mode",
        fallback_name="Operation Mode",
    )
    .enum(
        OppleCluster.AttributeDefs.phase.name,
        Phase,
        OppleCluster.cluster_id,
        translation_key="phase",
        fallback_name="Phase",
    )
    .enum(
        OppleCluster.AttributeDefs.power_on_behaviour.name,
        PowerOnBehaviour,
        OppleCluster.cluster_id,
        translation_key="power_on_behaviour",
        fallback_name="Power On Behaviour",
    )
    .number(
        OppleCluster.AttributeDefs.reporting_interval.name,
        OppleCluster.cluster_id,
        min_value=1,
        max_value=3600,
        step=1,
        translation_key="reporting_interval",
        fallback_name="Reporting Interval",
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
