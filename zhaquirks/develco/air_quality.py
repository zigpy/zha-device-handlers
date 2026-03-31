"""Develco Air Quality Sensor."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import (
    QuirkBuilder,
    ReportingConfig,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import (
    CONCENTRATION_PARTS_PER_BILLION,
    PERCENTAGE,
    UnitOfTemperature,
)
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.measurement import RelativeHumidity, TemperatureMeasurement
from zigpy.zcl.foundation import (
    ZCL_CLUSTER_REVISION_ATTR,
    ZCL_REPORTING_STATUS_ATTR,
    BaseAttributeDefs,
    ZCLAttributeDef,
)

from zhaquirks.develco import DevelcoPowerConfiguration


class AQSZB110PowerConfiguration(DevelcoPowerConfiguration):
    """PowerConfiguration that derives percent from voltage only."""

    MIN_VOLTS = 2.3
    MAX_VOLTS = 3.0

    async def read_attributes_raw(self, attributes, manufacturer=None, **kwargs):
        """Return battery percent from cached voltage instead of reading 0x0021."""
        attr_list = []
        requested_percent = False
        local_records = []
        for attr in attributes:
            try:
                attr_def = self.find_attribute(attr)
            except KeyError:
                # Unknown attribute: return an UNSUPPORTED_ATTRIBUTE record.
                local_records.append(
                    foundation.ReadAttributeRecord(
                        attr,
                        foundation.Status.UNSUPPORTED_ATTRIBUTE,
                        foundation.TypeValue(),
                    )
                )
                continue
            if attr_def.id == self.BATTERY_PERCENTAGE_REMAINING:
                requested_percent = True
            else:
                attr_list.append(attr_def.id)
        if requested_percent:
            try:
                attr_def = self.find_attribute(self.BATTERY_PERCENTAGE_REMAINING)
            except KeyError:
                # If the percentage attribute definition is missing, still
                # respond with UNSUPPORTED_ATTRIBUTE instead of raising.
                record = foundation.ReadAttributeRecord(
                    self.BATTERY_PERCENTAGE_REMAINING,
                    foundation.Status.UNSUPPORTED_ATTRIBUTE,
                    foundation.TypeValue(),
                )
            else:
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
            (records,) = await super().read_attributes_raw(
                attr_list, manufacturer=manufacturer, **kwargs
            )
            records.extend(local_records)
            return (records,)

        return (local_records,)


class DevelcoVOCMeasurement(CustomCluster):
    """Develco VOC cluster definition."""

    cluster_id = 0xFC03
    name = "VOC Level"
    ep_attribute = "develco_voc_level"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions, same as all the other `Measurement` clusters."""

        measured_value: Final = ZCLAttributeDef(
            id=0x0000,
            type=t.uint16_t,  # In parts per billion
            access="rp",
            mandatory=True,
            is_manufacturer_specific=True,
        )
        min_measured_value: Final = ZCLAttributeDef(
            id=0x0001,
            type=t.uint16_t,
            access="r",
            mandatory=True,
            is_manufacturer_specific=True,
        )
        max_measured_value: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.uint16_t,
            access="r",
            mandatory=True,
            is_manufacturer_specific=True,
        )
        tolerance: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.uint16_t,
            access="r",
            is_manufacturer_specific=True,
        )

        cluster_revision: Final = ZCL_CLUSTER_REVISION_ATTR
        reporting_status: Final = ZCL_REPORTING_STATUS_ATTR


class TemperatureMeasurementCustom(CustomCluster, TemperatureMeasurement):
    """Temperature Measurement Cluster with calibration attribute."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialize state for temperature offset handling."""
        super().__init__(*args, **kwargs)
        self._raw_measured_value: int | None = None
        # Set defaults so HA shows 0 until a value is written.
        self._update_attribute(self.AttributeDefs.temperature_offset.id, 0)

    class AttributeDefs(TemperatureMeasurement.AttributeDefs):
        """Attribute Definitions."""

        # A value in 1ºC offset to fix up incorrect values from sensor
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
        offset_attr_id = self.AttributeDefs.temperature_offset.id

        for attr_key, value in list(attributes.items()):
            attr_def = self.find_attribute(attr_key)
            if attr_def is None or attr_def.id != offset_attr_id:
                continue
            offset = value
            attributes.pop(attr_key)

        if offset is not None:
            self._update_attribute(offset_attr_id, offset)

        if attributes:
            return await super().write_attributes(attributes, **kwargs)

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.measured_value.id:
            self._raw_measured_value = value
            if value == 0x8000:
                return super()._update_attribute(attrid, value)
            offset = self._attr_cache.get(self.AttributeDefs.temperature_offset.id, 0)
            return super()._update_attribute(attrid, value + offset * 100)

        if attrid == self.AttributeDefs.temperature_offset.id:
            result = super()._update_attribute(attrid, value)
            if (
                getattr(self, "_raw_measured_value", None) is not None
                and self._raw_measured_value != 0x8000
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
            type=t.t.int16s,
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
        offset_attr_id = self.AttributeDefs.humidity_offset.id

        for attr_key, value in list(attributes.items()):
            attr_def = self.find_attribute(attr_key)
            if attr_def is None or attr_def.id != offset_attr_id:
                continue
            offset = value
            attributes.pop(attr_key)

        if offset is not None:
            self._update_attribute(offset_attr_id, offset)

        if attributes:
            return await super().write_attributes(attributes, **kwargs)

        return [[foundation.WriteAttributesStatusRecord(foundation.Status.SUCCESS)]]

    def _update_attribute(self, attrid, value):
        if attrid == self.AttributeDefs.measured_value.id:
            self._raw_measured_value = value
            if value == 0x8000:
                return super()._update_attribute(attrid, value)
            offset = self._attr_cache.get(self.AttributeDefs.humidity_offset.id, 0)
            return super()._update_attribute(attrid, value + offset * 100)

        if attrid == self.AttributeDefs.humidity_offset.id:
            result = super()._update_attribute(attrid, value)
            if (
                getattr(self, "_raw_measured_value", None) is not None
                and self._raw_measured_value != 0x8000
            ):
                super()._update_attribute(
                    self.AttributeDefs.measured_value.id,
                    self._raw_measured_value + value * 100,
                )
            return result

        return super()._update_attribute(attrid, value)


def measured_value_converter(value: int) -> int:
    """Ignore invalid value sent after initiation."""
    new_value = value if value < 0xFFFF else None
    return new_value


def value_to_caqi(value: int) -> str:
    """Convert raw VOC value to CAQI (0-5500 scale)."""
    if value < 66:
        return "Excellent"
    elif value < 221:
        return "Good"
    elif value < 661:
        return "Moderate"
    elif value < 2201:
        return "Poor"
    else:
        return "Bad"


(
    QuirkBuilder("frient A/S", "AQSZB-110")
    .applies_to("Develco Products A/S", "AQSZB-110")
    .replaces(DevelcoVOCMeasurement, endpoint_id=38)
    .replaces(AQSZB110PowerConfiguration, endpoint_id=38)
    .replaces(TemperatureMeasurementCustom, endpoint_id=38)
    .replaces(RelativeHumidityCustom, endpoint_id=38)
    .sensor(
        attribute_name=DevelcoVOCMeasurement.AttributeDefs.measured_value.name,
        cluster_id=DevelcoVOCMeasurement.cluster_id,
        endpoint_id=38,
        attribute_converter=measured_value_converter,
        device_class=SensorDeviceClass.VOLATILE_ORGANIC_COMPOUNDS_PARTS,
        state_class=SensorStateClass.MEASUREMENT,
        unit=CONCENTRATION_PARTS_PER_BILLION,
        fallback_name="VOC level",
        unique_id_suffix="voc_level",
        reporting_config=ReportingConfig(
            min_interval=30,
            max_interval=900,
            reportable_change=10,  # TVOC fluctuates a lot
        ),
    )
    .sensor(
        attribute_name=DevelcoVOCMeasurement.AttributeDefs.measured_value.name,
        cluster_id=DevelcoVOCMeasurement.cluster_id,
        endpoint_id=38,
        attribute_converter=value_to_caqi,
        device_class=SensorDeviceClass.ENUM,
        unit=None,  # No unit for enum values
        fallback_name="CAQI",
        unique_id_suffix="caqi_index",
    )
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
