"""Samjin Multi 2019 Refresh Quirk."""
from zigpy.quirks import CustomDevice
from zigpy.quirks.smartthings import SmartThingsAccelCluster
from zigpy.zcl.clusters.general import (
    Basic, Identify, Ota, PollControl, PowerConfiguration)
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class SmartthingsMultiPurposeSensor2019(CustomDevice):
    """Samjin multi device."""

    signature = {
        'models_info': [
            ('Samjin', 'multi')
        ],
        'endpoints': {
            # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
            # device_version=0 input_clusters=[0, 1, 3, 32, 1026, 1280,
            # 2821, 64514]
            # output_clusters=[3, 25]>
            1: {
                'profile_id': 0x0104,
                'device_type': 0x0402,
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    SmartThingsAccelCluster.cluster_id
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Ota.cluster_id
                ],
            }
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IasZone.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    SmartThingsAccelCluster
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Ota.cluster_id
                ],
            }
        }
    }
