import asyncio
import logging

import homeassistant.components.zha.const as zha_const
from zigpy.profiles import PROFILES, zha
from zigpy.zcl.clusters.general import LevelControl, Ota, Basic, Groups, OnOff,\
     Identify, Scenes
from zigpy.zcl.clusters.measurement import OccupancySensing
from zhaquirks.xiaomi import BasicCluster, PowerConfigurationCluster,\
     XiaomiCustomDevice
from zhaquirks import CustomCluster
from zhaquirks import Bus, LocalDataCluster

XIAOMI_CLUSTER_ID = 0xFFFF
OCCUPANCY_STATE = 0
ON = 1
OFF = 0

_LOGGER = logging.getLogger(__name__)

class MijaMotion(XiaomiCustomDevice):

    def __init__(self, *args, **kwargs):
        self.battery_size = 9
        self.motionBus = Bus()
        super().__init__(*args, **kwargs)

    class MijaOccupancy(CustomCluster, OccupancySensing):
        cluster_id = OccupancySensing.cluster_id

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._timer_handle = None

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)

            if attrid == OCCUPANCY_STATE and value == ON:
                if self._timer_handle:
                    self._timer_handle.cancel()
                self.endpoint.device.motionBus.listener_event('motion_event')
                loop = asyncio.get_event_loop()
                self._timer_handle = loop.call_later(120, self._turn_off)
                self.listener_event(
                    'zha_send_event',
                    self,
                    'motion',
                    {}
                )

        def _turn_off(self):
            self._timer_handle = None
            self._update_attribute(OCCUPANCY_STATE, OFF)


    signature = {
        # Endpoints:
        #   1: profile=0x104, device_type=DeviceType.DIMMER_SWITCH
        #     Input Clusters:
        #       Basic (0)
        #       Identify (3)
        #       Ota (25)
        #       Manufacturer Specific (65535)
        #     Output Clusters:
        #       Basic (0)
        #       Identify (3)
        #       Groups (4)
        #       Scenes (5)
        #       On/Off (6)
        #       Level control (8)
        #       Ota (25)
        1: {
            'manufacturer': 'LUMI',
            'model': 'lumi.sensor_motion',
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.DIMMER_SWITCH,
            'input_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Ota.cluster_id,
                XIAOMI_CLUSTER_ID
            ],
            'output_clusters': [
                Basic.cluster_id,
                Identify.cluster_id,
                Groups.cluster_id,
                Scenes.cluster_id,
                OnOff.cluster_id,
                LevelControl.cluster_id,
                Ota.cluster_id,
            ],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'manufacturer': 'LUMI',
                'model': 'lumi.sensor_motion',
                'device_type': zha.DeviceType.OCCUPANCY_SENSOR,
                'input_clusters': [
                    Identify.cluster_id,
                    BasicCluster,
                    PowerConfigurationCluster,
                    MijaOccupancy,
                ],
                'output_clusters': [
                    BasicCluster,
                    Scenes.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        },
    }
