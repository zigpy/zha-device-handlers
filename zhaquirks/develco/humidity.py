"""Develco Smart Humidity Sensor."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    QuirkBuilder,
    NumberDeviceClass,
)
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.quirks.v2.homeassistant import  UnitOfTemperature
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.foundation import (
    BaseAttributeDefs,
    ZCLAttributeDef,
)
from zhaquirks.develco import DevelcoPowerConfiguration


class HMSZB120PowerConfiguration(DevelcoPowerConfiguration):
    """PowerConfiguration that derives percent from voltage only."""

    MIN_VOLTS = 2.3
    MAX_VOLTS = 3.0

    async def read_attributes_raw(self, attributes, manufacturer=None, **kwargs):
        """Return battery percent from cached voltage instead of reading 0x0021."""
        attr_list = []
        requested_percent = False
        for attr in attributes:
            attr_def = self.find_attribute(attr)
            if attr_def is None:
                continue
            if attr_def.id == self.BATTERY_PERCENTAGE_REMAINING:
                requested_percent = True
            else:
                attr_list.append(attr_def.id)
        local_records = []

        if requested_percent:
            attr_def = self.find_attribute(self.BATTERY_PERCENTAGE_REMAINING)
            record = foundation.ReadAttributeRecord(
                attr_def.id,
                foundation.Status.UNSUPPORTED_ATTRIBUTE,
                foundation.TypeValue(),
            )
            voltage = self._attr_cache.get(self.BATTERY_VOLTAGE_ATTR)
            if voltage not in (None, 0, 255):
                percent = self._calculate_battery_percentage(voltage)
                record.value.value = attr_def.type(percent)
                record.status = foundation.Status.SUCCESS
            local_records.append(record)

        if attr_list:
            records, = await super().read_attributes_raw(
                attr_list, manufacturer=manufacturer, **kwargs
            )
            records.extend(local_records)
            return (records,)

        return (local_records,)

class TemperatureMeasurementCustom(CustomCluster, TemperatureMeasurement):
    """Temperature Measurement Cluster with calibration attribute."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._raw_measured_value: int | None = None
        # Set defaults so HA shows 0 until a value is written.
        self._update_attribute(self.AttributeDefs.temperature_offset.id, 0)

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Attribute Definitions."""

        # A value in 0.01ºC offset to fix up incorrect values from sensor
        temperature_offset: Final = ZCLAttributeDef(
            id=0x8888,
            type=t.int16s,
            access="rw",
            manufacturer_code=0x1015,
        )
    
    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, int],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Translate mode writes into manufacturer-specific commands."""
        offset = None

        if self.AttributeDefs.temperature_offset.id in attributes:
            offset = attributes.pop(self.AttributeDefs.temperature_offset.id)
            self._update_attribute(self.AttributeDefs.temperature_offset.id, offset)
        elif self.AttributeDefs.temperature_offset.name in attributes:
            offset = attributes.pop(self.AttributeDefs.temperature_offset.name)
            self._update_attribute(self.AttributeDefs.temperature_offset.id, offset)

        if attributes:
            return await super().write_attributes(attributes, **kwargs)

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.measured_value.id:
            self._raw_measured_value = value
            if value == 0x8000:
                return super()._update_attribute(attrid, value)
            offset = self._attr_cache.get(
                self.AttributeDefs.temperature_offset.id, 0
            )
            return super()._update_attribute(attrid, value + offset*100)

        if attrid == self.AttributeDefs.temperature_offset.id:
            result = super()._update_attribute(attrid, value)
            if (
                getattr(self, "_raw_measured_value", None) is not None
                and self._raw_measured_value != 0x8000
            ):
                super()._update_attribute(
                    self.AttributeDefs.measured_value.id,
                    self._raw_measured_value + value*100,
                )
            return result

        return super()._update_attribute(attrid, value)

class RelativeHumidityCustom(CustomCluster, RelativeHumidity):
    """Relative Humidity Cluster with calibration attribute."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._raw_measured_value: int | None = None
        # Set defaults so HA shows 0 until a value is written.
        self._update_attribute(self.AttributeDefs.humidity_offset.id, 0)

    class AttributeDefs(RelativeHumidity.AttributeDefs):
        """Attribute Definitions."""

        # A value in 0.01%RH offset to fix up incorrect values from sensor
        humidity_offset: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.uint16_t,
            access="rw",
            manufacturer_code=0x1015,
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, int],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Translate mode writes into manufacturer-specific commands."""
        offset = None

        if self.AttributeDefs.humidity_offset.id in attributes:
            offset = attributes.pop(self.AttributeDefs.humidity_offset.id)
            self._update_attribute(self.AttributeDefs.humidity_offset.id, offset)
        elif self.AttributeDefs.humidity_offset.name in attributes:
            offset = attributes.pop(self.AttributeDefs.humidity_offset.name)
            self._update_attribute(self.AttributeDefs.humidity_offset.id, offset)

        if attributes:
            return await super().write_attributes(attributes, **kwargs)

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.measured_value.id:
            self._raw_measured_value = value
            if value == 0x8000:
                return super()._update_attribute(attrid, value)
            offset = self._attr_cache.get(
                self.AttributeDefs.humidity_offset.id, 0
            )
            return super()._update_attribute(attrid, value + offset*100)

        if attrid == self.AttributeDefs.humidity_offset.id:
            result = super()._update_attribute(attrid, value)
            if (
                getattr(self, "_raw_measured_value", None) is not None
                and self._raw_measured_value != 0x8000
            ):
                super()._update_attribute(
                    self.AttributeDefs.measured_value.id,
                    self._raw_measured_value + value*100,
                )
            return result

        return super()._update_attribute(attrid, value)

(
    QuirkBuilder("frient A/S", "HMSZB-120")
    .replaces(TemperatureMeasurementCustom, endpoint_id=38)
    .replaces(HMSZB120PowerConfiguration, endpoint_id=38)
    .replaces(RelativeHumidityCustom, endpoint_id=38)
    .number(
        attribute_name=TemperatureMeasurementCustom.AttributeDefs.temperature_offset.name,
        cluster_id=TemperatureMeasurement.cluster_id,
        endpoint_id=38,
        min_value=-10,
        max_value=10,
        step=1,
        unit=UnitOfTemperature.CELSIUS,
        translation_key="temperature_offset",
        fallback_name="Temperature offset",
        unique_id_suffix="temperature_offset",
    )
    .number(
        attribute_name=RelativeHumidityCustom.AttributeDefs.humidity_offset.name,
        cluster_id=RelativeHumidity.cluster_id,
        endpoint_id=38,
        min_value=-10,
        max_value=10,
        step=1,
        unit=NumberDeviceClass.HUMIDITY,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
        unique_id_suffix="humidity_offset",
    )
    .add_to_registry()
)
