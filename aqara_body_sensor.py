import asyncio

from zigpy.zcl.clusters.measurement import IlluminanceMeasurement,\
    OccupancySensing
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.general import Basic, PowerConfiguration,\
    Identify, Ota
from zigpy.quirks import CustomDevice, CustomCluster
from zigpy.profiles import zha

import homeassistant.components.zha.const as zha_const

XIAOMI_CLUSTER_ID = 0xFFFF

if zha.PROFILE_ID not in zha_const.DEVICE_CLASS:
        zha_const.DEVICE_CLASS[zha.PROFILE_ID] = {}
zha_const.DEVICE_CLASS[zha.PROFILE_ID].update({
    zha.DeviceType.OCCUPANCY_SENSOR: 'binary_sensor'
})


class AqaraBodySensor(CustomDevice):
    class OccupancyCluster(CustomCluster, OccupancySensing):
        cluster_id = OccupancySensing.cluster_id

        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self._timer_handle = None

        def _update_attribute(self, attrid, value):
            super()._update_attribute(attrid, value)
            if attrid == 0 and value == 1:
                if self._timer_handle:
                    self._timer_handle.cancel()

                loop = asyncio.get_event_loop()
                self._timer_handle = loop.call_later(60, self._turn_off)

        def _turn_off(self):
            self._timer_handle = None
            self._update_attribute(0, 0)

    signature = {
        #  <SimpleDescriptor endpoint=1 profile=260 device_type=263 device_version=1 input_clusters=[0, 65535, 1030, 1024, 1280, 1, 3] output_clusters=[0, 25]>
        1: {
            'profile_id': zha.PROFILE_ID,
            'device_type': zha.DeviceType.OCCUPANCY_SENSOR,
            'input_clusters': [
                Basic.cluster_id,
                XIAOMI_CLUSTER_ID,
                OccupancySensing.cluster_id,
                IlluminanceMeasurement.cluster_id,
                IasZone.cluster_id,
                PowerConfiguration.cluster_id,
                Identify.cluster_id],
            'output_clusters': [
                Basic.cluster_id,
                Ota.cluster_id],
        },
    }

    replacement = {
        'endpoints': {
            1: {
                'input_clusters': [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    OccupancyCluster],
            }
        },
    }
