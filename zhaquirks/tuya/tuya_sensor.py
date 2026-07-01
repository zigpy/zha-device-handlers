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
    .tuya_temperature(dp_id=5, scale=10)
    .tuya_battery(dp_id=15)
    .tuya_soil_moisture(dp_id=3)
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
    .applies_to("_TZE200_utkemkbs", "TS0601")
    .applies_to("_TZE204_utkemkbs", "TS0601")
    .applies_to("_TZE284_utkemkbs", "TS0601")
    .applies_to("_TZE204_ksz749x8", "TS0601")
    .applies_to("_TZE284_upagmta9", "TS0601")
    .applies_to("_TZE204_1wnh8bqp", "TS0601")
    .applies_to("_TZE284_1wnh8bqp", "TS0601")
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
