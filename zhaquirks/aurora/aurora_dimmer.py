"""Device handler for Aurora dimmer switch, battery powered."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Identify,
    LevelControl,
    OnOff,
    Ota,
)
from zigpy.zcl.clusters.lighting import Color

from .. import EventableCluster, PowerConfigurationCluster
from ..const import (
    ARGS,
    CLUSTER_ID,
    COMMAND,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LEFT,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    RIGHT,
    SHORT_PRESS,
)

COLOR_UP = "color_up"
COLOR_DOWN = "color_down"


class AuroraDimmerBatteryPowered(CustomDevice):
    """Aurora dimmer switch, battery powered."""

    class WallSwitchOnOffCluster(EventableCluster, OnOff):
        """WallSwitchOnOffCluster: fire events corresponding to press type."""

    class WallSwitchLevelControlCluster(EventableCluster, LevelControl):
        """WallSwitchLevelControlCluster: fire events corresponding to level changes."""

    class WallSwitchColorCluster(EventableCluster, Color):
        """WallSwitchColorCluster: fire events corresponding to color changes."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=261
        #  device_version=0 input_clusters=[0, 1, 3, 6, 8, 768]
        #  output_clusters=[3, 6, 8, 25, 768]>
        MODELS_INFO: [("Aurora", "2GBatteryDimmer50AU")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=261
            #  device_version=0 input_clusters=[0, 3, 6, 8, 768]
            #  output_clusters=[3, 6, 8, 768]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
            # device_version=0 input_clusters=[] output_clusters=[33])
            242: {
                # <SimpleDescriptor endpoint=242 profile=41440 device_type=97
                # device_version=0
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
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    WallSwitchOnOffCluster,
                    WallSwitchLevelControlCluster,
                    WallSwitchColorCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    Color.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    WallSwitchOnOffCluster,
                    WallSwitchLevelControlCluster,
                    WallSwitchColorCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                ],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 97,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        }
    }

    device_automation_triggers = {
        (DIM_UP, RIGHT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            ARGS: [0, 26, 3],
        },
        (DIM_DOWN, RIGHT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            ARGS: [1, 26, 3],
        },
        (COLOR_UP, RIGHT): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: 768,
            ENDPOINT_ID: 1,
            ARGS: [3, 47, 3, 153, 454],
        },
        (COLOR_DOWN, RIGHT): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: 768,
            ENDPOINT_ID: 1,
            ARGS: [1, 47, 3, 153, 454],
        },
        (DIM_UP, LEFT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 2,
            ARGS: [0, 26, 3],
        },
        (DIM_DOWN, LEFT): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 2,
            ARGS: [1, 26, 3],
        },
        (COLOR_UP, LEFT): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: 768,
            ENDPOINT_ID: 1,
            ARGS: [3, 47, 3, 153, 454],
        },
        (COLOR_DOWN, LEFT): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: 768,
            ENDPOINT_ID: 1,
            ARGS: [1, 47, 3, 153, 454],
        },
        (SHORT_PRESS, RIGHT): {
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
            ARGS: [],
        },
        (SHORT_PRESS, LEFT): {
            CLUSTER_ID: 6,
            ENDPOINT_ID: 2,
            ARGS: [],
        },
    }
