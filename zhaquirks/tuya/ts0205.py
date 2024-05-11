import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.lightlink import LightLink
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import TuyaManufClusterAttributes

_LOGGER = logging.getLogger(__name__)

TUYA_SMOKE_DETECTED_ATTR = 0x0401  # [0]/[1] [Detected]/[Clear]!


class TuyaSmokeDetectorCluster(TuyaManufClusterAttributes):
    """Manufacturer Specific Cluster of the TS0205 smoke detector."""

    attributes = {
        TUYA_SMOKE_DETECTED_ATTR: ("smoke_detected", t.uint8_t, True),
    }

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if attrid == TUYA_SMOKE_DETECTED_ATTR:
            if value == 0:
                self.endpoint.ias_zone.update_attribute(
                    IasZone.AttributeDefs.zone_status.id, IasZone.ZoneStatus.Alarm_1
                )
            else:
                self.endpoint.ias_zone.update_attribute(
                    IasZone.AttributeDefs.zone_status.id, 0
                )
        else:
            _LOGGER.warning(
                "[0x%04x:%s:0x%04x] unhandled attribute: 0x%04x",
                self.endpoint.device.nwk,
                self.endpoint.endpoint_id,
                self.cluster_id,
                attrid,
            )


class TuyaIasZone(LocalDataCluster, IasZone):
    """IAS Zone."""

    _CONSTANT_ATTRIBUTES = {
        IasZone.AttributeDefs.zone_type.id: IasZone.ZoneType.Fire_Sensor
    }


class TuyaSmokeDetectorTS0205(CustomDevice):
    """Tuya smoke sensor PST-YG500A"""

    signature = {
        MODELS_INFO: [("_TZ3210_up3pngle", "TS0205")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    IasZone.cluster_id,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    OnOff.cluster_id,
                    Time.cluster_id,
                    Ota.cluster_id,
                    LightLink.cluster_id,
                ],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    TuyaIasZone,
                    TuyaSmokeDetectorCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Ota.cluster_id,
                ],
            }
        }
    }
