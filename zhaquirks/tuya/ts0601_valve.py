"""Collection of Tuya Valve devices e.g. water valves, gas valve etc."""

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
    TUYA_CLUSTER_ED00_ID,
    EnchantedDevice,
    TuyaLocalCluster,
    TuyaPowerConfigurationCluster4AA,
)
from zhaquirks.tuya.builder import TuyaQuirkBuilder
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

    class AttributeDefs(TuyaMCUCluster.AttributeDefs):
        """Attribute Definitions."""

        irrigation_mode = foundation.ZCLAttributeDef(
            id=GIEX_MODE_ATTR, type=t.Bool, is_manufacturer_specific=True
        )
        irrigation_start_time = foundation.ZCLAttributeDef(
            id=GIEX_START_TIME_ATTR, type=t.uint32_t, is_manufacturer_specific=True
        )
        irrigation_end_time = foundation.ZCLAttributeDef(
            id=GIEX_END_TIME_ATTR, type=t.uint32_t, is_manufacturer_specific=True
        )
        irrigation_num_times = foundation.ZCLAttributeDef(
            id=GIEX_NUM_TIMES_ATTR, type=t.uint32_t, is_manufacturer_specific=True
        )
        irrigation_target = foundation.ZCLAttributeDef(
            id=GIEX_TARGET_ATTR, type=t.uint32_t, is_manufacturer_specific=True
        )
        irrigation_interval = foundation.ZCLAttributeDef(
            id=GIEX_INTERVAL_ATTR, type=t.uint32_t, is_manufacturer_specific=True
        )
        irrigation_duration = foundation.ZCLAttributeDef(
            id=GIEX_DURATION_ATTR, type=t.uint32_t, is_manufacturer_specific=True
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
        MODELS_INFO: [
            ("_TZE200_sh1btabb", "TS0601"),
            ("_TZE200_a7sghmms", "TS0601"),
            ("_TZE204_7ytb3h8u", "TS0601"),
            ("_TZE200_7ytb3h8u", "TS0601"),
        ],
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


class GiexValveVar02(CustomDevice):
    """GiEX valve device, variant 2."""

    signature = {
        MODELS_INFO: [
            ("_TZE284_7ytb3h8u", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0x0051
            # input_clusters=[0x0000, 0x0004, 0x0005, 0xed00, 0xef00]
            # output_clusters=[0x000a, 0x0019]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TUYA_CLUSTER_ED00_ID,
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


class GiexIrrigationStatus(t.enum8):
    """Giex Irrigation Status Enum."""

    Manual = 0x00
    Auto = 0x01
    Idle = 0x02


(
    TuyaQuirkBuilder("_TZE284_8zizsafo", "TS0601")  # Giex GX04
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
