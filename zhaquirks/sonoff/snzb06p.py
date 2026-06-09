"""Sonoff SNZB-06 - Zigbee presence sensor."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class IlluminationStatus(t.enum8):
    """Last measureed state of illumination enum."""

    Dark = 0x00
    Light = 0x01


class SonoffFC11Cluster(CustomCluster):
    """Sonoff manufacture specific cluster that provides illuminance."""

    cluster_id = 0xFC11
    ep_attribute = "sonoff_manufacturer"

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        last_illumination_state = ZCLAttributeDef(id=0x2001, type=IlluminationStatus)


(
    QuirkBuilder("SONOFF", "SNZB-06P")
    .replaces(SonoffFC11Cluster, endpoint_id=1)
    .removes(IasZone.cluster_id, endpoint_id=1)
    .add_to_registry()
)
