"""Sonoff SNZB-02D - Zigbee LCD smart temperature humidity sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef


class TemperatureUnit(t.enum16):
    """Temperature unit."""

    Celsius = 0
    Fahrenheit = 1


class CustomSonoffCluster(CustomCluster):
    """Sonoff custom cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        temperature_threshold_high = ZCLAttributeDef(
            id=0x0003,
            type=t.int16s,
        )

        temperature_threshold_low = ZCLAttributeDef(
            id=0x0004,
            type=t.int16s,
        )

        humidity_threshold_low = ZCLAttributeDef(
            id=0x0005,
            type=t.uint16_t,
        )

        humidity_threshold_high = ZCLAttributeDef(
            id=0x0006,
            type=t.uint16_t,
        )

        temperature_unit = ZCLAttributeDef(
            id=0x0007,
            type=TemperatureUnit,
            zcl_type=DataTypeId.uint16,
        )

    @property
    def _is_manuf_specific(self):
        return False


(
    QuirkBuilder("SONOFF", "SNZB-02D")
    .replaces(CustomSonoffCluster)
    .number(
        CustomSonoffCluster.AttributeDefs.temperature_threshold_low.name,
        CustomSonoffCluster.cluster_id,
        min_value=-10,
        max_value=60,
        step=0.1,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="temperature_threshold_low",
        fallback_name="Temperature min threshold",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.temperature_threshold_high.name,
        CustomSonoffCluster.cluster_id,
        min_value=-10,
        max_value=60,
        step=0.1,
        unit=UnitOfTemperature.CELSIUS,
        multiplier=0.01,
        translation_key="temperature_threshold_high",
        fallback_name="Temperature max threshold",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.humidity_threshold_low.name,
        CustomSonoffCluster.cluster_id,
        min_value=5,
        max_value=95,
        step=0.1,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="humidity_threshold_low",
        fallback_name="Humidity min threshold",
    )
    .number(
        CustomSonoffCluster.AttributeDefs.humidity_threshold_high.name,
        CustomSonoffCluster.cluster_id,
        min_value=5,
        max_value=95,
        step=0.1,
        unit=PERCENTAGE,
        multiplier=0.01,
        translation_key="humidity_threshold_high",
        fallback_name="Humidity max threshold",
    )
    .enum(
        CustomSonoffCluster.AttributeDefs.temperature_unit.name,
        TemperatureUnit,
        CustomSonoffCluster.cluster_id,
        translation_key="temperature_unit",
        fallback_name="Temperature unit",
    )
    .add_to_registry()
)
