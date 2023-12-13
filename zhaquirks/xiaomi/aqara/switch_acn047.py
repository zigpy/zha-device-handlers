"""Aqara T2 relay device."""
from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    DeviceTemperature,
    Groups,
    Identify,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.xiaomi import (
    AnalogInputCluster,
    BasicCluster,
    ElectricalMeasurementCluster,
    MeteringCluster,
    XiaomiAqaraE1Cluster,
    XiaomiCustomDevice,
)


class OppleCluster(XiaomiAqaraE1Cluster):
    """Opple cluster."""

    class SwitchType(t.enum8):
        """Switch type."""

        Toggle = 0x01
        Momentary = 0x02
        NoSwitch = 0x03

    class StartupOnOff(t.enum8):
        """Startup mode."""

        On = 0x00
        Previous = 0x01
        Off = 0x02
        Toggle = 0x03

    class DecoupledMode(t.enum8):
        """Decoupled mode."""

        Decoupled = 0x00
        ControlRelay = 0x01

    class SwitchMode(t.enum8):
        """Switch Mode."""

        Power = 0x00
        Pulse = 0x01
        Dry = 0x03

    attributes = {
        0x000A: ("switch_type", SwitchType, True),
        0x0517: ("startup_on_off", StartupOnOff, True),
        0x0200: ("decoupled_mode", DecoupledMode, True),
        0x02D0: ("interlock", t.Bool, True),
        0x0289: ("switch_mode", SwitchMode, True),
        0x00EB: ("pulse_length", t.uint16_t, True),
    }


class AqaraT2Relay(XiaomiCustomDevice):
    """Aqara T2 in-wall relay device."""

    signature = {
        MODELS_INFO: [("Aqara", "lumi.switch.acn047")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 18, 1794, 2820, 64704]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    OppleCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=0
            # device_version=1
            # input_clusters=[3, 4, 5, 6, 18, 64704]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    OppleCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=21 profile=260 device_type=0
            # device_version=1
            # input_clusters=[12]
            # output_clusters=[]>
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [],
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
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    DeviceTemperature.cluster_id,
                    MeteringCluster,
                    ElectricalMeasurementCluster,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Scenes.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    MultistateInput.cluster_id,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [AnalogInputCluster],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
