"""Rti-Tek STHZB temperature and humidity sensor."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.builder import (
    PERCENTAGE,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster

RTI_TEK_FD22_CLUSTER_ID = 0xFD22


class RtiTekTemperatureUnit(t.enum8):
    """Temperature unit selected on the device."""

    Celsius = 0x00
    Fahrenheit = 0x01


class RtiTekAlarmStatus(t.enum8):
    """Temperature or humidity alarm state."""

    Normal = 0x00
    Low = 0x01
    High = 0x02


ALARM_STATUS_TEXT = {
    RtiTekAlarmStatus.Normal: "Normal",
    RtiTekAlarmStatus.Low: "Low",
    RtiTekAlarmStatus.High: "High",
}

ALARM_VALUE_STEPS: Final[dict[str, int]] = {
    "temperature_alarm_lower": 10,
    "temperature_alarm_upper": 10,
    "humidity_alarm_lower": 100,
    "humidity_alarm_upper": 100,
}

ALARM_LIMIT_RULES: Final[tuple[tuple[str, str, int, str], ...]] = (
    (
        "temperature_alarm_lower",
        "temperature_alarm_upper",
        20,
        "0.2 C",
    ),
    (
        "humidity_alarm_lower",
        "humidity_alarm_upper",
        200,
        "2 %RH",
    ),
)

FAULT_BITS = {
    0: "Internal sensor fault",
    1: "External sensor fault",
    2: "Low battery",
    3: "Poor battery status",
    4: "Battery too low for OTA",
}


def convert_alarm_status(value: int | None) -> str:
    """Convert a device alarm enum to diagnostic text."""

    try:
        status = RtiTekAlarmStatus(value)
    except (TypeError, ValueError):
        return "Unknown" if value is None else f"Unknown 0x{int(value):02x}"
    return ALARM_STATUS_TEXT.get(status, f"Unknown 0x{int(status):02x}")


def convert_fault_code(value: int | None) -> str:
    """Convert the FD22 fault bitmap to diagnostic text."""

    try:
        raw_value = int(value)
    except (TypeError, ValueError):
        return "Unknown"

    if raw_value == 0:
        return "No fault"

    faults = [name for bit, name in FAULT_BITS.items() if raw_value & (1 << bit)]
    unknown_bits = raw_value & ~sum(1 << bit for bit in FAULT_BITS)
    if unknown_bits:
        faults.append(f"Unknown 0x{unknown_bits:08x}")
    return ", ".join(faults)


class RtiTekFd22Cluster(CustomCluster):
    """STHZB private configuration and diagnostic cluster."""

    cluster_id = RTI_TEK_FD22_CLUSTER_ID

    class AttributeDefs(BaseAttributeDefs):
        """Private attributes verified on STHZB devices."""

        temperature_unit: Final = ZCLAttributeDef(
            id=0x0000,
            type=RtiTekTemperatureUnit,
            zcl_type=DataTypeId.enum8,
            manufacturer_code=None,
        )
        fault_code: Final = ZCLAttributeDef(
            id=0x0002,
            type=t.bitmap32,
            access="r",
            zcl_type=DataTypeId.map32,
            manufacturer_code=None,
        )
        product_name: Final = ZCLAttributeDef(
            id=0x0003,
            type=t.CharacterString,
            access="r",
            manufacturer_code=None,
        )
        internal_temperature_calibration: Final = ZCLAttributeDef(
            id=0xE005,
            type=t.int8s,
            manufacturer_code=None,
        )
        internal_humidity_calibration: Final = ZCLAttributeDef(
            id=0xE006,
            type=t.int8s,
            manufacturer_code=None,
        )
        sample_interval: Final = ZCLAttributeDef(
            id=0xE009,
            type=t.uint16_t,
            manufacturer_code=None,
        )
        temperature_alarm_upper: Final = ZCLAttributeDef(
            id=0xE00A,
            type=t.int16s,
            manufacturer_code=None,
        )
        temperature_alarm_lower: Final = ZCLAttributeDef(
            id=0xE00B,
            type=t.int16s,
            manufacturer_code=None,
        )
        humidity_alarm_upper: Final = ZCLAttributeDef(
            id=0xE00C,
            type=t.uint16_t,
            manufacturer_code=None,
        )
        humidity_alarm_lower: Final = ZCLAttributeDef(
            id=0xE00D,
            type=t.uint16_t,
            manufacturer_code=None,
        )
        temperature_alarm_status: Final = ZCLAttributeDef(
            id=0xE00E,
            type=RtiTekAlarmStatus,
            zcl_type=DataTypeId.enum8,
            access="r",
            manufacturer_code=None,
        )
        humidity_alarm_status: Final = ZCLAttributeDef(
            id=0xE00F,
            type=RtiTekAlarmStatus,
            zcl_type=DataTypeId.enum8,
            access="r",
            manufacturer_code=None,
        )

    @staticmethod
    def _normalize_alarm_value(name: str, value: int) -> int:
        """Normalize one alarm threshold to the observed firmware step."""

        raw_value = int(value)
        step = ALARM_VALUE_STEPS[name]
        if name.startswith("temperature_"):
            return int(raw_value / step) * step
        return ((raw_value + step // 2) // step) * step

    def _normalize_and_validate_alarm_limits(self, attributes: dict) -> None:
        """Validate alarm ordering after normalizing the written raw values."""

        normalized: dict[str, int] = {}
        for attribute, value in attributes.items():
            try:
                attribute_definition = self.find_attribute(attribute)
            except KeyError:
                continue
            if attribute_definition.name not in ALARM_VALUE_STEPS:
                continue
            normalized_value = self._normalize_alarm_value(
                attribute_definition.name, value
            )
            attributes[attribute] = normalized_value
            normalized[attribute_definition.name] = normalized_value

        for lower_name, upper_name, minimum_gap, display_gap in ALARM_LIMIT_RULES:
            lower_value = normalized.get(
                lower_name,
                self._attr_cache.get(getattr(self.AttributeDefs, lower_name).id),
            )
            upper_value = normalized.get(
                upper_name,
                self._attr_cache.get(getattr(self.AttributeDefs, upper_name).id),
            )
            if lower_value is None or upper_value is None:
                continue
            if int(upper_value) - int(lower_value) < minimum_gap:
                label = lower_name.removesuffix("_lower").replace("_", " ")
                raise ValueError(
                    f"{label} upper must be at least {display_gap} above lower"
                )

    async def write_attributes(self, attributes, manufacturer=None, **kwargs):
        """Normalize and validate device alarm threshold writes."""

        attributes = dict(attributes)
        self._normalize_and_validate_alarm_limits(attributes)
        return await super().write_attributes(
            attributes, manufacturer=manufacturer, **kwargs
        )


(
    QuirkBuilder()
    .applies_to("Rti-Tek", "STHZB")
    .replaces(RtiTekFd22Cluster)
    .enum(
        RtiTekFd22Cluster.AttributeDefs.temperature_unit.name,
        RtiTekTemperatureUnit,
        RtiTekFd22Cluster.cluster_id,
        translation_key="temperature_unit",
        fallback_name="Temperature unit",
    )
    .number(
        RtiTekFd22Cluster.AttributeDefs.internal_temperature_calibration.name,
        RtiTekFd22Cluster.cluster_id,
        min_value=-10.0,
        max_value=10.0,
        step=0.1,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE_DELTA,
        translation_key="internal_temperature_calibration",
        fallback_name="Internal temperature calibration",
    )
    .number(
        RtiTekFd22Cluster.AttributeDefs.internal_humidity_calibration.name,
        RtiTekFd22Cluster.cluster_id,
        min_value=-10.0,
        max_value=10.0,
        step=0.1,
        multiplier=0.1,
        unit=PERCENTAGE,
        device_class=NumberDeviceClass.HUMIDITY,
        translation_key="internal_humidity_calibration",
        fallback_name="Internal humidity calibration",
    )
    .number(
        RtiTekFd22Cluster.AttributeDefs.sample_interval.name,
        RtiTekFd22Cluster.cluster_id,
        min_value=1,
        max_value=3600,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="sample_interval",
        fallback_name="Sample interval",
    )
    .number(
        RtiTekFd22Cluster.AttributeDefs.temperature_alarm_upper.name,
        RtiTekFd22Cluster.cluster_id,
        min_value=-30.0,
        max_value=60.0,
        step=0.1,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="temperature_alarm_upper",
        fallback_name="Temperature alarm upper",
    )
    .number(
        RtiTekFd22Cluster.AttributeDefs.temperature_alarm_lower.name,
        RtiTekFd22Cluster.cluster_id,
        min_value=-30.0,
        max_value=60.0,
        step=0.1,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        device_class=NumberDeviceClass.TEMPERATURE,
        translation_key="temperature_alarm_lower",
        fallback_name="Temperature alarm lower",
    )
    .number(
        RtiTekFd22Cluster.AttributeDefs.humidity_alarm_upper.name,
        RtiTekFd22Cluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        multiplier=0.01,
        unit=PERCENTAGE,
        device_class=NumberDeviceClass.HUMIDITY,
        translation_key="humidity_alarm_upper",
        fallback_name="Humidity alarm upper",
    )
    .number(
        RtiTekFd22Cluster.AttributeDefs.humidity_alarm_lower.name,
        RtiTekFd22Cluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        multiplier=0.01,
        unit=PERCENTAGE,
        device_class=NumberDeviceClass.HUMIDITY,
        translation_key="humidity_alarm_lower",
        fallback_name="Humidity alarm lower",
    )
    .sensor(
        RtiTekFd22Cluster.AttributeDefs.temperature_alarm_status.name,
        RtiTekFd22Cluster.cluster_id,
        attribute_converter=convert_alarm_status,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="temperature_alarm_status",
        fallback_name="Temperature alarm status",
    )
    .sensor(
        RtiTekFd22Cluster.AttributeDefs.humidity_alarm_status.name,
        RtiTekFd22Cluster.cluster_id,
        attribute_converter=convert_alarm_status,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="humidity_alarm_status",
        fallback_name="Humidity alarm status",
    )
    .sensor(
        RtiTekFd22Cluster.AttributeDefs.fault_code.name,
        RtiTekFd22Cluster.cluster_id,
        attribute_converter=convert_fault_code,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="fault_status",
        fallback_name="Fault status",
    )
    .sensor(
        RtiTekFd22Cluster.AttributeDefs.product_name.name,
        RtiTekFd22Cluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="product_name",
        fallback_name="Product name",
    )
    .add_to_registry()
)
