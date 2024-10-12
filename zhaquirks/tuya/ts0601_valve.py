"""Collection of Tuya Valve devices e.g. water valves, gas valve etc."""

from datetime import datetime, timedelta, timezone

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.quirks.v2.homeassistant import UnitOfTime
from zigpy.quirks.v2.homeassistant.sensor import SensorDeviceClass, SensorStateClass
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
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
from zhaquirks.tuya import TUYA_CLUSTER_ED00_ID, EnchantedDevice, TuyaLocalCluster
from zhaquirks.tuya.mcu import (
    DPToAttributeMapping,
    TuyaMCUCluster,
    TuyaOnOff,
    TuyaOnOffNM,
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

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            0xEF01: ("time_left", t.uint32_t, True),
            0xEF02: ("state", t.enum8, True),
            0xEF03: ("last_valve_open_duration", t.uint32_t, True),
            0xEF04: ("dp_6", t.uint32_t, True),
            0xEF05: ("valve_position", t.uint32_t, True),
        }
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

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            0xEF11: ("timer_duration", t.uint32_t, True),
            0xEF12: ("timer_time_left", t.uint32_t, True),
            0xEF13: ("frost_lock", t.Bool, True),
            0xEF14: ("frost_lock_reset", t.Bool, True),  # 0 resets frost lock
        }
    )

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


class GiexPowerConfigurationCluster4AA(TuyaPowerConfigurationCluster):
    """PowerConfiguration cluster for devices with 4 AA."""

    _CONSTANT_ATTRIBUTES = {
        PowerConfiguration.AttributeDefs.battery_size.id: 3,
        PowerConfiguration.AttributeDefs.battery_rated_voltage.id: 15,
        PowerConfiguration.AttributeDefs.battery_quantity.id: 4,
    }


class TuyaTemperatureMeasurement(TemperatureMeasurement, TuyaLocalCluster):
    """Tuya local TemperatureMeasurement cluster."""


class GiexValveWaterConsumed(TuyaValveWaterConsumed):
    """Giex Valve Water consumed cluster."""

    def __init__(self, *args, **kwargs):
        """Init a GiexValveWaterConsumed cluster."""
        super().__init__(*args, **kwargs)
        self.add_unsupported_attribute(Metering.AttributeDefs.instantaneous_demand.id)


GIEX_MODE_ATTR = 0xEF01  # Mode [0] duration [1] capacity
GIEX_START_TIME_ATTR = 0xEF65  # Last irrigation start time (GMT)
GIEX_END_TIME_ATTR = 0xEF66  # Last irrigation end time (GMT)
GIEX_NUM_TIMES_ATTR = 0xEF67  # Number of cycle irrigation times min=0 max=100
GIEX_TARGET_ATTR = 0xEF68  # Irrigation target, duration in sec or capacity in litres (depending on mode) min=0 max=3600
GIEX_INTERVAL_ATTR = 0xEF69  # Cycle irrigation interval in seconds min=0 max=3600
GIEX_WX_DELAY_ATTR = 0xEF6B  # Weather Delay [0-3] No Delay, 24hr,48hr, 72hr
GIEX_CIRC_IRR_PARAM = 0xEF6D  # Circular irrigation parameters
GIEX_RT_DURATION_SEC = 0xEF6E  # Real-time cumulative duration (seconds)
GIEX_OTHER_EXT = 0xEF70  # Other extensions string
GIEX_TIMEING_FUNC = 0xEF71  # Timing Function,Add or remove schedule.
GIEX_DURATION_ATTR = 0xEF72  # Last irrigation duration
GIEX_TZ_ATTR = 0xEF73  # Offset in hours
GIEX_12HRS_AS_SEC = 43200
GIEX_24HRS_AS_MIN = 1440
UNIX_EPOCH_TO_ZCL_EPOCH = 946684800


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
        dev_dt.replace(hour=dt.hour, minute=dt.minute, second=dt.second)
    except ValueError:
        return None  # on initial start the device will return '--:--:--'
    return dev_dt.timestamp() + UNIX_EPOCH_TO_ZCL_EPOCH


class GiexValveManufCluster(TuyaMCUCluster):
    """GiEX valve manufacturer cluster."""

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

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            GIEX_MODE_ATTR: ("irrigation_mode", t.Bool, True),
            GIEX_START_TIME_ATTR: ("irrigation_start_time", t.CharacterString, True),
            GIEX_END_TIME_ATTR: ("irrigation_end_time", t.CharacterString, True),
            GIEX_NUM_TIMES_ATTR: ("irrigation_num_times", t.uint32_t, True),
            GIEX_TARGET_ATTR: ("irrigation_target", t.uint32_t, True),
            GIEX_INTERVAL_ATTR: ("irrigation_interval", t.uint32_t, True),
            GIEX_WX_DELAY_ATTR: ("weather_delay", t.uint8_t, True),
            GIEX_CIRC_IRR_PARAM: ("irrigation_circ_parm", t.LVBytes, True),
            GIEX_RT_DURATION_SEC: ("irrigation_accu_secs", t.uint32_t, True),
            GIEX_OTHER_EXT: ("irrigation_other_ext", t.CharacterString, True),
            GIEX_TIMEING_FUNC: ("irrigation_timeing_func", t.LVBytes, True),
            GIEX_DURATION_ATTR: ("irrigation_duration", t.uint32_t, True),
            GIEX_TZ_ATTR: ("device_tz", t.uint8_t, True),
        }
    )

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_mode",
        ),
        2: DPToAttributeMapping(
            TuyaOnOffNM.ep_attribute,
            "on_off",
        ),
        101: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_start_time",
            converter=lambda x: giex_string_to_dt(x),
        ),
        102: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_end_time",
            converter=lambda x: giex_string_to_dt(x),
        ),
        103: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_num_times",
        ),
        104: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_target",
        ),
        105: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_interval",
        ),
        106: DPToAttributeMapping(
            TuyaTemperatureMeasurement.ep_attribute,
            "measured_value",
        ),
        107: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "weather_delay",
        ),
        108: DPToAttributeMapping(
            GiexPowerConfigurationCluster4AA.ep_attribute,
            "battery_percentage_remaining",
        ),
        109: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_circ_parm",
        ),
        110: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_accu_secs",
        ),
        111: DPToAttributeMapping(
            TuyaValveWaterConsumed.ep_attribute,
            "current_summ_delivered",
        ),
        112: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_other_ext",
        ),
        113: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_timeing_func",
        ),
        114: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_duration",
            converter=lambda x: giex_string_to_td(x),
        ),
        115: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "device_tz",
        ),
    }
    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        101: "_dp_2_attr_update",
        102: "_dp_2_attr_update",
        103: "_dp_2_attr_update",
        104: "_dp_2_attr_update",
        105: "_dp_2_attr_update",
        106: "_dp_2_attr_update",
        107: "_dp_2_attr_update",
        108: "_dp_2_attr_update",
        109: "_dp_2_attr_update",
        110: "_dp_2_attr_update",
        111: "_dp_2_attr_update",
        112: "_dp_2_attr_update",
        113: "_dp_2_attr_update",
        114: "_dp_2_attr_update",
        115: "_dp_2_attr_update",
    }

    async def write_attributes(self, attributes, manufacturer=None):
        """Overwrite to force manufacturer code."""

        return await super().write_attributes(
            attributes, manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID
        )


class GX02BaseQuirk:
    """Giex GX02 Valve Base Quirk."""

    base_quirk: QuirkBuilder

    def __init__(self, max_duration: int) -> None:
        """Init a base quirk that applies to all GX02 valves."""
        time_unit: int = UnitOfTime.SECONDS

        if max_duration == GIEX_24HRS_AS_MIN:
            time_unit = UnitOfTime.MINUTES

        self.base_quirk = (
            QuirkBuilder("GIEX", "GX02")
            .replaces(GiexValveManufCluster)
            .removes(TUYA_CLUSTER_ED00_ID)
            .adds(TuyaOnOffNM)
            .adds(GiexPowerConfigurationCluster4AA)
            .adds(GiexValveWaterConsumed)
            .number(
                "irrigation_num_times",
                GiexValveManufCluster.cluster_id,
                min_value=0,
                max_value=100,
                step=1,
                translation_key="irrigation_num_times",
                fallback_name="Irrigation Num Times",
            )
            .enum(
                "irrigation_mode",
                GiexValveManufCluster.GiexIrrigationMode,
                GiexValveManufCluster.cluster_id,
                translation_key="irrigation_mode",
                fallback_name="Irrigation Mode",
            )
            .enum(
                "weather_delay",
                GiexValveManufCluster.GiexIrrigationWeatherDelay,
                GiexValveManufCluster.cluster_id,
                translation_key="weather_delay",
                fallback_name="Weather Delay",
                initially_disabled=True,
            )
            .sensor(
                "irrigation_duration",
                GiexValveManufCluster.cluster_id,
                state_class=SensorStateClass.MEASUREMENT,
                device_class=SensorDeviceClass.DURATION,
                unit=UnitOfTime.SECONDS,
                translation_key="irrigation_duration",
                fallback_name="Last Irrigation Duration",
            )
            .sensor(
                "irrigation_start_time",
                GiexValveManufCluster.cluster_id,
                device_class=SensorDeviceClass.TIMESTAMP,
                translation_key="irrigation_start_time",
                fallback_name="Irrigation Start Time",
            )
            .sensor(
                "irrigation_end_time",
                GiexValveManufCluster.cluster_id,
                device_class=SensorDeviceClass.TIMESTAMP,
                translation_key="irrigation_end_time",
                fallback_name="Irrigation End Time",
            )
            .number(
                "irrigation_target",
                GiexValveManufCluster.cluster_id,
                min_value=0,
                max_value=max_duration,
                step=1,
                translation_key="irrigation_target",
                fallback_name="Irrigation Target",
            )
            .number(
                "irrigation_interval",
                GiexValveManufCluster.cluster_id,
                min_value=0,
                max_value=max_duration,
                step=1,
                unit=time_unit,
                translation_key="irrigation_interval",
                fallback_name="Irrigation Interval",
            )
        )
        self.base_quirk.manufacturer_model_metadata = []


(
    GX02BaseQuirk(GIEX_24HRS_AS_MIN)
    .base_quirk.also_applies_to("_TZE200_sh1btabb", "TS0601")
    .add_to_registry()
)
(
    GX02BaseQuirk(GIEX_12HRS_AS_SEC)
    .base_quirk.also_applies_to("_TZE200_a7sghmms", "TS0601")
    .also_applies_to("_TZE204_a7sghmms", "TS0601")
    .also_applies_to("_TZE200_7ytb3h8u", "TS0601")
    .also_applies_to("_TZE204_7ytb3h8u", "TS0601")
    .also_applies_to("_TZE284_7ytb3h8u", "TS0601")
    .add_to_registry()
)
