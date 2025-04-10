"""Door/Windows sensors."""

from typing import Final

from zigpy.quirks.v2 import QuirkBuilder
import zigpy.types as t
from zigpy.zcl.clusters.general import BinaryInput
from zigpy.zcl.clusters.security import IasZone
from zigpy.zcl.foundation import Direction, ZCLCommandDef, ZoneStatus

from zhaquirks import PowerConfigurationCluster


class DevelcoPowerConfiguration(PowerConfigurationCluster):
    """Power configuration cluster."""

    MIN_VOLTS = 2.5  # advised voltage to replace batteries, device will blink red when this state hits.
    MAX_VOLTS = 3.0


class DevelcoIASZone(IasZone):
    """IAS Zone, patched to fix a bug with the status change notification command."""

    class ClientCommandDefs(IasZone.ClientCommandDefs):
        """IAS Zone command definitions."""

        status_change_notification: Final = ZCLCommandDef(
            id=0x00,
            schema={
                "zone_status": ZoneStatus,
                "extended_status": t.bitmap8,
                # These two should not be optional
                "zone_id?": t.uint8_t,
                "delay?": t.uint16_t,
            },
            direction=Direction.Client_to_Server,
        )


(
    QuirkBuilder("frient A/S", "WISZB-131")
    .applies_to("Develco Products A/S", "WISZB-120")
    .applies_to("frient A/S", "WISZB-120")
    .applies_to("Develco Products A/S", "WISZB-121")
    .applies_to("frient A/S", "WISZB-121")
    .replaces(DevelcoIASZone, endpoint_id=35)
    .replaces(DevelcoPowerConfiguration, endpoint_id=35)
    # The binary input cluster is a duplicate
    .prevent_default_entity_creation(endpoint_id=35, cluster_id=BinaryInput.cluster_id)
    .add_to_registry()
)
