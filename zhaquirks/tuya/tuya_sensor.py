"""Tuya temp and humidity sensors."""

import datetime

import zigpy.types as t
from zigpy.zcl import foundation

from zhaquirks.builder import (
    PERCENTAGE,
    BinarySensorDeviceClass,
    EntityPlatform,
    EntityType,
    SensorDeviceClass,
    SensorStateClass,
    UnitOfTemperature,
    UnitOfTime,
)
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


class TuyaWaterWarning(t.enum8):
    """Tuya water shortage warning enum."""

    None_ = 0x00
    Alarm = 0x01


class TuyaSoilFertilityWarning(t.enum8):
    """Tuya soil fertility warning enum."""

    None_ = 0x00
    Low = 0x01
    High = 0x02


class TuyaProbeTempWarning(t.enum8):
    """Tuya probe temperature warning enum."""

    None_ = 0x00
    Low = 0x01
    High = 0x02


class TuyaTempWarning(t.enum8):
    """Tuya temperature warning enum."""

    None_ = 0x00
    Low = 0x01
    High = 0x02


class TuyaHumiWarning(t.enum8):
    """Tuya humidity warning enum."""

    None_ = 0x00
    Low = 0x01
    High = 0x02


class TuyaTdsWarning(t.enum8):
    """Tuya TDS warning enum."""

    None_ = 0x00
    High = 0x01


class TuyaEcWarning(t.enum8):
    """Tuya EC warning enum."""

    None_ = 0x00
    Low = 0x01
    High = 0x02


class TuyaModeWater(t.enum8):
    """Tuya water mode enum."""

    Freshwater = 0x00
    Seawater = 0x01


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
        converter=lambda x: (x - 0xFFFF if x > 0x2000 else x) * 10,
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
        converter=lambda x: (x - 0xFFFF if x > 0x2000 else x) * 10,
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
    .applies_to("_TZE284_4dosadbh", "TS0601")
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
    .applies_to("_TZE284_tgrzpqf4", "TS0601")
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


# Excellux ZS-300TF Soil Fertility Sensor
# Note: Device IDs (_TZE2...) need to be discovered from actual devices
(
    TuyaQuirkBuilder("_TZE284_hdml1aav", "TS0601")
    .applies_to("_TZE2841000000_hdml1aav", "TS0601")
    .tuya_soil_moisture(dp_id=3)
    .tuya_temperature(dp_id=5, scale=10)
    .tuya_battery(dp_id=15)
    .tuya_humidity(dp_id=101, scale=100)
    .tuya_illuminance(dp_id=102)
    .tuya_number(
        dp_id=103,
        attribute_name="report_period",
        type=t.uint16_t,
        unit=UnitOfTime.SECONDS,
        min_value=5,
        max_value=1200,
        step=5,
        entity_type=EntityType.CONFIG,
        translation_key="report_period",
        fallback_name="Report period",
    )
    .tuya_number(
        dp_id=104,
        attribute_name="soil_calibration",
        type=t.int16_t,
        min_value=-1000,
        max_value=1000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="soil_calibration",
        fallback_name="Soil calibration",
    )
    .tuya_number(
        dp_id=105,
        attribute_name="humidity_calibration",
        type=t.int16_t,
        min_value=-1000,
        max_value=1000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_calibration",
        fallback_name="Humidity calibration",
    )
    .tuya_number(
        dp_id=106,
        attribute_name="illuminance_calibration",
        type=t.int16_t,
        min_value=-15,
        max_value=1000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="illuminance_calibration",
        fallback_name="Illuminance calibration",
    )
    .tuya_number(
        dp_id=107,
        attribute_name="temperature_calibration",
        type=t.int16_t,
        min_value=-1000,
        max_value=1000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_calibration",
        fallback_name="Temperature calibration",
    )
    .tuya_enum(
        dp_id=110,
        attribute_name="soil_warning",
        enum_class=TuyaSoilLightLevel,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="soil_warning",
        fallback_name="Soil warning",
    )
    .tuya_enum(
        dp_id=111,
        attribute_name="water_warning",
        enum_class=TuyaWaterWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="water_warning",
        fallback_name="Water warning",
    )
    .tuya_electrical_conductivity(dp_id=112, scale=1)
    .tuya_number(
        dp_id=113,
        attribute_name="soil_fertility_calibration",
        type=t.int16_t,
        min_value=-1000,
        max_value=1000,
        step=5,
        entity_type=EntityType.CONFIG,
        translation_key="soil_fertility_calibration",
        fallback_name="Soil fertility calibration",
    )
    .tuya_number(
        dp_id=114,
        attribute_name="soil_fertility_set_v0",
        type=t.uint16_t,
        min_value=0,
        max_value=5000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="soil_fertility_set_v0",
        fallback_name="Soil fertility set v0",
    )
    .tuya_number(
        dp_id=115,
        attribute_name="soil_fertility_set_v1",
        type=t.uint16_t,
        min_value=0,
        max_value=5000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="soil_fertility_set_v1",
        fallback_name="Soil fertility set v1",
    )
    .tuya_enum(
        dp_id=116,
        attribute_name="soil_fertility_warning",
        enum_class=TuyaSoilFertilityWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="soil_fertility_warning",
        fallback_name="Soil fertility warning",
    )
    .skip_configuration()
    .add_to_registry()
)


# Excellux ZG-109TDS Probe Temperature with EC && TDS && Salinity && SG && HT Sensor
# Note: Device IDs (_TZE2...) need to be discovered from actual devices
(
    TuyaQuirkBuilder("DTS1XM9", "Excellux")
    .tuya_temperature(
        dp_id=1,
        scale=10,
    )
    .tuya_battery(dp_id=4)
    .tuya_temperature(dp_id=5, scale=100)
    .tuya_number(
        dp_id=101,
        attribute_name="sampling_interval",
        type=t.uint16_t,
        unit=UnitOfTime.SECONDS,
        min_value=5,
        max_value=1200,
        step=5,
        entity_type=EntityType.CONFIG,
        translation_key="sampling_interval",
        fallback_name="Sampling interval",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="probe_temperature_calibration",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-2,
        max_value=2,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="probe_temperature_calibration",
        fallback_name="Probe temperature calibration",
    )
    .tuya_number(
        dp_id=109,
        attribute_name="probe_temperature_v0_set",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=125,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="probe_temperature_v0_set",
        fallback_name="Probe temperature v0 threshold",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="probe_temperature_v1_set",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=125,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="probe_temperature_v1_set",
        fallback_name="Probe temperature v1 threshold",
    )
    .tuya_enum(
        dp_id=112,
        attribute_name="probe_temperature_warning",
        enum_class=TuyaProbeTempWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="probe_temperature_warning",
        fallback_name="Probe temperature warning",
    )
    .tuya_number(
        dp_id=114,
        attribute_name="temperature_calibration",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-2,
        max_value=2,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_calibration",
        fallback_name="Temperature calibration",
    )
    .tuya_number(
        dp_id=115,
        attribute_name="temperature_v0_set",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=85,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_v0_set",
        fallback_name="Temperature v0 threshold",
    )
    .tuya_number(
        dp_id=116,
        attribute_name="temperature_v1_set",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=85,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_v1_set",
        fallback_name="Temperature v1 threshold",
    )
    .tuya_enum(
        dp_id=117,
        attribute_name="temperature_warning",
        enum_class=TuyaTempWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="temperature_warning",
        fallback_name="Temperature warning",
    )
    .tuya_humidity(
        dp_id=118,
        scale=100,
    )
    .tuya_number(
        dp_id=119,
        attribute_name="humidity_calibration",
        type=t.int16_t,
        unit=PERCENTAGE,
        min_value=-10,
        max_value=10,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_calibration",
        fallback_name="Humidity calibration",
    )
    .tuya_number(
        dp_id=120,
        attribute_name="humidity_v0_set",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_v0_set",
        fallback_name="Humidity v0 threshold",
    )
    .tuya_number(
        dp_id=121,
        attribute_name="humidity_v1_set",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_v1_set",
        fallback_name="Humidity v1 threshold",
    )
    .tuya_enum(
        dp_id=122,
        attribute_name="humidity_warning",
        enum_class=TuyaHumiWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="humidity_warning",
        fallback_name="Humidity warning",
    )
    .tuya_sensor(
        dp_id=124,
        attribute_name="tds",
        type=t.uint16_t,
        entity_type=EntityType.STANDARD,
        device_class=SensorDeviceClass.TDS,
        unit="ppm",
        translation_key="tds",
        fallback_name="TDS",
    )
    .tuya_number(
        dp_id=125,
        attribute_name="tds_warning_set",
        type=t.uint16_t,
        unit="ppm",
        min_value=0,
        max_value=13000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="tds_warning_set",
        fallback_name="TDS warning threshold",
    )
    .tuya_enum(
        dp_id=126,
        attribute_name="tds_warning",
        enum_class=TuyaTdsWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="tds_warning",
        fallback_name="TDS warning",
    )
    .tuya_electrical_conductivity(dp_id=127, scale=1)
    .tuya_number(
        dp_id=128,
        attribute_name="ec_v0_set",
        type=t.uint16_t,
        unit="µS/cm",
        min_value=0,
        max_value=20000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="ec_v0_set",
        fallback_name="EC v0 threshold",
    )
    .tuya_number(
        dp_id=129,
        attribute_name="ec_v1_set",
        type=t.uint16_t,
        unit="µS/cm",
        min_value=0,
        max_value=20000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="ec_v1_set",
        fallback_name="EC v1 threshold",
    )
    .tuya_enum(
        dp_id=130,
        attribute_name="ec_warning",
        enum_class=TuyaEcWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="ec_warning",
        fallback_name="EC warning",
    )
    .tuya_sensor(
        dp_id=131,
        attribute_name="salinity",
        type=t.uint16_t,
        converter=lambda x: x / 10,
        entity_type=EntityType.STANDARD,
        device_class=SensorDeviceClass.SALINITY,
        unit="‰",
        translation_key="salinity",
        fallback_name="Salinity",
    )
    .tuya_sensor(
        dp_id=132,
        attribute_name="sg",
        type=t.uint16_t,
        converter=lambda x: x / 1000,
        entity_type=EntityType.STANDARD,
        device_class=SensorDeviceClass.DENSITY,
        unit="g/cm³",
        translation_key="sg",
        fallback_name="Specific gravity",
    )
    .tuya_enum(
        dp_id=133,
        attribute_name="mode",
        enum_class=TuyaModeWater,
        entity_type=EntityType.CONFIG,
        translation_key="mode",
        fallback_name="Water mode",
    )
    .skip_configuration()
    .add_to_registry()
)


# Excellux ZG-105NTH Temperature and Humidity Sensor with Probe
# White-label: ZG-106NTH (NTCHT02), EZ-L01NTH (NTCHT03)
# Note: Device IDs (_TZE2...) need to be discovered from actual devices
(
    TuyaQuirkBuilder("Excellux", "NTCHT01")
    .applies_to("Excellux", "NTCHT02")
    .applies_to("Excellux", "NTCHT03")
    .tuya_temperature(
        dp_id=1,
        scale=10,
    )
    .tuya_battery(dp_id=4)
    .tuya_temperature(dp_id=5, scale=100)
    .tuya_humidity(dp_id=118, scale=100)
    .tuya_number(
        dp_id=101,
        attribute_name="sampling_interval",
        type=t.uint16_t,
        unit=UnitOfTime.SECONDS,
        min_value=5,
        max_value=1200,
        step=5,
        entity_type=EntityType.CONFIG,
        translation_key="sampling_interval",
        fallback_name="Sampling interval",
    )
    .tuya_number(
        dp_id=108,
        attribute_name="probe_temperature_calibration",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-2,
        max_value=2,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="probe_temperature_calibration",
        fallback_name="Probe temperature calibration",
    )
    .tuya_number(
        dp_id=109,
        attribute_name="probe_temperature_v0_set",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=125,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="probe_temperature_v0_set",
        fallback_name="Probe temperature v0 threshold",
    )
    .tuya_number(
        dp_id=110,
        attribute_name="probe_temperature_v1_set",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=125,
        step=0.1,
        multiplier=0.1,
        entity_type=EntityType.CONFIG,
        translation_key="probe_temperature_v1_set",
        fallback_name="Probe temperature v1 threshold",
    )
    .tuya_enum(
        dp_id=112,
        attribute_name="probe_temperature_warning",
        enum_class=TuyaProbeTempWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="probe_temperature_warning",
        fallback_name="Probe temperature warning",
    )
    .tuya_number(
        dp_id=114,
        attribute_name="temperature_calibration",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-2,
        max_value=2,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_calibration",
        fallback_name="Temperature calibration",
    )
    .tuya_number(
        dp_id=115,
        attribute_name="temperature_v0_set",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=85,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_v0_set",
        fallback_name="Temperature v0 threshold",
    )
    .tuya_number(
        dp_id=116,
        attribute_name="temperature_v1_set",
        type=t.int16_t,
        unit=UnitOfTemperature.CELSIUS,
        min_value=-40,
        max_value=85,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="temperature_v1_set",
        fallback_name="Temperature v1 threshold",
    )
    .tuya_enum(
        dp_id=117,
        attribute_name="temperature_warning",
        enum_class=TuyaTempWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="temperature_warning",
        fallback_name="Temperature warning",
    )
    .tuya_number(
        dp_id=119,
        attribute_name="humidity_calibration",
        type=t.int16_t,
        unit=PERCENTAGE,
        min_value=-10,
        max_value=10,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_calibration",
        fallback_name="Humidity calibration",
    )
    .tuya_number(
        dp_id=120,
        attribute_name="humidity_v0_set",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_v0_set",
        fallback_name="Humidity v0 threshold",
    )
    .tuya_number(
        dp_id=121,
        attribute_name="humidity_v1_set",
        type=t.uint16_t,
        unit=PERCENTAGE,
        min_value=0,
        max_value=100,
        step=0.01,
        multiplier=0.01,
        entity_type=EntityType.CONFIG,
        translation_key="humidity_v1_set",
        fallback_name="Humidity v1 threshold",
    )
    .tuya_enum(
        dp_id=122,
        attribute_name="humidity_warning",
        enum_class=TuyaHumiWarning,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="humidity_warning",
        fallback_name="Humidity warning",
    )
    .skip_configuration()
    .add_to_registry()
)


# Excellux ZG-104PLV PIR Motion Sensor, Vibration Sensor, and Light Sensor
(
    TuyaQuirkBuilder("Excellux", "PIRIV01")
    .tuya_binary_sensor(
        dp_id=1,
        attribute_name="occupancy",
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.MOTION,
        translation_key="occupancy",
        fallback_name="Occupancy",
    )
    .tuya_battery(dp_id=4)
    .tuya_binary_sensor(
        dp_id=3,
        attribute_name="vibration",
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.VIBRATION,
        translation_key="vibration",
        fallback_name="Vibration",
    )
    .tuya_number(
        dp_id=6,
        attribute_name="vibration_sensitivity",
        type=t.uint16_t,
        min_value=0,
        max_value=50,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="vibration_sensitivity",
        fallback_name="Vibration sensitivity",
    )
    .tuya_illuminance(dp_id=20)
    .tuya_sensor(
        dp_id=50,
        attribute_name="vibration_count",
        type=t.uint16_t,
        entity_type=EntityType.DIAGNOSTIC,
        device_class=SensorDeviceClass.ENERGY,
        state_class=SensorStateClass.TOTAL_INCREASING,
        translation_key="vibration_count",
        fallback_name="Vibration count",
    )
    .tuya_number(
        dp_id=101,
        attribute_name="sampling_interval",
        type=t.uint16_t,
        unit=UnitOfTime.SECONDS,
        min_value=5,
        max_value=1200,
        step=5,
        entity_type=EntityType.CONFIG,
        translation_key="sampling_interval",
        fallback_name="Sampling interval",
    )
    .tuya_number(
        dp_id=104,
        attribute_name="illuminance_v0",
        type=t.uint16_t,
        unit="lux",
        min_value=0,
        max_value=10000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="illuminance_v0",
        fallback_name="Illuminance v0 threshold",
    )
    .tuya_number(
        dp_id=105,
        attribute_name="illuminance_v1",
        type=t.uint16_t,
        unit="lux",
        min_value=0,
        max_value=10000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="illuminance_v1",
        fallback_name="Illuminance v1 threshold",
    )
    .tuya_number(
        dp_id=106,
        attribute_name="illuminance_calibration",
        type=t.int16_t,
        unit="lux",
        min_value=-1000,
        max_value=1000,
        step=1,
        entity_type=EntityType.CONFIG,
        translation_key="illuminance_calibration",
        fallback_name="Illuminance calibration",
    )
    .tuya_enum(
        dp_id=107,
        attribute_name="illuminance_warning",
        enum_class=TuyaSoilLightLevel,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="illuminance_warning",
        fallback_name="Illuminance warning",
    )
    .skip_configuration()
    .add_to_registry()
)
