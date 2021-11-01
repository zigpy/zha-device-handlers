"""Salus SP600 plug."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
)
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.smartenergy import Metering

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.salus import COMPUTIME


class TemperatureMeasurementCluster(CustomCluster, TemperatureMeasurement):
    """Temperature cluster that divides value by 2."""

    cluster_id = TemperatureMeasurement.cluster_id
    ATTR_ID = 0

    def _update_attribute(self, attrid, value):
        # divide values by 2
        if attrid == self.ATTR_ID:
            value = value / 2
        super()._update_attribute(attrid, value)


class SP600(CustomDevice):
    """Salus SP600 smart plug."""

    signature = {
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=9, profile=260 device_type=81
            # device_version=0
            # input_clusters=[0, 1, 3, 4, 5, 6, 1026, 1794, 64513]
            # output_clusters=[25]>
            9: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Metering.cluster_id,
                    0xFC01,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
        MODELS_INFO: [(COMPUTIME, "SP600")],
    }

    replacement = {
        ENDPOINTS: {
            9: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TemperatureMeasurementCluster,
                    Metering.cluster_id,
                    0xFC01,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }


class SPE600(CustomDevice):
    """Salus SPE600 smart plug."""

    signature = {
        ENDPOINTS: {
            # <SimpleDescriptor endpoint=9, profile=260 device_type=81
            # device_version=0
            # input_clusters=[0, 1, 3, 4, 5, 6, 1026, 1794, 64513]
            # output_clusters=[25]>
            9: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    Metering.cluster_id,
                    0xFC01,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
        MODELS_INFO: [(COMPUTIME, "SPE600")],
    }

    replacement = {
        ENDPOINTS: {
            9: {
                PROFILE_ID: 0x0104,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    TemperatureMeasurementCluster,
                    Metering.cluster_id,
                    0xFC01,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }
