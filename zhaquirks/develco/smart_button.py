"""Smart button."""

from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl import ClusterType
from zigpy.zcl.clusters.general import OnOff

(
    QuirkBuilder("frient A/S", "SBTZB-110")
    # The button emits `toggle()` commands in addition to attribute updates.
    # The `toggle()` command is unreliable, since the entity state will never match the
    # real state of the button if a command is lost.
    .prevent_default_entity_creation(
        endpoint_id=32,
        cluster_id=OnOff.cluster_id,
        cluster_type=ClusterType.Client,
    )
    .add_to_registry()
)
