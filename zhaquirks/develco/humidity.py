"""Develco Smart Humidity Sensor."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.develco import DevelcoPowerConfiguration


class HumidityPowerConfiguration(DevelcoPowerConfiguration):
    """PowerConfiguration with device-specific voltage bounds."""

    MIN_VOLTS = 2.3
    MAX_VOLTS = 3.0


class TemperatureMeasurementCustom(CustomCluster, TemperatureMeasurement):
    """Temperature Measurement Cluster with calibration attribute."""

    INVALID_MEASURED_VALUES = frozenset({0x8000, -32768})

    def __init__(self, *args, **kwargs) -> None:
        """Initialize state for temperature offset handling."""
        super().__init__(*args, **kwargs)
        self._raw_measured_value: int | None = None
        # Set defaults so HA shows 0 until a value is written.
        self._update_attribute(self.AttributeDefs.temperature_offset.id, 0)

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Attribute Definitions."""

        # A value in 1C offset to fix up incorrect values from sensor
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
        """Handle temperature offset writes locally and pass through others."""
        offset = None
        offset_attr_id = self.AttributeDefs.temperature_offset.id
        remaining = dict(attributes)

        for attr_key, value in attributes.items():
            if isinstance(attr_key, foundation.ZCLAttributeDef):
                attr_def = attr_key
            elif isinstance(attr_key, str):
                attr_def = self.attributes_by_name.get(attr_key)
            else:
                attr_def = self.attributes.get(attr_key)
            if attr_def is None or attr_def.id != offset_attr_id:
                continue
            offset = value
            remaining.pop(attr_key, None)

        if offset is not None:
            self._update_attribute(offset_attr_id, offset)

        if remaining:
            return await super().write_attributes(remaining, **kwargs)

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    async def read_attributes_raw(self, attributes, manufacturer=None, **kwargs):
        """Return cached temperature offset locally and delegate others."""
        offset_attr_id = self.AttributeDefs.temperature_offset.id
        delegated = []
        local_records = []

        for attr in attributes:
            if isinstance(attr, foundation.ZCLAttributeDef):
                attr_def = attr
            elif isinstance(attr, str):
                attr_def = self.attributes_by_name.get(attr)
            else:
                attr_def = self.attributes.get(attr)

            if attr_def is None:
                local_records.append(
                    foundation.ReadAttributeRecord(
                        attr,
                        foundation.Status.UNSUPPORTED_ATTRIBUTE,
                        foundation.TypeValue(),
                    )
                )
                continue

            if attr_def.id != offset_attr_id:
                delegated.append(attr_def.id)
                continue

            record = foundation.ReadAttributeRecord(
                offset_attr_id,
                foundation.Status.SUCCESS,
                foundation.TypeValue(),
            )
            cached = self._attr_cache.get(offset_attr_id, 0)
            record.value.value = attr_def.type(cached)
            local_records.append(record)

        if delegated:
            (records,) = await super().read_attributes_raw(
                delegated, manufacturer=manufacturer, **kwargs
            )
            records.extend(local_records)
            return (records,)

        return (local_records,)

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.measured_value.id:
            self._raw_measured_value = value
            if value in self.INVALID_MEASURED_VALUES:
                return super()._update_attribute(attrid, value)
            offset = self._attr_cache.get(self.AttributeDefs.temperature_offset.id, 0)
            return super()._update_attribute(attrid, value + offset * 100)

        if attrid == self.AttributeDefs.temperature_offset.id:
            result = super()._update_attribute(attrid, value)
            if (
                getattr(self, "_raw_measured_value", None) is not None
                and self._raw_measured_value not in self.INVALID_MEASURED_VALUES
            ):
                super()._update_attribute(
                    self.AttributeDefs.measured_value.id,
                    self._raw_measured_value + value * 100,
                )
            return result

        return super()._update_attribute(attrid, value)


class RelativeHumidityCustom(CustomCluster, RelativeHumidity):
    """Relative Humidity Cluster with calibration attribute."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize state for humidity offset handling."""
        super().__init__(*args, **kwargs)
        self._raw_measured_value: int | None = None
        # Set defaults so HA shows 0 until a value is written.
        self._update_attribute(self.AttributeDefs.humidity_offset.id, 0)

    class AttributeDefs(RelativeHumidity.AttributeDefs):
        """Attribute Definitions."""

        # A value in 1%RH offset to fix up incorrect values from sensor
        humidity_offset: Final = ZCLAttributeDef(
            id=0x0010,
            type=t.int16s,
            access="rw",
            manufacturer_code=0x1015,
        )

    async def write_attributes(
        self,
        attributes: dict[str | int | foundation.ZCLAttributeDef, int],
        **kwargs,
    ) -> list[list[foundation.WriteAttributesStatusRecord]]:
        """Handle humidity offset writes locally and pass through others."""
        offset = None
        offset_attr_id = self.AttributeDefs.humidity_offset.id
        remaining = dict(attributes)

        for attr_key, value in attributes.items():
            if isinstance(attr_key, foundation.ZCLAttributeDef):
                attr_def = attr_key
            elif isinstance(attr_key, str):
                attr_def = self.attributes_by_name.get(attr_key)
            else:
                attr_def = self.attributes.get(attr_key)
            if attr_def is None or attr_def.id != offset_attr_id:
                continue
            offset = value
            remaining.pop(attr_key, None)

        if offset is not None:
            self._update_attribute(offset_attr_id, offset)

        if remaining:
            return await super().write_attributes(remaining, **kwargs)

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    async def read_attributes_raw(self, attributes, manufacturer=None, **kwargs):
        """Return cached humidity offset locally and delegate others."""
        offset_attr_id = self.AttributeDefs.humidity_offset.id
        delegated = []
        local_records = []

        for attr in attributes:
            if isinstance(attr, foundation.ZCLAttributeDef):
                attr_def = attr
            elif isinstance(attr, str):
                attr_def = self.attributes_by_name.get(attr)
            else:
                attr_def = self.attributes.get(attr)

            if attr_def is None:
                local_records.append(
                    foundation.ReadAttributeRecord(
                        attr,
                        foundation.Status.UNSUPPORTED_ATTRIBUTE,
                        foundation.TypeValue(),
                    )
                )
                continue

            if attr_def.id != offset_attr_id:
                delegated.append(attr_def.id)
                continue

            record = foundation.ReadAttributeRecord(
                offset_attr_id,
                foundation.Status.SUCCESS,
                foundation.TypeValue(),
            )
            cached = self._attr_cache.get(offset_attr_id, 0)
            record.value.value = attr_def.type(cached)
            local_records.append(record)

        if delegated:
            (records,) = await super().read_attributes_raw(
                delegated, manufacturer=manufacturer, **kwargs
            )
            records.extend(local_records)
            return (records,)

        return (local_records,)

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.measured_value.id:
            self._raw_measured_value = value
            if value == 0xFFFF:
                return super()._update_attribute(attrid, value)
            offset = self._attr_cache.get(self.AttributeDefs.humidity_offset.id, 0)
            return super()._update_attribute(attrid, value + offset * 100)

        if attrid == self.AttributeDefs.humidity_offset.id:
            result = super()._update_attribute(attrid, value)
            if (
                getattr(self, "_raw_measured_value", None) is not None
                and self._raw_measured_value != 0xFFFF
            ):
                super()._update_attribute(
                    self.AttributeDefs.measured_value.id,
                    self._raw_measured_value + value * 100,
                )
            return result

        return super()._update_attribute(attrid, value)


(
    QuirkBuilder("frient A/S", "HMSZB-120")
    .applies_to("Develco Products A/S", "HMSZB-120")
    .applies_to("frient A/S", "HMSZB-110")
    .applies_to("Develco Products A/S", "HMSZB-110")
    .replaces(TemperatureMeasurementCustom, endpoint_id=38)
    .replaces(HumidityPowerConfiguration, endpoint_id=38)
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
        unit=PERCENTAGE,
        translation_key="humidity_offset",
        fallback_name="Humidity offset",
        unique_id_suffix="humidity_offset",
    )
    .add_to_registry()
)
