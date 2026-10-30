"""CTM Lyng AX Valve Controller."""

from zha.application.platforms.binary_sensor import IASZone
from zigpy.profiles import zha
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityFilter,
    EntityType,
    QuirkBuilder,
)
from zhaquirks.ctm import CTM_MANUF_NAME

(
    QuirkBuilder(CTM_MANUF_NAME, "AX Valve Controller")
    # The valve endpoint reports an undefined device type (0xffff).
    .replaces_endpoint(1, device_type=zha.DeviceType.ON_OFF_OUTPUT)
    # Replace the default ZHA IAS Zone entity to rename it to "Water leak".
    .removes_entity(
        EntityFilter(
            entity_cls=IASZone,
            endpoint_id=2,
            cluster_id=IasZone.cluster_id,
        )
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=2,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.MOISTURE,
        # Alarm_2 latches until the alarm is acknowledged with the button on the device
        # that raised it, and the valve stays closed and ignores external on/off
        # commands until then.
        attribute_converter=lambda value: bool(
            value & (IasZone.ZoneStatus.Alarm_1 | IasZone.ZoneStatus.Alarm_2)
        ),
        # Reuse the default IAS Zone entity's unique id ("{ieee}-2-1280").
        unique_id_suffix=str(IasZone.cluster_id),
        translation_key="water_leak",
        fallback_name="Water leak",
    )
    .binary_sensor(
        attribute_name=IasZone.AttributeDefs.zone_status.name,
        cluster_id=IasZone.cluster_id,
        endpoint_id=2,
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
        endpoint_id=2,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=BinarySensorDeviceClass.POWER,
        attribute_converter=lambda value: not (value & IasZone.ZoneStatus.AC_mains),
        unique_id_suffix="mains_power",
        fallback_name="Power",
    )
    .add_to_registry()
)
