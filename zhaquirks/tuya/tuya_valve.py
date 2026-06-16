"""Collection of Tuya Valve devices e.g. water valves, gas valve etc."""

from datetime import datetime, timedelta, timezone

from zigpy.quirks.v2 import BinarySensorDeviceClass, EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant import (
    PERCENTAGE,
    UnitOfElectricPotential,
    UnitOfTime,
    UnitOfVolume,
)
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import BatterySize
from zhaquirks.tuya import TUYA_CLUSTER_ID, TUYA_SEND_DATA
from zhaquirks.tuya.builder import TuyaQuirkBuilder, TuyaValveWaterConsumed
from zhaquirks.tuya.mcu import TuyaMCUCluster


class TuyaValveWeatherDelay(t.enum8):
    """Tuya Irrigation Valve weather delay enum."""

    Disabled = 0x00
    Delayed_24h = 0x01
    Delayed_48h = 0x02
    Delayed_72h = 0x03


class TuyaValveWeatherDelayVar02(t.enum8):
    """Tuya Irrigation Valve weather delay enum var 02.

    Disabled is 0x03
    """

    Delayed_24h = 0x00
    Delayed_48h = 0x01
    Delayed_72h = 0x02
    Disabled = 0x03


class TuyaValveTimerState(t.enum8):
    """Tuya Irrigation Valve timer state enum."""

    Disabled = 0x00
    Active = 0x01
    Enabled = 0x02


class TuyaValveStatus(t.enum8):
    """Tuya Irrigation Valve status enum."""

    Off = 0x00
    Auto = 0x01
    Disabled = 0x02


(
    TuyaQuirkBuilder("_TZE200_81isopgh", "TS0601")
    .applies_to("_TZE200_1n2zev06", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_metering(
        dp_id=5, scale=0.0295735
    )  # per z2m reports in fl oz, convert to liters
    .tuya_dp_attribute(
        dp_id=6,
        attribute_name="dp_6",
        type=t.uint32_t,
    )
    .tuya_battery(dp_id=7, battery_type=BatterySize.AA, battery_qty=4)
    .tuya_enum(
        dp_id=10,
        attribute_name="weather_delay",
        enum_class=TuyaValveWeatherDelay,
        translation_key="weather_delay",
        fallback_name="Weather delay",
        initially_disabled=True,
    )
    .tuya_sensor(
        dp_id=11,
        attribute_name="time_left",
        type=t.uint32_t,
        converter=lambda x: x / 60,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        translation_key="time_left",
        fallback_name="Time left",
    )
    .tuya_enum(
        dp_id=12,
        attribute_name="timer_state",
        enum_class=TuyaValveTimerState,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="timer_state",
        fallback_name="Timer state",
    )
    .tuya_sensor(
        dp_id=15,
        attribute_name="last_valve_open_duration",
        type=t.uint32_t,
        divisor=60,
        entity_type=EntityType.DIAGNOSTIC,
        unit=UnitOfTime.MINUTES,
        translation_key="last_valve_open_duration",
        fallback_name="Last valve open duration",
    )
    .tuya_dp_attribute(
        dp_id=102,
        attribute_name="valve_position",
        type=t.uint32_t,
    )
    .skip_configuration()
    .add_to_registry()
)


class ParksideTuyaValveManufCluster(TuyaMCUCluster):
    """Manufacturer Specific Cluster for the _TZE200_htnnfasr water valve sold as PARKSIDE."""

    async def bind(self):
        """Bind cluster.

        When adding this device tuya gateway issues factory reset,
        we just need to reset the frost lock, because its state is unknown to us.
        """
        result = await super().bind()
        await self.write_attributes({self.attributes_by_name["frost_lock_reset"].id: 0})
        return result


(
    TuyaQuirkBuilder(
        "_TZE200_htnnfasr", "TS0601"
    )  # HG06875, Lidl - Parkside smart watering timer
    .tuya_onoff(dp_id=1)
    .tuya_number(
        dp_id=5,
        attribute_name="timer_duration",
        type=t.uint32_t,
        min_value=1,
        max_value=599,
        step=1,
        unit=UnitOfTime.MINUTES,
        translation_key="timer_duration",
        fallback_name="Timer duration",
    )
    .tuya_sensor(
        dp_id=6,
        attribute_name="time_left",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        translation_key="time_left",
        fallback_name="Time left",
    )
    .tuya_battery(dp_id=11, battery_type=BatterySize.AA, battery_qty=4)
    .tuya_switch(
        dp_id=108,
        attribute_name="frost_lock",
        entity_type=EntityType.STANDARD,
        on_value=0,  # Invert
        off_value=1,
        translation_key="frost_lock",
        fallback_name="Frost lock",
    )
    .tuya_dp_attribute(
        dp_id=109,
        attribute_name="frost_lock_reset",
        type=t.Bool,
    )
    .write_attr_button(
        attribute_name="frost_lock_reset",
        cluster_id=TUYA_CLUSTER_ID,
        attribute_value=0x00,  # 0 resets frost lock
        translation_key="frost_lock_reset",
        fallback_name="Frost lock reset",
    )
    .skip_configuration()
    .add_to_registry(replacement_cluster=ParksideTuyaValveManufCluster)
)


GIEX_12HRS_AS_SEC = 43200
GIEX_24HRS_AS_MIN = 1440
UNIX_EPOCH_TO_ZCL_EPOCH = 946684800


class GiexIrrigationMode(t.enum8):
    """Giex Irrigation Mode Enum."""

    Duration = 0x00
    Capacity = 0x01


class GiexIrrigationWeatherDelay(t.enum8):
    """Giex Irrigation Weather Delay Enum."""

    NoDelay = 0x00
    TwentyFourHourDelay = 0x01
    FortyEightHourDelay = 0x02
    SeventyTwoHourDelay = 0x03


def giex_string_to_td(v: str) -> int:
    """Convert Giex String Duration to seconds."""
    dt = datetime.strptime(v, "%H:%M:%S,%f")
    return timedelta(hours=dt.hour, minutes=dt.minute, seconds=dt.second).seconds


def giex_string_to_dt(v: str) -> datetime | None:
    """Convert Giex String Duration datetime."""
    dev_tz = timezone(timedelta(hours=4))
    dev_dt = datetime.now(dev_tz)

    try:
        dt = datetime.strptime(v, "%H:%M:%S").replace(tzinfo=dev_tz)
    except ValueError:
        return None  # on initial start the device will return '--:--:--'
    else:
        return dev_dt.replace(hour=dt.hour, minute=dt.minute, second=dt.second)


gx02_base_quirk = (
    TuyaQuirkBuilder()
    .tuya_battery(dp_id=108, battery_type=BatterySize.AA, battery_qty=4)
    .tuya_metering(dp_id=111)
    .tuya_onoff(dp_id=2)
    .tuya_number(
        dp_id=103,
        attribute_name="irrigation_cycles",
        type=t.uint8_t,
        min_value=0,
        max_value=100,
        step=1,
        translation_key="irrigation_cycles",
        fallback_name="Irrigation cycles",
    )
    .tuya_dp_attribute(
        dp_id=1,
        attribute_name="irrigation_mode",
        type=t.Bool,
    )
    .enum(
        attribute_name="irrigation_mode",
        cluster_id=TUYA_CLUSTER_ID,
        enum_class=GiexIrrigationMode,
        translation_key="irrigation_mode",
        fallback_name="Irrigation mode",
    )
    .tuya_enum(
        dp_id=107,
        attribute_name="weather_delay",
        enum_class=GiexIrrigationWeatherDelay,
        translation_key="weather_delay",
        fallback_name="Weather delay",
        initially_disabled=True,
    )
    .tuya_sensor(
        dp_id=114,
        attribute_name="irrigation_duration",
        type=t.uint32_t,
        converter=lambda x: giex_string_to_td(x),
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        translation_key="irrigation_duration",
        fallback_name="Irrigation duration",
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="irrigation_start_time",
        type=t.CharacterString,
        converter=lambda x: giex_string_to_dt(x),
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key="irrigation_start_time",
        fallback_name="Irrigation start time",
    )
    .tuya_sensor(
        dp_id=102,
        attribute_name="irrigation_end_time",
        type=t.CharacterString,
        converter=lambda x: giex_string_to_dt(x),
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key="irrigation_end_time",
        fallback_name="Irrigation end time",
    )
    .skip_configuration()
)


(
    gx02_base_quirk.clone()
    .applies_to("_TZE200_sh1btabb", "TS0601")
    .tuya_number(
        dp_id=104,
        attribute_name="irrigation_target",
        type=t.uint32_t,
        min_value=0,
        max_value=GIEX_24HRS_AS_MIN,
        step=1,
        translation_key="irrigation_target",
        fallback_name="Irrigation target",
    )
    .tuya_number(
        dp_id=105,
        attribute_name="irrigation_interval",
        min_value=0,
        type=t.uint32_t,
        max_value=GIEX_24HRS_AS_MIN,
        step=1,
        unit=UnitOfTime.MINUTES,
        translation_key="irrigation_interval",
        fallback_name="Irrigation interval",
    )
    .add_to_registry()
)


(
    gx02_base_quirk.clone()
    .applies_to("_TZE200_a7sghmms", "TS0601")
    .applies_to("_TZE204_a7sghmms", "TS0601")
    .applies_to("_TZE200_7ytb3h8u", "TS0601")  # Giex GX02 Var 1
    .applies_to("_TZE204_7ytb3h8u", "TS0601")  # Giex GX02 Var 1
    .applies_to("_TZE284_7ytb3h8u", "TS0601")  # Giex GX02 Var 3
    .tuya_number(
        dp_id=104,
        attribute_name="irrigation_target",
        type=t.uint32_t,
        min_value=0,
        max_value=GIEX_12HRS_AS_SEC,
        step=1,
        translation_key="irrigation_target",
        fallback_name="Irrigation target",
    )
    .tuya_number(
        dp_id=105,
        attribute_name="irrigation_interval",
        type=t.uint32_t,
        min_value=0,
        max_value=GIEX_12HRS_AS_SEC,
        step=1,
        unit=UnitOfTime.SECONDS,
        translation_key="irrigation_interval",
        fallback_name="Irrigation interval",
    )
    .add_to_registry()
)


class GiexIrrigationStatus(t.enum8):
    """Giex Irrigation Status Enum."""

    Manual = 0x00
    Auto = 0x01
    Idle = 0x02


(
    TuyaQuirkBuilder("_TZE284_8zizsafo", "TS0601")  # Giex GX04
    .applies_to("_TZE284_iilebqoo", "TS0601")  # NovaDigital ZVL_DUAL
    .applies_to("_TZE284_eaet5qt5", "TS0601")  # Insoma SGW08W
    .applies_to("_TZE284_fhvpaltk", "TS0601")  # SGW08
    .tuya_battery(dp_id=59, battery_type=BatterySize.AA, battery_qty=4)
    .tuya_switch(
        dp_id=1,
        attribute_name="valve_on_off_1",
        entity_type=EntityType.STANDARD,
        translation_key="valve_on_off_1",
        fallback_name="Valve 1",
    )
    .tuya_switch(
        dp_id=2,
        attribute_name="valve_on_off_2",
        entity_type=EntityType.STANDARD,
        translation_key="valve_on_off_2",
        fallback_name="Valve 2",
    )
    .tuya_number(
        dp_id=13,
        attribute_name="valve_countdown_1",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        min_value=0,
        max_value=1440,
        step=1,
        translation_key="valve_countdown_1",
        fallback_name="Irrigation time 1",
    )
    .tuya_number(
        dp_id=14,
        attribute_name="valve_countdown_2",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        min_value=0,
        max_value=1440,
        step=1,
        translation_key="valve_countdown_2",
        fallback_name="Irrigation time 2",
    )
    .tuya_sensor(
        dp_id=25,
        attribute_name="valve_duration_1",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_type=EntityType.STANDARD,
        translation_key="irrigation_duration_1",
        fallback_name="Irrigation duration 1",
    )
    .tuya_sensor(
        dp_id=26,
        attribute_name="valve_duration_2",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        entity_type=EntityType.STANDARD,
        translation_key="irriation_duration_2",
        fallback_name="Irrigation duration 2",
    )
    .tuya_enum(
        dp_id=104,
        attribute_name="valve_status_1",
        enum_class=GiexIrrigationStatus,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="valve_status_1",
        fallback_name="Status 1",
    )
    .tuya_enum(
        dp_id=105,
        attribute_name="valve_status_2",
        enum_class=GiexIrrigationStatus,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.STANDARD,
        translation_key="valve_status_2",
        fallback_name="Status 2",
    )
    .skip_configuration()
    .add_to_registry()
)


(
    TuyaQuirkBuilder("_TZE200_2wg5qrjy", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_battery(dp_id=7, battery_type=BatterySize.AA, battery_qty=2)
    # Water consumed (value comes in deciliters - convert it to liters)
    .tuya_metering(dp_id=5, scale=0.1)
    # Timer time left/remaining (raw value in seconds)
    .tuya_number(
        dp_id=11,
        attribute_name="timer_time_left",
        type=t.uint32_t,
        min_value=1,
        max_value=600,
        step=1,
        multiplier=1 / 60,
        unit=UnitOfTime.MINUTES,
        translation_key="timer_time_left",
        fallback_name="Timer time left",
    )
    # Weather delay
    .tuya_enum(
        dp_id=10,
        attribute_name="weather_delay",
        enum_class=TuyaValveWeatherDelay,
        translation_key="weather_delay",
        fallback_name="Weather delay",
        initially_disabled=True,
    )
    # Timer state - read-only
    .tuya_enum(
        dp_id=12,
        attribute_name="timer_state",
        enum_class=TuyaValveTimerState,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="timer_state",
        fallback_name="Timer state",
    )
    # Last valve open duration - read-only (raw value in seconds)
    .tuya_sensor(
        dp_id=15,
        attribute_name="last_valve_open_duration",
        type=t.uint32_t,
        divisor=60,
        entity_type=EntityType.DIAGNOSTIC,
        unit=UnitOfTime.MINUTES,
        translation_key="last_valve_open_duration",
        fallback_name="Last valve open duration",
    )
    .add_to_registry()
)


# NEO NAS-WV03B
(
    TuyaQuirkBuilder("_TZE204_rzrrjkz2", "TS0601")
    .applies_to("_TZE204_uab532m0", "TS0601")
    .applies_to("_TZE204_z7a2jmyy", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_enum(
        dp_id=3,
        attribute_name="valve_status",
        enum_class=TuyaValveStatus,
        entity_type=EntityType.STANDARD,
        entity_platform=EntityPlatform.SENSOR,
        translation_key="valve_status",
        fallback_name="Valve status",
    )
    .tuya_number(
        dp_id=5,
        attribute_name="valve_countdown",
        type=t.uint16_t,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        min_value=1,
        max_value=240,
        step=1,
        translation_key="valve_countdown",
        fallback_name="Irrigation time",
    )
    .tuya_sensor(
        dp_id=6,
        attribute_name="valve_duration",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.MINUTES,
        entity_type=EntityType.STANDARD,
        translation_key="valve_duration",
        fallback_name="Irrigation duration",
    )
    .tuya_dp(
        dp_id=9,
        ep_attribute=TuyaValveWaterConsumed.ep_attribute,
        attribute_name=Metering.AttributeDefs.instantaneous_demand.name,
    )
    .tuya_metering(dp_id=15, metering_cfg=TuyaValveWaterConsumed)
    .tuya_battery(dp_id=11, battery_type=BatterySize.AA, battery_qty=2)
    .tuya_binary_sensor(
        dp_id=19,
        attribute_name="valve_alarm",
        device_class=BinarySensorDeviceClass.PROBLEM,
        translation_key="valve_alarm",
        fallback_name="Valve alarm",
    )
    .tuya_enum(
        dp_id=37,
        attribute_name="weather_delay",
        enum_class=TuyaValveWeatherDelayVar02,
        translation_key="weather_delay",
        fallback_name="Weather delay",
        initially_disabled=True,
    )
    .tuya_dp_attribute(
        dp_id=38,
        attribute_name="normal_timer",
        type=t.CharacterString,
    )
    .tuya_switch(
        dp_id=42,
        attribute_name="switch_enabled",
        entity_type=EntityType.STANDARD,
        translation_key="switch_enabled",
        fallback_name="Switch enabled",
    )
    .tuya_sensor(
        dp_id=47,
        attribute_name="smart_irrigation",
        type=t.uint16_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="smart_irrigation",
        fallback_name="Smart irrigation",
    )
    .tuya_switch(
        dp_id=101,
        attribute_name="total_flow_reset_switch",
        entity_type=EntityType.STANDARD,
        translation_key="total_flow_reset_switch",
        fallback_name="Total flow reset switch",
    )
    .tuya_number(
        dp_id=102,
        attribute_name="quantitative_watering",
        type=t.uint16_t,
        unit=UnitOfVolume.LITERS,
        device_class=SensorDeviceClass.VOLUME,
        min_value=0,
        max_value=10000,
        step=1,
        translation_key="quantitative_watering",
        fallback_name="Quantitative watering",
    )
    .tuya_binary_sensor(
        dp_id=103,
        attribute_name="flow_switch",
        entity_type=EntityType.STANDARD,
        translation_key="flow_switch",
        fallback_name="Flow switch",
    )
    .tuya_switch(
        dp_id=104,
        attribute_name="child_lock",
        translation_key="child_lock",
        fallback_name="Child lock",
    )
    .tuya_sensor(
        dp_id=105,
        attribute_name="surplus_flow",
        type=t.uint16_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="surplus_flow",
        fallback_name="Surplus flow",
    )
    .tuya_sensor(
        dp_id=106,
        attribute_name="single_watering_duration",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.DURATION,
        unit=UnitOfTime.SECONDS,
        translation_key="single_watering_duration",
        fallback_name="Single watering duration",
    )
    .tuya_sensor(
        dp_id=108,
        attribute_name="single_watering_amount",
        type=t.uint32_t,
        state_class=SensorStateClass.MEASUREMENT,
        device_class=SensorDeviceClass.VOLUME,
        unit=UnitOfVolume.LITERS,
        translation_key="single_watering_amount",
        fallback_name="Single watering amount",
    )
    .skip_configuration()
    .add_to_registry()
)


# Tuya Rain Seer Valve
(
    TuyaQuirkBuilder("_TZ3210_0jxeoadc", "TS0049")
    .tuya_sensor(
        dp_id=26,
        attribute_name="error_status",
        type=t.uint32_t,
        entity_type=EntityType.DIAGNOSTIC,
        translation_key="error_status",
        fallback_name="Error status",
    )
    .tuya_onoff(dp_id=101)
    .tuya_number(
        dp_id=111,
        attribute_name="valve_duration",
        type=t.uint32_t,
        min_value=0,
        max_value=255,
        step=1,
        unit=UnitOfTime.MINUTES,
        translation_key="valve_duration",
        fallback_name="Irrigation duration",
    )
    .tuya_battery(dp_id=115, battery_type=BatterySize.AA, battery_qty=2)
    .tuya_enchantment()
    .skip_configuration()
    .add_to_registry(mcu_write_command=TUYA_SEND_DATA)
)


# Tuya 214C Ultrasonic water meter valve
(
    TuyaQuirkBuilder("_TZE200_zlwr0raf", "TS0601")
    .tuya_metering(dp_id=1, metering_cfg=TuyaValveWaterConsumed)
    # Skipped DP 2,3,4,5,6,16,18
    .tuya_onoff(dp_id=13)
    .tuya_switch(
        dp_id=14,
        attribute_name="auto_clean",
        entity_type=EntityType.CONFIG,
        translation_key="auto_clean",
        fallback_name="Autoclean",
    )
    .tuya_dp(
        dp_id=21,
        ep_attribute=TuyaValveWaterConsumed.ep_attribute,
        attribute_name=Metering.AttributeDefs.instantaneous_demand.name,
    )
    .tuya_temperature(dp_id=22)
    .tuya_sensor(
        dp_id=26,
        attribute_name="voltage",
        type=t.uint16_t,
        converter=lambda x: x * 100,
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        unit=UnitOfElectricPotential.VOLT,
        entity_type=EntityType.STANDARD,
        fallback_name="Voltage",
    )
    .skip_configuration()
    .add_to_registry()
)

# Tuya Solar Valve
(
    TuyaQuirkBuilder("_TZE200_arge1ptm", "TS0601")
    .applies_to("_TZE200_anv5ujhv", "TS0601")
    .applies_to("_TZE200_xlppj4f5", "TS0601")
    .tuya_number(
        dp_id=2,
        attribute_name="valve_state_auto_shutdown",
        type=t.uint32_t,
        min_value=0,
        max_value=100,
        step=5,
        unit=PERCENTAGE,
        translation_key="valve_state_auto_shutdown",
        fallback_name="Valve state auto-shutdown",
    )
    .tuya_sensor(
        dp_id=3,
        attribute_name="water_flow",
        type=t.uint32_t,
        unit=PERCENTAGE,
        translation_key="water_flow",
        fallback_name="Water flow",
    )
    .tuya_number(
        dp_id=11,
        attribute_name="shutdown_timer",
        type=t.uint32_t,
        min_value=0,
        max_value=14400,
        step=5,
        unit=UnitOfTime.SECONDS,
        translation_key="shutdown_timer",
        fallback_name="Shutdown timer",
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="remaining_watering_time",
        type=t.uint32_t,
        unit=UnitOfTime.SECONDS,
        translation_key="remaining_watering_time",
        fallback_name="Remaining watering time",
    )
    .tuya_sensor(
        dp_id=107,
        attribute_name="last_watering_duration",
        type=t.uint32_t,
        unit=UnitOfTime.SECONDS,
        translation_key="last_watering_duration",
        fallback_name="Last watering duration",
    )
    .tuya_battery(dp_id=110, battery_type=BatterySize.AA, battery_qty=2)
    .tuya_enchantment()
    .skip_configuration()
    .add_to_registry()
)
