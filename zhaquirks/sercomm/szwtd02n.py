"""Device handler for Sercomm SZ-WTD02N flood sensor and XHS2-SE contact sensor."""

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks import PowerConfigurationCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.sercomm import SERCOMM


class SercommPowerConfiguration(PowerConfigurationCluster):
    """Sercomm power configuration cluster for flood sensor."""

    MAX_VOLTS = 3.2
    MIN_VOLTS = 2.1


class SZWTD02N(CustomDevice):
    """Custom device representing Sercomm SZ-WTD02N flood sensor."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 1280, 32, 2821]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [(SERCOMM, "SZ-WTD02N_SF")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    SercommPowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    SercommPowerConfiguration,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }

class XHS2SE(CustomDevice):
   """Custom device representing XHS2-SE by Sercomm Corp."""

   signature = {
       #  <SimpleDescriptor endpoint=1 profile=260 device_type=0x0402
       #  input_clusters=["0x0000", "0x0001", "0x0003","0x0020","0x0402", "0x0500", "0x0b05","0xfc01","0xfc02"]
       #  output_clusters=["0x0003","0x0019"]>
       MODELS_INFO: [(SERCOMM, "XHS2-SE")],
       ENDPOINTS: {
           1: {
               PROFILE_ID: zha.PROFILE_ID,
               DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
               INPUT_CLUSTERS: [
                   Basic.cluster_id,
                   SercommPowerConfiguration.cluster_id,
                   Identify.cluster_id,
                   PollControl.cluster_id,
                   TemperatureMeasurement.cluster_id,
                   IasZone.cluster_id,
                   Diagnostic.cluster_id,
               ],
               OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
           }
       },
   }

   replacement = {
       ENDPOINTS: {
           1: {
               INPUT_CLUSTERS: [
                   Basic.cluster_id,
                   SercommPowerConfiguration,
                   Identify.cluster_id,
                   PollControl.cluster_id,
                   TemperatureMeasurement.cluster_id,
                   IasZone.cluster_id,
                   Diagnostic.cluster_id,
               ],
               OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
           }
       }
   }
