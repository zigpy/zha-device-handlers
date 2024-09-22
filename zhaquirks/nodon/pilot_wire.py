"""NodOn pilot wire heating module."""

from zigpy.quirks.v2 import EntityType, QuirkBuilder

from zhaquirks.nodon import (
    NODON,
    NODON_PILOT_WIRE_CLUSTER_ID,
    NodOnPilotWireCluster,
    NodOnPilotWireMode,
)

(
    QuirkBuilder(NODON, "SIN-4-FP-21")
    .replaces(NodOnPilotWireCluster)
    .enum(
        attribute_name=NodOnPilotWireCluster.AttributeDefs.pilot_wire_mode.name,
        enum_class=NodOnPilotWireMode,
        cluster_id=NODON_PILOT_WIRE_CLUSTER_ID,
        entity_type=EntityType.STANDARD,
    )
    .add_to_registry()
)
