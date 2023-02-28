"""Device handler for IKEA of Sweden TRADFRI SYMFONISK remote control."""
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
    Scenes,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import Bus
from zhaquirks.const import (
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_MOVE_ON_OFF,
    COMMAND_STEP,
    COMMAND_STEP_ON_OFF,
    COMMAND_STOP,
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
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    RIGHT,
    ROTATED,
    SHORT_PRESS,
    STOP,
    TRIPLE_PRESS,
    TURN_ON,
)
from zhaquirks.ikea import (
    IKEA,
    IKEA_CLUSTER_ID,
    WWAH_CLUSTER_ID,
    LevelControlCluster,
    PowerConfiguration1CRCluster,
    PowerConfiguration2AAACluster,
    ShortcutCluster,
)


class IkeaSYMFONISK1(CustomDevice):
    """Custom device representing IKEA of Sweden TRADFRI remote control."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=6
        # device_version=1
        # input_clusters=[0, 1, 3, 32, 4096]
        # output_clusters=[3, 4, 6, 8, 25, 4096]>
        MODELS_INFO: [(IKEA, "SYMFONISK Sound Controller")],
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
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration1CRCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
        },
        (ROTATED, RIGHT): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 0},
        },
        (ROTATED, LEFT): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"move_mode": 1},
        },
        (ROTATED, STOP): {
            COMMAND: COMMAND_STOP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
        },
        (DOUBLE_PRESS, TURN_ON): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 0},
        },
        (TRIPLE_PRESS, TURN_ON): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            PARAMS: {"step_mode": 1},
        },
    }


class IkeaSYMFONISK2(CustomDevice):
    """Custom device representing IKEA of Sweden TRADFRI remote control."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=6
        # device_version=1
        # input_clusters=[0, 1, 3, 32, 4096 64636]
        # output_clusters=[3, 4, 5, 6, 8, 25, 4096,]>
        MODELS_INFO: [(IKEA, "SYMFONISK Sound Controller")],
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
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration1CRCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    IKEA_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        }
    }

    device_automation_triggers = IkeaSYMFONISK1.device_automation_triggers.copy()


class IkeaSYMFONISKRemote2(CustomDevice):
    """Custom device representing IKEA of Sweden SYMFONISK sound remote gen2."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.levelcontrol_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=6
        # device_version=1
        # input_clusters=[0, 1, 3, 32, 4096, 64599]
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
                    ShortcutCluster.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.REMOTE_CONTROL,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration2AAACluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    LightLink.cluster_id,
                    IKEA_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    LevelControlCluster,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                    ShortcutCluster,
                ],
            }
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_TOGGLE,
        },
        (SHORT_PRESS, DIM_UP): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            PARAMS: {"move_mode": 0},
        },
        (SHORT_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_MOVE_ON_OFF,
            PARAMS: {"move_mode": 1},
        },
        (LONG_PRESS, DIM_UP): {
            COMMAND: COMMAND_MOVE,
            PARAMS: {"move_mode": 0},
        },
        (LONG_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_MOVE,
            PARAMS: {"move_mode": 1},
        },
        (SHORT_PRESS, LEFT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            PARAMS: {"step_mode": 1},
        },
        (SHORT_PRESS, RIGHT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            PARAMS: {"step_mode": 0},
        },
        (SHORT_PRESS, BUTTON_1): {
            COMMAND: COMMAND_STEP_ON_OFF,
            CLUSTER_ID: 8,
            "args": {"step_mode": 0, "step_size": 1},
        },
        (SHORT_PRESS, BUTTON_2): {
            COMMAND: COMMAND_STEP_ON_OFF,
            CLUSTER_ID: 8,
            "args": {"step_mode": 1, "step_size": 1},
        },
        (DOUBLE_PRESS, BUTTON_1): {
            COMMAND: COMMAND_STEP_ON_OFF,
            CLUSTER_ID: 8,
            "args": {"step_mode": 0, "step_size": 2},
        },
        (DOUBLE_PRESS, BUTTON_2): {
            COMMAND: COMMAND_STEP_ON_OFF,
            CLUSTER_ID: 8,
            "args": {"step_mode": 1, "step_size": 2},
        },
        (LONG_PRESS, BUTTON_1): {
            COMMAND: COMMAND_STEP_ON_OFF,
            CLUSTER_ID: 8,
            "args": {"step_mode": 0, "step_size": 3},
        },
        (LONG_PRESS, BUTTON_2): {
            COMMAND: COMMAND_STEP_ON_OFF,
            CLUSTER_ID: 8,
            "args": {"step_mode": 1, "step_size": 3},
        },
    }
