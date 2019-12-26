"""Device handler for smartthings moistureV4 sensor."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import Basic, BinaryInput, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

from . import SMART_THINGS
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class CustomIasZone(CustomCluster, IasZone):
    """Custom IasZone cluster."""

    MOISTURE_TYPE = 0x002A
    ZONE_TYPE = 0x0001

    def _update_attribute(self, attrid, value):
        if attrid == self.ZONE_TYPE:
            super()._update_attribute(attrid, self.MOISTURE_TYPE)
        else:
            super()._update_attribute(attrid, value)


class SmartThingsMoistureV4(CustomDevice):
    """SmartThingsMoistureV4."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 15, 1026, 1280, 32]
        #  output_clusters=[25]>
        MODELS_INFO: [(SMART_THINGS, "moisturev4")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    BinaryInput.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    CustomIasZone,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
