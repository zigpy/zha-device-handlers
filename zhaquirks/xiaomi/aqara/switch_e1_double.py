"""Aqara E1 double rocker switch quirks. Adapted from switch_h1_double.py."""

from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import (
    Alarms,
    Basic,
    DeviceTemperature,
    GreenPowerProxy,
    Groups,
    Identify,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
    Time,
)

from zhaquirks.const import (
    ARGS,
    ATTR_ID,
    BUTTON_1,
    BUTTON_2,
    CLUSTER_ID,
    COMMAND_BUTTON_DOUBLE,
    COMMAND_BUTTON_HOLD,
    COMMAND_BUTTON_SINGLE,
    COMMAND_DOUBLE,
    COMMAND_SINGLE,
    DEVICE_TYPE,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    VALUE,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    DeviceTemperatureCluster,
    OnOffCluster,
    XiaomiCustomDevice,
)
from zhaquirks.xiaomi.aqara.opple_remote import MultistateInputCluster
from zhaquirks.xiaomi.aqara.opple_switch import BOTH_BUTTONS, OppleSwitchCluster


# Helper functions for trigger definitions
def _trigger(endpoint, press, value):
    return {
        ENDPOINT_ID: endpoint,
        CLUSTER_ID: 18,
        ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: press, VALUE: value},
    }


def _hold_trigger(endpoint, value=0):
    return {
        ENDPOINT_ID: endpoint,
        CLUSTER_ID: 0xFCC0,
        ARGS: {ATTR_ID: 0x00FC, VALUE: value},
    }


# Shared replacement clusters
_REPLACEMENT_INPUT_BASE = [
    BasicCluster,
    Identify.cluster_id,
    Groups.cluster_id,
    Scenes.cluster_id,
    OnOffCluster,
    MultistateInputCluster,
    OppleSwitchCluster,
]

class AqaraE1DoubleRockerSwitchWithNeutralBase(XiaomiCustomDevice):
    """Aqara E1 Double Rocker Switch (with neutral) base class."""

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [DeviceTemperatureCluster] + _REPLACEMENT_INPUT_BASE,
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: _REPLACEMENT_INPUT_BASE,
                OUTPUT_CLUSTERS: [],
            },
            3: {
            },
            # Button 1 endpoint
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # Button 2 endpoint
            42: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # Both buttons endpoint
            51: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,
                ],
            },
        },
    }

    device_automation_triggers = {
        # Button 1 triggers
        (COMMAND_BUTTON_SINGLE, BUTTON_1): _trigger(41, COMMAND_SINGLE, 1),
        (COMMAND_BUTTON_DOUBLE, BUTTON_1): _trigger(41, COMMAND_DOUBLE, 2),
        (COMMAND_BUTTON_HOLD, BUTTON_1): _hold_trigger(41, False),
        # Button 2 triggers
        (COMMAND_BUTTON_SINGLE, BUTTON_2): _trigger(42, COMMAND_SINGLE, 1),
        (COMMAND_BUTTON_DOUBLE, BUTTON_2): _trigger(42, COMMAND_DOUBLE, 2),
        (COMMAND_BUTTON_HOLD, BUTTON_2): _hold_trigger(42, False),
        # Both buttons triggers
        (COMMAND_BUTTON_SINGLE, BOTH_BUTTONS): _trigger(51, COMMAND_SINGLE, 1),
        (COMMAND_BUTTON_DOUBLE, BOTH_BUTTONS): _trigger(51, COMMAND_DOUBLE, 2),
        (COMMAND_BUTTON_HOLD, BOTH_BUTTONS): _hold_trigger(51, 0),
    }


# Shared signature components to reduce duplication
_COMMON_INPUT_CLUSTERS = [
    Basic.cluster_id,
    Identify.cluster_id,
    Groups.cluster_id,
    Scenes.cluster_id,
    OnOff.cluster_id,
]

_EP2_COMMON_BASE = {
    PROFILE_ID: zha.PROFILE_ID,
    DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
    OUTPUT_CLUSTERS: [],
}

_EP1_COMMON_BASE = {
    **_EP2_COMMON_BASE,
    OUTPUT_CLUSTERS: [
        Time.cluster_id,
        Ota.cluster_id,
    ],
}

_EP1_INPUT_BASE = [DeviceTemperature.cluster_id] + _COMMON_INPUT_CLUSTERS

_EP1_FULL = {
    **_EP1_COMMON_BASE,
    INPUT_CLUSTERS: _EP1_INPUT_BASE + [
        MultistateInputCluster.cluster_id,
        OppleSwitchCluster.cluster_id,
    ],
}

_EP1_SLIM = {
    **_EP1_COMMON_BASE,
    INPUT_CLUSTERS: _EP1_INPUT_BASE + [
        Alarms.cluster_id,
    ],
}

_EP2_SLIM = {
    **_EP2_COMMON_BASE,
    INPUT_CLUSTERS: _COMMON_INPUT_CLUSTERS,
}

_EP2_FULL = {
    **_EP2_SLIM,
    INPUT_CLUSTERS: _EP2_SLIM[INPUT_CLUSTERS] + [
        MultistateInputCluster.cluster_id,
        OppleSwitchCluster.cluster_id,
    ],
}

_COMMON_ENDPOINTS = {
    3: _EP2_SLIM,
    242: {
        PROFILE_ID: zgp.PROFILE_ID,
        DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
        INPUT_CLUSTERS: [],
        OUTPUT_CLUSTERS: [
            GreenPowerProxy.cluster_id,
        ],
    },
}

_BUTTON_ENDPOINT = {
    PROFILE_ID: zha.PROFILE_ID,
    DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
    INPUT_CLUSTERS: [MultistateInput.cluster_id],
    OUTPUT_CLUSTERS: [],
}

_EXTRA_BUTTON_ENDPOINTS = {
    41: _BUTTON_ENDPOINT,
    42: _BUTTON_ENDPOINT,
    51: _BUTTON_ENDPOINT,
}


class AqaraE1DoubleRockerSwitchWithNeutral_Full(
    AqaraE1DoubleRockerSwitchWithNeutralBase
):
    """Aqara E1 Double Rocker Switch (with neutral) - Full variant."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.b2nc01")],
        ENDPOINTS: {
            1: _EP1_FULL,
            2: _EP2_FULL,
            **_COMMON_ENDPOINTS,
        },
    }


class AqaraE1DoubleRockerSwitchWithNeutral_Full_Buttons(
    AqaraE1DoubleRockerSwitchWithNeutral_Full
):
    """Aqara E1 Double Rocker Switch (with neutral) - Full variant with extra endpoints."""

    signature = {
        **AqaraE1DoubleRockerSwitchWithNeutral_Full.signature,
        ENDPOINTS: {
            **AqaraE1DoubleRockerSwitchWithNeutral_Full.signature[ENDPOINTS],
            **_EXTRA_BUTTON_ENDPOINTS,
        },
    }


class AqaraE1DoubleRockerSwitchWithNeutral_Slim(
    AqaraE1DoubleRockerSwitchWithNeutralBase
):
    """Aqara E1 Double Rocker Switch (with neutral) - Slim variant."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.b2nc01")],
        ENDPOINTS: {
            1: _EP1_SLIM,
            2: _EP2_SLIM,
            **_COMMON_ENDPOINTS,
        },
    }


class AqaraE1DoubleRockerSwitchWithNeutral_Slim_Buttons(
    AqaraE1DoubleRockerSwitchWithNeutral_Slim
):
    """Aqara E1 Double Rocker Switch (with neutral) - Slim variant with extra endpoints."""

    signature = {
        **AqaraE1DoubleRockerSwitchWithNeutral_Slim.signature,
        ENDPOINTS: {
            **AqaraE1DoubleRockerSwitchWithNeutral_Slim.signature[ENDPOINTS],
            **_EXTRA_BUTTON_ENDPOINTS,
        },
    }


class AqaraE1DoubleRockerSwitchWithNeutral_Mixed(
    AqaraE1DoubleRockerSwitchWithNeutral_Slim
):
    """Aqara E1 Double Rocker Switch (with neutral) - Mixed variant."""

    signature = {
        **AqaraE1DoubleRockerSwitchWithNeutral_Slim.signature,
        ENDPOINTS: {
            **AqaraE1DoubleRockerSwitchWithNeutral_Slim.signature[ENDPOINTS],
            2: _EP2_FULL,
        },
    }



