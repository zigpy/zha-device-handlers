"""Heiman H1-E temperature and humidity sensor."""

from typing import Final

from zha.application.helpers import write_attributes_safe
from zha.application.platforms import AttrConfig, ClusterConfig
from zha.application.platforms.select import ZCLEnumSelectEntity
from zha.exceptions import ZHAException
import zigpy.types as t
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef

from zhaquirks.builder import PERCENTAGE, EntityType, QuirkBuilder, UnitOfTemperature
from zhaquirks.clusters import CustomCluster

CELSIUS_DISPLAY_BIT: Final = 0x01


class TemperatureDisplayMode(t.enum8):
    """Unit options exposed by the display setting's bit 0."""

    Celsius = 1
    Fahrenheit = 0


class HeimanTemperatureMeasurement(CustomCluster, TemperatureMeasurement):
    """Temperature measurement with a manufacturer-specific display setting."""

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Attribute definitions."""

        temperature_display_mode: Final = ZCLAttributeDef(
            # Preserve the device's int8 wire type for this bit field.
            id=0xF002,
            type=t.int8s,
            manufacturer_code=0x120B,
        )


class TemperatureDisplaySelect(ZCLEnumSelectEntity):
    """Select the temperature unit while preserving the other display bits."""

    _attribute_name = (
        HeimanTemperatureMeasurement.AttributeDefs.temperature_display_mode.name
    )
    _enum = TemperatureDisplayMode
    _unique_id_suffix = "temperature_display_mode"
    _server_cluster_config = {
        TemperatureMeasurement.cluster_id: ClusterConfig(
            attributes={
                HeimanTemperatureMeasurement.AttributeDefs.temperature_display_mode: AttrConfig(
                    read_on_startup=True
                )
            }
        )
    }

    @property
    def current_option(self) -> str | None:
        """Decode the unit from bit 0 of the original device value."""
        value = self._cluster.get(self._attribute_name)
        if value is None:
            return None
        return TemperatureDisplayMode(int(value) & CELSIUS_DISPLAY_BIT).name

    async def async_select_option(self, option: str) -> None:
        """Update only the temperature unit bit of the cached device value."""
        unit = self._enum[option]
        current = self._cluster.get(self._attribute_name)
        if current is None:
            raise ZHAException("Temperature display settings are not available")

        value = (int(current) & ~CELSIUS_DISPLAY_BIT) | int(unit)
        await write_attributes_safe(self._cluster, {self._attribute_name: value})
        self.maybe_emit_state_changed_event()


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
    .adds_entity(
        TemperatureDisplaySelect,
        endpoint_id=1,
        cluster_id=TemperatureMeasurement.cluster_id,
        force_create=True,
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
