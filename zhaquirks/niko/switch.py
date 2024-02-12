"""Niko switches (only Niko Double connectable switch,10A (552-721X2) at this time)"""

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic

from zhaquirks import EventableCluster
from zhaquirks.const import (
    ARGS,
    BUTTON_1,
    BUTTON_2,
    BUTTON_3,
    BUTTON_4,
    COMMAND_CLICK,
    COMMAND_HOLD,
    COMMAND_RELEASE,
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.niko import NIKO


class NikoConfigCluster(CustomCluster):
    """manufacturer specific cluster related to device settings"""

    class ButtonOperationMode(t.enum8):
        # WARN: while one can technically write 0x00 to the operationMode attribute
        #       this seems to brick the device and it will need to be rejoined
        Decoupled = 0x01
        ControlRelay = 0x02

    class LedState(t.uint8_t):
        Off = 0x00
        On = 0xFF

    class LedOperationMode(t.enum8):
        Decoupled = 0x00
        ControlledByRelay = 0x01
        # Notable behaviour:
        # If LedOperationMode == ControlledByRelay, ButtonOperationMode == ControlRelay and LedState == On, then LED reflects status of corresponding relay
        # If ButtonOperationMode == Decoupled, then neither buttons nor relay affect the LEDs (i.e. LedOperationMode acts as if ==Decoupled)
        # If LedOperationMode == Decoupled and/or ButtonOperationMode == Decoupled, then LED can nevertheless by controlled by writing LedState ('always on' or 'always off')

    cluster_id = 0xFC00
    ep_attribute = "niko_config_cluster"
    attributes = {
        # If this would ever be expanded to outlets:
        # WARNING: 0x0000 has different datatypes!
        # enum8 (switch) vs. bitmap8 (outlet)
        # unknown usage/function on outlet
        0x0000: ("button_operation_mode", ButtonOperationMode, True),
        0x0100: ("led_state", LedState, True),
        0x0104: ("led_operation_mode", LedOperationMode, True),
    }


class NikoActionCluster(EventableCluster):
    """manufacturer specific cluster related to registered action (if ButtonOperationMode == Decoupled)"""

    cluster_id = 0xFC01
    ep_attribute = "niko_action_cluster"
    attributes = {
        # Notable behaviour:
        # BUTTON1 (left) = {16: null, 64: 'click', 32: 'hold', 48: 'release'}
        # BUTTON2 (right) = {4096: null, 16384: 'click', 8192: 'hold', 12288: 'release'}
        # BUTTON3 (left_ext) = {256: null, 1024: 'click', 512: 'hold', 768: 'release'}
        # BUTTON4 (right_ext) = {65536: null, 262144: 'click', 131072: 'hold', 196608: 'release'}
        0x0002: ("action", t.bitmap32, True),
    }


class NikoSingleConnectableSwitch(CustomDevice):
    """Niko Single connectable switch,10A (552-721X1)"""

    signature = {
        MODELS_INFO: [(NIKO, "single connectable switch,10A")],
        ENDPOINTS: {
            # SimpleDescriptor(endpoint=1, profile=260, device_type=266,
            # device_version=1,
            # input_clusters=[0, 3, 4, 5, 6, 2821, 64512, 64513],
            # output_clusters=[25])
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Diagnostic.cluster_id,
                    NikoConfigCluster.cluster_id,
                    NikoActionCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
            # SimpleDescriptor(endpoint=2, profile=260, device_type=266,
            # device_version=1,
            # input_clusters=[0, 3, 4, 5, 6, 2821, 64512, 64513],
            # output_clusters=[])
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Diagnostic.cluster_id,
                    NikoConfigCluster.cluster_id,
                    NikoActionCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # SimpleDescriptor(endpoint=242, profile=41440, device_type=97,
            # device_version=1,
            # input_clusters=[],
            # output_clusters=[33])
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Diagnostic.cluster_id,
                    NikoConfigCluster,
                    NikoActionCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                INPUT_CLUSTERS: [
                    # Most of the clusters repeated in the second endpoint are not actually independent (i.e. a change in one endpoint also changes it in the other).
                    # Accordingly, one might think you could e.g. control the button and/or LED operation independently for both sides, but that's not actually the case.
                    # As such, the clusters which (I believe) are superfluous have been omitted in the replacement dict.
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (COMMAND_CLICK, BUTTON_1): {ARGS: {"value": 64}},
        (COMMAND_HOLD, BUTTON_1): {ARGS: {"value": 32}},
        (COMMAND_RELEASE, BUTTON_1): {ARGS: {"value": 48}},
        (COMMAND_CLICK, BUTTON_2): {ARGS: {"value": 1024}},
        (COMMAND_HOLD, BUTTON_2): {ARGS: {"value": 512}},
        (COMMAND_RELEASE, BUTTON_2): {ARGS: {"value": 768}},
    }


class NikoDoubleConnectableSwitch(CustomDevice):
    """Niko Double connectable switch,10A (552-721X2)"""

    signature = {
        MODELS_INFO: [(NIKO, "Double connectable switch,10A")],
        ENDPOINTS: {
            # SimpleDescriptor(endpoint=1, profile=260, device_type=266,
            # device_version=1,
            # input_clusters=[0, 3, 4, 5, 6, 2821, 64512, 64513],
            # output_clusters=[25])
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Diagnostic.cluster_id,
                    NikoConfigCluster.cluster_id,
                    NikoActionCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
            # SimpleDescriptor(endpoint=2, profile=260, device_type=266,
            # device_version=1,
            # input_clusters=[0, 3, 4, 5, 6, 2821, 64512, 64513],
            # output_clusters=[])
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Diagnostic.cluster_id,
                    NikoConfigCluster.cluster_id,
                    NikoActionCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # SimpleDescriptor(endpoint=242, profile=41440, device_type=97,
            # device_version=1,
            # input_clusters=[],
            # output_clusters=[33])
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Diagnostic.cluster_id,
                    NikoConfigCluster,
                    NikoActionCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_PLUG_IN_UNIT,
                INPUT_CLUSTERS: [
                    # Most of the clusters repeated in the second endpoint are not actually independent (i.e. a change in one endpoint also changes it in the other).
                    # Accordingly, one might think you could e.g. control the button and/or LED operation independently for both sides, but that's not actually the case.
                    # As such, the clusters which (I believe) are superfluous have been omitted in the replacement dict.
                    OnOff.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: 41440,
                DEVICE_TYPE: 0x0061,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        (COMMAND_CLICK, BUTTON_1): {ARGS: {"value": 64}},
        (COMMAND_HOLD, BUTTON_1): {ARGS: {"value": 32}},
        (COMMAND_RELEASE, BUTTON_1): {ARGS: {"value": 48}},
        (COMMAND_CLICK, BUTTON_2): {ARGS: {"value": 16384}},
        (COMMAND_HOLD, BUTTON_2): {ARGS: {"value": 8192}},
        (COMMAND_RELEASE, BUTTON_2): {ARGS: {"value": 12288}},
        (COMMAND_CLICK, BUTTON_3): {ARGS: {"value": 1024}},
        (COMMAND_HOLD, BUTTON_3): {ARGS: {"value": 512}},
        (COMMAND_RELEASE, BUTTON_3): {ARGS: {"value": 768}},
        (COMMAND_CLICK, BUTTON_4): {ARGS: {"value": 262144}},
        (COMMAND_HOLD, BUTTON_4): {ARGS: {"value": 131072}},
        (COMMAND_RELEASE, BUTTON_4): {ARGS: {"value": 196608}},
    }
