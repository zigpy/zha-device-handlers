"""Eurotronic Spirit Zigbee quirk."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    Ota,
    PowerConfiguration,
    Time,
)
from zigpy.zcl.clusters.hvac import Thermostat

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

from . import EUROTRONIC, ThermostatCluster


class SPZB0001(CustomDevice):
    """Eurotronic Spirit Zigbee device."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=769
        # device_version=1
        # input_clusters=[0, 1, 3, 513, 25, 10]
        # output_clusters=[0, 1, 3, 4, 513, 25, 10]>
        MODELS_INFO: [(EUROTRONIC, "SPZB0001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Thermostat.cluster_id,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Thermostat.cluster_id,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.THERMOSTAT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    ThermostatCluster,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    ThermostatCluster,
                    Ota.cluster_id,
                    Time.cluster_id,
                ],
            }
        }
    }
