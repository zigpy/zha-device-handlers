"""Tuya Gas Sensor."""

from zigpy.quirks.v2 import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant import CONCENTRATION_PARTS_PER_MILLION
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t

from zhaquirks.tuya import TuyaPowerConfigurationCluster2AA
from zhaquirks.tuya.builder import TuyaQuirkBuilder


class TuyaSelfTestResult(t.enum8):
    """Tuya self test result enum."""

    Checking = 0x00
    Success = 0x01
    Failure = 0x02
    Others = 0x03


(
    TuyaQuirkBuilder("_TZE200_ggev5fsl", "TS0601")
    .applies_to("_TZE200_hr0tdd47", "TS0601")
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
    .tuya_battery(dp_id=15, power_cfg=TuyaPowerConfigurationCluster2AA)
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
