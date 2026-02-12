"""Sonoff MINI-ZBDIM - Zigbee Dimmer Switch."""

from typing import Any

from zigpy import types
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfPower,
    UnitOfTime,
)
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import LevelControl
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeAccess, ZCLAttributeDef

ACTION_ID_MAPPING = [0xFFD1, 0xFFD2, 0xFFD3]
BRIGHTNESS_ID_MAPPING = [0x4001, 0x4002, 0x4006]

class SonoffCluster(CustomCluster):
    """Custom Sonoff cluster."""

    cluster_id = 0xFC11

    manufacturer_id_override = foundation.ZCLHeader.NO_MANUFACTURER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        delayed_power_on_state = ZCLAttributeDef(
            id=0x0014,
            type=t.Bool,
            is_manufacturer_specific=True,
        )
        delayed_power_on_time = ZCLAttributeDef(
            id=0x0015,
            type=t.uint16_t,
            is_manufacturer_specific=True,
        )
        external_trigger_mode = ZCLAttributeDef(
            id=0x0016,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        set_calibration_action = ZCLAttributeDef(
            id=0x001D,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )
        set_calibration_action_start = ZCLAttributeDef(
            id=0xFFD1,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )
        set_calibration_action_stop = ZCLAttributeDef(
            id=0xFFD2,
            type=t.CharacterString,
            is_manufacturer_specific=True,
        )
        calibration_status = ZCLAttributeDef(
            id=0x001E,
            type=t.uint8_t,
            access=(ZCLAttributeAccess.Read | ZCLAttributeAccess.Report),
            is_manufacturer_specific=True,
        )
        calibration_progress = ZCLAttributeDef(
            id=0x0020,
            type=t.uint8_t,
            access=(ZCLAttributeAccess.Read | ZCLAttributeAccess.Report),
            is_manufacturer_specific=True,
        )
        transition_time = ZCLAttributeDef(
            id=0x001F,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        min_brightness_threshold = ZCLAttributeDef(
            id=0x4001,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        dimming_light_rate = ZCLAttributeDef(
            id=0x4003,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        accurrent_current_value = ZCLAttributeDef(
            id=0x7004,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        accurrent_voltage_value = ZCLAttributeDef(
            id=0x7005,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        accurrent_power_value = ZCLAttributeDef(
            id=0x7006,
            type=t.uint32_t,
            is_manufacturer_specific=True,
        )
        max_brightness_threshold = ZCLAttributeDef(
            id=0x4002,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )
        level_for_calibration = ZCLAttributeDef(
            id=0x4006,
            type=t.uint8_t,
            is_manufacturer_specific=True,
        )

    async def write_attributes(self, attributes, manufacturer=None):
        """Convert the min_brightness_threshold attribute value."""
        if "min_brightness_threshold" in attributes:
            val = attributes.get("min_brightness_threshold")
            attributes["min_brightness_threshold"] = 255 / 100 * val
        elif "max_brightness_threshold" in attributes:
            val = attributes.get("max_brightness_threshold")
            attributes["max_brightness_threshold"] = 255 / 100 * val
        elif "level_for_calibration" in attributes:
            val = attributes.get("level_for_calibration")
            attributes["level_for_calibration"] = 255 / 100 * val
        
        return await super().write_attributes(attributes, manufacturer=manufacturer)

    async def write_attributes_raw(
        self,
        attributes: list[foundation.Attribute],
        manufacturer: int | None = None,
        **kwargs,
    ):
        """Handle virtual attributes."""
        for attr in attributes:
            if attr.attrid in ACTION_ID_MAPPING:
                attr.attrid = 0x001D

        return await super().write_attributes_raw(
            attributes, manufacturer=manufacturer, **kwargs
        )

    def _update_attribute(self, attrid, value):
        """Convert attribute value."""
        if attrid in BRIGHTNESS_ID_MAPPING:
            val = round(float(value) / 255 * 100)
            super()._update_attribute(attrid, val) 
        else:
            super()._update_attribute(attrid, value)

    async def apply_custom_configuration(self, *args, **kwargs):
        """Apply custom configuration."""
        await self.read_attributes({0x0008: 0x0000})


class SonoffLevelControl(CustomCluster, LevelControl):
    """Override level control cluster."""

    def _update_attribute(self, attrid: int | t.uint16_t, value: Any) -> None:
        """Convert the current level attribute."""
        if attrid == 0000 and value <= 2:
            value = 2
        super()._update_attribute(attrid, value)


class ExternalTriggerMode(types.enum8):
    """External trigger mode attribute values."""

    Edge = 0x00
    Pulse = 0x01
    Double_pulse = 0x03
    Triple_pulse = 0x04


class DimmingLightRate(types.enum8):
    """Dimming light rate attribute values."""

    X1 = 1
    X2 = 2
    X3 = 3
    X4 = 4
    X5 = 5


# class SetCalibrationAction(Enum):
#     """Set calibration action attribute values."""

#     Start = bytes([0x01,0x01,0x01]).decode("latin-1"),
#     Stop = bytes([0x01,0x01,0x02]).decode("latin-1"),
#     Clear = bytes([0x01,0x01,0x03]).decode("latin-1"),


class CalibrationStatus(types.enum8):
    """Calibration status attribute values."""

    UnCalibrate = 0x00
    Calibrating = 0x01
    CalibrationFailed = 0x02
    Calibrated = 0x03


(
    QuirkBuilder("SONOFF", "MINI-ZBDIM")
    .replaces(SonoffCluster)
    .replaces(SonoffLevelControl)
    .removes(cluster_id=0x0B04)
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.accurrent_current_value.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.CURRENT,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricCurrent.AMPERE,
        translation_key="accurrent_current_value",
        fallback_name="Current",
        divisor=1000,
        suggested_display_precision=2,
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.accurrent_voltage_value.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        divisor=1000,
        translation_key="accurrent_voltage_value",
        fallback_name="Voltage",
        suggested_display_precision=2,
    )
    .sensor(
        attribute_name=SonoffCluster.AttributeDefs.accurrent_power_value.name,
        cluster_id=SonoffCluster.cluster_id,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfPower.WATT,
        divisor=1000,
        translation_key="accurrent_power_value",
        fallback_name="Power",
        suggested_display_precision=2,
    )
    .switch(
        SonoffCluster.AttributeDefs.delayed_power_on_state.name,
        SonoffCluster.cluster_id,
        off_value=0,
        on_value=1,
        translation_key="delayed_power_on_state",
        fallback_name="Delayed power on state",
    )
    .number(
        SonoffCluster.AttributeDefs.delayed_power_on_time.name,
        SonoffCluster.cluster_id,
        min_value=0.5,
        max_value=3599.5,
        step=0.5,
        device_class=NumberDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        multiplier=0.5,
        translation_key="delayed_power_on_time",
        fallback_name="Delayed power on time",
    )
    .write_attr_button(
        SonoffCluster.AttributeDefs.set_calibration_action_stop.name,
        bytes([0x01, 0x01, 0x02]).decode("latin-1"),
        SonoffCluster.cluster_id,
        translation_key="stop_calibrate",
        fallback_name="Stop calibrate",
    )
    .write_attr_button(
        SonoffCluster.AttributeDefs.set_calibration_action_start.name,
        bytes([0x01, 0x01, 0x01]).decode("latin-1"),
        SonoffCluster.cluster_id,
        translation_key="start_calibrate",
        fallback_name="Start calibrate",
    )
    # .enum(
    #     SonoffCluster.AttributeDefs.set_calibration_action.name,
    #     SetCalibrationAction,
    #     SonoffCluster.cluster_id,
    #     translation_key="set_calibration_action",
    #     fallback_name="Set calibration action",
    # )
    .enum(
        SonoffCluster.AttributeDefs.calibration_status.name,
        CalibrationStatus,
        SonoffCluster.cluster_id,
        translation_key="calibration_status",
        fallback_name="Calibration status",
    )
    .number(
        SonoffCluster.AttributeDefs.calibration_progress.name,
        SonoffCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        multiplier=1,
        translation_key="calibration_progress",
        fallback_name="Calibration progress",
    )
    .enum(
        SonoffCluster.AttributeDefs.external_trigger_mode.name,
        ExternalTriggerMode,
        SonoffCluster.cluster_id,
        translation_key="external_trigger_mode",
        fallback_name="External trigger mode",
    )
    .number(
        SonoffCluster.AttributeDefs.min_brightness_threshold.name,
        SonoffCluster.cluster_id,
        min_value=1,
        max_value=99,
        step=1,
        unit=PERCENTAGE,
        multiplier=2.55,
        translation_key="min_brightness_threshold",
        fallback_name="Min brightness threshold",
    )
    .number(
        SonoffCluster.AttributeDefs.transition_time.name,
        SonoffCluster.cluster_id,
        min_value=0,
        max_value=5,
        step=0.1,
        unit="s",
        multiplier=0.1,
        translation_key="transition_time",
        fallback_name="Transition time",
    )
    .enum(
        SonoffCluster.AttributeDefs.dimming_light_rate.name,
        DimmingLightRate,
        SonoffCluster.cluster_id,
        translation_key="dimming_light_rate",
        fallback_name="Dimming light rate",
    )
    .number(
        SonoffCluster.AttributeDefs.max_brightness_threshold.name,
        SonoffCluster.cluster_id,
        min_value=2,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        multiplier=2.55,
        translation_key="max_brightness_threshold",
        fallback_name="Max brightness threshold",
    )
    .number(
        SonoffCluster.AttributeDefs.level_for_calibration.name,
        SonoffCluster.cluster_id,
        min_value=1,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        multiplier=2.55,
        translation_key="level_for_calibration",
        fallback_name="Level For Calibration",
    )
    .add_to_registry()
)