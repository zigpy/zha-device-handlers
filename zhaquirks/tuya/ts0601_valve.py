"""Collection of Tuya Valve devices e.g. water valves, gas valve etc."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
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
from zhaquirks.tuya import EnchantedDevice, TuyaLocalCluster
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


# info from https://github.com/Koenkk/zigbee-herdsman-converters/blob/master/devices/giex.js
GIEX_MODE_ATTR = 0xEF01  # Mode [0] duration [1] capacity
GIEX_START_TIME_ATTR = 0xEF65  # Last irrigation start time (GMT)
GIEX_END_TIME_ATTR = 0xEF66  # Last irrigation end time (GMT)
GIEX_NUM_TIMES_ATTR = 0xEF67  # Number of cycle irrigation times min=0 max=100
GIEX_TARGET_ATTR = 0xEF68  # Irrigation target, duration in sec or capacity in litres (depending on mode) min=0 max=3600
GIEX_INTERVAL_ATTR = 0xEF69  # Cycle irrigation interval in seconds min=0 max=3600
GIEX_DURATION_ATTR = 0xEF72  # Last irrigation duration


class GiexValveManufCluster(TuyaMCUCluster):
    """GiEX valve manufacturer cluster."""

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            GIEX_MODE_ATTR: ("irrigation_mode", t.Bool, True),
            GIEX_START_TIME_ATTR: ("irrigation_start_time", t.uint32_t, True),
            GIEX_END_TIME_ATTR: ("irrigation_end_time", t.uint32_t, True),
            GIEX_NUM_TIMES_ATTR: ("irrigation_num_times", t.uint32_t, True),
            GIEX_TARGET_ATTR: ("irrigation_target", t.uint32_t, True),
            GIEX_INTERVAL_ATTR: ("irrigation_interval", t.uint32_t, True),
            GIEX_DURATION_ATTR: ("irrigation_duration", t.uint32_t, True),
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
        ),
        102: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_end_time",
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
        108: DPToAttributeMapping(
            TuyaPowerConfigurationCluster.ep_attribute,
            "battery_percentage_remaining",
        ),
        111: DPToAttributeMapping(
            TuyaValveWaterConsumed.ep_attribute,
            "current_summ_delivered",
        ),
        114: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "irrigation_duration",
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
        108: "_dp_2_attr_update",
        111: "_dp_2_attr_update",
        114: "_dp_2_attr_update",
    }

    async def write_attributes(self, attributes, manufacturer=None):
        """Overwrite to force manufacturer code."""

        return await super().write_attributes(
            attributes, manufacturer=foundation.ZCLHeader.NO_MANUFACTURER_ID
        )


class GiexValve(CustomDevice):
    """GiEX valve device."""

    signature = {
        MODELS_INFO: [("_TZE200_sh1btabb", "TS0601"), ("_TZE200_a7sghmms", "TS0601"), ( "_TZE204_7ytb3h8u", "TS0601")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0x0051
            # input_clusters=[0x0000, 0x0004, 0x0005, 0xef00]
            # output_clusters=[0x000a, 0x0019]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    GiexValveManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOffNM,
                    TuyaPowerConfigurationCluster,
                    TuyaValveWaterConsumed,
                    GiexValveManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
