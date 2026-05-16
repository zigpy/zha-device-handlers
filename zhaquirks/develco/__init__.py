"""Quirks for Develco Products A/S."""

from typing import Final

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import CustomDeviceV2
import zigpy.types as t
from zigpy.zcl import foundation
from zigpy.zcl.clusters.security import IasZone, ZoneStatus

from zhaquirks import PowerConfigurationCluster

FRIENT = "frient A/S"
DEVELCO = "Develco Products A/S"


class DevelcoPowerConfiguration(PowerConfigurationCluster):
    """Common use power configuration cluster."""

    MIN_VOLTS = 2.6  # old 2.1
    MAX_VOLTS = 3.0  # old 3.2


class DevelcoIasZone(CustomCluster, IasZone):
    """IAS Zone, patched to fix a bug with the status change notification command."""

    class ClientCommandDefs(IasZone.ClientCommandDefs):
        """IAS Zone command definitions."""

        status_change_notification: Final = foundation.ZCLCommandDef(
            id=0x00,
            schema={
                "zone_status": ZoneStatus,
                "extended_status": t.bitmap8,
                # These two should not be optional
                "zone_id?": t.uint8_t,
                "delay?": t.uint16_t,
            },
            direction=foundation.Direction.Client_to_Server,
        )


class ManufacturerDeviceV2(CustomDeviceV2):
    """Custom device class used to remap cluster IDs in requests."""

    async def request(
        self,
        *args,
        **kwargs,
    ):
        """Remap cluster IDs for clusters that substitute for others."""
        # this method is always called with kwargs
        endpoint_id = kwargs["src_ep"]
        cluster_id = kwargs["cluster"]

        # ignore ZDO and narrow down to manufacturer specific clusters
        if endpoint_id != 0 and cluster_id >= 0xFC00:
            cluster = self.endpoints[endpoint_id].in_clusters.get(cluster_id)
            substitution_cluster = getattr(cluster, "SUBSTITUTION_FOR", None)

            if substitution_cluster:
                kwargs["cluster"] = t.ClusterId(substitution_cluster)

        return await super().request(
            *args,
            **kwargs,
        )
