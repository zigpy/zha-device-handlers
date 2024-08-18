"""NodOn pilot wire heating module."""

from zigpy.quirks.v2 import QuirkBuilder, EntityType

from zhaquirks.nodon import (
    NodOnPilotWireCluster,
    NodOnPilotWireMode,
    NODON_PILOT_WIRE_CLUSTER_ID,
    NODON
)

(
    QuirkBuilder(NODON, "SIN-4-FP-21")
    .replaces(NodOnPilotWireCluster)
    .enum(
        attribute_name=NodOnPilotWireCluster.AttributeDefs.pilot_wire_mode.name,
        enum_class=NodOnPilotWireMode,
        cluster_id=NODON_PILOT_WIRE_CLUSTER_ID,
        entity_type=EntityType.STANDARD)
    .add_to_registry()
)
