"""Tint remote."""

from zigpy.profiles import zha
from zigpy.zcl import foundation
from zigpy.zcl.clusters.general import (
    Basic,
    Groups,
    Identify,
    LevelControl,
    OnOff,
    Ota,
    PowerConfiguration,
    Scenes,
    Time,
)
from zigpy.zcl.clusters.lighting import Color
from zigpy.zcl.clusters.lightlink import LightLink

from zhaquirks import Bus, LocalDataCluster
from zhaquirks.clusters import CustomCluster
from zhaquirks.const import (
    DEVICE_TYPE,
    ENDPOINTS,
    INPUT_CLUSTERS,
    MODELS_INFO,
    OUTPUT_CLUSTERS,
    PROFILE_ID,
)
from zhaquirks.legacy import CustomDevice
from zhaquirks.tuya import TuyaNewManufCluster

TINT_SCENE_ATTR = 0x4005


class TintRemoteE003Cluster(CustomCluster):
    """Tuya cluster 0xE003 of the Tint remote (unused, kept for signature parity)."""

    cluster_id = 0xE003


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


class TintRemoteTS1001(TintRemote):
    """Müller Licht Tint remote, Tuya variant (_TZ3000_bdbb0fon / TS1001).

    Same remote as :class:`TintRemote` but with a Tuya module. The device does
    not report the Color cluster in its output clusters even though it sends
    ``move_to_color_temp``/``move_to_color`` commands, so ZHA would otherwise
    not decode them. The replacement adds ``Color`` to the output clusters and
    keeps the scene handling of the MLI variant.
    """

    signature = {
        # SizePrefixedSimpleDescriptor(endpoint=1, profile=260, device_type=260,
        #   device_version=1, input_clusters=[0, 1, 3, 4, 4096, 61184],
        #   output_clusters=[0, 3, 4, 5, 6, 8, 10, 25, 4096, 57347])
        MODELS_INFO: [("_TZ3000_bdbb0fon", "TS1001")],
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    PowerConfiguration.cluster_id,  # 1
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    LightLink.cluster_id,  # 4096
                    TuyaNewManufCluster.cluster_id,  # 0xEF00
                ],
                OUTPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    Scenes.cluster_id,  # 5
                    OnOff.cluster_id,  # 6
                    LevelControl.cluster_id,  # 8
                    Time.cluster_id,  # 0x000A
                    Ota.cluster_id,  # 25
                    LightLink.cluster_id,  # 4096
                    TintRemoteE003Cluster.cluster_id,  # 0xE003
                ],
            },
        },
    }

    replacement = {
        ENDPOINTS: {
            1: {
                PROFILE_ID: zha.PROFILE_ID,
                DEVICE_TYPE: zha.DeviceType.DIMMER_SWITCH,
                INPUT_CLUSTERS: [
                    Basic.cluster_id,  # 0
                    PowerConfiguration.cluster_id,  # 1
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    LightLink.cluster_id,  # 4096
                    TuyaNewManufCluster,  # 0xEF00
                ],
                OUTPUT_CLUSTERS: [
                    TintRemoteBasicCluster,  # 0 (client->server writes land here)
                    Identify.cluster_id,  # 3
                    Groups.cluster_id,  # 4
                    TintRemoteScenesCluster,  # 5
                    OnOff.cluster_id,  # 6
                    LevelControl.cluster_id,  # 8
                    Time.cluster_id,  # 0x000A
                    Ota.cluster_id,  # 25
                    Color.cluster_id,  # 768 (added so incoming color cmds are decoded)
                    LightLink.cluster_id,  # 4096
                    TintRemoteE003Cluster,  # 0xE003
                ],
            },
        },
    }
