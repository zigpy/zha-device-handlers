"""Sonoff SWV - Zigbee smart water valve."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import EntityPlatform, EntityType, QuirkBuilder
import zigpy.types as t
from zigpy.zcl.foundation import BaseAttributeDefs, ZCLAttributeDef


class ValveState(t.enum8):
    """Water valve state."""

    Normal = 0
    Water_Shortage = 1
    Water_Leakage = 2
    Water_Shortage_And_Leakage = 3


class EwelinkCluster(CustomCluster):
    """Ewelink specific cluster."""

    cluster_id = 0xFC11

    class AttributeDefs(BaseAttributeDefs):
        """Attribute definitions."""

        water_valve_state = ZCLAttributeDef(
            id=0x500C,
            type=ValveState,
        )

    @property
    def _is_manuf_specific(self):
        return False


(
    QuirkBuilder("SONOFF", "SWV")
    .replaces(EwelinkCluster)
    .enum(
        EwelinkCluster.AttributeDefs.water_valve_state.name,
        ValveState,
        EwelinkCluster.cluster_id,
        entity_platform=EntityPlatform.SENSOR,
        entity_type=EntityType.DIAGNOSTIC,
    )
    .add_to_registry()
)
