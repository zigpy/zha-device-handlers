"""Frient Range Extender quirks.

REXZB-111: expose battery (from PowerConfiguration) and indicate whether
the device is mains or battery powered.
"""

from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import (
    PERCENTAGE,
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
)
from zhaquirks.develco import DevelcoPowerConfiguration


class RangeExtenderPowerConfiguration(DevelcoPowerConfiguration):
    """PowerConfiguration with device-specific voltage bounds."""

    MIN_VOLTS = 3.2
    MAX_VOLTS = 4.1


# REXZB-111: expose battery percentage and diagnostic binary sensors
# derived from IasZone.zone_status for AC power state and battery-low status.
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
        # AC mains bit is 0 when mains OK, 1 on mains fault; invert so True = AC power available.
        attribute_converter=lambda value: not bool(value & IasZone.ZoneStatus.AC_mains),
        unique_id_suffix="ac_power",
        translation_key="ac_power",
        fallback_name="AC power",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .binary_sensor(
        endpoint_id=37,
        cluster_id=IasZone.cluster_id,
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        device_class=BinarySensorDeviceClass.BATTERY,
        # Battery bit is 0 when battery is ok, 1 when battery is low.
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Battery),
        unique_id_suffix="battery",
        fallback_name="Battery",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .sensor(
        endpoint_id=37,
        cluster_id=PowerConfiguration.cluster_id,
        attribute_name=RangeExtenderPowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        divisor=2,
        translation_key="battery_percentage",
        fallback_name="Battery percentage",
        unique_id_suffix="battery_percentage",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)
