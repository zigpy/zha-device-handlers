"""Device handler for IKEA of Sweden SYMFONISK sound remote gen2."""

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
    CLUSTER_ID,
    COMMAND,
    COMMAND_M_INITIAL_PRESS,
    COMMAND_M_LONG_PRESS,
    COMMAND_M_LONG_RELEASE,
    COMMAND_M_MULTI_PRESS_COMPLETE,
    COMMAND_M_SHORT_RELEASE,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_STEP,
    COMMAND_TOGGLE,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LEFT,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PRESSED,
    PROFILE_ID,
    RIGHT,
    SHORT_PRESS,
    TOGGLE,
)
from zhaquirks.ikea import (
    COMMAND_SHORTCUT_V1,
    IKEA,
    IKEA_CLUSTER_ID,
    WWAH_CLUSTER_ID,
    DoublingPowerConfig2AAACluster,
    PowerConfig2AAACluster,
    ShortcutV1Cluster,
    ShortcutV2Cluster,
)


class Symfonisk2CommonTriggers:
    """IKEA Symfonisk 2 common device triggers."""

    device_automation_triggers = {
        (SHORT_PRESS, TOGGLE): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
        },
        (SHORT_PRESS, DIM_UP): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 0},
        },
        (LONG_PRESS, DIM_UP): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 0},
        },
        (SHORT_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 1},
        },
        (LONG_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 1},
        },
        (SHORT_PRESS, RIGHT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 0},
        },
        (SHORT_PRESS, LEFT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
    }


class IkeaSymfoniskGen2v1(CustomDevice):
    """Custom device representing IKEA SYMFONISK sound remote gen2 V1.0.012."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=6
        # device_version=1
        # input_clusters=[0, 1, 3, 32, 4096, 64636]
        # output_clusters=[3, 4, 6, 8, 25, 4096, 64639]>
        MODELS_INFO: [(IKEA, "SYMFONISK sound remote gen2")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    WWAH_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                    ShortcutV1Cluster.cluster_id,
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
                    DoublingPowerConfig2AAACluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    WWAH_CLUSTER_ID,
                    ShortcutV1Cluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                    ShortcutV1Cluster,
                ],
            },
        },
    }

    device_automation_triggers = (
        Symfonisk2CommonTriggers.device_automation_triggers.copy()
    )
    device_automation_triggers.update(
        {
            (SHORT_PRESS, BUTTON_1): {
                COMMAND: COMMAND_SHORTCUT_V1,
                PARAMS: {"shortcut_button": 1, "shortcut_event": 1},
            },
            (DOUBLE_PRESS, BUTTON_1): {
                COMMAND: COMMAND_SHORTCUT_V1,
                PARAMS: {"shortcut_button": 1, "shortcut_event": 2},
            },
            (LONG_PRESS, BUTTON_1): {
                COMMAND: COMMAND_SHORTCUT_V1,
                PARAMS: {"shortcut_button": 1, "shortcut_event": 3},
            },
            (SHORT_PRESS, BUTTON_2): {
                COMMAND: COMMAND_SHORTCUT_V1,
                PARAMS: {"shortcut_button": 2, "shortcut_event": 1},
            },
            (DOUBLE_PRESS, BUTTON_2): {
                COMMAND: COMMAND_SHORTCUT_V1,
                PARAMS: {"shortcut_button": 2, "shortcut_event": 2},
            },
            (LONG_PRESS, BUTTON_2): {
                COMMAND: COMMAND_SHORTCUT_V1,
                PARAMS: {"shortcut_button": 2, "shortcut_event": 3},
            },
        },
    )


class IkeaSymfoniskGen2v2(CustomDevice):
    """Custom device representing IKEA SYMFONISK sound remote gen2 V1.0.32."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=6
        # device_version=1
        # input_clusters=[0, 1, 3, 32, 4096, 64636]
        # output_clusters=[3, 4, 6, 8, 25, 4096]>
        MODELS_INFO: [(IKEA, "SYMFONISK sound remote gen2")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    IKEA_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 3, 64640]
            # output_clusters=[3, 4, 64640]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    ShortcutV2Cluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    ShortcutV2Cluster.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=1 profile=260 device_type=6
            # device_version=1
            # input_clusters=[0, 3, 64640]
            # output_clusters=[3, 4, 64640]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    ShortcutV2Cluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
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
                    PowerConfig2AAACluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    IKEA_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    ShortcutV2Cluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    ShortcutV2Cluster,
                ],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    ShortcutV2Cluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    ShortcutV2Cluster,
                ],
            },
        },
    }

    device_automation_triggers = (
        Symfonisk2CommonTriggers.device_automation_triggers.copy()
    )
    device_automation_triggers.update(
        {
            (PRESSED, BUTTON_1): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_INITIAL_PRESS},
            (SHORT_PRESS, BUTTON_1): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_SHORT_RELEASE},
            (DOUBLE_PRESS, BUTTON_1): {
                ENDPOINT_ID: 2,
                COMMAND: COMMAND_M_MULTI_PRESS_COMPLETE,
            },
            (LONG_PRESS, BUTTON_1): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_LONG_PRESS},
            (LONG_RELEASE, BUTTON_1): {ENDPOINT_ID: 2, COMMAND: COMMAND_M_LONG_RELEASE},
            (PRESSED, BUTTON_2): {ENDPOINT_ID: 3, COMMAND: COMMAND_M_INITIAL_PRESS},
            (SHORT_PRESS, BUTTON_2): {ENDPOINT_ID: 3, COMMAND: COMMAND_M_SHORT_RELEASE},
            (DOUBLE_PRESS, BUTTON_2): {
                ENDPOINT_ID: 3,
                COMMAND: COMMAND_M_MULTI_PRESS_COMPLETE,
            },
            (LONG_PRESS, BUTTON_2): {ENDPOINT_ID: 3, COMMAND: COMMAND_M_LONG_PRESS},
            (LONG_RELEASE, BUTTON_2): {ENDPOINT_ID: 3, COMMAND: COMMAND_M_LONG_RELEASE},
        },
    )
