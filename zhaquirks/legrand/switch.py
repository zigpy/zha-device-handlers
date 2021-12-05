"""Device handler for Light switch with neutral."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legrand import LEGRAND

MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC01  # decimal = 64513


class LegrandCluster(CustomCluster, ManufacturerSpecificCluster):
    """LegrandCluster."""

    cluster_id = MANUFACTURER_SPECIFIC_CLUSTER_ID
    name = "LegrandCluster"
    ep_attribute = "legrand_cluster"
    manufacturer_attributes = {
        0x0001: ("led_on_when_off", t.Bool),
        0x0002: ("led_on_when_on", t.Bool),
        #Some legrand's devices requires this value to be set on the 3rd attribute instead of the 1rst (bticino)
        0x0003: ("other_led_on_when_off", t.Bool),
    }


class LightSwitchWithNeutral(CustomDevice):
    """Light switch with neutral."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=256
        # device_version=1
        # input_clusters=[0, 3, 4, 8, 6, 5, 15, 64513]
        # output_clusters=[0, 25, 64513]>
        MODELS_INFO: [(f" {LEGRAND}", " Light switch with neutral")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    WindowCovering.cluster_id,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0066,
                INPUT_CLUSTERS: [0x0021],
                OUTPUT_CLUSTERS: [0x0021],
            },
        },
    }
    
    replacement = {
        
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    BinaryInput.cluster_id,
                    LegrandCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    WindowCovering.cluster_id,
                    LegrandCluster,
                ],
            },
        }
    }