"""Tuya temp and humidity sensors."""

import datetime

from zigpy.quirks.v2 import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant import PERCENTAGE, UnitOfTemperature, UnitOfTime
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass
import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.tuya import (
    TUYA_SET_TIME,
    TuyaPowerConfigurationCluster2AAA,
    TuyaTimePayload,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder, TuyaTemperatureMeasurement
from zhaquirks.tuya.mcu import TuyaMCUCluster


class TuyaTempUnitConvert(t.enum8):
    """Tuya temperature unit convert enum."""

    Celsius = 0x00
    Fahrenheit = 0x01


class TuyaSoilLightLevel(t.enum8):
    """Tuya soil sensor light level enum."""

    Low = 0x00
    Normal = 0x02
    High = 0x04


class TuyaNousTempHumiAlarm(t.enum8):
    """Tuya temperature and humidity alarm enum."""

    LowerAlarm = 0x00
    UpperAlarm = 0x01
    Canceled = 0x02


class NoManufTimeTuyaMCUCluster(TuyaMCUCluster):
    """Tuya Manufacturer Cluster with set_time mod."""

    set_time_offset = datetime.datetime(1970, 1, 1, tzinfo=datetime.UTC)
    set_time_local_offset = datetime.datetime(1970, 1, 1)

    class ServerCommandDefs(TuyaMCUCluster.ServerCommandDefs):
        """Server command definitions."""

        set_time = foundation.ZCLCommandDef(
            id=TUYA_SET_TIME,
            schema={"time": TuyaTimePayload},
            is_manufacturer_specific=False,
        )


(
    TuyaQuirkBuilder("_TZE200_bjawzodf", "TS0601")
    .applies_to("_TZE200_zl1kmjqx", "TS0601")
    .applies_to("_TZE284_9ern5sfh", "TS0601")
    # Not using tuya_temperature because device reports negative values incorrectly
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaTemperatureMeasurement.ep_attribute,
        attribute_name=TuyaTemperatureMeasurement.AttributeDefs.measured_value.name,
        converter=lambda x: ((x - 0xFFFF if x > 0x2000 else x) * 10),
    )
    .adds(TuyaTemperatureMeasurement)
    .tuya_humidity(dp_id=2, scale=10)
    .tuya_battery(dp_id=4)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE200_bq5c8xfe", "TS0601")
    .applies_to("_TZE200_vs0skpuc", "TS0601")
    .applies_to("_TZE200_qyflbnbj", "TS0601")
    .applies_to("_TZE204_qyflbnbj", "TS0601")
    .applies_to("_TZE284_qyflbnbj", "TS0601")
    .applies_to("_TZE200_44af8vyi", "TS0601")
    # Not using tuya_temperature because device reports negative values incorrectly
    .tuya_dp(
        dp_id=1,
        ep_attribute=TuyaTemperatureMeasurement.ep_attribute,
        attribute_name=TuyaTemperatureMeasurement.AttributeDefs.measured_value.name,
        converter=lambda x: ((x - 0xFFFF if x > 0x2000 else x) * 10),
    )
    .adds(TuyaTemperatureMeasurement)
    .tuya_humidity(dp_id=2)
    .tuya_battery(dp_id=4)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE200_a8sdabtg", "TS0601")  # Variant without screen, round
    .applies_to("_TZE200_qoy0ekbd", "TS0601")
    .applies_to("_TZE200_znbl8dj5", "TS0601")
    .applies_to("_TZE200_zppcgbdj", "TS0601")
    .applies_to("_TZE204_s139roas", "TS0601")
    .applies_to("_TZE200_s1xgth2u", "TS0601")  # Nedis ZBSC30WT
    .applies_to("_TZE200_t3xd7l44", "TS0601")
    .applies_to("_TZE284_kdqrazmy", "TS0601")
    .applies_to("_TZE200_dikkika5", "TS0601")
    .applies_to("_TZE200_3xfjp0ag", "TS0601")
    .applies_to("_TZE200_ehhrv2e3", "TS0601")
    .applies_to("_TZE200_lhqtjwax", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .adds(TuyaTemperatureMeasurement)
    .tuya_humidity(dp_id=2)
    .tuya_battery(dp_id=4)
    .skip_configuration()
    .add_to_registry()
)


# TH01Z - Temperature and humidity sensor with clock
(
    TuyaQuirkBuilder("_TZE200_lve3dvpy", "TS0601")
    .applies_to("_TZE200_c7emyjom", "TS0601")
    .applies_to("_TZE200_locansqn", "TS0601")
    .applies_to("_TZE200_qrztc3ev", "TS0601")
    .applies_to("_TZE200_snloy4rw", "TS0601")
    .applies_to("_TZE200_eanjj2pa", "TS0601")
    .applies_to("_TZE200_ydrdfkim", "TS0601")
    .applies_to("_TZE284_locansqn", "TS0601")
    .applies_to("_TZE200_w6n8jeuu", "TS0601")
    .applies_to("_TZE200_vvmbj46n", "TS0601")
    .applies_to("_TZE284_vvmbj46n", "TS0601")
    .applies_to("_TZE284_4dosadbh", "TS0601")
    .applies_to("_TZE284_cwyqwqbf", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_battery(dp_id=4)
    .tuya_number(
        dp_id=17,
        attribute_name="temperature_report_interval",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        min_value=5,
        max_value=120,
        step=5,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_report_interval",
        fallback_name="Temperature report interval",
    )
    .tuya_number(
        dp_id=18,
        attribute_name="humidity_report_interval",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        min_value=5,
        max_value=120,
        step=5,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_report_interval",
        fallback_name="Humidity report interval",
    )
    .tuya_enum(
        dp_id=9,
        attribute_name="display_unit",
        enum_class=TuyaTempUnitConvert,
        entity_type=EntityType.CONFIG,
        translation_key="display_unit",
        fallback_name="Display unit",
    )
    .tuya_enum(
        dp_id=14,
        attribute_name="temperature_alarm",
        enum_class=TuyaNousTempHumiAlarm,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="temperature_alarm",
        fallback_name="Temperature alarm",
    )
    .tuya_number(
        dp_id=10,
        attribute_name="alarm_temperature_max",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-20,
        max_value=60,
        step=1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_temperature_max",
        fallback_name="Alarm temperature max",
    )
    .tuya_number(
        dp_id=11,
        attribute_name="alarm_temperature_min",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-20,
        max_value=60,
        step=1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_temperature_min",
        fallback_name="Alarm temperature min",
    )
    .tuya_number(
        dp_id=19,
        attribute_name="temperature_sensitivity",
        type=t.uint16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=0.1,
        max_value=50,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_sensitivity",
        fallback_name="Temperature sensitivity",
    )
    .tuya_enum(
        dp_id=15,
        attribute_name="humidity_alarm",
        enum_class=TuyaNousTempHumiAlarm,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="humidity_alarm",
        fallback_name="Humidity alarm",
    )
    .tuya_number(
        dp_id=12,
        attribute_name="alarm_humidity_max",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_humidity_max",
        fallback_name="Alarm humidity max",
    )
    .tuya_number(
        dp_id=13,
        attribute_name="alarm_humidity_min",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_humidity_min",
        fallback_name="Alarm humidity min",
    )
    .tuya_number(
        dp_id=20,
        attribute_name="humidity_sensitivity",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=1,
        max_value=100,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_sensitivity",
        fallback_name="Humidity sensitivity",
    )
    .tuya_enchantment(data_query_spell=True)
    .skip_configuration()
    .add_to_registry(replacement_cluster=NoManufTimeTuyaMCUCluster)
)


(
    TuyaQuirkBuilder("_TZE284_aao3yzhs", "TS0601")
    .applies_to("_TZE284_sgabhwa6", "TS0601")
    .applies_to("_TZE284_nhgdf6qr", "TS0601")  # Giex GX04
    .applies_to("_TZE284_ap9owrsa", "TS0601")  # Novadigital SG-ZB
    .applies_to("_TZE284_awepdiwi", "TS0601")  # Solar powered
    .applies_to("_TZE284_33bwcga2", "TS0601")  # iHseno
    .applies_to("_TZE284_wckqztdq", "TS0601")
    .applies_to("_TZE284_3urschql", "TS0601")
    .applies_to("_TZE284_tgrzpqf4", "TS0601")
    .applies_to("_TZE284_g2e6cpnw", "TS0601")
    .tuya_temperature(dp_id=5, scale=10)
    .tuya_battery(dp_id=15)
    .tuya_soil_moisture(dp_id=3)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE284_nt4pquef", "TS0601")  # SG502Z
    .tuya_temperature(dp_id=5, scale=10)
    .tuya_enum(
        dp_id=2,
        attribute_name="light_level",
        enum_class=TuyaSoilLightLevel,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="light_level",
        fallback_name="Light level",
    )
    .tuya_soil_moisture(dp_id=3)
    .tuya_enum(
        dp_id=9,
        attribute_name="display_unit",
        enum_class=TuyaTempUnitConvert,
        entity_type=EntityType.CONFIG,
        translation_key="display_unit",
        fallback_name="Display unit",
    )
    .tuya_battery(dp_id=15)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE284_rqcuwlsa", "TS0601")  # NEO NAS-STH02B2
    .tuya_battery(dp_id=15)
    .tuya_electrical_conductivity(dp_id=1)
    .tuya_soil_moisture(dp_id=3)
    .tuya_temperature(dp_id=5, scale=10)
    .tuya_enchantment(data_query_spell=True)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE200_myd45weu", "TS0601")
    .applies_to("_TZE200_ga1maeof", "TS0601")
    .applies_to("_TZE200_9cqcpkgb", "TS0601")
    .applies_to("_TZE204_myd45weu", "TS0601")
    .applies_to("_TZE284_myd45weu", "TS0601")
    .applies_to("_TZE200_2se8efxh", "TS0601")  # Immax Neo
    .applies_to("_TZE284_oitavov2", "TS0601")
    .applies_to("_TZE284_2se8efxh", "TS0601")
    .tuya_temperature(dp_id=5)
    .tuya_battery(dp_id=15)
    .tuya_soil_moisture(dp_id=3)
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE200_upagmta9", "TS0601")
    .applies_to("_TZE204_upagmta9", "TS0601")
    .applies_to("_TZE200_cirvgep4", "TS0601")
    .applies_to("_TZE204_cirvgep4", "TS0601")
    .applies_to("_TZE204_jygvp6fk", "TS0601")
    .applies_to("_TZE200_yjjdcqsq", "TS0601")
    .applies_to("_TZE204_yjjdcqsq", "TS0601")
    .applies_to("_TZE284_yjjdcqsq", "TS0601")
    .applies_to("_TZE200_9yapgbuv", "TS0601")
    .applies_to("_TZE204_9yapgbuv", "TS0601")
    .applies_to("_TZE284_9yapgbuv", "TS0601")
    .applies_to("_TZE200_utkemkbs", "TS0601")
    .applies_to("_TZE204_utkemkbs", "TS0601")
    .applies_to("_TZE284_utkemkbs", "TS0601")
    .applies_to("_TZE204_ksz749x8", "TS0601")
    .applies_to("_TZE284_upagmta9", "TS0601")
    .applies_to("_TZE204_1wnh8bqp", "TS0601")
    .applies_to("_TZE284_1wnh8bqp", "TS0601")
    .applies_to("_TZE204_kwi6bbk4", "TS0601")
    .applies_to("_TZE200_d7lpruvi", "TS0601")
    .applies_to("_TZE204_d7lpruvi", "TS0601")
    .applies_to("_TZE284_d7lpruvi", "TS0601")
    .applies_to("_TZE284_hdyjyqjm", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_dp(
        dp_id=3,
        ep_attribute=TuyaPowerConfigurationCluster2AAA.ep_attribute,
        attribute_name="battery_percentage_remaining",
        converter=lambda x: {0: 50, 1: 100, 2: 200}[x],
    )
    .tuya_enum(
        dp_id=9,
        attribute_name="display_unit",
        enum_class=TuyaTempUnitConvert,
        entity_type=EntityType.CONFIG,
        translation_key="display_unit",
        fallback_name="Display unit",
    )
    .adds(TuyaPowerConfigurationCluster2AAA)
    .tuya_enchantment(data_query_spell=True)
    .skip_configuration()
    .add_to_registry()
)


# Contact, temperature and humidity sensor
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_contact_temperature_humidity_sensor.html
(
    TuyaQuirkBuilder("_TZE200_nvups4nh", "TS0601")
    .tuya_contact(dp_id=1)
    .tuya_battery(dp_id=2)
    .tuya_temperature(dp_id=7, scale=10)
    .tuya_humidity(dp_id=8)
    .skip_configuration()
    .add_to_registry()
)


# Illuminance, temperature & humidity sensor
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_illuminance_temperature_humidity_sensor_2.html
(
    TuyaQuirkBuilder("_TZE200_rbbx5mfq", "TS0601")
    .applies_to("_TZE204_rbbx5mfq", "TS0601")
    .tuya_illuminance(dp_id=2)
    .tuya_temperature(dp_id=6, scale=10)
    .tuya_humidity(dp_id=7, scale=10)
    .skip_configuration()
    .add_to_registry()
)


# Zigbee air quality sensor (CO2, temperature, humidity, VOC, formaldehyde)
# Z2M reference: https://www.zigbee2mqtt.io/devices/TS0601_airbox.html
(
    TuyaQuirkBuilder("_TZE284_8b9zpaav", "TS0601")
    .tuya_co2(dp_id=2)
    .tuya_temperature(dp_id=18, scale=10)
    .tuya_humidity(dp_id=19)
    .tuya_voc(dp_id=21)
    .tuya_formaldehyde(dp_id=22)
    .skip_configuration()
    .add_to_registry()
)


# PM2.5 air quality sensor (CO2, temperature, humidity, PM2.5, VOC, formaldehyde)
# Z2M reference: https://www.zigbee2mqtt.io/devices/PM2.5_airbox.html
(
    TuyaQuirkBuilder("_TZE284_it9utkro", "TS0601")
    .tuya_co2(dp_id=2)
    .tuya_temperature(dp_id=18, scale=10)
    .tuya_humidity(dp_id=19, scale=10)
    .tuya_pm25(dp_id=20)
    .tuya_voc(dp_id=21)
    .tuya_formaldehyde(dp_id=22)
    .skip_configuration()
    .add_to_registry()
)


# Temperature & humidity sensor with external probe
# Z2M reference: https://www.zigbee2mqtt.io/devices/ZY-ZTH03PRO.html
(
    TuyaQuirkBuilder("_TZE284_hodyryli", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_sensor(
        dp_id=38,
        attribute_name="external_temperature",
        type=t.int16s,
        divisor=10,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.STANDARD,
        translation_key="external_temperature",
        fallback_name="External temperature",
    )
    .skip_configuration()
    .add_to_registry()
)


# Temperature & humidity sensor with external probe (variant)
# Z2M reference: https://www.zigbee2mqtt.io/devices/TZ-ZT01_GA4.html
(
    TuyaQuirkBuilder("_TZE284_8se38w3c", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_sensor(
        dp_id=38,
        attribute_name="temperature_probe",
        type=t.int16s,
        divisor=10,
        device_class=SensorDeviceClass.TEMPERATURE,
        unit=UnitOfTemperature.CELSIUS,
        entity_type=EntityType.STANDARD,
        translation_key="temperature_probe",
        fallback_name="Temperature probe",
    )
    .skip_configuration()
    .add_to_registry()
)


# Temperature and humidity sensor (RSH-HS06)
# Z2M reference: https://www.zigbee2mqtt.io/devices/RSH-HS06.html
(
    TuyaQuirkBuilder("_TZE200_ysm4dsb1", "TS0601")
    .tuya_temperature(dp_id=1, scale=10)
    .tuya_humidity(dp_id=2)
    .tuya_battery(dp_id=4)
    .tuya_enum(
        dp_id=9,
        attribute_name="display_unit",
        enum_class=TuyaTempUnitConvert,
        entity_type=EntityType.CONFIG,
        translation_key="display_unit",
        fallback_name="Display unit",
    )
    .skip_configuration()
    .add_to_registry()
)


# Soil moisture sensor (ZS-301Z)
# Z2M reference: https://www.zigbee2mqtt.io/devices/ZS-301Z.html
(
    TuyaQuirkBuilder("_TZE284_o9ofysmo", "TS0601")
    .applies_to("_TZE284_xc3vwx5a", "TS0601")
    .tuya_soil_moisture(dp_id=3)
    .tuya_temperature(dp_id=5, scale=10)
    .tuya_humidity(dp_id=101)
    .tuya_illuminance(dp_id=102)
    .skip_configuration()
    .add_to_registry()
)


# Soil moisture sensor (ZS-300Z)
# Z2M reference: https://www.zigbee2mqtt.io/devices/ZS-300Z.html
(
    TuyaQuirkBuilder("_TZE284_k7p2q5d9", "TS0601")
    .applies_to("_TZE284_65gzcss7", "TS0601")
    .applies_to("_TZE284_0ints6wl", "TS0601")
    .applies_to("_TZE284_yzr43ayq", "TS0601")
    .tuya_soil_moisture(dp_id=3)
    .tuya_temperature(dp_id=5, scale=10)
    .tuya_humidity(dp_id=101)
    .tuya_illuminance(dp_id=102)
    .skip_configuration()
    .add_to_registry()
)


# Soil moisture sensor (CS-201Z)
# Z2M reference: https://www.zigbee2mqtt.io/devices/CS-201Z.html
(
    TuyaQuirkBuilder("_TZE200_npj9bug3", "TS0601")
    .applies_to("_TZE200_wrmhp6b3", "TS0601")
    .tuya_soil_moisture(dp_id=3)
    .tuya_temperature(dp_id=5, scale=10)
    .tuya_humidity(dp_id=109)
    .tuya_battery(dp_id=15)
    .tuya_enum(
        dp_id=9,
        attribute_name="display_unit",
        enum_class=TuyaTempUnitConvert,
        entity_type=EntityType.CONFIG,
        translation_key="display_unit",
        fallback_name="Display unit",
    )
    .skip_configuration()
    .add_to_registry()
)


# Soil moisture sensor (ZG-303Z)
# Z2M reference: https://www.zigbee2mqtt.io/devices/ZG-303Z.html
(
    TuyaQuirkBuilder("_TZE200_wqashyqo", "TS0601")
    .tuya_soil_moisture(dp_id=107)
    .tuya_temperature(dp_id=103, scale=10)
    .tuya_humidity(dp_id=109)
    .tuya_battery(dp_id=108)
    .tuya_enum(
        dp_id=9,
        attribute_name="display_unit",
        enum_class=TuyaTempUnitConvert,
        entity_type=EntityType.CONFIG,
        translation_key="display_unit",
        fallback_name="Display unit",
    )
    .skip_configuration()
    .add_to_registry()
)


# Soil fertility sensor (ZS-300TF)
# Z2M reference: https://www.zigbee2mqtt.io/devices/ZS-300TF.html
(
    TuyaQuirkBuilder("_TZE284_hdml1aav", "TS0601")
    .tuya_soil_moisture(dp_id=3)
    .tuya_temperature(dp_id=5, scale=10)
    .tuya_battery(dp_id=15)
    .tuya_humidity(dp_id=101)
    .tuya_illuminance(dp_id=102)
    .tuya_sensor(
        dp_id=112,
        attribute_name="soil_fertility",
        type=t.uint16_t,
        entity_type=EntityType.STANDARD,
        translation_key="soil_fertility",
        fallback_name="Soil fertility",
    )
    .skip_configuration()
    .add_to_registry()
)


class TuyaAirQuality(t.enum8):
    """Tuya air quality enum."""

    Excellent = 0x00
    Moderate = 0x01
    Poor = 0x02


class TuyaAlarmRingtone(t.enum8):
    """Tuya alarm ringtone enum."""

    Melody1 = 0x00
    Melody2 = 0x01
    Off = 0x02


# Multifunctional CO2 detector (ZR360CDB)
# Z2M reference: https://www.zigbee2mqtt.io/devices/ZR360CDB.html
(
    TuyaQuirkBuilder("_TZE200_pl31aqf5", "TS0601")
    .applies_to("_TZE200_xpvamyfz", "TS0601")
    .applies_to("_TZE284_xpvamyfz", "TS0601")
    .tuya_co2(dp_id=2)
    .tuya_temperature(dp_id=18)
    .tuya_humidity(dp_id=19)
    .tuya_enum(
        dp_id=1,
        attribute_name="air_quality",
        enum_class=TuyaAirQuality,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="air_quality",
        fallback_name="Air quality",
    )
    .tuya_enum(
        dp_id=5,
        attribute_name="alarm_ringtone",
        enum_class=TuyaAlarmRingtone,
        entity_type=EntityType.CONFIG,
        translation_key="alarm_ringtone",
        fallback_name="Alarm ringtone",
    )
    .skip_configuration()
    .add_to_registry()
)


class TuyaSensitivityLevel(t.enum8):
    """Tuya sensitivity level enum."""

    Low = 0x00
    Middle = 0x01
    High = 0x02


# Vibration sensor (ZG-103Z)
# Z2M reference: https://www.zigbee2mqtt.io/devices/ZG-103Z.html
(
    TuyaQuirkBuilder("_TZE200_iba1ckek", "TS0601")
    .applies_to("_TZE200_hggxgsjj", "TS0601")
    .applies_to("_TZE200_yjryxpot", "TS0601")
    .applies_to("_TZE200_afycb3cg", "TS0601")
    .tuya_vibration(dp_id=1)
    .tuya_binary_sensor(
        dp_id=7,
        attribute_name="tilt",
        translation_key="tilt",
        fallback_name="Tilt",
    )
    .tuya_battery(dp_id=105)
    .tuya_enum(
        dp_id=104,
        attribute_name="sensitivity",
        enum_class=TuyaSensitivityLevel,
        entity_type=EntityType.CONFIG,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    .skip_configuration()
    .add_to_registry()
)


# Vibration sensor (ZG-102ZM)
# Z2M reference: https://www.zigbee2mqtt.io/devices/ZG-102ZM.html
(
    TuyaQuirkBuilder("_TZE200_wzk0x7fq", "TS0601")
    .applies_to("_TZE200_jfw0a4aa", "TS0601")
    .tuya_vibration(dp_id=1)
    .tuya_contact(dp_id=101)
    .tuya_battery(dp_id=4)
    .tuya_number(
        dp_id=6,
        attribute_name="sensitivity",
        type=t.uint16_t,
        min_value=1,
        max_value=10,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    .skip_configuration()
    .add_to_registry()
)


# Vibration sensor (TZE284_4cqhd2ha)
# Z2M reference: https://www.zigbee2mqtt.io/devices/TZE284_4cqhd2ha.html
(
    TuyaQuirkBuilder("_TZE284_4cqhd2ha", "TS0601")
    .applies_to("_TZE200_8ply8mjj", "TS0601")
    .tuya_vibration(dp_id=1)
    .tuya_number(
        dp_id=101,
        attribute_name="sensitivity",
        type=t.uint16_t,
        min_value=1,
        max_value=10,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="sensitivity",
        fallback_name="Sensitivity",
    )
    .tuya_switch(
        dp_id=103,
        attribute_name="buzzer_mute",
        entity_type=EntityType.CONFIG,
        translation_key="buzzer_mute",
        fallback_name="Buzzer mute",
    )
    .skip_configuration()
    .add_to_registry()
)


class TuyaRainwaterStatus(t.enum8):
    """Tuya rainwater status enum."""

    Clear = 0x00
    Raining = 0x01


# Rainwater detection sensor (ZG-223Z)
# Z2M reference: https://www.zigbee2mqtt.io/devices/ZG-223Z.html
(
    TuyaQuirkBuilder("_TZE200_jsaqgakf", "TS0601")
    .applies_to("_TZE200_u6x1zyv2", "TS0601")
    .applies_to("_TZE200_2pddnnrk", "TS0601")
    .tuya_enum(
        dp_id=1,
        attribute_name="rainwater",
        enum_class=TuyaRainwaterStatus,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="rainwater",
        fallback_name="Rainwater",
    )
    .tuya_illuminance(dp_id=102)
    .tuya_battery(dp_id=104)
    .skip_configuration()
    .add_to_registry()
)
