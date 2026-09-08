"""BSEED BHT-009 Thermostat quirk."""

from homeassistant.components.number import NumberDeviceClass
from homeassistant.const import UnitOfTemperature
from zigpy.quirks.v2.homeassistant import EntityPlatform, EntityType
import zigpy.types as t

from zhaquirks.tuya.builder import TuyaQuirkBuilder


# Enums for better readability in Home Assistant
class OperationMode(t.enum8):
    """Operation mode: Scheduled follow internal timer, Manual follow setpoint."""

    Scheduled = 0x00
    Manual = 0x01


class HeatingStatus(t.enum8):
    """Heating status: Device logic uses 0 for Heating and 1 for Idle."""

    Heating = 0x00
    Idle = 0x01


(
    TuyaQuirkBuilder("_TZE204_tagezcph", "TS0601")
    .applies_to("_TZE204_tagezcph", "TS0601")
    # 1. Local Temperature (DP 24 / 0x18)
    .tuya_temperature(dp_id=24, scale=10)
    # 2. Target Temperature (DP 16 / 0x10)
    .tuya_number(
        dp_id=16,
        attribute_name="occupied_heating_setpoint",
        type=t.uint16_t,
        device_class=NumberDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        min_value=5.0,
        max_value=35.0,
        step=0.5,
        multiplier=0.1,
        translation_key="target_temperature",
        fallback_name="Target temperature",
    )
    # 3. Switches: Power (DP 1), Child Lock (DP 39), Eco Mode (DP 40)
    .tuya_switch(
        dp_id=1,
        attribute_name="system_mode",
        translation_key="system_mode",
        fallback_name="Power",
    )
    .tuya_switch(
        dp_id=39,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_switch(
        dp_id=40,
        attribute_name="eco_mode",
        translation_key="eco_mode",
        fallback_name="Eco mode",
    )
    # 4. Operation Mode: Scheduled/Manual (DP 2 / 0x02)
    .tuya_enum(
        dp_id=2,
        attribute_name="operation_mode",
        enum_class=OperationMode,
        translation_key="operation_mode",
        fallback_name="Operation mode",
    )
    # 5. Heating State (DP 36 / 0x24)
    .tuya_enum(
        dp_id=36,
        attribute_name="heating_state",
        enum_class=HeatingStatus,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="heating_state",
        fallback_name="Heating state",
    )
    .skip_configuration()
    .add_to_registry()
)
