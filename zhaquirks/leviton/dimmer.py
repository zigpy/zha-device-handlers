"""Module for Leviton dimmers."""

from zigpy.zcl.clusters.general import LevelControl

from zhaquirks import NoReplyMixin
from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster


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
