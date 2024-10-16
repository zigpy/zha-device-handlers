"""Aqara light."""

from zigpy import types as t
from zigpy.profiles import zgp, zha
from zigpy.zcl.clusters.general import (
    Alarms,
    AnalogInput,
    BinaryInput,
    DeviceTemperature,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.smartenergy import Metering
from zigpy.zcl.foundation import ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    LUMI,
    BasicCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
)


class LumiPowerOnBehaviorMode(t.uint8_t):
    """Power on behavior mode."""

    On = 0x00
    """Will be turned on after power outage."""
    PreserveState = 0x01
    """Will keep the state it was before power outage."""
    Off = 0x02
    """Will be turned off after power outage."""


class OppleClusterLight(XiaomiAqaraE1Cluster):
    """Add Opple cluster for power outage memory attribute."""

    attributes = {
        0x0201: ("power_outage_memory", t.Bool, True),
    }


class LumiClusterLight(XiaomiAqaraE1Cluster):
    """Add power on behavior management for Lumi devices."""

    manufacturer_id_override = 4447

    attributes = XiaomiAqaraE1Cluster.attributes.copy()
    attributes[0x0517] = ZCLAttributeDef(
        id=0x0517, type=LumiPowerOnBehaviorMode, is_manufacturer_specific=True,
        name="power_on_behavior"
    )


class LumiLightAcn003(XiaomiCustomDevice):
    """Quirk for Aqara ceiling light L1-350 also known as Xiaomi ZNXDD01LM.

    Provides dimmable light control with color temperature setting.
    This quirk adds support for power on behavior by adding the power_outage_memory attribute.
    """

    signature = {
        MODELS_INFO: [
            ("Aqara", "lumi.light.acn003"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Color.cluster_id,  # 0x0300
                    OppleClusterLight.cluster_id,  # 0xFCC0 - manufacturer specific
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,  # 0x000A
                    Ota.cluster_id,  # 0x0019
                ],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Color.cluster_id,  # 0x0300
                    OppleClusterLight,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,  # 0x000A
                    Ota.cluster_id,  # 0x0019
                ],
            }
        }
    }


class LumiLightAcn014(XiaomiCustomDevice):
    """Quirk for Aqara LED Bulb T1 also known as Xiaomi ZNLDP13LM.

    It identifies itself as lumi.light.acn014, however someone reported there are devices with the same model number
    but identification lumi.light.cwac02.
    Provides dimmable light control with color temperature setting.
    This quirk adds support for power on behavior by adding power_outage_memory attribute.
    """

    signature = {
        MODELS_INFO: [
            (LUMI, "lumi.light.acn014"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,  # 0x0000
                    DeviceTemperature.cluster_id,  # 0x0002
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Alarms.cluster_id,  # 0x0009
                    AnalogInput.cluster_id,  # 0x000C
                    BinaryInput.cluster_id,  # 0x000F
                    MultistateInput.cluster_id,  # 0x0012
                    Color.cluster_id,  # 0x0300
                    Metering.cluster_id,  # 0x0702
                    ElectricalMeasurement.cluster_id,  # 0x0B04
                    OppleClusterLight.cluster_id,  # 0xFCC0 - manufacturer specific
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,  # 0x000A
                    Ota.cluster_id,  # 0x0019
                ],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,  # 0x000C
                ],
                OUTPUT_CLUSTERS: [],
            },
            31: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    AnalogInput.cluster_id,  # 0x000C
                ],
                OUTPUT_CLUSTERS: [],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,  # 0x0021
                ],
            },
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_TEMPERATURE_LIGHT,
                INPUT_CLUSTERS: [
                    BasicCluster,  # 0x0000
                    DeviceTemperature.cluster_id,  # 0x0002
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Alarms.cluster_id,  # 0x0009
                    AnalogInput.cluster_id,  # 0x000C
                    MultistateInput.cluster_id,  # 0x0012
                    Color.cluster_id,  # 0x0300
                    OppleClusterLight,  # 0xFCC0 - manufacturer specific
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,  # 0x000A
                    Ota.cluster_id,  # 0x0019
                ],
            },
            242: {
                PROFILE_ID: zgp.PROFILE_ID,
                DEVICE_TYPE: zgp.DeviceType.PROXY_BASIC,
                INPUT_CLUSTERS: [],
                OUTPUT_CLUSTERS: [
                    GreenPowerProxy.cluster_id,  # 0x0021
                ],
            },
        }
    }


class LumiLightAcn032(XiaomiCustomDevice):
    """Aqara Light T1M (ceiling light with RGB ring).

    This quirk adds support for power on behavior by adding the power_outage_memory attribute, the rest works out
    of the box.

    It MIGHT also work for the Model T1 (acn031) but it has not been tested.
    """

    signature = {
        MODELS_INFO: [("Aqara", "lumi.light.acn032"), ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,  # 0x0000
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Color.cluster_id,  # 0x0300
                    LumiClusterLight.cluster_id,  # 0xFCC0 - manufacturer specific
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,  # 0x000A
                    Ota.cluster_id,  # 0x0019
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Color.cluster_id,  # 0x0300
                    LumiClusterLight.cluster_id,  # 0xFCC0 - manufacturer specific
                ],
                OUTPUT_CLUSTERS: [],
            }
        }
    }
    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    BasicCluster.cluster_id,
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Color.cluster_id,  # 0x0300
                    LumiClusterLight,
                ],
                OUTPUT_CLUSTERS: [
                    Time.cluster_id,  # 0x000A
                    Ota.cluster_id,  # 0x0019
                ],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,  # 0x0003
                    Groups.cluster_id,  # 0x0004
                    Scenes.cluster_id,  # 0x0005
                    OnOff.cluster_id,  # 0x0006
                    LevelControl.cluster_id,  # 0x0008
                    Color.cluster_id,  # 0x0300
                    LumiClusterLight.cluster_id,  # 0xFCC0 - manufacturer specific
                ],
                OUTPUT_CLUSTERS: [],
            }
        }
    }
