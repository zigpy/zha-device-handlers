"""Device handler for IKEA of Sweden TRADFRI remote control."""
from zigpy.profiles import zha
from zigpy.zcl.clusters.general import (
    Basic, Identify, Groups, OnOff, PowerConfiguration, Alarms, Ota
)
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.quirks import CustomDevice
from . import LightLinkCluster
from .. import DoublingPowerConfigurationCluster

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821


class IkeaTradfriMotion(CustomDevice):
    """Custom device representing IKEA of Sweden TRADFRI remote control."""

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=2128
        # device_version=2
        # input_clusters=[0, 1, 3, 9, 2821, 4096]
        # output_clusters=[3, 4, 6, 25, 4096]>
        'models_info': [
            ('IKEA of Sweden', 'TRADFRI motion sensor')
        ],
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': zha.DeviceType.ON_OFF_SENSOR,
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    LightLink.cluster_id
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id
                ],
            },
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'device_type': zha.DeviceType.ON_OFF_SENSOR,
                'input_clusters': [
                    Basic.cluster_id,
                    DoublingPowerConfigurationCluster,
                    Identify.cluster_id,
                    Alarms.cluster_id,
                    DIAGNOSTICS_CLUSTER_ID,
                    LightLinkCluster
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id
                ],
            }
        },
    }
