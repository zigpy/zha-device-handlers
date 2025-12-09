"""Quirk for AwoX ERCU_WS_Zm remote control."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import MODELS_INFO, PROFILE_ID
from zhaquirks.const import (
    ARGS,
    CLUSTER_ID,
    COMMAND,
    COMMAND_OFF,
    COMMAND_ON,
    COMMAND_STEP,
    COMMAND_STEP_COLOR_TEMP,
    COMMAND_STEP_ON_OFF,
    COMMAND_TOGGLE,
    DEVICE_TYPE,
    DIM_DOWN,
    DIM_UP,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    OUTPUT_CLUSTERS,
    PARAMS,
    SHORT_PRESS,
    TOGGLE,
    TURN_OFF,
    TURN_ON,
)


class AwoXERCU_WS_Zm(CustomDevice):
    """AwoX ERCU_WS_Zm remote control."""

    signature = {
        MODELS_INFO: [("AwoX", "ERCU_WS_Zm")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: 0x128F,
                DEVICE_TYPE: zha.DeviceType.COLOR_CONTROLLER,
                INPUT_CLUSTERS: [0xFF50, 0xFF51],
                OUTPUT_CLUSTERS: [0xFF50, 0xFF51],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    LightLink.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    Color.cluster_id,
                    LightLink.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: 0x128F,
                DEVICE_TYPE: zha.DeviceType.COLOR_CONTROLLER,
                INPUT_CLUSTERS: [0xFF50, 0xFF51],
                OUTPUT_CLUSTERS: [0xFF50, 0xFF51],
            },
        },
    }

    device_automation_triggers = {
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0006, endpoint_id=1, cluster_id=6, command=on, args=[], params=>
        (SHORT_PRESS, TURN_ON): {
            COMMAND: COMMAND_ON,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: [],
        },
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0006, endpoint_id=1, cluster_id=6, command=off, args=[], params=>
        (SHORT_PRESS, TURN_OFF): {
            COMMAND: COMMAND_OFF,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: [],
        },
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0006, endpoint_id=1, cluster_id=6, command=toggle, args=[], params=>
        (SHORT_PRESS, TOGGLE): {
            COMMAND: COMMAND_TOGGLE,
            CLUSTER_ID: OnOff.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: [],
        },
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0008, endpoint_id=1, cluster_id=8, command=step_with_on_off, args=[<StepMode.Up: 0>, 36, 2], params=step_mode=StepMode.Up, step_size=36, transition_time=2>
        (SHORT_PRESS, DIM_UP): {
            COMMAND: COMMAND_STEP_ON_OFF,
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: [0, 36, 2],
            PARAMS: {"step_mode": 0, "step_size": 36, "transition_time": 2},
        },
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0008, endpoint_id=1, cluster_id=8, command=step, args=[<StepMode.Down: 1>, 36, 2], params=step_mode=StepMode.Down, step_size=36, transition_time=2, options_mask=None, options_override=None>
        (SHORT_PRESS, DIM_DOWN): {
            COMMAND: COMMAND_STEP,
            CLUSTER_ID: LevelControl.cluster_id,
            ENDPOINT_ID: 1,
            ARGS: [1, 36, 2],
            PARAMS: {
                "step_mode": 1,
                "step_size": 36,
                "transition_time": 2,
                "options_mask": None,
                "options_override": None,
            },
        },
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0300, endpoint_id=1, cluster_id=768, command=move_to_hue_and_saturation, args=[25, 254, 5, <OptionsMask: 0>, <Options: 0>], params=hue=25, saturation=254, transition_time=5, options_mask=0, options_override=0>
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0300, endpoint_id=1, cluster_id=768, command=move_to_hue_and_saturation, args=[38, 254, 5, <OptionsMask: 0>, <Options: 0>], params=hue=38, saturation=254, transition_time=5, options_mask=0, options_override=0>
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0300, endpoint_id=1, cluster_id=768, command=move_to_hue_and_saturation, args=[50, 254, 5, <OptionsMask: 0>, <Options: 0>], params=hue=50, saturation=254, transition_time=5, options_mask=0, options_override=0>
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0300, endpoint_id=1, cluster_id=768, command=move_to_hue_and_saturation, args=[63, 254, 5, <OptionsMask: 0>, <Options: 0>], params=hue=63, saturation=254, transition_time=5, options_mask=0, options_override=0>
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0300, endpoint_id=1, cluster_id=768, command=move_to_hue_and_saturation, args=[76, 254, 5, <OptionsMask: 0>, <Options: 0>], params=hue=76, saturation=254, transition_time=5, options_mask=0, options_override=0>
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0300, endpoint_id=1, cluster_id=768, command=move_to_hue_and_saturation, args=[88, 254, 5, <OptionsMask: 0>, <Options: 0>], params=hue=88, saturation=254, transition_time=5, options_mask=0, options_override=0>
        (LONG_PRESS, "change_color"): {
            COMMAND: "move_to_hue_and_saturation",
            CLUSTER_ID: Color.cluster_id,
            ENDPOINT_ID: 1,
        },
        # <Event zha_event[L]: device_ieee=a4:c1:38:ee:ab:32:76:81, device_id=82539657af7e1302ab1cc1cf0f27158b, unique_id=a4:c1:38:ee:ab:32:76:81:1:0x0300, endpoint_id=1, cluster_id=768, command=step_color_temp, args=[<StepMode.Down: 3>, 21, 0, 0, 0], params=step_mode=StepMode.Down, step_size=21, transition_time=0, color_temp_min_mireds=0, color_temp_max_mireds=0, options_mask=None, options_override=None>
        (LONG_PRESS, "change_color_temp"): {
            COMMAND: COMMAND_STEP_COLOR_TEMP,
            CLUSTER_ID: Color.cluster_id,
            ENDPOINT_ID: 1,
        },
    }
