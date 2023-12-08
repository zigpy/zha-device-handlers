"""Tuya based cover and blinds."""
from typing import Dict

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, GreenPowerProxy, Groups, Ota, Scenes, Time

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import NoManufacturerCluster
from zhaquirks.tuya.mcu import DPToAttributeMapping, TuyaMCUCluster

TUYA_MANUFACTURER_GARAGE = "tuya_manufacturer_garage"


class TuyaGarageManufCluster(NoManufacturerCluster, TuyaMCUCluster):
    """Tuya garage door opener."""

    ep_attribute = TUYA_MANUFACTURER_GARAGE

    attributes = TuyaMCUCluster.attributes.copy()
    attributes.update(
        {
            # ramdom attribute IDs
            0xEF01: ("button", t.Bool, True),
            0xEF02: ("dp_2", t.uint32_t, True),
            0xEF03: ("contact_sensor", t.Bool, True),
            0xEF04: ("dp_4", t.uint32_t, True),
            0xEF05: ("dp_5", t.uint32_t, True),
            0xEF0B: ("dp_11", t.Bool, True),
            0xEF0C: ("dp_12", t.enum8, True),
        }
    )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        # garage door trigger ¿on movement, on open, on closed?
        1: DPToAttributeMapping(
            TUYA_MANUFACTURER_GARAGE,
            "button",
        ),
        2: DPToAttributeMapping(
            TUYA_MANUFACTURER_GARAGE,
            "dp_2",
        ),
        3: DPToAttributeMapping(
            TUYA_MANUFACTURER_GARAGE,
            "contact_sensor",
        ),
        4: DPToAttributeMapping(
            TUYA_MANUFACTURER_GARAGE,
            "dp_4",
        ),
        5: DPToAttributeMapping(
            TUYA_MANUFACTURER_GARAGE,
            "dp_5",
        ),
        11: DPToAttributeMapping(
            TUYA_MANUFACTURER_GARAGE,
            "dp_11",
        ),
        # garage door status (open, closed, ...)
        12: DPToAttributeMapping(
            TUYA_MANUFACTURER_GARAGE,
            "dp_12",
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
        3: "_dp_2_attr_update",
        4: "_dp_2_attr_update",
        5: "_dp_2_attr_update",
        11: "_dp_2_attr_update",
        12: "_dp_2_attr_update",
    }


class TuyaGarageSwitchTO(CustomDevice):
    """Tuya Garage switch."""

    signature = {
        MODELS_INFO: [
            ("_TZE200_nklqjk62", "TS0601"),
            ("_TZE200_wfxuhoea", "TS0601"),
            ("_TZE204_nklqjk62", "TS0601"),
        ],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0x0051
            # input_clusters=[0, 4, 5, 61184]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaGarageManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # input_clusters=[]
            # output_clusters=[33]
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaGarageManufCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }
