"""Xiaomi lumi.plug plug."""
import logging

from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    AnalogInput,
    Basic,
    BinaryOutput,
    DeviceTemperature,
    Groups,
    Identify,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)

from zhaquirks import Bus
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)
from zhaquirks.xiaomi import (
    LUMI,
    AnalogInputCluster,
    BasicCluster,
    ElectricalMeasurementCluster,
    XiaomiCustomDevice,
)

_LOGGER = logging.getLogger(__name__)


class Plug(XiaomiCustomDevice):
    """lumi.plug plug."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.voltage_bus = Bus()
        self.consumption_bus = Bus()
        self.power_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(LUMI, "lumi.plug")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=81
            # device_version=1
            # input_clusters=[0, 4, 3, 6, 16, 5, 10, 1, 2]
            # output_clusters=[25, 10]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    DeviceTemperature.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    BinaryOutput.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=9
            # device_version=1
            # input_clusters=[12]
            # output_clusters=[12, 4]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [AnalogInput.cluster_id, Groups.cluster_id],
            },
            # <SimpleDescriptor endpoint=3 profile=260 device_type=83
            # device_version=1
            # input_clusters=[12]
            # output_clusters=[12]>
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [AnalogInput.cluster_id],
            },
        },
    }
    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    BasicCluster,
                    PowerConfiguration.cluster_id,
                    DeviceTemperature.cluster_id,
                    Groups.cluster_id,
                    Identify.cluster_id,
                    OnOff.cluster_id,
                    Scenes.cluster_id,
                    BinaryOutput.cluster_id,
                    Time.cluster_id,
                    ElectricalMeasurementCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.MAIN_POWER_OUTLET,
                INPUT_CLUSTERS: [AnalogInputCluster],
                OUTPUT_CLUSTERS: [AnalogInput.cluster_id, Groups.cluster_id],
            },
            3: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.METER_INTERFACE,
                INPUT_CLUSTERS: [AnalogInput.cluster_id],
                OUTPUT_CLUSTERS: [AnalogInput.cluster_id],
            },
        },
    }
