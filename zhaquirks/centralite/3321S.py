"""Centralite 3321S quirk."""
# pylint disable=C0103
from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PollControl
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.centralite import (
    CentraLiteAccelCluster, PowerConfigurationCluster)

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821
MANUFACTURER_SPECIFIC_PROFILE_ID = 0xC2DF  # decimal = 49887
MANUFACTURER_SPECIFIC_CLUSTER_ID = 0xFC0F  # decimal = 64527


class CentraLite3321S(CustomDevice):
    """CentraLite3321S custom device implementation."""

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        #  device_version=0
        #  input_clusters=[0, 1, 3, 1026, 1280, 32, 2821, 64514]
        #  output_clusters=[25]>
        1: {
            'manufacturer': 'CentraLite',
            'model': '3321-S',
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.IAS_ZONE,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                PollControl.cluster_id,
                TemperatureMeasurement.cluster_id,
                IasZone.cluster_id,
                DIAGNOSTICS_CLUSTER_ID,
                CentraLiteAccelCluster.cluster_id
            ],
            'output_clusters': [
                Ota.cluster_id
            ],
        },
        #  <SimpleDescriptor endpoint=2 profile=49887 device_type=12
        #  device_version=0
        #  input_clusters=[0, 1, 3, 2821, 64527]
        #  output_clusters=[3]>
        2: {
            'manufacturer': 'CentraLite',
            'model': '3321-S',
            'profile_id': MANUFACTURER_SPECIFIC_PROFILE_ID,
            'device_type': zha.DeviceType.SIMPLE_SENSOR,
            'input_clusters': [
                Basic.cluster_id,
                PowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                DIAGNOSTICS_CLUSTER_ID,
                MANUFACTURER_SPECIFIC_CLUSTER_ID
            ],
            'output_clusters': [
                Identify.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'CentraLite',
                'model': '3321-S',
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    CentraLiteAccelCluster
                ],
                'output_clusters': [
                    Ota.cluster_id
                ],
            },
            2: {
                'manufacturer': 'CentraLite',
                'model': '3321-S',
                'input_clusters': [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    MANUFACTURER_SPECIFIC_CLUSTER_ID
                ],
                'output_clusters': [
                    Identify.cluster_id
                ],
            }
        },
    }
