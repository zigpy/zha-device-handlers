"""Xiaomi aqara button sensor."""
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
from zigpy.zcl.clusters.homeautomation import ElectricalMeasurement

from .. import (
    LUMI,
    POWER_REPORTED,
    BasicCluster,
    ElectricalMeasurementCluster,
    XiaomiCustomDevice,
)
from ... import Bus, CustomCluster
from ...const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    SKIP_CONFIGURATION,
)

_LOGGER = logging.getLogger(__name__)


class AnalogInputCluster(CustomCluster, AnalogInput):
    """Analog input cluster."""

    cluster_id = AnalogInput.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if value is not None and value >= 0:
            self.endpoint.device.power_bus.listener_event(POWER_REPORTED, value)


class Relay(XiaomiCustomDevice):
    """lumi.plug.maus01 device."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.voltage_bus = Bus()
        self.consumption_bus = Bus()
        self.power_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [(LUMI, "lumi.relay.c2acn01")],
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=257
            # device_version=2
            # input_clusters=[0, 3, 4, 5, 1, 2, 10, 6, 16, 2820, 12]
            # output_clusters=[25, 10]>
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
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
                    ElectricalMeasurement.cluster_id,
                    AnalogInput.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            # <SimpleDescriptor endpoint=2 profile=260 device_type=257
            # device_version=2
            # input_clusters=[6, 16, 4, 5]
            # output_clusters=[]>
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    OnOff.cluster_id,
                    BinaryOutput.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
    replacement = {
        SKIP_CONFIGURATION: True,
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
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
                    AnalogInputCluster,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id, Time.cluster_id],
            },
            2: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    OnOff.cluster_id,
                    BinaryOutput.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                ],
                OUTPUT_CLUSTERS: [],
            },
        },
    }
