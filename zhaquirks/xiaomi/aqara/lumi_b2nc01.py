"""Aqara E1 double rocker switch quirks. Also see switch_h1_double.py for similar H1 rocker switches."""

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
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import LUMI, BasicCluster, DeviceTemperatureCluster, OnOffCluster
from zhaquirks.xiaomi.aqara.opple_remote import MultistateInputCluster
from zhaquirks.xiaomi.aqara.opple_switch import (
    OppleSwitchCluster,
    XiaomiOpple2ButtonSwitchBase,
)


class AqaraE1DoubleRockerSwitchBase(XiaomiOpple2ButtonSwitchBase):
    """Aqara E1 Double Rocker Switch (with neutral) base class."""

    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    DeviceTemperatureCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOffCluster,
                    MultistateInputCluster,
                    OppleSwitchCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            2: {
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOffCluster,
                    MultistateInputCluster,
                    OppleSwitchCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # Endpoint 3 only reports an OnOff cluster and corresponds to no
            # physical rocker; leave it blank so no light/switch entity is
            # exposed for it (matches zigbee2mqtt, which is left/right only).
            3: {},
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            42: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
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

    # device_automation_triggers are inherited from
    # XiaomiOpple2ButtonSwitchBase: hold is emitted by OppleSwitchCluster on
    # endpoint 1 (endpoints 41/42/51 host only MultistateInput), with single/
    # double presses on 41/42/51.


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
    INPUT_CLUSTERS: _EP1_INPUT_BASE
    + [
        MultistateInputCluster.cluster_id,
        OppleSwitchCluster.cluster_id,
    ],
}

_EP1_SLIM = {
    **_EP1_COMMON_BASE,
    INPUT_CLUSTERS: _EP1_INPUT_BASE
    + [
        Alarms.cluster_id,
    ],
}

_EP2_SLIM = {
    **_EP2_COMMON_BASE,
    INPUT_CLUSTERS: _COMMON_INPUT_CLUSTERS,
}

_EP2_SLIM_CLUSTERS: list = _EP2_SLIM[INPUT_CLUSTERS]

_EP2_FULL = {
    **_EP2_SLIM,
    INPUT_CLUSTERS: _EP2_SLIM_CLUSTERS
    + [
        MultistateInputCluster.cluster_id,
        OppleSwitchCluster.cluster_id,
    ],
}

_GPP_ENDPOINT = {
    242: {
        PROFILE_ID: zgp.PROFILE_ID,
        DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
        INPUT_CLUSTERS: [],
        OUTPUT_CLUSTERS: [
            GreenPowerProxy.cluster_id,
        ],
    },
}

_COMMON_ENDPOINTS = {
    3: _EP2_SLIM,
    **_GPP_ENDPOINT,
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


class AqaraE1DoubleRockerSwitchFull(AqaraE1DoubleRockerSwitchBase):
    """Aqara E1 Double Rocker Switch (with neutral) - Full variant."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.b2nc01")],
        ENDPOINTS: {
            1: _EP1_FULL,
            2: _EP2_FULL,
            **_COMMON_ENDPOINTS,
        },
    }


class AqaraE1DoubleRockerSwitchFullNoEp3(AqaraE1DoubleRockerSwitchBase):
    """Aqara E1 Double Rocker Switch (with neutral) - Full variant, no endpoint 3.

    Some devices report endpoints {1, 2, 41, 42, 51, 242} without endpoint 3,
    which reports only an OnOff cluster and corresponds to no physical rocker.
    This is the signature seen in the ZHA device snapshot for
    ``lumi.switch.b2nc01``.
    """

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.b2nc01")],
        ENDPOINTS: {
            1: _EP1_FULL,
            2: _EP2_FULL,
            **_EXTRA_BUTTON_ENDPOINTS,
            **_GPP_ENDPOINT,
        },
    }


class AqaraE1DoubleRockerSwitchFullButtons(AqaraE1DoubleRockerSwitchFull):
    """Aqara E1 Double Rocker Switch (with neutral) - Full variant with extra endpoints."""

    signature = {
        **AqaraE1DoubleRockerSwitchFull.signature,
        ENDPOINTS: {
            **AqaraE1DoubleRockerSwitchFull.signature[ENDPOINTS],
            **_EXTRA_BUTTON_ENDPOINTS,
        },
    }


class AqaraE1DoubleRockerSwitchSlim(AqaraE1DoubleRockerSwitchBase):
    """Aqara E1 Double Rocker Switch (with neutral) - Slim variant."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.b2nc01")],
        ENDPOINTS: {
            1: _EP1_SLIM,
            2: _EP2_SLIM,
            **_COMMON_ENDPOINTS,
        },
    }


class AqaraE1DoubleRockerSwitchSlimButtons(AqaraE1DoubleRockerSwitchSlim):
    """Aqara E1 Double Rocker Switch (with neutral) - Slim variant with extra endpoints."""

    signature = {
        **AqaraE1DoubleRockerSwitchSlim.signature,
        ENDPOINTS: {
            **AqaraE1DoubleRockerSwitchSlim.signature[ENDPOINTS],
            **_EXTRA_BUTTON_ENDPOINTS,
        },
    }


class AqaraE1DoubleRockerSwitchMixed(AqaraE1DoubleRockerSwitchSlim):
    """Aqara E1 Double Rocker Switch (with neutral) - Mixed variant."""

    signature = {
        **AqaraE1DoubleRockerSwitchSlim.signature,
        ENDPOINTS: {
            **AqaraE1DoubleRockerSwitchSlim.signature[ENDPOINTS],
            2: _EP2_FULL,
        },
    }
