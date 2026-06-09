"""Linkind Motion Sensors."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.security import IasZone

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


(
    QuirkBuilder("lk", "ZB-MotionSensor-D0003")
    .replaces(LinkindBasicCluster, endpoint_id=1)
    .replaces(IasZoneLinkind, endpoint_id=1)
    .add_to_registry()
)
