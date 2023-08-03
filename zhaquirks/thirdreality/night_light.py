"""Third Reality night light zigbee devices."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    MultistateInput,
    OnOff,
    Ota,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.manufacturer_specific import ManufacturerSpecificCluster
from zigpy.zcl.clusters.measurement import (
    OccupancySensing,
    IlluminanceMeasurement,
)

from zhaquirks import (
    Bus,
    LocalDataCluster,
    MotionOnEvent,
    OccupancyWithReset,
    QuickInitDevice,
)
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
    ATTRIBUTE_ID,
    ATTRIBUTE_NAME,
    COMMAND_ATTRIBUTE_UPDATED,
    COMMAND_TRIPLE,
    UNKNOWN,
    VALUE,
    ZHA_SEND_EVENT,
    ZONE_STATUS,
    ZHA_SEND_EVENT,
    ZONE_STATUS_CHANGE_COMMAND,
)

ThirdReality_Specific_CLUSTER_ID = 0xFC00
MOTION_TYPE = 0x0002
ZONE_TYPE = 0x0001
MOTION_REPORTED = "motion_reported"

class OccupancyCluster(OccupancyWithReset):
    """Occupancy cluster."""

class MotionCluster(LocalDataCluster, MotionOnEvent):
    """Motion cluster."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: MOTION_TYPE}
    reset_s: int = 30


_LOGGER = logging.getLogger(__name__)

class ThirdRealitySpecificCluster(CustomCluster):
    """privatecluster, only used to relay ias zone information to ias zone Cluster."""

    cluster_id = ThirdReality_Specific_CLUSTER_ID

    def __init__(self, *args, **kwargs):
        """Init."""
        self._current_state = {}
        super().__init__(*args, **kwargs)

    def _update_attribute(self, attrid, value):
        super()._update_attribute(attrid, value)
        if value is not None and value >= 0:
            self.endpoint.device.motion_bus.listener_event("ias_zone_reported", value)


class ThirdRealitySpecificIasZoneCluster(CustomCluster, IasZone):
    """ias cluster to receive reports that are sent to the private cluster."""

    cluster_id = IasZone.cluster_id
    attributes = IasZone.attributes.copy()
    ZONE_STATUS = 0x0002

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)
        self.endpoint.device.motion_bus.add_listener(self)

    def ias_zone_reported(self, value):
        """ias zone reported."""
        self._update_attribute(self.ZONE_STATUS, value)

class Nightlight(CustomDevice):
    """Custom device for 3RSNL02043Z."""
    def __init__(self, *args, **kwargs):
        """Init."""
        self.motion_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        MODELS_INFO: [("Third Reality, Inc", "3RSNL02043Z")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    MultistateInput.cluster_id,
                    Color.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    0x1000,
                    ThirdReality_Specific_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        },
    }
    replacement = {
        ENDPOINTS: {
            1: {
                DEVICE_TYPE: zha.DeviceType.COLOR_DIMMABLE_LIGHT,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Identify.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    OnOff.cluster_id,
                    LevelControl.cluster_id,
                    MultistateInput.cluster_id,
                    Color.cluster_id,
                    IlluminanceMeasurement.cluster_id,
                    0x1000,
                    ThirdRealitySpecificCluster,
                    ThirdRealitySpecificIasZoneCluster,
                ],
                OUTPUT_CLUSTERS: [
                    Ota.cluster_id,
                ],
            }
        }
    }
