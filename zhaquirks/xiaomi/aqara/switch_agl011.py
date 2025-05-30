"""Aqara H2 EU dimmer switch"""

from zigpy import types as t
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
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
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ZHA_SEND_EVENT,
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

    class Sensitivity(t.enum8):
        """Rotation sensitivity."""

        Low = 0x02D0  # 720
        Medium = 0x0168  # 360
        High = 0x00B4  # 180

    class Phase(t.enum8):
        """Startup mode."""

        Forward = 0x0000
        Reverse = 0x0001

    class MinBrightness(t.uint8_t):
        """Minimum brightness."""

        def __init__(self, value: int = 0):
            """Initialize with a default value."""
            super().__init__(value)
            if not (0 <= value <= 99):
                raise ValueError("Minimum brightness must be between 0 and 100.")

    class MaxBrightness(t.uint8_t):
        """Maximum brightness."""

        def __init__(self, value: int = 100):
            """Initialize with a default value."""
            super().__init__(value)
            if not (1 <= value <= 100):
                raise ValueError("Maximum brightness must be between 1 and 100.")

    attributes = {
        0x0234: ("sensitivity", Sensitivity, True),
        0x030A: ("phase", Phase, True),
        0x0515: ("min_brightness", MinBrightness, True),
        0x0516: ("max_brightness", MaxBrightness, True),
    }

    def _update_attribute(self, attrid, value):
        """Handle attribute updates."""
        super()._update_attribute(attrid, value)
        if attrid in self.attributes:
            self.listener_event(
                ZHA_SEND_EVENT,
                {
                    "type": self.attributes[attrid][0],
                    "value": value,
                },
            )


class AqaraDimmerSwitchH2EU(XiaomiCustomDevice):
    """Aqara H2 EU dimmer switch (KD-R01D)"""

    signature = {
        MODELS_INFO: [("Aqara", "lumi.switch.agl011")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=0
            # device_version=1
            # input_clusters=[0, 3, 4, 5, 6, 8, 18, 1794, 2820, 64704]
            # output_clusters=[10, 25]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    MultistateInput.cluster_id,
                    Metering.cluster_id,
                    ElectricalMeasurement.cluster_id,
                    OppleCluster.cluster_id
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=0
            # device_version=1
            # input_clusters=[64704]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=0
            # device_version=1
            # input_clusters=[64704]
            # output_clusters=[]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
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
            # <SimpleDescriptor endpoint=71 profile=260 device_type=0
            # device_version=1
            # input_clusters=[64704]
            # output_clusters=[]>
            71: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            # <SimpleDescriptor endpoint=72 profile=260 device_type=0
            # device_version=1
            # input_clusters=[64704]
            # output_clusters=[]>
            72: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
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
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    MultistateInput.cluster_id,
                    MeteringCluster,
                    ElectricalMeasurementCluster,
                    OppleCluster,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            21: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [AnalogInputCluster],
                OUTPUT_CLUSTERS: [],
            },
            71: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
            72: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [OppleCluster.cluster_id],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
