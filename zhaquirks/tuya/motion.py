"""BlitzWolf IS-3/Tuya motion rechargeable occupancy sensor."""

from typing import Tuple

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
from zigpy.zcl.clusters.general import Basic, Identify, Ota
from zigpy.zcl.clusters.security import IasZone

from . import TuyaManufCluster
from .. import Bus, LocalDataCluster, MotionOnEvent
from ..const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    MOTION_EVENT,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

ZONE_TYPE = 0x0001


class MotionCluster(LocalDataCluster, MotionOnEvent):
    """Tuya Motion Sensor."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Motion_Sensor}
    reset_s = 15


class TuyaManufacturerClusterMotion(TuyaManufCluster):
    """Manufacturer Specific Cluster of the Motion device."""

    def handle_cluster_request(
        self, tsn: int, command_id: int, args: Tuple[TuyaManufCluster.Command]
    ) -> None:
        """Handle cluster request."""
        tuya_cmd = args[0]
        if command_id == 0x0001 and tuya_cmd.command_id == 1027:
            self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)


class TuyaMotion(CustomDevice):
    """BW-IS3 occupancy sensor."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #  endpoint=1 profile=260 device_type=0 device_version=0 input_clusters=[0, 3]
        #  output_clusters=[3, 25]>
        MODELS_INFO: [("_TYST11_i5j6ifxj", "5j6ifxj"), ("_TYST11_7hfcudw5", "hfcudw5")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.ON_OFF_SWITCH,
                INPUT_CLUSTERS: [Basic.cluster_id, Identify.cluster_id],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.OCCUPANCY_SENSOR,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    MotionCluster,
                    TuyaManufacturerClusterMotion,
                ],
                OUTPUT_CLUSTERS: [Identify.cluster_id, Ota.cluster_id],
            }
        }
    }
