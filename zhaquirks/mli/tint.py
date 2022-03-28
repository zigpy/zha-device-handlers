"""Tint remote."""
import logging

from zigpy.profiles import zha
from zigpy.quirks import CustomCluster, CustomDevice
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    Scenes,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)

TINT_SCENE_ATTR = 0x4005

_LOGGER = logging.getLogger(__name__)


class TintRemoteScenesCluster(LocalDataCluster, Scenes):
    """Tint remote cluster."""

    cluster_id = Scenes.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

        self.endpoint.device.scene_bus.add_listener(self)

    def change_scene(self, value):
        """Change scene attribute to new value."""
        self._update_attribute(self.attributes_by_name["current_scene"].id, value)


class TintRemoteBasicCluster(CustomCluster, Basic):
    """Tint remote cluster."""

    cluster_id = Basic.cluster_id

    def __init__(self, *args, **kwargs):
        """Init."""
        super().__init__(*args, **kwargs)

    def handle_cluster_general_request(self, hdr, args, *, dst_addressing=None):
        """Send write_attributes value to TintRemoteSceneCluster."""
        if hdr.command_id != foundation.GeneralCommand.Write_Attributes:
            return

        attr = args[0][0]
        if attr.attrid != TINT_SCENE_ATTR:
            return

        value = attr.value.value
        self.endpoint.device.scene_bus.listener_event("change_scene", value)


class TintRemote(CustomDevice):
    """Tint remote quirk."""

    def __init__(self, *args, **kwargs):
        """Init."""
        self.scene_bus = Bus()
        super().__init__(*args, **kwargs)

    signature = {
        # endpoint=1 profile=260 device_type=2048 device_version=1 input_clusters=[0, 3, 4096]
        # output_clusters=[0, 3, 4, 5, 8, 25, 768, 4096]
        MODELS_INFO: [("MLI", "ZBT-Remote-ALL-RGBW")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    LightLink.cluster_id,  # 4096
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    OnOff.cluster_id,  # 6
                    LevelControl.cluster_id,  # 8
                    Ota.cluster_id,  # 25
                    Color.cluster_id,  # 768
                    LightLink.cluster_id,  # 4096
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.COLOR_CONTROLLER,
                INPUT_CLUSTERS: [
                    TintRemoteBasicCluster,  # 0
                    Identify.cluster_id,  # 3
                    LightLink.cluster_id,  # 4096
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    TintRemoteScenesCluster,  # 5
                    OnOff.cluster_id,  # 6
                    LevelControl.cluster_id,  # 8
                    Ota.cluster_id,  # 25
                    Color.cluster_id,  # 768
                    LightLink.cluster_id,  # 4096
                ],
            },
        },
    }
