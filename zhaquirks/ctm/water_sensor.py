"""CTM Lyng AX Water Sensor."""

from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster
from zhaquirks.builder import BinarySensorDeviceClass, EntityType, QuirkBuilder
from zhaquirks.ctm import CTM_MANUF_NAME


class CtmWaterSensorPowerConfiguration(PowerConfigurationCluster):
    """Derive the battery percentage from the voltage, the only value reported."""

    MIN_VOLTS = 2.5
    MAX_VOLTS = 3.2


(
    QuirkBuilder(CTM_MANUF_NAME, "AX Water Sensor")
    .replaces(CtmWaterSensorPowerConfiguration)
    # The default ZHA IAS Zone entity reports `Alarm_1 | Alarm_2` and is kept as the
    # leak alarm: Alarm_2 latches until the alarm is acknowledged with the button on
    # the sensor, which is also what keeps a bound valve closed.
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.MOISTURE,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Alarm_1),
        unique_id_suffix="active_water_leak",
        translation_key="active_water_leak",
        fallback_name="Active water leak",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.BATTERY,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Battery),
        unique_id_suffix="battery_low",
        fallback_name="Battery low",
    )
    .add_to_registry()
)
