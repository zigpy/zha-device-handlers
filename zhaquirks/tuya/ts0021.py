"""Device handler the TS0021."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Ota, PowerConfiguration, Time
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import EventableCluster
from zhaquirks.const import (
    ARGS,
    ATTRIBUTE_ID,
    CLUSTER_ID,
    COMMAND,
    COMMAND_ATTRIBUTE_UPDATED,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    VALUE,
)
from zhaquirks.tuya import TUYA_CLUSTER_ID, DPToAttributeMapping, TuyaNewManufCluster

BTN_1 = "Button 1"
BTN_2 = "Button 2"

ATTR_BTN_1_PRESSED = "btn_1_pressed"
ATTR_BTN_2_PRESSED = "btn_2_pressed"


class TuyaCustomCluster(TuyaNewManufCluster, EventableCluster):
    """Tuya Custom Cluster for mapping data points to attributes."""

    dp_to_attribute: dict[int, DPToAttributeMapping] = {
        1: DPToAttributeMapping(
            TuyaNewManufCluster.ep_attribute,
            ATTR_BTN_1_PRESSED,
        ),
        2: DPToAttributeMapping(
            TuyaNewManufCluster.ep_attribute,
            ATTR_BTN_2_PRESSED,
        ),
    }

    data_point_handlers = {
        1: "_dp_2_attr_update",
        2: "_dp_2_attr_update",
    }


class TS0021(CustomDevice):
    """Tuya TS0021 2-button switch device."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=1026,
        # device_version=1,
        # input_clusters=[1, 1280, 61184, 0],
        # output_clusters=[25, 10])
        MODELS_INFO: [("_TZ3210_3ulg9kpo", "TS0021")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IasZone.cluster_id,
                    TuyaNewManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    IasZone.cluster_id,
                    TuyaCustomCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, BTN_1): {
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            CLUSTER_ID: TUYA_CLUSTER_ID,
            ENDPOINT_ID: 1,
            ARGS: {ATTRIBUTE_ID: ATTR_BTN_1_PRESSED, VALUE: 0},
        },
        (DOUBLE_PRESS, BTN_1): {
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            CLUSTER_ID: TUYA_CLUSTER_ID,
            ENDPOINT_ID: 1,
            ARGS: {ATTRIBUTE_ID: ATTR_BTN_1_PRESSED, VALUE: 1},
        },
        (LONG_PRESS, BTN_1): {
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            CLUSTER_ID: TUYA_CLUSTER_ID,
            ENDPOINT_ID: 1,
            ARGS: {ATTRIBUTE_ID: ATTR_BTN_1_PRESSED, VALUE: 2},
        },
        (SHORT_PRESS, BTN_2): {
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            CLUSTER_ID: TUYA_CLUSTER_ID,
            ENDPOINT_ID: 1,
            ARGS: {ATTRIBUTE_ID: ATTR_BTN_2_PRESSED, VALUE: 0},
        },
        (DOUBLE_PRESS, BTN_2): {
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            CLUSTER_ID: TUYA_CLUSTER_ID,
            ENDPOINT_ID: 1,
            ARGS: {ATTRIBUTE_ID: ATTR_BTN_2_PRESSED, VALUE: 1},
        },
        (LONG_PRESS, BTN_2): {
            COMMAND: COMMAND_ATTRIBUTE_UPDATED,
            CLUSTER_ID: TUYA_CLUSTER_ID,
            ENDPOINT_ID: 1,
            ARGS: {ATTRIBUTE_ID: ATTR_BTN_2_PRESSED, VALUE: 2},
        },
    }
