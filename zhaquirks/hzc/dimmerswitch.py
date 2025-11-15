"""Quirk for HZC Dimmer-Switch-ZB3.0 (e.g. D688-ZG)."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import OnOff

from zhaquirks import NoReplyMixin


class HzcOnOff(NoReplyMixin, CustomCluster, OnOff):
    """HZC On Off Cluster."""

    void_input_commands = {cmd.id for cmd in OnOff.commands_by_name.values()}


(
    QuirkBuilder("HZC", "Dimmer-Switch-ZB3.0")
    .applies_to("Shyugj", "Dimmer-Switch-ZB3.0")
    .replaces(HzcOnOff, endpoint_id=1)
    .add_to_registry()
)
