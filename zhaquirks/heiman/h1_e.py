"""Heiman H1-E temperature and humidity sensor."""

from typing import Final, Self

import zigpy.types as t
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import PERCENTAGE, EntityType, QuirkBuilder, UnitOfTemperature
from zhaquirks.clusters import CustomCluster


class TemperatureDisplayMode(t.enum8):
    """Temperature unit shown on the device screen."""

    Celsius = 1
    Fahrenheit = 0

    @classmethod
    def _missing_(cls, value: object) -> Self:
        """Treat other nonzero device values as Celsius."""
        return cls.Celsius


class HeimanTemperatureMeasurement(CustomCluster, TemperatureMeasurement):
    """Temperature measurement with a manufacturer-specific display setting."""

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Attribute definitions."""

        temperature_display_mode: Final = ZCLAttributeDef(
            id=0xF002, type=t.int8s, manufacturer_code=0x120B
        )


class CustomHeimanCluster(CustomCluster):
    """Heiman H1-E calibration settings and diagnostics."""

    cluster_id = 0xFC90
    name = "Heiman H1-E"
    ep_attribute = "heiman_h1"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        rebooted_count: Final = ZCLAttributeDef(
            id=0x0019, type=t.uint16_t, access="rp", manufacturer_code=0x120B
        )
        rejoined_count: Final = ZCLAttributeDef(
            id=0x001A, type=t.uint16_t, access="rp", manufacturer_code=0x120B
        )
        reported_packages: Final = ZCLAttributeDef(
            id=0x001B, type=t.uint16_t, access="rp", manufacturer_code=0x120B
        )
        temperature_offset: Final = ZCLAttributeDef(
            id=0x100D, type=t.int16s, manufacturer_code=0x120B
        )
        humidity_offset: Final = ZCLAttributeDef(
            id=0x1012, type=t.int16s, manufacturer_code=0x120B
        )


# ZHA discovers temperature and battery on endpoint 1 and humidity on endpoint 2.
(
    QuirkBuilder("Heiman", "H1-E")
    .applies_to("HEIMAN", "H1-E")
    .replaces(HeimanTemperatureMeasurement)
    .replaces(CustomHeimanCluster)
    .enum(
        attribute_name=HeimanTemperatureMeasurement.AttributeDefs.temperature_display_mode.name,
        cluster_id=HeimanTemperatureMeasurement.cluster_id,
        enum_class=TemperatureDisplayMode,
        attribute_initialized_from_cache=False,
        translation_key="temperature_display_mode",
        fallback_name="Temperature display mode",
    )
    .number(
        attribute_name=CustomHeimanCluster.AttributeDefs.temperature_offset.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        min_value=-15,
        max_value=15,
        step=0.1,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        attribute_initialized_from_cache=False,
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
    )
    .number(
        attribute_name=CustomHeimanCluster.AttributeDefs.humidity_offset.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        min_value=-15,
        max_value=15,
        step=0.1,
        multiplier=0.01,
        unit=PERCENTAGE,
        attribute_initialized_from_cache=False,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
    )
    .sensor(
        attribute_name=CustomHeimanCluster.AttributeDefs.rebooted_count.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        attribute_initialized_from_cache=False,
        translation_key="rebooted_count",
        fallback_name="Rebooted count",
    )
    .sensor(
        attribute_name=CustomHeimanCluster.AttributeDefs.rejoined_count.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        attribute_initialized_from_cache=False,
        translation_key="rejoined_count",
        fallback_name="Rejoined count",
    )
    .sensor(
        attribute_name=CustomHeimanCluster.AttributeDefs.reported_packages.name,
        cluster_id=CustomHeimanCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        initially_disabled=True,
        attribute_initialized_from_cache=False,
        translation_key="reported_packages",
        fallback_name="Reported packages",
    )
    .add_to_registry()
)
