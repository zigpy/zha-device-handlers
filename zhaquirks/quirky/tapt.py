"""GE Quirky TAPT device."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)

from . import QUIRKY
from ..const import (
    ARGS,
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)

TAPT_MFG_CODE = 0x5488  # 21640 base 10
TAPT_CLUSTER = 0xFC20  # 64544 base 10

_LOGGER = logging.getLogger(__name__)


class TaptConfig(CustomCluster):
    """TAPT Configuration Cluster."""

    cluster_id = TAPT_CLUSTER
    name = "TAPTCluster"
    ep_attribute = "tapt_cluster"
    server_commands = {}
    client_commands = {}
    manufacturer_attributes = {
        0x0000: ("Switch Mode", t.uint8_t),
        # Value, Description
        # 0 - Standard On/Off Switch, No Smart Status, Relay Status Endpoint 2
        # 1 - Standard On/Off Switch, Smart Status on Endpoint 1, Relay Status on Endpoint 2
        # 2 - Smart Switch, Mains always On, Smart Status on Endpoint 1
        # 3 - Upper Toggles Load, Smart Status on Endpoint 1, Relay Status on Endpoint 2
        # 4 - Lower Toggles Load, Smart Status on Endpoint 1, Relay Status on Endpoint 2
    }


class TAPTSwitch(CustomDevice):
    """GE Quirky TAPT Switch."""

    manufacturer_id_override = TAPT_MFG_CODE

    signature = {
        MODELS_INFO: [(QUIRKY, "Smart Switch")],
        ENDPOINTS: {
            # <Optional endpoint=1 profile=260 device_type=260
            # device_version=0
            # input_clusters=[0, 3, 64544]
            # output_clusters=[6, 8, 3, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    TAPT_CLUSTER,  # 64544
                ],
                OUTPUT_CLUSTERS: [
                    OnOff.cluster_id,  # 6
                    LevelControl.cluster_id,  # 8
                    Identify.cluster_id,  # 3
                    Ota.cluster_id,  # 25
                ],
            },
            # <Optional endpoint=2 profile=260 device_type=2
            # device_version=0
            # input_clusters=[0, 3, 6, 5, 4]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    OnOff.cluster_id,  # 6
                    Scenes.cluster_id,  # 5
                    Groups.cluster_id,  # 4
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    TaptConfig,
                ],
                OUTPUT_CLUSTERS: [
                    OnOff.cluster_id,  # 6
                    LevelControl.cluster_id,  # 8
                    Identify.cluster_id,  # 3
                    Ota.cluster_id,  # 25
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_OUTPUT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    OnOff.cluster_id,  # 6
                    Scenes.cluster_id,  # 5
                    Groups.cluster_id,  # 4
                ],
                OUTPUT_CLUSTERS: [],
            },
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
            ARGS: [],
        },
        (SHORT_PRESS, TURN_OFF): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: 6,
            ENDPOINT_ID: 1,
            ARGS: [],
        },
        (LONG_PRESS, DIM_UP): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            ARGS: [0, 50],
        },
        (LONG_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_MOVE,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            ARGS: [1, 50],
        },
        (LONG_RELEASE, BUTTON): {
            COMMAND: COMMAND_STOP,
            CLUSTER_ID: 8,
            ENDPOINT_ID: 1,
            ARGS: [],
        },
    }
