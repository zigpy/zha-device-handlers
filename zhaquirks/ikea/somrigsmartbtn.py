"""Device handler for IKEA of Sweden SOMRIG shortcut button."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    COMMAND,
    COMMAND_M_INITIAL_PRESS,
    COMMAND_M_LONG_PRESS,
    COMMAND_M_LONG_RELEASE,
    COMMAND_M_MULTI_PRESS_COMPLETE,
    COMMAND_M_SHORT_RELEASE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESSED,
    PROFILE_ID,
    SHORT_PRESS,
)
from zhaquirks.ikea import (
    IKEA,
    IKEA_CLUSTER_ID,
    PowerConfig1AAACluster,
    ShortcutV2Cluster,
)


class IkeaSomrigSmartButton(CustomDevice):
    """Custom device representing IKEA SOMRIG shortcut button."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260, device_type=6
        # device_version=1
        # input_clusters=[0, 1, 3, 4, 32, 4096, 64636, 64640]
        # output_clusters=[3, 4, 6, 8, 25, 4096, 64640]>
        MODELS_INFO: [(IKEA, "SOMRIG shortcut button")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    IKEA_CLUSTER_ID,
                    ShortcutV2Cluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                    ShortcutV2Cluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2  profile=260  device_type=6
            # device_version=1
            # input_clusters=[0, 3, 4, 64640]
            # output_clusters=[3, 4, 6, 8, 64640]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    ShortcutV2Cluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    ShortcutV2Cluster.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfig1AAACluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    IKEA_CLUSTER_ID,
                    ShortcutV2Cluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                    ShortcutV2Cluster,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    ShortcutV2Cluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    ShortcutV2Cluster,
                ],
            },
        },
    }

    device_automation_triggers = {
        (PRESSED, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: COMMAND_M_INITIAL_PRESS},
        (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: COMMAND_M_SHORT_RELEASE},
        (DOUBLE_PRESS, BUTTON_1): {
            ENDPOINT_ID: 1,
            COMMAND: COMMAND_M_MULTI_PRESS_COMPLETE,
        },
        (LONG_PRESS, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: COMMAND_M_LONG_PRESS},
        (LONG_RELEASE, BUTTON_1): {ENDPOINT_ID: 1, COMMAND: COMMAND_M_LONG_RELEASE},
        (PRESSED, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_INITIAL_PRESS},
        (SHORT_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_SHORT_RELEASE},
        (DOUBLE_PRESS, BUTTON_2): {
            ENDPOINT_ID: 2,
            COMMAND: COMMAND_M_MULTI_PRESS_COMPLETE,
        },
        (LONG_PRESS, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_LONG_PRESS},
        (LONG_RELEASE, BUTTON_2): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_LONG_RELEASE},
    }
