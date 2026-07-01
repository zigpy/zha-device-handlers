"""Aqara H1 double rocker switch quirks. Also see opple_switch.py for similar double rocker switches."""

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
from zhaquirks.xiaomi import LUMI
from zhaquirks.xiaomi.aqara.opple_switch import (
    OppleSwitchCluster,
    XiaomiOpple2ButtonSwitch1,
    XiaomiOpple2ButtonSwitch3,
    XiaomiOpple2ButtonSwitch4,
    XiaomiOpple2ButtonSwitchBase,
)


class AqaraH1DoubleRockerSwitchWithNeutral1(XiaomiOpple2ButtonSwitchBase):
    """Aqara H1 Double Rocker Switch (with neutral). Based on signature 1."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.n2aeu1")],
        ENDPOINTS: XiaomiOpple2ButtonSwitch1.signature[ENDPOINTS],
    }


class AqaraH1DoubleRockerSwitchWithNeutral3(XiaomiOpple2ButtonSwitchBase):
    """Aqara H1 Double Rocker Switch (with neutral). Based on signature 3."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.n2aeu1")],
        ENDPOINTS: XiaomiOpple2ButtonSwitch3.signature[ENDPOINTS],
    }


class AqaraH1DoubleRockerSwitchWithNeutral4(XiaomiOpple2ButtonSwitchBase):
    """Aqara H1 Double Rocker Switch (with neutral). Based on signature 4."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.n2aeu1")],
        ENDPOINTS: XiaomiOpple2ButtonSwitch4.signature[ENDPOINTS],
    }


class AqaraH1DoubleRockerSwitchNoNeutral(XiaomiOpple2ButtonSwitchBase):
    """Aqara H1 Double Rocker Switch (no neutral)."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.l2aeu1")],
        ENDPOINTS: {
            # input_clusters=[0, 2, 3, 4, 5, 6, 18, 64704], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    OppleSwitchCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            # input_clusters=[0, 3, 4, 5, 6, 18, 64704], output_clusters=[]
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    OppleSwitchCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            42: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # input_clusters=[18], output_clusters=[]
            51: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    MultistateInput.cluster_id,
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


class AqaraH1DoubleRockerSwitchNoNeutralAlt(XiaomiOpple2ButtonSwitchBase):
    """Aqara H1 Double Rocker Switch (no neutral) alternative signature."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.l2aeu1")],
        ENDPOINTS: {
            # input_clusters=[0, 2, 3, 4, 5, 6, 9], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Alarms.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            # input_clusters=[0, 3, 4, 5, 6], output_clusters=[]
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
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
