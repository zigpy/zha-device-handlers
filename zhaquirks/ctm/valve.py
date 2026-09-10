"""CTM Lyng AX Valve Controller."""

from zigpy.profiles import zha
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import BinarySensorDeviceClass, EntityType, QuirkBuilder
from zhaquirks.ctm import CTM_MANUF_NAME

(
    QuirkBuilder(CTM_MANUF_NAME, "AX Valve Controller")
    # The valve endpoint reports an undefined device type (0xffff).
    .replaces_endpoint(1, device_type=zha.DeviceType.ON_OFF_OUTPUT)
    # Remove the default ZHA IAS Zone entity: it reports `Alarm_1 | Alarm_2`, which
    # the two sensors below separate.
    .prevent_default_entity_creation(
        endpoint_id=2,
        cluster_id=IasZone.cluster_id,
        function=lambda entity: entity.__class__.__name__ == "IASZone",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.MOISTURE,
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Alarm_1),
        unique_id_suffix="water_leak",
        translation_key="water_leak",
        fallback_name="Water leak",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.PROBLEM,
        # Alarm_2 latches: it clears only on a button press on the device that raised
        # the alarm, and the valve ignores external on/off commands until it does.
        attribute_converter=lambda value: bool(value & IasZone.ZoneStatus.Alarm_2),
        unique_id_suffix="valve_alarm",
        translation_key="valve_alarm",
        fallback_name="Valve alarm",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.POWER,
        attribute_converter=lambda value: not value & IasZone.ZoneStatus.AC_mains,
        unique_id_suffix="mains_power",
        fallback_name="Power",
    )
    .add_to_registry()
)
