"""Linkind Motion Sensors."""

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    Identify,
    Ota,
    PollControl,
    PowerConfiguration,
)
from zigpy.zcl.clusters.homeautomation import Diagnostic
from zigpy.zcl.clusters.security import IasZone

from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.linkind import LinkindBasicCluster

LINKIND_CLUSTER_ID = 0xFC81


class IasZoneLinkind(CustomCluster, IasZone):
    """IasZone cluster for Linkind devices that ignores Alarm_2.

    The sensor uses Alarm_1 for motion and Alarm_2 for brightness. Tamper is apparently also provided by the tamper bit.
    As ZHA only needs either Alarm_1 or Alarm_2 to activate the motion entity, we need to ignore Alarm_2 for now.
    """

    def _update_attribute(self, attrid, value):
        if attrid == IasZone.AttributeDefs.zone_status.id:
            # always set Alarm_2 bit to 0
            value = value & ~IasZone.ZoneStatus.Alarm_2
        super()._update_attribute(attrid, value)


class LinkindD0003(CustomDevice):
    """Linkind ZB-MotionSensor-D0003."""

    signature = {
        MODELS_INFO: [("lk", "ZB-MotionSensor-D0003")],
        # <SimpleDescriptor endpoint=1 profile=260 device_type=1026
        # device_version=1
        # input_clusters=[0, 1, 3, 32, 1280, 2821, 64641]
        # output_clusters=[25]>
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZone.cluster_id,
                    Diagnostic.cluster_id,
                    LINKIND_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.IAS_ZONE,
                INPUT_CLUSTERS: [
                    LinkindBasicCluster,
                    PowerConfiguration.cluster_id,
                    Identify.cluster_id,
                    PollControl.cluster_id,
                    IasZoneLinkind,
                    Diagnostic.cluster_id,
                    LINKIND_CLUSTER_ID,
                ],
                OUTPUT_CLUSTERS: [Ota.cluster_id],
            }
        },
    }
