"""Namron 4512783 floor heating thermostat quirk."""

from typing import Final

import zigpy.types as t
from zigpy.zcl.clusters.hvac import TemperatureDisplayMode, Thermostat, UserInterface
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.builder import (
    PERCENTAGE,
    BinarySensorDeviceClass,
    EntityType,
    QuirkBuilder,
    UnitOfTemperature,
    UnitOfTime,
)
from zhaquirks.clusters import CustomCluster


class NamronSensorMode(t.enum8):
    """Namron thermostat sensor and regulator mode."""

    Internal_air_sensor = 0x00
    Floor_sensor = 0x01
    Internal_air_with_floor_limit = 0x02
    External_room_sensor = 0x03
    External_room_with_floor_limit = 0x04
    Floor_sensor_with_regulator = 0x05
    Regulator = 0x06


class NamronWorkDays(t.enum8):
    """Namron thermostat weekly schedule type."""

    Monday_Friday_Saturday_Sunday = 0x00
    Monday_Saturday_Sunday = 0x01
    No_time_off = 0x02
    Time_off = 0x03


class NamronScreenOnTime(t.enum8):
    """Namron thermostat screen-on duration."""

    Always_on = 0x00
    Ten_seconds = 0x01
    Thirty_seconds = 0x02
    Sixty_seconds = 0x03


class NamronThermostatCluster(CustomCluster, Thermostat):
    """Thermostat cluster with Namron private attributes."""

    class AttributeDefs(Thermostat.AttributeDefs):
        """Namron thermostat attribute definitions."""

        window_open_check: Final = ZCLAttributeDef(
            id=0x8000,
            type=t.Bool,
            access="rwp",
            manufacturer_code=None,
        )
        anti_frost: Final = ZCLAttributeDef(
            id=0x8001,
            type=t.Bool,
            access="rwp",
            manufacturer_code=None,
        )
        window_state: Final = ZCLAttributeDef(
            id=0x8002,
            type=t.Bool,
            access="rwp",
            manufacturer_code=None,
        )
        work_days: Final = ZCLAttributeDef(
            id=0x8003,
            type=NamronWorkDays,
            access="rwp",
            manufacturer_code=None,
        )
        sensor_mode: Final = ZCLAttributeDef(
            id=0x8004,
            type=NamronSensorMode,
            access="rwp",
            manufacturer_code=None,
        )
        panel_brightness: Final = ZCLAttributeDef(
            id=0x8005,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=None,
        )
        fault: Final = ZCLAttributeDef(
            id=0x8006,
            type=t.bitmap8,
            access="rp",
            manufacturer_code=None,
        )
        regulator_cycle: Final = ZCLAttributeDef(
            id=0x8007,
            type=t.uint8_t,
            access="rwp",
            manufacturer_code=None,
        )
        holiday_temperature: Final = ZCLAttributeDef(
            id=0x8013,
            type=t.int16s,
            access="rwp",
            manufacturer_code=None,
        )
        regulator_percentage: Final = ZCLAttributeDef(
            id=0x801D,
            type=t.int16s,
            access="rwp",
            manufacturer_code=None,
        )
        vacation_mode: Final = ZCLAttributeDef(
            id=0x801F,
            type=t.Bool,
            access="rwp",
            manufacturer_code=None,
        )
        automatic_time: Final = ZCLAttributeDef(
            id=0x8022,
            type=t.Bool,
            access="rwp",
            manufacturer_code=None,
        )
        max_heat_temperature: Final = ZCLAttributeDef(
            id=0x8025,
            type=t.int16s,
            access="rwp",
            manufacturer_code=None,
        )
        screen_on_time: Final = ZCLAttributeDef(
            id=0x8029,
            type=NamronScreenOnTime,
            access="rwp",
            manufacturer_code=None,
        )


(
    QuirkBuilder("Namron AS", "4512783")
    .replaces(NamronThermostatCluster)
    # The thermostat does not reliably report these attributes, so read them at startup.
    .switch(
        attribute_name=NamronThermostatCluster.AttributeDefs.window_open_check.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="window_open_detection",
        fallback_name="Window-open detection",
    )
    .switch(
        attribute_name=NamronThermostatCluster.AttributeDefs.anti_frost.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="anti_frost",
        fallback_name="Anti-frost",
    )
    .binary_sensor(
        attribute_name=NamronThermostatCluster.AttributeDefs.window_state.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        device_class=BinarySensorDeviceClass.WINDOW,
        attribute_initialized_from_cache=False,
        fallback_name="Window state",
    )
    .enum(
        attribute_name=NamronThermostatCluster.AttributeDefs.work_days.name,
        enum_class=NamronWorkDays,
        cluster_id=NamronThermostatCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="work_days",
        fallback_name="Schedule type",
    )
    .enum(
        attribute_name=NamronThermostatCluster.AttributeDefs.sensor_mode.name,
        enum_class=NamronSensorMode,
        cluster_id=NamronThermostatCluster.cluster_id,
        attribute_initialized_from_cache=False,
        unique_id_suffix="operation_mode",
        translation_key="sensor_mode",
        fallback_name="Sensor mode",
    )
    .number(
        attribute_name=NamronThermostatCluster.AttributeDefs.panel_brightness.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        min_value=1,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        attribute_initialized_from_cache=False,
        translation_key="panel_brightness",
        fallback_name="Panel brightness",
    )
    .sensor(
        attribute_name=NamronThermostatCluster.AttributeDefs.fault.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        entity_type=EntityType.DIAGNOSTIC,
        attribute_initialized_from_cache=False,
        translation_key="fault",
        fallback_name="Fault flags",
    )
    # Zero is the device's default sentinel, not a zero-minute cycle.
    .number(
        attribute_name=NamronThermostatCluster.AttributeDefs.regulator_cycle.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        min_value=1,
        max_value=30,
        step=1,
        unit=UnitOfTime.MINUTES,
        attribute_initialized_from_cache=False,
        translation_key="regulator_cycle",
        fallback_name="Regulator cycle",
    )
    .number(
        attribute_name=NamronThermostatCluster.AttributeDefs.holiday_temperature.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        min_value=5,
        max_value=35,
        step=0.5,
        multiplier=0.01,
        unit=UnitOfTemperature.CELSIUS,
        attribute_initialized_from_cache=False,
        translation_key="holiday_temperature",
        fallback_name="Holiday temperature",
    )
    .number(
        attribute_name=NamronThermostatCluster.AttributeDefs.regulator_percentage.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        min_value=0,
        max_value=100,
        step=1,
        unit=PERCENTAGE,
        attribute_initialized_from_cache=False,
        translation_key="regulator_percentage",
        fallback_name="Regulator percentage",
    )
    .binary_sensor(
        attribute_name=NamronThermostatCluster.AttributeDefs.vacation_mode.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        entity_type=EntityType.STANDARD,
        attribute_initialized_from_cache=False,
        translation_key="vacation_mode",
        fallback_name="Vacation mode",
    )
    .switch(
        attribute_name=NamronThermostatCluster.AttributeDefs.automatic_time.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="automatic_time",
        fallback_name="Automatic time",
    )
    .number(
        attribute_name=NamronThermostatCluster.AttributeDefs.max_heat_temperature.name,
        cluster_id=NamronThermostatCluster.cluster_id,
        min_value=15,
        max_value=35,
        step=0.5,
        multiplier=0.1,
        unit=UnitOfTemperature.CELSIUS,
        attribute_initialized_from_cache=False,
        translation_key="max_heat_temperature",
        fallback_name="Maximum heat temperature",
    )
    .enum(
        attribute_name=NamronThermostatCluster.AttributeDefs.screen_on_time.name,
        enum_class=NamronScreenOnTime,
        cluster_id=NamronThermostatCluster.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="screen_on_time",
        fallback_name="Screen-on time",
    )
    .enum(
        attribute_name=UserInterface.AttributeDefs.temperature_display_mode.name,
        enum_class=TemperatureDisplayMode,
        cluster_id=UserInterface.cluster_id,
        attribute_initialized_from_cache=False,
        translation_key="temperature_display_mode",
        fallback_name="Temperature display mode",
    )
    .add_to_registry()
)
