"""Tuya temp and humidity sensors."""

from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t

from zhaquirks.tuya.builder import TuyaPowerConfigurationCluster2AAA, TuyaQuirkBuilder

(
    TuyaQuirkBuilder("_TZE200_bjawzodf", "TS0601")
    .applies_to("_TZE200_zl1kmjqx", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2, scale=10)
    .tuya_battery(dp_id=4)
    .skip_configuration()
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE200_a8sdabtg", "TS0601")  # Variant without screen, round
    .applies_to("_TZE200_qoy0ekbd", "TS0601")
    .applies_to("_TZE200_znbl8dj5", "TS0601")
    .applies_to("_TZE200_qyflbnbj", "TS0601")
    .applies_to("_TZE200_zppcgbdj", "TS0601")
    .applies_to("_TZE204_s139roas", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_battery(dp_id=4)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE200_yjjdcqsq", "TS0601")
    .applies_to("_TZE200_9yapgbuv", "TS0601")
    .applies_to("_TZE204_9yapgbuv", "TS0601")
    .applies_to("_TZE204_yjjdcqsq", "TS0601")
    .applies_to("_TZE200_utkemkbs", "TS0601")
    .applies_to("_TZE204_utkemkbs", "TS0601")
    .applies_to("_TZE204_yjjdcqsq", "TS0601")
    .applies_to("_TZE204_ksz749x8", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_dp(
        dp_id=4,
        ep_attribute=TuyaPowerConfigurationCluster2AAA.ep_attribute,
        attribute_name="battery_percentage_remaining",
        converter=lambda x: {0: 50, 1: 100, 2: 200}[x],
    )
    .adds(TuyaPowerConfigurationCluster2AAA)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE284_aao3yzhs", "TS0601")
    .applies_to("_TZE284_sgabhwa6", "TS0601")
    .applies_to("_TZE284_nhgdf6qr", "TS0601")  # Giex GX04
    .tuya_temperature(dp_id=5, scale=10)
    .tuya_battery(dp_id=15)
    .tuya_soil_moisture(dp_id=3)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE200_myd45weu", "TS0601")
    .applies_to("_TZE200_ga1maeof", "TS0601")
    .applies_to("_TZE200_9cqcpkgb", "TS0601")
    .applies_to("_TZE204_myd45weu", "TS0601")
    .tuya_temperature(dp_id=5)
    .tuya_battery(dp_id=15)
    .tuya_soil_moisture(dp_id=3)
    .skip_configuration()
    .add_to_registry()
)

(
    TuyaQuirkBuilder("_TZE200_pay2byax", "TS0601")  # Cusam ZG-102ZL
    .applies_to("_TZE200_n8dljorx", "TS0601")
    .tuya_sensor(
        dp_id=101,
        attribute_name="measured_value",
        type=t.uint16_t,
        fallback_name="Illuminance",
        device_class=SensorDeviceClass.ILLUMINANCE,
        state_class=SensorStateClass.MEASUREMENT,
    )
    .tuya_contact(dp_id=1)
    .tuya_battery(dp_id=2)
    .skip_configuration()
    .add_to_registry()
)
