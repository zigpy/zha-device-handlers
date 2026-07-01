"""Senoro Window Sensor (TS0601)."""

from zigpy.quirks.v2 import BinarySensorDeviceClass, EntityPlatform, EntityType
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.tuya import TUYA_CLUSTER_ID, BatterySize
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class OpeningStateEnum(t.enum8):
    """Enum for opening state."""

    Open = 0
    Closed = 1
    Tilted = 2


(
    TuyaQuirkBuilder("_TZE200_ytx9fudw", "TS0601")
    .tuya_battery(
        dp_id=2,
        battery_type=BatterySize.CR2032,
        battery_qty=3,
    )
    .tuya_enum(
        dp_id=101,
        attribute_name="opening_state",
        enum_class=OpeningStateEnum,
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="opening",
        fallback_name="Opening",
    )
    .tuya_dp_attribute(
        dp_id=16,
        attribute_name="alarm",
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write,
    )
    .binary_sensor(
        attribute_name="alarm",
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.TAMPER,
        unique_id_suffix="alarm_sensor",
        fallback_name="Tamper",
    )
    .write_attr_button(
        attribute_name="alarm",
        attribute_value=0,
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        unique_id_suffix="alarm_reset",
        translation_key="reset_alarm",
        fallback_name="Reset alarm",
    )
    .skip_configuration()
    .add_to_registry()
)
