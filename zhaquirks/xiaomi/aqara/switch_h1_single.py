"""Aqara H1 single rocker switch quirks. Also see opple_switch.py for similar double rocker switches."""

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Alarms,
    AnalogInput,
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
    BUTTON,
    CLUSTER_ID,
    COMMAND,
    COMMAND_DOUBLE,
    COMMAND_HOLD,
    COMMAND_SINGLE,
    DEVICE_TYPE,
    DOUBLE_PRESS,
    ENDPOINT_ID,
    ENDPOINTS,
    INPUT_CLUSTERS,
    LONG_PRESS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PRESS_TYPE,
    PROFILE_ID,
    SHORT_PRESS,
    VALUE,
)
from zhaquirks.xiaomi import (
    LUMI,
    AnalogInputCluster,
    BasicCluster,
    DeviceTemperatureCluster,
    ElectricalMeasurementCluster,
    MeteringCluster,
    OnOffCluster,
)
from zhaquirks.xiaomi.aqara.opple_remote import MultistateInputCluster
from zhaquirks.xiaomi.aqara.opple_switch import OppleSwitchCluster

XIAOMI_COMMAND_SINGLE = "41_single"
XIAOMI_COMMAND_DOUBLE = "41_double"
XIAOMI_COMMAND_HOLD = "1_hold"


class AqaraH1SingleRockerBase(CustomDevice):
    """Device automation triggers for the Aqara H1 Single Rocker Switches."""

    device_automation_triggers = {
        (SHORT_PRESS, BUTTON): {
            ENDPOINT_ID: 41,
            CLUSTER_ID: 18,
            COMMAND: XIAOMI_COMMAND_SINGLE,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_SINGLE, VALUE: 1},
        },
        (DOUBLE_PRESS, BUTTON): {
            ENDPOINT_ID: 41,
            CLUSTER_ID: 18,
            COMMAND: XIAOMI_COMMAND_DOUBLE,
            ARGS: {ATTR_ID: 0x0055, PRESS_TYPE: COMMAND_DOUBLE, VALUE: 2},
        },
        (LONG_PRESS, BUTTON): {
            ENDPOINT_ID: 1,
            CLUSTER_ID: 64704,
            COMMAND: XIAOMI_COMMAND_HOLD,
            ARGS: {ATTR_ID: 0x00FC, PRESS_TYPE: COMMAND_HOLD, VALUE: 0},
        },
    }


class AqaraH1SingleRockerSwitchWithNeutral(AqaraH1SingleRockerBase):
    """Aqara H1 Single Rocker Switch (with neutral) (inherits above class for device automation triggers)."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.n1aeu1")],
        ENDPOINTS: {
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
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            31: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            41: {
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

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOffCluster,
                    MultistateInputCluster,
                    MeteringCluster,
                    ElectricalMeasurementCluster,
                    OppleSwitchCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    AnalogInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            31: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
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


class AqaraH1SingleRockerSwitchWithNeutralAlt(AqaraH1SingleRockerSwitchWithNeutral):
    """Aqara H1 Single Rocker Switch (with neutral) signature 2 (inherits above class for replacement + triggers)."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.n1aeu1")],
        ENDPOINTS: {
            #  input_clusters=[0, 2, 3, 4, 5, 6, 18, 64704], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperatureCluster.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    Alarms.cluster_id,
                    MeteringCluster.cluster_id,
                    0x0B04,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
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


class AqaraH1SingleRockerSwitchNoNeutral(AqaraH1SingleRockerBase):
    """Aqara H1 Single Rocker Switch (no neutral) (inherits class for device triggers)."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.l1aeu1")],
        ENDPOINTS: {
            #  input_clusters=[0, 2, 3, 4, 5, 6, 9], output_clusters=[10, 25]
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    DeviceTemperatureCluster.cluster_id,
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

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    DeviceTemperatureCluster.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOffCluster,
                    Alarms.cluster_id,
                    MultistateInputCluster,
                    OppleSwitchCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    MultistateInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [GreenPowerProxy.cluster_id],
            },
        },
    }

class AqaraSingleButtonSwitchWithNeutral(AqaraH1SingleRockerBase):
    """Aqara US Wall Switch with neutral (WS-USC03)."""

    signature = {
        MODELS_INFO: [(LUMI, "lumi.switch.b1naus01")],
        ENDPOINTS: {
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
                    OppleSwitchCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            31: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            41: {
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

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    DeviceTemperature.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOffCluster,
                    MultistateInputCluster,
                    MeteringCluster,
                    ElectricalMeasurementCluster,
                    OppleSwitchCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,
                    Ota.cluster_id,
                ],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    AnalogInputCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            31: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            41: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
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
