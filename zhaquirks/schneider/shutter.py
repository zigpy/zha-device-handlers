"""Module to handle quirks of the Schneider Electric shutter.

manufacturer specific attributes to control displaying and specific configuration.
"""

from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.closures import WindowCovering
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class SchneiderShutterCluster(CustomCluster, WindowCovering):
    """Schneider custom cluster."""

    manufacturer_attributes = {
        0xE014: ("LiftDriveUpTime", t.uint16_t),
        0xE015: ("LiftDriveDownTime", t.uint16_t),
        0xE016: ("TiltOpenCloseAndStepTime", t.uint16_t),
        0xE017: ("TiltPositionPercentageAfterMoveToLevel", t.uint8_t),
    }


class SchneiderShutter(CustomDevice):
    """SchneiderShutter custom device."""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=5, profile=260, device_type=0x0202, device_version=1, input_clusters=[0,3,4,5,0x0102,0x0B05], output_clusters=[25],endpoint=21, profile=260, device_type=0x0202, device_version=1, input_clusters=[0,3,0x0102,0xFF17], output_clusters=[3,4,5,6,8,0x0B05])
        MODELS_INFO: [("Schneider Electric", "NHPB/SHUTTER/1")],
        ENDPOINTS: {
            5: {
                PROFILE_ID: 260,
                DEVICE_TYPE: 514,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    WindowCovering.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            21: {
                PROFILE_ID: 260,
                DEVICE_TYPE: 260,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Diagnostic.cluster_id,
                    65303,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [33],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            5: {
                INPUT_CLUSTERS: [
                    Basic,
                    Identify,
                    Groups,
                    Scenes,
                    SchneiderShutterCluster,
                    Diagnostic,
                ],
                OUTPUT_CLUSTERS: [Ota],
            },
            21: {
                PROFILE_ID: 260,
                DEVICE_TYPE: 260,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Diagnostic.cluster_id,
                    65303,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    WindowCovering.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [33],
            },
        }
    }
