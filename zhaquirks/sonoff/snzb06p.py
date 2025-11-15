"""Sonoff SNZB-06 - Zigbee presence sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone

SONOFF_CLUSTER_FC11_ID = 0xFC11
SONOFF_CLUSTER_FC57_ID = 0xFC57
ATTR_SONOFF_ILLUMINATION_STATUS = 0x2001


class IlluminationStatus(t.enum8):
    """Last measureed state of illumination enum."""

    Dark = 0x00
    Light = 0x01


class SonoffFC11Cluster(CustomCluster):
    """Sonoff manufacture specific cluster that provides illuminance."""

    cluster_id = SONOFF_CLUSTER_FC11_ID
    ep_attribute = "sonoff_manufacturer"
    attributes = {
        ATTR_SONOFF_ILLUMINATION_STATUS: ("last_illumination_state", IlluminationStatus)
    }


(
    QuirkBuilder("SONOFF", "SNZB-06P")
    .replaces(SonoffFC11Cluster, cluster_id=SONOFF_CLUSTER_FC11_ID, endpoint_id=1)
    .removes(IasZone.cluster_id, endpoint_id=1)
    .add_to_registry()
)
