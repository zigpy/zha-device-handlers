"""Centralite 3310S implementation."""
from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import TemperatureMeasurement

from zhaquirks import PowerConfigurationCluster
from zhaquirks.centralite import CENTRALITE
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821
SMRT_THINGS_REL_HUM_CLSTR = 0xFC45


class SmartthingsRelativeHumidityCluster(CustomCluster):
    """Smart Things Relative Humidity Cluster."""

    cluster_id = SMRT_THINGS_REL_HUM_CLSTR
    name = "Smartthings Relative Humidity Measurement"
    ep_attribute = "humidity"
    manufacturer_attributes = {
        # Relative Humidity Measurement Information
        0x0000: ("measured_value", t.int16s)
    }


class CentraLite3310S(CustomDevice):
    """CentraLite3310S custom device implementation."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=770
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 2821, 64581]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [
            (CENTRALITE, "3310-G"),
            (CENTRALITE, "3310-S"),
            (CENTRALITE, "3310"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.TEMPERATURE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    SmartthingsRelativeHumidityCluster.cluster_id,
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
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    SmartthingsRelativeHumidityCluster,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
