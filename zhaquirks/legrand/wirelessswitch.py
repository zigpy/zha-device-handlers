"""Module for Legrand wireless radiant switch."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    BinaryInput,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PollControl,
)

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    BUTTON,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STOP,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    LONG_RELEASE,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PARAMS,
    PROFILE_ID,
    SHORT_PRESS,
    TURN_OFF,
    TURN_ON,
)
from zhaquirks.legrand import LEGRAND, LegrandCluster, LegrandPowerConfigurationCluster


class RadiantWirelessSwitch(CustomDevice):
    """Wireless radiant switch"""

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=260,
        # device_version=1, input_clusters=[0, 3, 15, 32, 1, 64513],
        # output_clusters=[3, 6, 8, 0, 64513, 25])
        MODELS_INFO: [(f" {LEGRAND}", " Remote switch")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    LegrandCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LegrandCluster.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    LegrandPowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    LegrandCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Ota.cluster_id,
                    LegrandCluster,
                ],
            }
        }
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {COMMAND: COMMAND_ON},
        (LONG_PRESS, TURN_ON): {
            COMMAND: COMMAND_MOVE,
            PARAMS: {"move_mode": 0, "rate": 255},
        },
        (SHORT_PRESS, TURN_OFF): {COMMAND: COMMAND_OFF},
        (LONG_PRESS, TURN_OFF): {
            COMMAND: COMMAND_MOVE,
            PARAMS: {"move_mode": 1, "rate": 255},
        },
        (LONG_RELEASE, BUTTON): {COMMAND: COMMAND_STOP},
    }
