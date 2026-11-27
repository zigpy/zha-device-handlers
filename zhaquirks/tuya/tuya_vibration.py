"""Tuya vibration, tilt and drop sensors."""

import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.builder import (
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    SensorStateClass,
)
from zhaquirks.const import BatterySize
from zhaquirks.tuya import TUYA_CLUSTER_ID
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaMotionEvent(t.enum8):
    """Last movement event reported by the sensor."""

    Idle = 0x00
    Vibration = 0x01
    Drop = 0x02
    Tilt = 0x03


class TuyaMotionSensitivity(t.enum8):
    """Movement detection sensitivity."""

    Low = 0x00
    Medium = 0x01
    High = 0x02


# ONENUO ZG-103Z / SMATRUL 3-in-1 vibration, tilt and drop sensor.
# It reports as TS0210 like the IAS based sensors in ts0210.py, but sends
# everything as Tuya DPs on 0xEF00. Its IAS Zone cluster (zone type 0x8003)
# never changes state, so the default IAS Zone entity is not created.
#
# Tuya DPs:
#   DP 4:   battery (%)
#   DP 101: X axis (int32, signed)
#   DP 102: Y axis (int32, signed)
#   DP 103: Z axis (int32, signed)
#   DP 104: event (enum: idle, vibration, drop, tilt), back to idle
#           about 10 s after the last event
#   DP 105: sensitivity (enum: low, medium, high)
#
# The device only reports DPs after the Tuya attribute read spell, which
# it accepts while it is awake right after joining. Configuration must
# therefore not be skipped, and the device has to be paired with the quirk
# already loaded.
(
    TuyaQuirkBuilder("_TZ32101000000_5oy7cysk", "TS0210")
    .tuya_dp_attribute(
        dp_id=104,
        attribute_name="motion_event",
        type=TuyaMotionEvent,
        access=foundation.ZCLAttributeAccess.Read
        | foundation.ZCLAttributeAccess.Report,
    )
    .binary_sensor(
        attribute_name="motion_event",
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.VIBRATION,
        attribute_converter=lambda value: value != TuyaMotionEvent.Idle,
        unique_id_suffix="vibration",
        fallback_name="Vibration",
    )
    .enum(
        attribute_name="motion_event",
        enum_class=TuyaMotionEvent,
        cluster_id=TUYA_CLUSTER_ID,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="motion_event",
        fallback_name="Motion event",
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="x_axis",
        type=t.int32s,
        state_class=SensorStateClass.MEASUREMENT,
        entity_type=EntityType.STANDARD,
        translation_key="x_axis",
        fallback_name="X axis",
    )
    .tuya_sensor(
        dp_id=102,
        attribute_name="y_axis",
        type=t.int32s,
        state_class=SensorStateClass.MEASUREMENT,
        entity_type=EntityType.STANDARD,
        translation_key="y_axis",
        fallback_name="Y axis",
    )
    .tuya_sensor(
        dp_id=103,
        attribute_name="z_axis",
        type=t.int32s,
        state_class=SensorStateClass.MEASUREMENT,
        entity_type=EntityType.STANDARD,
        translation_key="z_axis",
        fallback_name="Z axis",
    )
    .tuya_enum(
        dp_id=105,
        attribute_name="sensitivity",
        enum_class=TuyaMotionSensitivity,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    .tuya_battery(dp_id=4, battery_type=BatterySize.AAA, battery_qty=2)
    .prevent_default_entity_creation(endpoint_id=1, cluster_id=IasZone.cluster_id)
    .tuya_enchantment(read_attr_spell=True)
    .add_to_registry()
)
