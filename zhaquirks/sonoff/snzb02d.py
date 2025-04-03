"""Sonoff SNZB-02D - Zigbee LCD smart temperature humidity sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef


class TemperatureUnit(t.enum16):
    """Temperature unit."""

    Celsius = 0
    Fahrenheit = 1


class CustomSonoffCluster(CustomCluster):
    """Sonoff custom cluster."""

    cluster_id = 0xFC11
    manufacturer_id_override: t.uint16_t = foundation.ZCLHeader.NO_MANUFACTURER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        comfort_temperature_max = ZCLAttributeDef(
            id=0x0003,
            type=t.int16s,
        )

        comfort_temperature_min = ZCLAttributeDef(
            id=0x0004,
            type=t.int16s,
        )

        comfort_humidity_min = ZCLAttributeDef(
            id=0x0005,
            type=t.uint16_t,
        )

        comfort_humidity_max = ZCLAttributeDef(
            id=0x0006,
            type=t.uint16_t,
        )

        temperature_unit = ZCLAttributeDef(
            id=0x0007,
            type=TemperatureUnit,
            zcl_type=DataTypeId.uint16,
        )


(
    QuirkBuilder("SONOFF", "SNZB-02D")
    .replaces(CustomSonoffCluster)
    .number(
        CustomSonoffCluster.AttributeDefs.comfort_temperature_min.name,
        CustomSonoffCluster.cluster_id,
        min_value=-10,
        max_value=60,
        step=0.1,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="comfort_temperature_min",
        fallback_name="Comfort temperature min",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.comfort_temperature_max.name,
        CustomSonoffCluster.cluster_id,
        min_value=-10,
        max_value=60,
        step=0.1,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="comfort_temperature_max",
        fallback_name="Comfort temperature max",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.comfort_humidity_min.name,
        CustomSonoffCluster.cluster_id,
        min_value=5,
        max_value=95,
        step=0.1,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="comfort_humidity_min",
        fallback_name="Comfort humidity min",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.comfort_humidity_max.name,
        CustomSonoffCluster.cluster_id,
        min_value=5,
        max_value=95,
        step=0.1,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="comfort_humidity_max",
        fallback_name="Comfort humidity max",
    )
    .enum(
        CustomSonoffCluster.AttributeDefs.temperature_unit.name,
        TemperatureUnit,
        CustomSonoffCluster.cluster_id,
        translation_key="display_unit",
        fallback_name="Display unit",
    )
    .add_to_registry()
)
