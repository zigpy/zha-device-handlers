"""TS0210 vibration sensor."""

from typing import Optional, Tuple, Union
from zhaquirks.tuya import TuyaLocalCluster, TuyaManufCluster, TuyaManufClusterAttributes
from zhaquirks.tuya.ts0601_smoke import TuyaIasZone

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Identify, Ota, PowerConfiguration, Time
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, LocalDataCluster, MotionOnEvent, _Motion
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODEL,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    MOTION_EVENT

)
import logging
import json
_LOGGER = logging.getLogger(__name__)

ZONE_TYPE = 0x0001


class TuyaManufacturerClusterVibration( TuyaManufCluster, MotionOnEvent):
    """Manufacturer Specific Cluster of the Motion device."""
    cluster_id= IasZone.cluster_id
    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Vibration_Movement_Sensor}
    _LOGGER.info('initializing tuya vibes')
    reset_s = 15

    def handle_cluster_request(
        self,
        hdr: foundation.ZCLHeader,
        args: Tuple[TuyaManufCluster.Command],
        *,
        dst_addressing: Optional[
            Union[t.Addressing.Group, t.Addressing.IEEE, t.Addressing.NWK]
        ] = None,
    ) -> None:
        """Handle cluster request."""
        _LOGGER.info("Manufacturer Event")
        self.endpoint.device.motion_bus.listener_event(MOTION_EVENT)


class TuyaVibration(CustomDevice):
    """Tuya vibration sensor."""

    def __init__(self, *args, **kwargs):
        """Init device."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        #   SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=1026, device_version=0, input_clusters=[0, 10, 1, 1280], output_clusters=[25])
        MODEL: "TS0210",
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0402,#zha.DeviceType.IAS_ZONE,  
                INPUT_CLUSTERS: [Basic.cluster_id, Time.cluster_id, PowerConfiguration.cluster_id, IasZone.cluster_id],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: 0x0402,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Time.cluster_id,
                    TuyaManufacturerClusterVibration
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        }
    }
