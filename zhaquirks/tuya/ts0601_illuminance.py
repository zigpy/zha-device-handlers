"""Tuya HOME-LUX illuminance sensor"""

import math
from typing import Dict, Optional, Tuple, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.measurement import (
    IlluminanceMeasurement,
)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, LocalDataCluster, MotionOnEvent
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    DPToAttributeMapping,
    TuyaLocalCluster,
    TuyaNewManufCluster,
)


TUYA_BRIGHTNESS_LEVEL_ATTR = 0x01 # 0-2 "Low, Medium, High"
TUYA_ILLUMINANCE_ATTR = 0x02 # [0, 0, 3, 232] illuminance

TUYA_BRIGHTNESS_LEVEL_STR = [ "Low", "Medium", "High" ]

class TuyaIlluminanceMeasurement(IlluminanceMeasurement, TuyaLocalCluster):
    """Tuya local IlluminanceMeasurement cluster."""
    attributes = IlluminanceMeasurement.attributes.copy()
    attributes.update(
        {
            0xFF00: ("brightness_level", t.CharacterString, True),
        }
    )

class TuyaIlluminanceCluster(TuyaNewManufCluster):
    """Tuya Illuminance cluster."""


    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        TUYA_BRIGHTNESS_LEVEL_ATTR: DPToAttributeMapping(
            TuyaIlluminanceMeasurement.ep_attribute,
            "brightness_level",
            lambda x: TUYA_BRIGHTNESS_LEVEL_STR[x]
        ),


        TUYA_ILLUMINANCE_ATTR: DPToAttributeMapping(
            TuyaIlluminanceMeasurement.ep_attribute,
            "measured_value",
            lambda x: (10000.0 * math.log10(x) + 1.0 if x != 0 else 0)
        ),
    }

    data_point_handlers = {
        TUYA_BRIGHTNESS_LEVEL_ATTR: "_dp_2_attr_update",
        TUYA_ILLUMINANCE_ATTR: "_dp_2_attr_update",

    }


class TuyaIlluminance(CustomDevice):
    """HOME-LUX illuminance sensor. Sense maximum 1000 lumen."""

    signature = {
        #  endpoint=1, profile=260, device_type=81, device_version=1,
        #  input_clusters=[4, 5, 61184, 0], output_clusters=[25, 10])
        MODELS_INFO: [
            ("_TZE200_yi4jtqq1", "TS0601"),
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
                    TuyaIlluminanceCluster,
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


