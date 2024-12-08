"""Smoke Sensor."""

from zigpy.quirks.v2 import BinarySensorDeviceClass, EntityType

from zhaquirks.tuya.builder import TuyaPowerConfigurationCluster2AAA, TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE200_aycxwiau", "TS0601")
    .applies_to("_TZE200_dq1mfjug", "TS0601")
    .applies_to("_TZE200_m9skfctm", "TS0601")
    .applies_to("_TZE200_rccxox8p", "TS0601")
    .applies_to("_TZE200_vzekyi4c", "TS0601")
    .applies_to("_TZE204_ntcy3xu1", "TS0601")
    .applies_to("_TZE204_vawy74yh", "TS0601")
    .tuya_ias(dp_id=1)
    .skip_configuration()
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE204_ntcy3xu1", "TS0601")
    .tuya_ias(dp_id=1)
    .tuya_binary_sensor(
        dp_id=4,
        attribute_name="tamper_status",
        device_class=BinarySensorDeviceClass.TAMPER,
        fallback_name="Tamper",
        entity_type=EntityType.DIAGNOSTIC,
    )
    .tuya_dp(
        dp_id=14,
        ep_attribute=TuyaPowerConfigurationCluster2AAA.ep_attribute,
        attribute_name="battery_percentage_remaining",
        converter=lambda x: {0: 5, 1: 100}[x],
    )
    .adds(TuyaPowerConfigurationCluster2AAA)
    .skip_configuration()
    .add_to_registry()
)
