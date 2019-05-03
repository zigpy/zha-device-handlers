"""Samjin button device."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic, Identify, Ota, PollControl, PowerConfiguration)
from zigpy.zcl.clusters.measurement import TemperatureMeasurement
from zigpy.zcl.clusters.security import IasZone

DIAGNOSTICS_CLUSTER_ID = 0x0B05  # decimal = 2821

_LOGGER = logging.getLogger(__name__)

SINGLE = 1
DOUBLE = 2
HOLD = 3

CLICK_TYPES = {
    SINGLE: 'single',
    DOUBLE: 'double',
    HOLD: 'hold'
}


class SamjinButton(CustomDevice):
    """Samjin button device."""

    class IASCluster(CustomCluster, IasZone):
        """Occupancy cluster."""

        cluster_id = IasZone.cluster_id

        def handle_cluster_request(self, tsn, command_id, args):
            """Handle a cluster command received on this cluster."""
            if command_id == 0:
                state = args[0] & 3
                event_args = {
                    'press_type': CLICK_TYPES[state],
                    'command_id': command_id,
                    'args': args
                }
                action = "button_{}".format(CLICK_TYPES[state])
                self.listener_event(
                    'zha_send_event',
                    self,
                    action,
                    event_args
                )

    signature = {
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=0
        # input_clusters=[0, 1, 3, 32, 1026, 1280, 2821]
        # output_clusters=[3, 25]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.IAS_ZONE,
            'model': 'button',
            'manufacturer': 'Samjin',
            'input_clusters': [
                Basic.cluster_id,
                PowerConfiguration.cluster_id,
                Identify.cluster_id,
                PollControl.cluster_id,
                TemperatureMeasurement.cluster_id,
                IASCluster.cluster_id,
                DIAGNOSTICS_CLUSTER_ID
            ],
            'output_clusters': [
                Identify.cluster_id,
                Ota.cluster_id
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'profile_id': zha.PROFILE_ID,
                'model': 'button',
                'manufacturer': 'Samjin',
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    TemperatureMeasurement.cluster_id,
                    IASCluster,
                    DIAGNOSTICS_CLUSTER_ID
                ],
                'output_clusters': [
                    Identify.cluster_id,
                    Ota.cluster_id
                ],
            },
        }
    }
