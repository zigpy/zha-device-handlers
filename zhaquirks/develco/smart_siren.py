"""Smart siren."""

from zigpy.zcl.clusters.general import PowerConfiguration
from zigpy.zcl.clusters.security import IasWd, IasZone

from zhaquirks.builder import (
    PERCENTAGE,
    BinarySensorDeviceClass,
    EntityType,
    NumberDeviceClass,
    QuirkBuilder,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTime,
)
from zhaquirks.develco import DEVELCO, FRIENT

BASE_SIREN_QUIRK = (
    QuirkBuilder()
    # Hide the default `ias_zone` entity
    .prevent_default_entity_creation(
        endpoint_id=43,
        cluster_id=IasZone.cluster_id,
        function=lambda entity: entity.translation_key == "ias_zone",
    )
    # Hide unsupported strobe controls.
    .prevent_default_entity_creation(
        endpoint_id=43,
        cluster_id=IasWd.cluster_id,
        function=lambda entity: (
            entity.translation_key
            in (
                "default_strobe_level",
                "default_strobe",
            )
        ),
    )
    # Allow setting IAS WD max warning duration in seconds.
    .number(
        attribute_name=IasWd.AttributeDefs.max_duration.name,
        cluster_id=IasWd.cluster_id,
        endpoint_id=43,
        min_value=0,
        max_value=65535,
        step=1,
        mode="box",
        unit=UnitOfTime.SECONDS,
        device_class=NumberDeviceClass.DURATION,
        translation_key="max_duration",
        fallback_name="Maximum siren duration",
    )
    # This is a mains-powered device that has a backup battery.
    .sensor(
        attribute_name=PowerConfiguration.AttributeDefs.battery_percentage_remaining.name,
        cluster_id=PowerConfiguration.cluster_id,
        endpoint_id=43,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        unit=PERCENTAGE,
        divisor=2,  # ZCL reports battery in units of 0.5%, so 200 => 100%
        fallback_name="Battery",
        unique_id_suffix="battery",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .binary_sensor(
        endpoint_id=43,
        cluster_id=IasZone.cluster_id,
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        device_class=BinarySensorDeviceClass.POWER,
        # AC mains bit is 0 when mains OK, 1 on mains fault; invert so True = AC power available.
        attribute_converter=lambda value: not bool(value & IasZone.ZoneStatus.AC_mains),
        unique_id_suffix="power",
        fallback_name="AC power",
    )
)

(
    # Devices with tamper
    BASE_SIREN_QUIRK.clone()
    .applies_to(FRIENT, "SIRZB-110")
    .applies_to(FRIENT, "SIRZB-112")
    .applies_to(DEVELCO, "SIRZB-110")
    .applies_to(DEVELCO, "SIRZB-112")
    # Create a tamper sensor
    .binary_sensor(
        endpoint_id=43,
        cluster_id=IasZone.cluster_id,
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        device_class=BinarySensorDeviceClass.TAMPER,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Tamper),
        unique_id_suffix="tamper",
        fallback_name="Tamper",
    )
    .add_to_registry()
)

(
    # Device without tamper
    BASE_SIREN_QUIRK.clone()
    .applies_to(FRIENT, "SIRZB-111")
    .applies_to(DEVELCO, "SIRZB-111")
    .add_to_registry()
)
