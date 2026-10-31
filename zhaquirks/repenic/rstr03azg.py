"""Repenic RS921-ZG."""

from zigpy import types as t
from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder


class RemoteMode(t.enum8):
    """Remote mode enum."""

    Load_mode = 0x00
    Remote_mode = 0x01


class RepenicRemoteModeCluster(CustomCluster):
    """Private cluster 0xE00B for remote mode."""

    cluster_id = 0xE00B
    name = "Repenic Remote Mode"
    ep_attribute = "repenic_remote_mode"
    attributes = {
        0x0000: ("remote_mode", RemoteMode, False),
    }


(
    QuirkBuilder("Repenic Ltd.", "RS-T03AZG")
    .applies_to("Repenic Ltd.", "RS-R03AZG")
    .replaces(RepenicRemoteModeCluster)
    .enum(
        attribute_name="remote_mode",
        enum_class=RemoteMode,
        cluster_id=RepenicRemoteModeCluster.cluster_id,
        attribute_initialized_from_cache=True,
        translation_key="remote_mode",
        fallback_name="Remote mode",
    )
    .add_to_registry()
)
