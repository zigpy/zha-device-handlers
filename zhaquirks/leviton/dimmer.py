"""Module for Leviton dimmers."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks import NoReplyMixin


class LevitonLevelControl(NoReplyMixin, CustomCluster, LevelControl):
    """Leviton LevelControl cluster."""

    void_input_commands = {cmd.id for cmd in LevelControl.commands_by_name.values()}


(
    QuirkBuilder()
    .applies_to("LEVITON", "ZK700-D0W")
    .applies_to("Leviton Inc", "LU107")
    .replaces(LevitonLevelControl)
    .add_to_registry()
)
