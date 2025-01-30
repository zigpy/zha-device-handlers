"""Quirk for EcoDim 05 two gang dimmer (e.g. HZC Smart Double Dimmer D686-ZG)."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import QuirkBuilder
from zigpy.zcl.clusters.general import OnOff

from zhaquirks import NoReplyMixin


class HzcOnOff(NoReplyMixin, CustomCluster, OnOff):
    """HZC On Off Cluster."""

    void_input_commands = {cmd.id for cmd in OnOff.commands_by_name.values()}


(
    QuirkBuilder("EcoDim BV", "EcoDim-Zigbee 3.0")
    .replace_cluster_occurrences(HzcOnOff, replace_client_instances=False)
    .add_to_registry()
)
