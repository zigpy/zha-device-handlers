"""Tuya NOUS E6 temperature and humidity sensor with screen."""

from zigpy.quirks.v2 import EntityType
from zigpy.quirks.v2.homeassistant import UnitOfTemperature
import zigpy.types as t

from zhaquirks.const import BatterySize
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.tuya_sensor import NoManufTimeTuyaMCUCluster, TuyaTempUnitConvert

(
    TuyaQuirkBuilder("_TZE284_wtikaxzs", "TS0601")
    .applies_to("_TZE200_nnrfa68v", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_battery(dp_id=4, battery_type=BatterySize.AAA, battery_qty=2)
    .tuya_enum(
        dp_id=9,
        attribute_name="display_unit",
        enum_class=TuyaTempUnitConvert,
        entity_type=EntityType.CONFIG,
        translation_key="display_unit",
        fallback_name="Display unit",
    )
    .tuya_number(
        dp_id=10,
        attribute_name="alarm_temperature_max",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-20,
        max_value=60,
        step=1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_temperature_max",
        fallback_name="Alarm temperature max",
    )
    .tuya_number(
        dp_id=11,
        attribute_name="alarm_temperature_min",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-20,
        max_value=60,
        step=1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_temperature_min",
        fallback_name="Alarm temperature min",
    )
    .tuya_number(
        dp_id=19,
        attribute_name="temperature_sensitivity",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=0.1,
        max_value=10,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_sensitivity",
        fallback_name="Temperature sensitivity",
    )
    .tuya_enchantment(data_query_spell=True)
    .skip_configuration()
    .add_to_registry(replacement_cluster=NoManufTimeTuyaMCUCluster)
)
