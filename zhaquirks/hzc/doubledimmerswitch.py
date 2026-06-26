"""Quirk for EcoDim 05 two gang dimmer (e.g. HZC Smart Double Dimmer D686-ZG)."""

from zigpy.zcl.clusters.general import OnOff

from zhaquirks import NoReplyMixin
from zhaquirks.builder import QuirkBuilder
from zhaquirks.clusters import CustomCluster


class HzcOnOff(NoReplyMixin, CustomCluster, OnOff):
    """HZC On Off Cluster."""

    void_input_commands = {cmd.id for cmd in OnOff.commands_by_name.values()}


(
    QuirkBuilder("EcoDim BV", "EcoDim-Zigbee 3.0")
    .applies_to("EcoDim BV", "Eco-Dim.05 Zigbee")
    .replace_cluster_occurrences(HzcOnOff, replace_client_instances=False)
    .add_to_registry()
)
