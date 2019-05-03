"""Device handler for smartthings tagV4 sensors."""
import logging

import homeassistant.components.zha.const as zha_const
from zigpy.profiles import PROFILES, zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, BinaryInput, Identify, Ota, PollControl)

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.centralite import PowerConfigurationCluster

_LOGGER = logging.getLogger(__name__)

ARRIVAL_SENSOR_DEVICE_TYPE = 0x8000


class FastPollingPowerConfigurationCluster(PowerConfigurationCluster):
    """FastPollingPowerConfigurationCluster."""

    cluster_id = PowerConfigurationCluster.cluster_id
    FREQUENCY = 45
    MINIMUM_CHANGE = 1

    async def configure_reporting(self, attribute, min_interval,
                                  max_interval, reportable_change,
                                  manufacturer=None):
        """Configure reporting."""
        result = await super().configure_reporting(
            PowerConfigurationCluster.BATTERY_VOLTAGE_ATTR,
            self.FREQUENCY,
            self.FREQUENCY,
            self.MINIMUM_CHANGE
        )
        return result

    def _update_attribute(self, attrid, value):
        self.endpoint.device.tracking_bus.listener_event(
            'update_tracking',
            attrid,
            value
        )
        super()._update_attribute(attrid, value)


# stealing this for tracking alerts
class TrackingCluster(LocalDataCluster, BinaryInput):
    """Tracking cluster."""

    cluster_id = BinaryInput.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.tracking_bus.add_listener(self)

    def update_tracking(self, attrid, value):
        """Update tracking info."""
        # prevent unbounded null entries from going into zigbee.db
        self._update_attribute(0, 1)


class SmartThingsTagV4(CustomDevice):
    """Custom device representing smartthings tagV4 sensors."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.tracking_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=12
        #  device_version=0
        #  input_clusters=[0, 1, 3, 15, 32]
        #  output_clusters=[3, 25]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.SIMPLE_SENSOR,
            'input_clusters': [
                Basic.cluster_id,
                FastPollingPowerConfigurationCluster.cluster_id,
                Identify.cluster_id,
                PollControl.cluster_id,
                TrackingCluster.cluster_id
            ],
            'output_clusters': [
                Identify.cluster_id,
                Ota.cluster_id
            ],
        }
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'SmartThings',
                'model': 'tagv4',
                'device_type': ARRIVAL_SENSOR_DEVICE_TYPE,
                'input_clusters': [
                    Basic.cluster_id,
                    FastPollingPowerConfigurationCluster,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TrackingCluster
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Ota.cluster_id
                ],
            }
        },
    }


PROFILES[zha.PROFILE_ID].CLUSTERS[ARRIVAL_SENSOR_DEVICE_TYPE] = (
    [
        Basic.cluster_id,
        Identify.cluster_id,
        PollControl.cluster_id,
        TrackingCluster.cluster_id
    ],
    [
        Identify.cluster_id,
        Ota.cluster_id
    ]
)

if zha.PROFILE_ID not in zha_const.DEVICE_CLASS:
    zha_const.DEVICE_CLASS[zha.PROFILE_ID] = {}

zha_const.DEVICE_CLASS[zha.PROFILE_ID].update(
    {
        ARRIVAL_SENSOR_DEVICE_TYPE: 'device_tracker'
    }
)
