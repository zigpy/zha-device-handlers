"""Quirk for GLEDOPTO GL-SD-* dimmers."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import LevelControl

from zhaquirks import NoReplyMixin


class LevelControlNoReply(NoReplyMixin, CustomCluster, LevelControl):
    """LevelControl cluster that does not require default responses."""

    void_input_commands = {cmd.id for cmd in LevelControl.commands_by_name.values()}


(
    QuirkBuilder("GLEDOPTO", "GL-SD-001")
    .applies_to("GLEDOPTO", "GL-SD-003P")
    .replaces(LevelControlNoReply, endpoint_id=1)
    .add_to_registry()
)
