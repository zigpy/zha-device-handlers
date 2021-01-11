"""Device handler for centralite ias sensors."""
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, BinaryInput, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import PowerConfigurationCluster

from . import CENTRALITE
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC0F  # decimal = 64527
MANUFACTURER_SPECIFIC_PROFILE_ID = 0xC2DF  # decimal = 49887


class CentraLiteIASSensor(CustomDevice):
    """Custom device representing centralite ias sensors."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
        #  output_clusters=[25]>
        MODELS_INFO: [
            (CENTRALITE, "3300-S"),
            (CENTRALITE, "3315-G"),
            (CENTRALITE, "3315-L"),
            (CENTRALITE, "3315-S"),
            (CENTRALITE, "3315-Seu"),
            (CENTRALITE, "3315"),
            (CENTRALITE, "3320-L"),
            (CENTRALITE, "Contact Sensor-A"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            #  <SimpleDescriptor endpoint=2 profile=49887 device_type=12
            #  device_version=0
            #  input_clusters=[0, 1, 3, 2821, 64527]
            #  output_clusters=[3]>
            2: {
                PROFILE_ID: MANUFACTURER_SPECIFIC_PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
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
                    IasZone.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            },
            2: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        }
    }


class CentraLiteIASSensorV2(CustomDevice):
    """Custom device representing centralite ias sensors."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
        #  output_clusters=[25]>
        MODELS_INFO: CentraLiteIASSensor.signature[MODELS_INFO],
        ENDPOINTS: {
            1: CentraLiteIASSensor.signature[ENDPOINTS][1],
            #  <SimpleDescriptor endpoint=2 profile=49887 device_type=12
            #  device_version=0
            #  input_clusters=[0, 1, 3, 15, 2821, 64527]
            #  output_clusters=[3]>
            2: {
                PROFILE_ID: MANUFACTURER_SPECIFIC_PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    BinaryInput.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        },
    }

    replacement = CentraLiteIASSensor.replacement


class CentraLiteIASSensorV3(CustomDevice):
    """Custom device representing centralite ias sensors."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
        #  output_clusters=[25]>
        MODELS_INFO: CentraLiteIASSensor.signature[MODELS_INFO],
        ENDPOINTS: {
            1: CentraLiteIASSensor.signature[ENDPOINTS][1],
            #  <SimpleDescriptor endpoint=2 profile=49887 device_type=12
            #  device_version=0
            #  input_clusters=[0, 1, 3, 15, 2821]
            #  output_clusters=[3]>
            2: {
                PROFILE_ID: MANUFACTURER_SPECIFIC_PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SIMPLE_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    BinaryInput.cluster_id,
                    PowerConfigurationCluster.cluster_id,
                    Identify.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id],
            },
        },
    }

    replacement = CentraLiteIASSensor.replacement
