"""Tuya Gas Sensor."""

from zigpy.quirks.v2 import BinarySensorDeviceClass, EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant import CONCENTRATION_PARTS_PER_MILLION, UnitOfTime
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import BatterySize
from zhaquirks.tuya import TuyaLocalCluster
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaSelfTestResult(t.enum8):
    """Tuya self test result enum."""

    Checking = 0x00
    Success = 0x01
    Failure = 0x02
    Others = 0x03


class TuyaSirenRingtone(t.enum8):
    """Tuya siren ringtone enum."""

    Ringtone_01 = 0x00
    Ringtone_02 = 0x01
    Ringtone_03 = 0x02
    Ringtone_04 = 0x03
    Ringtone_05 = 0x04


class TuyaGasState(t.enum8):
    """Tuya enum gas state."""

    Present = 0x00
    Clear = 0x01


class TuyaIasGasLEL(IasZone, TuyaLocalCluster):
    """Tuya local IAS LEL gas cluster."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Standard_Warning_Device
    }


(
    TuyaQuirkBuilder("_TZE200_hr0tdd47", "TS0601")
    .applies_to("_TZE200_rjxqso4a", "TS0601")
    .applies_to("_TZE284_rjxqso4a", "TS0601")
    .tuya_gas(dp_id=1)
    .tuya_sensor(
        dp_id=2,
        attribute_name="co",
        type=t.int16s,
        device_class=SensorDeviceClass.CO,
        state_class=SensorStateClass.MEASUREMENT,
        unit=CONCENTRATION_PARTS_PER_MILLION,
        fallback_name="CO concentration",
    )
    .tuya_enum(
        dp_id=9,
        attribute_name="self_test_result",
        enum_class=TuyaSelfTestResult,
        entity_type=EntityType.DIAGNOSTIC,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="self_test_result",
        fallback_name="Self test result",
    )
    .tuya_battery(dp_id=15, battery_type=BatterySize.AA, battery_qty=2)
    .tuya_switch(
        dp_id=16,
        attribute_name="mute_siren",
        entity_type=EntityType.STANDARD,
        translation_key="mute_siren",
        fallback_name="Mute siren",
    )
    .skip_configuration()
    .add_to_registry()
)


tuya_gas_alarm_base = (
    TuyaQuirkBuilder()
    .tuya_ias(
        dp_id=1,
        ias_cfg=TuyaIasGasLEL,
        converter=lambda x: IasZone.ZoneStatus.Alarm_1
        if x == TuyaGasState.Present
        else 0,
    )  # Reports as enum, not bool
    .tuya_switch(
        dp_id=8,
        attribute_name="self_test_switch",
        entity_type=EntityType.STANDARD,
        translation_key="self_test_switch",
        fallback_name="Self test",
    )
    .tuya_enum(
        dp_id=9,
        attribute_name="self_test",
        enum_class=TuyaSelfTestResult,
        entity_type=EntityType.DIAGNOSTIC,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="self_test",
        fallback_name="Self test result",
    )
    .tuya_binary_sensor(
        dp_id=16,
        attribute_name="silence_alarm",
        entity_type=EntityType.STANDARD,
        translation_key="silence_alarm",
        fallback_name="Silence alarm",
    )
    .tuya_enchantment()
    .tuya_enchantment()
    .skip_configuration()
)


(
    tuya_gas_alarm_base.clone()  # 1, 8, 9, and 16 from base
    .applies_to("_TZE200_yojqa8xn", "TS0601")
    .applies_to("_TZE204_zougpkpy", "TS0601")
    .applies_to("_TZE204_chbyv06x", "TS0601")
    .applies_to("_TZE204_yojqa8xn", "TS0601")
    .tuya_sensor(
        dp_id=2,
        attribute_name="lower_explosive_limit",
        type=t.int16s,
        divisor=10,
        state_class=SensorStateClass.MEASUREMENT,
        unit="%LEL",  # Not present in zigpy
        translation_key="lower_explosive_limit",
        fallback_name="% Lower explosive limit",
    )
    .tuya_enum(
        dp_id=6,
        attribute_name="alarm_ringtone",
        enum_class=TuyaSirenRingtone,
        translation_key="alarm_ringtone",
        fallback_name="Alarm ringtone",
    )
    .tuya_number(
        dp_id=7,
        attribute_name="alarm_duration",
        min_value=1,
        type=t.uint16_t,
        max_value=180,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="alarm_duration",
        fallback_name="Alarm duration",
    )
    .tuya_binary_sensor(
        dp_id=10,
        attribute_name="preheat_active",
        entity_type=EntityType.STANDARD,
        translation_key="preheat_active",
        fallback_name="Preheat active",
    )
    # 13 ignored in z2m
    .add_to_registry()
)


(
    tuya_gas_alarm_base.clone()  # 1, 8, 9, and 16 from base
    .applies_to("_TZE200_ggev5fsl", "TS0601")
    .applies_to("_TZE200_u319yc66", "TS0601")
    .applies_to("_TZE200_kvpwq8z7", "TS0601")
    .tuya_binary_sensor(
        dp_id=11,
        attribute_name="fault_alarm",
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.PROBLEM,
        translation_key="fault_alarm",
        fallback_name="Fault alarm",
    )
    .add_to_registry()
)
