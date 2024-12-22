"""Collection of Tuya Valve devices e.g. water valves, gas valve etc."""

from datetime import datetime, timedelta, timezone

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import EntityPlatform, EntityType
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Groups, Identify, OnOff, Ota, Scenes, Time
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks import DoublingPowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    TUYA_CLUSTER_ID,
    EnchantedDevice,
    TuyaLocalCluster,
    TuyaPowerConfigurationCluster2AA,
    TuyaPowerConfigurationCluster4AA,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaMCUCluster,
    TuyaOnOff,
    TuyaPowerConfigurationCluster,
)


class TuyaValveWaterConsumed(Metering, TuyaLocalCluster):
    """Tuya Valve Water consumed cluster."""

    VOLUME_LITERS = 0x0007
    WATER_METERING = 0x02

    """Setting unit of measurement."""
    _CONSTANT_ATTRIBUTES = {
        0x0300: VOLUME_LITERS,
        0x0306: WATER_METERING,
    }


class TuyaValveManufCluster(TuyaMCUCluster):
    """On/Off Tuya cluster with extra device attributes."""

    class AttributeDefs(TuyaMCUCluster.AttributeDefs):
        """Attribute Definitions."""

        time_left = foundation.ZCLAttributeDef(
            id=0xEF01, type=t.uint32_t, is_manufacturer_specific=True
        )
        state = foundation.ZCLAttributeDef(
            id=0xEF02, type=t.enum8, is_manufacturer_specific=True
        )
        last_valve_open_duration = foundation.ZCLAttributeDef(
            id=0xEF03, type=t.uint32_t, is_manufacturer_specific=True
        )
        dp_6 = foundation.ZCLAttributeDef(
            id=0xEF04, type=t.uint32_t, is_manufacturer_specific=True
        )
        valve_position = foundation.ZCLAttributeDef(
            id=0xEF05, type=t.uint32_t, is_manufacturer_specific=True
        )

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
        ),
        5: DPToAttributeMapping(
            TuyaValveWaterConsumed.ep_attribute,
            "current_summ_delivered",
        ),
        6: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_6",
        ),
        7: DPToAttributeMapping(
            DoublingPowerConfigurationCluster.ep_attribute,
            "battery_percentage_remaining",
        ),
        11: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "time_left",
        ),
        12: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "state",
        ),
        15: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "last_valve_open_duration",
        ),
        102: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "valve_position",
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        6: "_dp_2_attr_update",
        7: "_dp_2_attr_update",
        11: "_dp_2_attr_update",
        12: "_dp_2_attr_update",
        15: "_dp_2_attr_update",
        102: "_dp_2_attr_update",
    }


class TuyaValve(CustomDevice):
    """Tuya valve device."""

    signature = {
        MODELS_INFO: [("_TZE200_81isopgh", "TS0601")],
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=81, device_version=1,
        # input_clusters=[0, 4, 5, 61184], output_clusters=[25, 10])
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaValveManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOff,
                    TuyaValveWaterConsumed,
                    DoublingPowerConfigurationCluster,
                    TuyaValveManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class BasicTuyaValve(CustomDevice):
    """Basic Tuya valve device."""

    signature = {
        MODELS_INFO: [("_TZE200_1n2zev06", "TS0601")],
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=81, device_version=1,
        # input_clusters=[0, 4, 5, 61184], output_clusters=[25, 10])
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaValveManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOff,
                    TuyaValveManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class ParksideTuyaValveManufCluster(TuyaMCUCluster):
    """Manufacturer Specific Cluster for the _TZE200_htnnfasr water valve sold as PARKSIDE."""

    class AttributeDefs(TuyaMCUCluster.AttributeDefs):
        """Attribute Definitions."""

        timer_duration = foundation.ZCLAttributeDef(
            id=0xEF11, type=t.uint32_t, is_manufacturer_specific=True
        )
        timer_time_left = foundation.ZCLAttributeDef(
            id=0xEF12, type=t.uint32_t, is_manufacturer_specific=True
        )
        frost_lock = foundation.ZCLAttributeDef(
            id=0xEF13, type=t.Bool, is_manufacturer_specific=True
        )
        frost_lock_reset = foundation.ZCLAttributeDef(
            id=0xEF14, type=t.Bool, is_manufacturer_specific=True
        )  # 0 resets frost lock

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOnOff.ep_attribute,
            "on_off",
        ),
        5: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "timer_duration",
        ),
        6: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "timer_time_left",
        ),
        11: DPToAttributeMapping(
            TuyaPowerConfigurationCluster.ep_attribute,
            "battery_percentage_remaining",
        ),
        108: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "frost_lock",
            lambda x: not x,  # invert for lock entity
        ),
        109: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "frost_lock_reset",
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        6: "_dp_2_attr_update",
        11: "_dp_2_attr_update",
        108: "_dp_2_attr_update",
        109: "_dp_2_attr_update",
    }

    async def bind(self):
        """Bind cluster.

        When adding this device tuya gateway issues factory reset,
        we just need to reset the frost lock, because its state is unknown to us.
        """
        result = await super().bind()
        await self.write_attributes({self.attributes_by_name["frost_lock_reset"].id: 0})
        return result


class ParksidePSBZS(EnchantedDevice):
    """LIDL Parkside water without implemented scheduler."""

    signature = {
        MODELS_INFO: [("_TZE200_htnnfasr", "TS0601")],  # HG06875
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0
            # device_version=1
            # input_clusters=[0, 1, 3, 4, 5, 6, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    ParksideTuyaValveManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOff,
                    TuyaPowerConfigurationCluster,
                    ParksideTuyaValveManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }


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


def giex_string_to_ts(v: str) -> int | None:
    """Convert Giex String Duration datetime."""
    dev_tz = timezone(timedelta(hours=4))
    dev_dt = datetime.now(dev_tz)
    try:
        dt = datetime.strptime(v, "%H:%M:%S").replace(tzinfo=dev_tz)
        dev_dt.replace(hour=dt.hour, minute=dt.minute, second=dt.second)
    except ValueError:
        return None  # on initial start the device will return '--:--:--'
    return int(dev_dt.timestamp() + UNIX_EPOCH_TO_ZCL_EPOCH)


gx02_base_quirk = (
    TuyaQuirkBuilder()
    .tuya_battery(dp_id=108, power_cfg=TuyaPowerConfigurationCluster4AA)
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
        fallback_name="Last irrigation duration",
    )
    .tuya_sensor(
        dp_id=101,
        attribute_name="irrigation_start_time",
        type=t.CharacterString,
        converter=lambda x: giex_string_to_ts(x),
        device_class=SensorDeviceClass.TIMESTAMP,
        translation_key="irrigation_start_time",
        fallback_name="Irrigation start time",
    )
    .tuya_sensor(
        dp_id=102,
        attribute_name="irrigation_end_time",
        type=t.CharacterString,
        converter=lambda x: giex_string_to_ts(x),
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
    .applies_to("_TZE284_eaet5qt5", "TS0601")  # Insoma SGW08W
    .tuya_battery(dp_id=59, power_cfg=TuyaPowerConfigurationCluster4AA)
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


class RoyalGardineerWeatherDelay(t.enum8):
    """Royal Gardineer Irrigation Valve weather delay enum."""

    Disabled = 0x00
    Delayed_24h = 0x01
    Delayed_48h = 0x02
    Delayed_72h = 0x03


class RoyalGardineerTimerState(t.enum8):
    """Royal Gardineer Irrigation Valve timer state enum."""

    Disabled = 0x00
    Active = 0x01
    Enabled = 0x02


(
    TuyaQuirkBuilder("_TZE200_2wg5qrjy", "TS0601")
    .tuya_onoff(dp_id=1)
    .tuya_battery(dp_id=7, power_cfg=TuyaPowerConfigurationCluster2AA)
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
        enum_class=RoyalGardineerWeatherDelay,
        translation_key="weather_delay",
        fallback_name="Weather delay",
        initially_disabled=True,
    )
    # Timer state - read-only
    .tuya_enum(
        dp_id=12,
        attribute_name="timer_state",
        enum_class=RoyalGardineerTimerState,
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
