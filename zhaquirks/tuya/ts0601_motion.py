"""BlitzWolf IS-3/Tuya motion rechargeable occupancy sensor."""

from typing import Dict, Optional, Tuple, Union

from zigpy.profiles import zha
from zigpy.quirks import CustomDevice
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import Basic, Groups, Identify, Ota, Scenes, Time
from zigpy.zcl.clusters.measurement import (
    OccupancySensing,
    RelativeHumidity,
    TemperatureMeasurement,
)
from zigpy.zcl.clusters.security import IasZone

from zhaquirks import Bus, LocalDataCluster, MotionOnEvent
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    MOTION_EVENT,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.tuya import (
    DPToAttributeMapping,
    TuyaLocalCluster,
    TuyaManufCluster,
    TuyaNewManufCluster,
)

ZONE_TYPE = 0x0001


class TuyaOccupancySensing(OccupancySensing, TuyaLocalCluster):
    """Tuya local OccupancySensing cluster."""


class TuyaTemperatureMeasurement(TemperatureMeasurement, TuyaLocalCluster):
    """Tuya local TemperatureMeasurement cluster."""


class TuyaRelativeHumidity(RelativeHumidity, TuyaLocalCluster):
    """Tuya local RelativeHumidity cluster."""


class NeoMotionManufCluster(TuyaNewManufCluster):
    """Neo manufacturer cluster."""

    attributes = TuyaNewManufCluster.attributes.copy()
    attributes.update(
        {
            0xEF0D: ("dp_113", t.enum8, True),  # ramdom attribute ID
        }
    )

    dp_to_attribute: Dict[int, DPToAttributeMapping] = {
        101: DPToAttributeMapping(
            TuyaOccupancySensing.ep_attribute,
            "occupancy",
        ),
        104: DPToAttributeMapping(
            TuyaTemperatureMeasurement.ep_attribute,
            "measured_value",
            lambda x: x * 10,
        ),
        105: DPToAttributeMapping(
            TuyaRelativeHumidity.ep_attribute,
            "measured_value",
            lambda x: x * 100,
        ),
        113: DPToAttributeMapping(
            TuyaNewManufCluster.ep_attribute,
            "dp_113",
        ),
    }

    data_point_handlers = {
        101: "_dp_2_attr_update",
        104: "_dp_2_attr_update",
        105: "_dp_2_attr_update",
        113: "_dp_2_attr_update",
    }


class MotionCluster(LocalDataCluster, MotionOnEvent):
    """Tuya Motion Sensor."""

    _CONSTANT_ATTRIBUTES = {ZONE_TYPE: IasZone.ZoneType.Motion_Sensor}
    reset_s = 15


class TuyaManufacturerClusterMotion(TuyaManufCluster):
    """Manufacturer Specific Cluster of the Motion device."""

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
        tuya_cmd = args[0]
        self.debug("handle_cluster_request--> hdr: %s, args: %s", hdr, args)
        if hdr.command_id == 0x0001 and tuya_cmd.command_id == 1027:
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


class NeoMotion(CustomDevice):
    """NAS-PD07 occupancy sensor."""

    signature = {
        #  endpoint=1 profile=260 device_type=81 device_version=0 input_clusters=[0, 4, 5, 61184]
        #  output_clusters=[10, 25]>
        MODELS_INFO: [
            ("_TZE200_7hfcudw5", "TS0601"),
            ("_TZE200_ppuj1vem", "TS0601"),
        ],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.SMART_PLUG,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    NeoMotionManufCluster.cluster_id,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
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
                    Groups.cluster_id,
                    Scenes.cluster_id,
                    NeoMotionManufCluster,
                    TuyaOccupancySensing,
                    TuyaTemperatureMeasurement,
                    TuyaRelativeHumidity,
                ],
                OUTPUT_CLUSTERS: [Time.cluster_id, Ota.cluster_id],
            }
        }
    }
