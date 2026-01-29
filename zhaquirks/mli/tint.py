"""Tint remote."""

from zigpy.quirks import CustomCluster
from zigpy.quirks.v2 import CustomDeviceV2, QuirkBuilder
from zigpy.zcl import ClusterType, foundation
from zigpy.zcl.clusters.general import Basic, Scenes

from zhaquirks import Bus, LocalDataCluster

TINT_SCENE_ATTR = 0x4005


class TintRemoteScenesCluster(LocalDataCluster, Scenes):
    """Tint remote cluster."""

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

        self.endpoint.device.scene_bus.add_listener(self)

    def change_scene(self, value):
        """Change scene attribute to new value."""
        self._update_attribute(self.attributes_by_name["current_scene"].id, value)


class TintRemoteBasicCluster(CustomCluster, Basic):
    """Tint remote cluster."""

    def handle_cluster_general_request(self, hdr, args, *, dst_addressing=None):
        """Send write_attributes value to TintRemoteSceneCluster."""
        if hdr.command_id != foundation.GeneralCommand.Write_Attributes:
            return

        attr = args[0][0]
        if attr.attrid != TINT_SCENE_ATTR:
            return

        value = attr.value.value
        self.endpoint.device.scene_bus.listener_event("change_scene", value)


class TintRemote(CustomDeviceV2):
    """Tint remote quirk."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.scene_bus = Bus()
        super().__init__(*args, **kwargs)


(
    QuirkBuilder("MLI", "ZBT-Remote-ALL-RGBW")
    .device_class(TintRemote)
    .replaces(TintRemoteBasicCluster, endpoint_id=1)
    .adds(TintRemoteScenesCluster, cluster_type=ClusterType.Client, endpoint_id=1)
    .add_to_registry()
)
