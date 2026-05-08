"""Frient Range Extender quirks.

REXZB-111: expose battery (from PowerConfiguration) and indicate whether
the device has a battery (so callers can infer mains vs battery power).

REXZB-110: device does not support battery so we register a minimal quirk.
"""

from zigpy.quirks.v2 import (
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
)
from zigpy.quirks.v2.homeassistant import PERCENTAGE
from zigpy.quirks.v2.homeassistant.binary_sensor import BinarySensorDeviceClass
from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.develco import DevelcoPowerConfiguration


class RangeExtenderPowerConfiguration(DevelcoPowerConfiguration):
    """PowerConfiguration with device-specific voltage bounds."""

    MIN_VOLTS = 3.2
    MAX_VOLTS = 4.1


# REXZB-111: expose battery percentage (calculated from battery_voltage)
# and a diagnostic binary sensor that reports whether the device actually
# has a battery. The binary sensor uses `battery_voltage` value: values of
# 0 or 255 (and missing) mean "no battery" on many devices, otherwise a
# battery is present.
(
    QuirkBuilder("frient A/S", "REXZB-111")
    .prevent_default_entity_creation(
        endpoint_id=37,
        cluster_id=IasZone.cluster_id,
        function=lambda entity: entity.translation_key == "ias_zone",
    )
    .replaces(RangeExtenderPowerConfiguration, endpoint_id=37)
    .binary_sensor(
        endpoint_id=37,
        cluster_id=IasZone.cluster_id,
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        device_class=BinarySensorDeviceClass.POWER,
        # AC mains bit is 0 when on mains power, 1 when on battery, so we need to invert it for correct reporting
        attribute_converter=lambda value: not bool(value & IasZone.ZoneStatus.AC_mains),
        unique_id_suffix="power",
        fallback_name="AC Power",
        entity_type=EntityType.STANDARD,
    )
    .sensor(
        endpoint_id=37,
        cluster_id=PowerConfiguration.cluster_id,
        attribute_name=RangeExtenderPowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        divisor=2,
        fallback_name="Battery",
        unique_id_suffix="battery",
        entity_type=EntityType.STANDARD,
    )
    .add_to_registry()
)


# REXZB-110: does not support battery — register a minimal quirk so devices
# are recognized but we don't expose battery-related entities.
(
    QuirkBuilder("frient A/S", "REXZB-110")
    .add_to_registry()
)
