"""Tuya based remote dimmer switch."""
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks.const import (
    BUTTON,
    COMMAND,
    COMMAND_MOVE,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    COMMAND_STOP,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
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
from zhaquirks.tuya import TuyaDimmerSwitch, TuyaOnOff


class TuyaRemoteTS1001(TuyaDimmerSwitch):
    """TS1001 remote control with triggers."""

    signature = {
        MODELS_INFO: [
            ("_TYZB01_7qf81wty", "TS1001"),  # Immax NEO 07087-2 Smart Remote Control v2
            ("_TYZB01_bngwdjsr", "TS1001"),  # Livarno Lux Remote Control Dimmer
        ],
        ENDPOINTS: {
            # Endpoint id=1
            # in=[basic:0x0000, power:0x0001, identify:0x0003, groups:0x0004, lightlink:0x1000]
            # out=[ota:0x0019, time:0x000A, identify:0x0003, groups:0x0004, scenes:0x0005, on_off:0x0006, level:0x0008, lightlink:0x1000]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                    Time.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaOnOff,
                    LevelControl.cluster_id,
                    LightLink.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_ON,
        },
        (SHORT_PRESS, TURN_OFF): {
            COMMAND: COMMAND_OFF,
        },
        (SHORT_PRESS, DIM_UP): {
            COMMAND: COMMAND_STEP,
            PARAMS: {
                "step_mode": 0,
                "step_size": 51,
                "transition_time": 10,
            },
        },
        (SHORT_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_STEP,
            PARAMS: {
                "step_mode": 1,
                "step_size": 51,
                "transition_time": 10,
            },
        },
        (LONG_PRESS, DIM_UP): {
            COMMAND: COMMAND_MOVE,
            PARAMS: {
                "move_mode": 0,
                "rate": 51,
            },
        },
        (LONG_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_MOVE,
            PARAMS: {
                "move_mode": 1,
                "rate": 51,
            },
        },
        (LONG_RELEASE, BUTTON): {
            COMMAND: COMMAND_STOP,
        },
    }
