"""Quirk for EcoDim 05 two gang dimmer (e.g. HZC Smart Double Dimmer D686-ZG)."""

from zigpy.profiles import zgp, zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl.clusters.general import (
    Basic,
    GreenPowerProxy,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import NoReplyMixin
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)


class HzcOnOff(NoReplyMixin, CustomCluster, OnOff):
    """HZC On Off Cluster."""

    void_input_commands = {cmd.id for cmd in OnOff.commands_by_name.values()}


(
    QuirkBuilder("EcoDim BV", "EcoDim-Zigbee 3.0")
    .replaces(HzcOnOff)
    .replaces(HzcOnOff, endpoint_id=2)
    .add_to_registry()
)
