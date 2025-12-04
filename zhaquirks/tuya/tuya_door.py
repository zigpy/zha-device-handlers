"""Senoro Window Sensor (TS0601)."""

from zigpy.quirks.v2 import BinarySensorDeviceClass, EntityPlatform, EntityType
import zigpy.types as t
from zigpy.zcl import foundation

from zigpy.quirks.v2.homeassistant import UnitOfTime
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


(
    TuyaQuirkBuilder("_TZE284_6teua268", "TS0601")
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
    .tuya_dp_attribute(
        dp_id=107,
        attribute_name="setup_mode",
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Read | foundation.ZCLAttributeAccess.Write,
    )
    .binary_sensor(
        attribute_name="setup_mode",
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.TAMPER,
        unique_id_suffix="setup_mode_sensor",
        fallback_name="Exit Setup Mode",
    )
    .write_attr_button(
        attribute_name="setup_mode",
        attribute_value=0,
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        unique_id_suffix="setup_mode_reset",
        translation_key="reset_setup_mode",
        fallback_name="Exit Setup Mode",
    )
    .tuya_dp_attribute(
        dp_id=103,
        attribute_name="alarm_siren",
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Read |
            foundation.ZCLAttributeAccess.Write |
            foundation.ZCLAttributeAccess.Report,
    )
    .switch(
        attribute_name="alarm_siren",
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        unique_id_suffix="alarm_siren_switch",
        translation_key="alarm_siren",
        fallback_name="Use Alarm Siren",
    )
    .tuya_number(
        dp_id=109, 
        attribute_name="alarm_siren_duration", 
        type=t.uint16_t,
        min_value=5, 
        max_value=180, 
        unit=UnitOfTime.SECONDS,
        step=1, 
        fallback_name="Alarm Siren Duration", 
        translation_key="alarm_siren_duration"
    )
    .tuya_dp_attribute(
        dp_id=102, 
        attribute_name="vibration", 
        type=t.uint16_t,
        access=foundation.ZCLAttributeAccess.Read | 
            foundation.ZCLAttributeAccess.Report
    )
    .tuya_number(
        dp_id=106, 
        attribute_name="vibration_limit", 
        type=t.uint16_t,
        min_value=0, 
        max_value=100, 
        step=1, 
        fallback_name="Value of vibration.", 
        translation_key="vibration_limit"
    )
    .tuya_number(
        dp_id=110, 
        attribute_name="vibration_siren_duration", 
        type=t.uint16_t,
        min_value=5, 
        max_value=180, 
        unit=UnitOfTime.SECONDS,
        step=1, 
        fallback_name="Duration of the vibrating siren.", 
        translation_key="vibration_siren_duration"
    )
    .tuya_dp_attribute(
        dp_id=108, 
        attribute_name="vibration_siren", 
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Read | 
            foundation.ZCLAttributeAccess.Write
    )
    .switch(
        attribute_name="vibration_siren",
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        translation_key="vibration_siren",
        fallback_name="Activate the siren when vibrating.",
    )
    .tuya_dp_attribute(
        dp_id=104, 
        attribute_name="close_signal", 
        type=t.Bool,
        access=foundation.ZCLAttributeAccess.Read | 
            foundation.ZCLAttributeAccess.Write)
    .switch(
        attribute_name="close_signal",
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        translation_key="close_signal",
        fallback_name="Enable sound when closing the window.",
    )
    .tuya_number(
        dp_id=105, 
        attribute_name="transmission_power", 
        type=t.uint8_t,
        min_value=11, 
        max_value=19, 
        step=1, 
        fallback_name="Transmission power 11-19. High value > battery consumption.", 
        translation_key="transmission_power"
    )  
    .tuya_dp_attribute(
        dp_id=111, 
        attribute_name="magnetic_status",
        type=t.Bool,
        converter=lambda value: not value,
        dp_converter=lambda value: not value,
        access=foundation.ZCLAttributeAccess.Read | 
            foundation.ZCLAttributeAccess.Report)    
    .binary_sensor(attribute_name="magnetic_status",
        cluster_id=TUYA_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.DOOR,        
        translation_key="magnetic_status",
        fallback_name="Magnetic status."
    )
    .skip_configuration()    
    .add_to_registry()
)