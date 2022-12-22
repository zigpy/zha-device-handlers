"""BlitzWolf IS-3/Tuya motion rechargeable occupancy sensor."""

import math
from typing import Dict, Optional, Tuple, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
    OccupancySensing,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, LocalDataCluster, MotionOnEvent
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    MOTION_EVENT,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    DPToAttributeMapping,
    TuyaLocalCluster,
    TuyaManufCluster,
    TuyaNewManufCluster,
)
from zhaquirks.tuya.mcu import TuyaMCUCluster

ZONE_TYPE = 0x0001


class TuyaOccupancySensing(OccupancySensing, TuyaLocalCluster):
    """Tuya local OccupancySensing cluster."""


class TuyaAnalogInput(AnalogInput, TuyaLocalCluster):
    """Tuya local AnalogInput cluster."""


class TuyaIlluminanceMeasurement(IlluminanceMeasurement, TuyaLocalCluster):
    """Tuya local IlluminanceMeasurement cluster."""


class TuyaTemperatureMeasurement(TemperatureMeasurement, TuyaLocalCluster):
    """Tuya local TemperatureMeasurement cluster."""


class TuyaRelativeHumidity(RelativeHumidity, TuyaLocalCluster):
    """Tuya local RelativeHumidity cluster."""


class NeoBatteryLevel(t.enum8):
    """NEO battery level enum."""

    BATTERY_FULL = 0x00
    BATTERY_HIGH = 0x01
    BATTERY_MEDIUM = 0x02
    BATTERY_LOW = 0x03
    USB_POWER = 0x04


class NeoMotionManufCluster(TuyaNewManufCluster):
    """Neo manufacturer cluster."""

    attributes = TuyaNewManufCluster.attributes.copy()
    attributes.update(
        {
            0xEF0D: ("dp_113", t.enum8, True),  # ramdom attribute ID
        }
    )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        101: DPToAttributeMapping(
            TuyaOccupancySensing.ep_attribute,
            "occupancy",
        ),
        104: DPToAttributeMapping(
            TuyaTemperatureMeasurement.ep_attribute,
            "measured_value",
            lambda x: x * 10,
        ),
        105: DPToAttributeMapping(
            TuyaRelativeHumidity.ep_attribute,
            "measured_value",
            lambda x: x * 100,
        ),
        113: DPToAttributeMapping(
            TuyaNewManufCluster.ep_attribute,
            "dp_113",
        ),
    }

    data_point_handlers = {
        101: "_dp_2_attr_update",
        104: "_dp_2_attr_update",
        105: "_dp_2_attr_update",
        113: "_dp_2_attr_update",
    }


class MmwRadarManufCluster(TuyaMCUCluster):
    """Neo manufacturer cluster."""

    # # Possible DPs and values
    # presence_state: presence
    # target distance: 1.61m
    # illuminance: 250lux
    # sensitivity: 9
    # minimum_detection_distance: 0.00m
    # maximum_detection_distance: 4.05m
    # dp_detection_delay: 0.1
    # dp_fading_time: 5.0
    # ¿illuminance?: 255lux
    # presence_brightness: no control
    # no_one_brightness: no control
    # current_brightness: off

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            # ramdom attribute IDs
            0xEF02: ("dp_2", t.uint32_t, True),
            0xEF03: ("dp_3", t.uint32_t, True),
            0xEF04: ("dp_4", t.uint32_t, True),
            0xEF06: ("dp_6", t.enum8, True),
            0xEF65: ("dp_101", t.uint32_t, True),
            0xEF66: ("dp_102", t.uint32_t, True),
            0xEF67: ("dp_103", t.CharacterString, True),
            0xEF69: ("dp_105", t.enum8, True),
            0xEF6A: ("dp_106", t.enum8, True),
            0xEF6B: ("dp_107", t.enum8, True),
            0xEF6C: ("dp_108", t.uint32_t, True),
        }
    )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaOccupancySensing.ep_attribute,
            "occupancy",
        ),
        2: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_2",
        ),
        3: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_3",
        ),
        4: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_4",
        ),
        6: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_6",
        ),
        9: DPToAttributeMapping(
            TuyaAnalogInput.ep_attribute,
            "present_value",
            lambda x: x / 100,
        ),
        101: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_101",
        ),
        102: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_102",
        ),
        103: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_103",
        ),
        104: DPToAttributeMapping(
            TuyaIlluminanceMeasurement.ep_attribute,
            "measured_value",
            lambda x: 10000 * math.log10(x) + 1,
        ),
        105: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_105",
        ),
        106: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_106",
        ),
        107: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_107",
        ),
        108: DPToAttributeMapping(
            TuyaMCUCluster.ep_attribute,
            "dp_108",
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        3: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
        6: "_dp_2_attr_update",
        9: "_dp_2_attr_update",
        101: "_dp_2_attr_update",
        102: "_dp_2_attr_update",
        103: "_dp_2_attr_update",
        104: "_dp_2_attr_update",
        105: "_dp_2_attr_update",
        106: "_dp_2_attr_update",
        107: "_dp_2_attr_update",
        108: "_dp_2_attr_update",
    }


class MotionCluster(LocalDataCluster, MotionOnEvent):
    """Tuya Motion Sensor."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Motion_Sensor}
    reset_s = 15


class TuyaManufacturerClusterMotion(TuyaManufCluster):
    """Manufacturer Specific Cluster of the Motion device."""

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Tuple[TuyaManufCluster.Command],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle cluster request."""
        tuya_cmd = args[0]
        self.debug("handle_cluster_request--> hdr: %s, args: %s", hdr, args)
        if hdr.command_id == 0x0001 and tuya_cmd.command_id == 1027:
            self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)


class TuyaMotion(CustomDevice):
    """BW-IS3 occupancy sensor."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=0 device_version=0 input_clusters=[0, 3]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [("_TYST11_i5j6ifxj", "5j6ifxj"), ("_TYST11_7hfcudw5", "hfcudw5")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    MotionCluster,
                    TuyaManufacturerClusterMotion,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }


class NeoMotion(CustomDevice):
    """NAS-PD07 occupancy sensor."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=0 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE200_7hfcudw5", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    NeoMotionManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    NeoMotionManufCluster,
                    TuyaOccupancySensing,
                    TuyaTemperatureMeasurement,
                    TuyaRelativeHumidity,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }


class MmwRadarMotion(CustomDevice):
    """Millimeter wave occupancy sensor."""

    signature = {
        #  endpoint=1, profile=260, device_type=81, device_version=1,
        #  input_clusters=[0, 4, 5, 61184], output_clusters=[25, 10]
        MODELS_INFO: [
            ("_TZE200_ar0slwnd", "TS0601"),
            ("_TZE200_sfiy5tfs", "TS0601"),
            ("_TZE200_mrf6vtua", "TS0601"),
            ("_TZE200_ztc6ggyl", "TS0601"),
            ("_TZE204_ztc6ggyl", "TS0601"),
            ("_TZE200_wukb7rhc", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaNewManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MmwRadarManufCluster,
                    TuyaOccupancySensing,
                    TuyaAnalogInput,
                    TuyaIlluminanceMeasurement,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
        }
    }


class MmwRadarMotionGPP(CustomDevice):
    """Millimeter wave occupancy sensor."""

    signature = {
        #  endpoint=1, profile=260, device_type=81, device_version=1,
        #  input_clusters=[4, 5, 61184, 0], output_clusters=[25, 10])
        MODELS_INFO: [
            ("_TZE200_ar0slwnd", "TS0601"),
            ("_TZE200_sfiy5tfs", "TS0601"),
            ("_TZE200_mrf6vtua", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaNewManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # input_clusters=[]
                # output_clusters=[33]
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    MmwRadarManufCluster,
                    TuyaOccupancySensing,
                    TuyaAnalogInput,
                    TuyaIlluminanceMeasurement,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }
