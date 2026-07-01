"""Aqara light."""

from typing import Final

from zigpy import types as t
from zigpy.profiles import zgp, zha
from zigpy.quirks.v2 import QuirkBuilder
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
from zigpy.zcl.foundation import BaseAttributeDefs, DataTypeId, ZCLAttributeDef

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    AQARA,
    LUMI,
    BasicCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
)


class LumiPowerOnStateMode(t.enum8):
    """Power on state mode."""

    On = 0x00
    LastState = 0x01
    Off = 0x02


class OppleClusterLight(XiaomiAqaraE1Cluster):
    """Add Opple cluster for power outage memory attribute."""

    class AttributeDefs(XiaomiAqaraE1Cluster.AttributeDefs):
        """Attribute definitions."""

        power_outage_memory: Final = ZCLAttributeDef(
            id=0x0201, type=t.Bool, is_manufacturer_specific=True
        )


class AqaraLightT1M(XiaomiAqaraE1Cluster):
    """Add power on state management for Lumi devices."""

    class AttributeDefs(BaseAttributeDefs):
        """Manufacturer specific attributes."""

        power_on_state = ZCLAttributeDef(
            id=0x0517,
            type=LumiPowerOnStateMode,
            zcl_type=DataTypeId.uint8,
            access="rw",
            is_manufacturer_specific=True,
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


(
    QuirkBuilder(AQARA, "lumi.light.acn032")
    .friendly_name(manufacturer="Aqara", model="Ceiling Light T1M")
    .replaces(AqaraLightT1M)
    .replaces(AqaraLightT1M, endpoint_id=2)
    .enum(
        AqaraLightT1M.AttributeDefs.power_on_state.name,
        LumiPowerOnStateMode,
        AqaraLightT1M.cluster_id,
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .enum(
        AqaraLightT1M.AttributeDefs.power_on_state.name,
        LumiPowerOnStateMode,
        AqaraLightT1M.cluster_id,
        endpoint_id=2,
        translation_key="power_on_state",
        fallback_name="Power on state",
    )
    .add_to_registry()
)
