"""Netvox device."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Commissioning, Identify, PollControl
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

from ..const import DEVICE_TYPE, ENDPOINTS, INPUT_CLUSTERS, OUTPUT_CLUSTERS, PROFILE_ID

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class CustomPowerConfigurationCluster(PowerConfigurationCluster):
    """Custom PowerConfigurationCluster."""

    cluster_id = PowerConfigurationCluster.cluster_id
    MIN_VOLTS = 2.1
    MAX_VOLTS = 3.0


class Z308E3ED(CustomDevice):
    """Netvox Z308E3ED."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 21, 1280, 32, 2821]
        #  output_clusters=[]>
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomPowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                    Commissioning.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [],
            }
        }
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    CustomPowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                    Commissioning.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                ]
            }
        }
    }
