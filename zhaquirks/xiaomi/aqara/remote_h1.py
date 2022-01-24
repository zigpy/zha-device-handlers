"""Aqara H1-series wireless remote."""
from zigpy.profiles import zha
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, OnOff, PowerConfiguration

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    ALT_DOUBLE_PRESS,
    ALT_SHORT_PRESS,
    ARGS,
    BUTTON,
    COMMAND,
    COMMAND_OFF,
    COMMAND_TOGGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LEFT,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    RIGHT,
    SHORT_PRESS,
    TRIPLE_PRESS,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
)
from zhaquirks.xiaomi.aqara.opple_remote import (
    COMMAND_1_DOUBLE,
    COMMAND_1_HOLD,
    COMMAND_1_SINGLE,
    COMMAND_1_TRIPLE,
    COMMAND_2_DOUBLE,
    COMMAND_2_HOLD,
    COMMAND_2_SINGLE,
    COMMAND_2_TRIPLE,
    COMMAND_3_DOUBLE,
    COMMAND_3_HOLD,
    COMMAND_3_SINGLE,
    COMMAND_3_TRIPLE,
    MultistateInputCluster,
)

BOTH_BUTTONS = "both_buttons"


class AqaraRemoteManuSpecificCluster(XiaomiAqaraE1Cluster):
    """Aqara manufacturer specific settings."""

    ep_attribute = "aqara_cluster"

    # manufacture override code: 4447 (0x115f)
    # to get/set these attributes, you might need to click the button 5 times
    # quickly.
    attributes = XiaomiAqaraE1Cluster.attributes.copy()
    attributes.update(
        {
            # operation_mode:
            # 0 means "command" mode.
            # 1 means "event" mode.
            0x0009: ("operation_mode", t.uint8_t, True),
            # click_mode:
            # 1 means single click mode, which is low latency (50ms) but only sends
            #   single click events.
            # 2 means multiple click mode, which has a slightly higher latency but
            #   supports single/double/triple click and long press.
            # default value after factory reset: 1.
            0x0125: ("click_mode", t.uint8_t, True),
        }
    )


class PowerConfigurationClusterH1Remote(PowerConfigurationCluster):
    """Reports battery level."""

    # Aqara H1 wireless remote uses one CR2450 battery.
    # Values are copied from zigbee-herdsman-converters.
    MIN_VOLTS = 2.5
    MAX_VOLTS = 3.0


class RemoteH1SingleRocker(XiaomiCustomDevice):
    """Aqara H1 Wireless Remote Single Rocker Version WRS-R01."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.remote.b18ac1")],
        ENDPOINTS: {
            # SizePrefixedSimpleDescriptor(
            #   endpoint=1, profile=260, device_type=259, device_version=1,
            #   input_clusters=[0, 3, 1], output_clusters=[3, 6])
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationClusterH1Remote,
                    MultistateInputCluster,
                    AqaraRemoteManuSpecificCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            }
        }
    }
    device_automation_triggers = {
        # triggers when operation_mode == event
        # the button doesn't send an release event after hold
        (SHORT_PRESS, BUTTON): {COMMAND: COMMAND_1_SINGLE},
        (DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_1_DOUBLE},
        (TRIPLE_PRESS, BUTTON): {COMMAND: COMMAND_1_TRIPLE},
        (LONG_PRESS, BUTTON): {COMMAND: COMMAND_1_HOLD},
        # triggers when operation_mode == command
        (ALT_SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 1, ARGS: []},
        (ALT_DOUBLE_PRESS, BUTTON): {COMMAND: COMMAND_OFF, ENDPOINT_ID: 1, ARGS: []},
    }


class RemoteH1DoubleRocker1(XiaomiCustomDevice):
    """Aqara H1 Wireless Remote Double Rocker Version WRS-R02, variant 1."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.remote.b28ac1")],
        ENDPOINTS: {
            1: {
                # SizePrefixedSimpleDescriptor(
                #   endpoint=1, profile=260, device_type=259, device_version=1,
                #   input_clusters=[0, 3, 1], output_clusters=[3, 6])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            3: {
                # SizePrefixedSimpleDescriptor(
                #   endpoint=3, profile=260, device_type=259, device_version=1,
                #   input_clusters=[3], output_clusters=[6])
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    PowerConfigurationClusterH1Remote,
                    MultistateInputCluster,
                    AqaraRemoteManuSpecificCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
        }
    }
    device_automation_triggers = {
        # triggers when operation_mode == event
        # the button doesn't send an release event after hold
        (SHORT_PRESS, LEFT): {COMMAND: COMMAND_1_SINGLE},
        (DOUBLE_PRESS, LEFT): {COMMAND: COMMAND_1_DOUBLE},
        (TRIPLE_PRESS, LEFT): {COMMAND: COMMAND_1_TRIPLE},
        (LONG_PRESS, LEFT): {COMMAND: COMMAND_1_HOLD},
        (SHORT_PRESS, RIGHT): {COMMAND: COMMAND_2_SINGLE},
        (DOUBLE_PRESS, RIGHT): {COMMAND: COMMAND_2_DOUBLE},
        (TRIPLE_PRESS, RIGHT): {COMMAND: COMMAND_2_TRIPLE},
        (LONG_PRESS, RIGHT): {COMMAND: COMMAND_2_HOLD},
        (SHORT_PRESS, BOTH_BUTTONS): {COMMAND: COMMAND_3_SINGLE},
        (DOUBLE_PRESS, BOTH_BUTTONS): {COMMAND: COMMAND_3_DOUBLE},
        (TRIPLE_PRESS, BOTH_BUTTONS): {COMMAND: COMMAND_3_TRIPLE},
        (LONG_PRESS, BOTH_BUTTONS): {COMMAND: COMMAND_3_HOLD},
        # triggers when operation_mode == command
        # known issue: it seems impossible to know which button being pressed
        # when operation_mode == command
        (ALT_SHORT_PRESS, BUTTON): {COMMAND: COMMAND_TOGGLE, ENDPOINT_ID: 1, ARGS: []},
    }


class RemoteH1DoubleRocker2(XiaomiCustomDevice):
    """Aqara H1 Wireless Remote Double Rocker Version WRS-R02, variant 2."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.remote.b28ac1")],
        ENDPOINTS: {
            1: {
                # "1": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": [ "0x0000", "0x0001", "0x0003" ],
                #   "out_clusters": [ "0x0003", "0x0006" ] }
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            2: {
                # "2": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": [ "0x0003" ],
                #   "out_clusters": [ "0x0003", "0x0006" ] }
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    OnOff.cluster_id,
                ],
            },
            3: {
                # "3": {
                #   "profile_id": 260, "device_type": "0x0103",
                #   "in_clusters": [ "0x0003" ],
                #   "out_clusters": [ "0x0006" ] }
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT_SWITCH,
                INPUT_CLUSTERS: [Identify.cluster_id],
                OUTPUT_CLUSTERS: [OnOff.cluster_id],
            },
        },
    }
    replacement = RemoteH1DoubleRocker1.replacement
    device_automation_triggers = RemoteH1DoubleRocker1.device_automation_triggers
